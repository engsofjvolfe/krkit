from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, session, flash, make_response
import os
import secrets
import qrcode
from io import BytesIO
import base64
import string
import random
from dotenv import load_dotenv
import subprocess
from flask_session import Session
import json
from functools import wraps

load_dotenv()

app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)

# Configuração da sessão do servidor
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

MUSIC_DIR = os.getenv('MUSIC_DIR')
OWNER_PASSWORD = os.getenv('OWNER_PASSWORD')
SESSIONS_FILE = 'sessions.json'

# Variáveis globais para armazenar QR codes únicos e temporários
unique_qr = None
temporary_qr_codes = set()
invalid_qr_codes = set()  # Para armazenar QR codes inválidos após o logout
owner_authenticated = False

def save_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump({
            'unique_qr': unique_qr,
            'temporary_qr_codes': list(temporary_qr_codes),
            'invalid_qr_codes': list(invalid_qr_codes)
        }, f)
    print("Sessões salvas")

def load_sessions():
    global unique_qr, temporary_qr_codes, invalid_qr_codes
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'r') as f:
            data = json.load(f)
            unique_qr = data.get('unique_qr')
            temporary_qr_codes = set(data.get('temporary_qr_codes', []))
            invalid_qr_codes = set(data.get('invalid_qr_codes', []))
    print("Sessões carregadas")

def generate_random_string(length=10):
    letters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(letters) for i in range(length))
    print(f"String gerada: {random_string}")
    return random_string

def check_owner_authentication(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        print(f"Verificando autenticação do proprietário: {owner_authenticated}")
        if not owner_authenticated:
            flash('Acesso negado. O proprietário encerrou a sessão.')
            print("Proprietário não autenticado. Redirecionando para a página de aviso.")
            return redirect(url_for('owner_disconnected'))
        return func(*args, **kwargs)
    return decorated_function

@app.route('/songs', methods=['GET'])
@check_owner_authentication
def list_songs():
    print("Entrando na função list_songs")
    print(f"session['access_granted']: {session.get('access_granted')}")
    print(f"session: {session}")
    if 'access_granted' in session and session['access_granted']:
        songs = [f for f in os.listdir(MUSIC_DIR) if os.path.isfile(os.path.join(MUSIC_DIR, f))]
        print(f"Músicas encontradas: {songs}")
        return jsonify(songs)
    print("Acesso negado ao listar músicas")
    return jsonify({'status': 'error', 'message': 'Access denied'}), 403

@app.route('/play', methods=['POST'])
@check_owner_authentication
def play_song():
    print("Entrando na função play_song")
    print(f"session['access_granted']: {session.get('access_granted')}")
    print(f"session: {session}")
    if 'access_granted' in session and session['access_granted']:
        song = request.json.get('song')
        if song and os.path.isfile(os.path.join(MUSIC_DIR, song)):
            song_path = os.path.join(MUSIC_DIR, song)
            print(f"Tocando a música: {song}")
            subprocess.run(['vlc', '--fullscreen', '--play-and-exit', song_path])
            return jsonify({'status': 'success', 'message': f'Playing {song}'})
        else:
            print("Música não encontrada")
            return jsonify({'status': 'error', 'message': 'Song not found'}), 404
    print("Acesso negado ao tocar música")
    return jsonify({'status': 'error', 'message': 'Access denied'}), 403

@app.route('/')
@check_owner_authentication
def index():
    print("Entrando na função index")
    print(f"session['access_granted']: {session.get('access_granted')}")
    print(f"session: {session}")
    if 'access_granted' in session and session['access_granted']:
        print("Acesso permitido à página inicial")
        return send_from_directory(app.static_folder, 'index.html')
    print("Redirecionando para a página de login")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global owner_authenticated
    print("Entrando na função login")
    if request.method == 'POST':
        print("Método POST na função login")
        if request.form['password'] == OWNER_PASSWORD:
            session['owner_authenticated'] = True
            owner_authenticated = True
            print("Senha correta, redirecionando para owner")
            return redirect(url_for('owner'))
        else:
            flash('Senha incorreta. Tente novamente.')
            print("Senha incorreta")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/owner', methods=['GET', 'POST'])
def owner():
    global unique_qr, temporary_qr_codes, owner_authenticated
    print("Entrando na função owner")
    qr_code = None
    access_type = None

    if request.method == 'POST':
        print("Método POST na função owner")
        if 'password' in request.form:
            if request.form['password'] == OWNER_PASSWORD:
                session['owner_authenticated'] = True
                owner_authenticated = True
                print("Senha correta, redirecionando para owner")
                return redirect(url_for('owner'))
            else:
                flash('Senha incorreta. Tente novamente.')
                print("Senha incorreta")
                return redirect(url_for('login'))

        if 'owner_authenticated' not in session:
            print("Proprietário não autenticado, redirecionando para login")
            return redirect(url_for('login'))

        access_type = request.form.get('access')
        print(f"Tipo de acesso solicitado: {access_type}")
        if access_type == 'unrestricted':
            unique_qr = generate_random_string()
            qr_code = generate_qr_code(unique_qr)
            print(f"QR Code irrestrito gerado: {unique_qr}")
        elif access_type == 'temporary':
            while True:
                temporary_qr = generate_random_string()
                if temporary_qr not in temporary_qr_codes and temporary_qr not in invalid_qr_codes:
                    temporary_qr_codes.add(temporary_qr)
                    break
            qr_code = generate_qr_code(temporary_qr)
            print(f"QR Code temporário gerado: {temporary_qr}")
        save_sessions()
        print("Sessões salvas")
        return render_template('owner.html', qr_code=qr_code, access_type=access_type)

    if 'owner_authenticated' not in session:
        print("Proprietário não autenticado, redirecionando para login")
        return redirect(url_for('login'))

    return render_template('owner.html', qr_code=qr_code, access_type=access_type)

@app.route('/access/<access_code>', methods=['GET'])
def grant_access(access_code):
    global unique_qr

    print(f"Tentando conceder acesso com o código: {access_code}")

    if access_code in invalid_qr_codes:
        print(f"Código inválido: {access_code}")
        return render_template('invalid_qr.html', redirect_to_login=False)

    if access_code == unique_qr:
        session['access_granted'] = True
        session['qr_code_access'] = unique_qr  # Track access granted via QR code
        print(f"Acesso concedido com QR Code irrestrito: {access_code}")
        response = make_response(redirect(url_for('index')))
        response.set_cookie('access_granted', 'true', httponly=True, secure=True)
        return response
    elif access_code in temporary_qr_codes:
        session['access_granted'] = True
        session['qr_code_access'] = access_code  # Track access granted via QR code
        temporary_qr_codes.remove(access_code)
        save_sessions()
        print(f"Acesso concedido com QR Code temporário: {access_code}")
        response = make_response(redirect(url_for('index')))
        response.set_cookie('access_granted', 'true', httponly=True, secure=True)
        return response
    else:
        print(f"Código inválido: {access_code}")
        return render_template('invalid_qr.html', redirect_to_login=False)

@app.route('/logout', methods=['GET'])
def logout():
    global unique_qr, owner_authenticated
    print("Entrando na função logout")
    owner_authenticated = False
    session.pop('access_granted', None)
    session.pop('owner_authenticated', None)
    session.pop('qr_code_access', None)  # Remove QR code access tracking
    if unique_qr:
        invalid_qr_codes.add(unique_qr)
        unique_qr = None
    invalid_qr_codes.update(temporary_qr_codes)
    temporary_qr_codes.clear()
    save_sessions()
    flash('Sessão encerrada com sucesso.')
    print("Sessão encerrada e cookies excluídos")

    response = make_response(redirect(url_for('login')))
    response.delete_cookie('access_granted')
    response.delete_cookie('owner_authenticated')
    return response

@app.route('/shutdown', methods=['POST'])
def shutdown():
    print("Entrando na função shutdown")
    save_sessions()
    shutdown_server()
    print("Servidor encerrado com sucesso")
    return 'Servidor encerrado com sucesso.'

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/owner_disconnected')
def owner_disconnected():
    return render_template('owner_disconnected.html')


@app.route('/test_session', methods=['GET'])
def test_session():
    return f"Session: {dict(session)}\nCookies: {request.cookies}"

def generate_qr_code(data):
    print(f"Gerando QR Code para os dados: {data}")
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url_for('grant_access', access_code=data, _external=True))
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    print("QR Code gerado")
    return img_str

def clear_sessions_on_startup():
    global unique_qr, temporary_qr_codes, invalid_qr_codes
    unique_qr = None
    temporary_qr_codes.clear()
    invalid_qr_codes.clear()
    save_sessions()
    print("Sessões limpas no início")

if __name__ == '__main__':
    clear_sessions_on_startup()
    load_sessions()
    app.run(host='0.0.0.0', port=5000)
