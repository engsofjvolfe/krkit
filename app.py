from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, session, flash
import os
import secrets
import qrcode
from io import BytesIO
import base64
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)

MUSIC_DIR = os.getenv('MUSIC_DIR')
OWNER_PASSWORD = os.getenv('OWNER_PASSWORD')

# Variáveis globais para armazenar QR codes únicos e temporários
unique_qr = None
temporary_qr_codes = set()

def generate_random_string(length=10):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

@app.route('/songs', methods=['GET'])
def list_songs():
    if 'access_granted' in session and session['access_granted']:
        songs = [f for f in os.listdir(MUSIC_DIR) if os.path.isfile(os.path.join(MUSIC_DIR, f))]
        return jsonify(songs)
    return jsonify({'status': 'error', 'message': 'Access denied'}), 403

@app.route('/play', methods=['POST'])
def play_song():
    if 'access_granted' in session and session['access_granted']:
        song = request.json.get('song')
        if song and os.path.isfile(os.path.join(MUSIC_DIR, song)):
            song_path = os.path.join(MUSIC_DIR, song)
            os.system(f'vlc --one-instance --playlist-enqueue "{song_path}"')
            return jsonify({'status': 'success', 'message': f'Playing {song}'})
        else:
            return jsonify({'status': 'error', 'message': 'Song not found'}), 404
    return jsonify({'status': 'error', 'message': 'Access denied'}), 403

@app.route('/')
def index():
    if 'access_granted' in session and session['access_granted']:
        return send_from_directory(app.static_folder, 'index.html')
    return redirect(url_for('owner'))

@app.route('/owner', methods=['GET', 'POST'])
def owner():
    global unique_qr, temporary_qr_codes
    qr_code = None
    access_type = None

    if request.method == 'POST':
        if 'password' in request.form:
            if request.form['password'] == OWNER_PASSWORD:
                session['owner_authenticated'] = True
                return redirect(url_for('owner'))
            else:
                flash('Senha incorreta. Tente novamente.')
                return redirect(url_for('owner'))

        if 'owner_authenticated' not in session:
            return redirect(url_for('owner'))

        access_type = request.form.get('access')
        if access_type == 'unrestricted':
            unique_qr = generate_qr_code('unrestricted')
            qr_code = unique_qr
        elif access_type == 'temporary':
            while True:
                temporary_qr = generate_random_string()
                if temporary_qr not in temporary_qr_codes:
                    temporary_qr_codes.add(temporary_qr)
                    break
            qr_code = generate_qr_code(temporary_qr)
        return render_template('owner.html', qr_code=qr_code, access_type=access_type)

    if 'owner_authenticated' not in session:
        return render_template('login.html')
    
    return render_template('owner.html', qr_code=qr_code, access_type=access_type)

@app.route('/access/<access_code>', methods=['GET'])
def grant_access(access_code):
    if access_code == 'unrestricted':
        session['access_granted'] = True
    elif access_code in temporary_qr_codes:
        session['access_granted'] = True
        temporary_qr_codes.remove(access_code)
    else:
        return jsonify({'status': 'error', 'message': 'Invalid access code'}), 403
    return redirect(url_for('index'))

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url_for('grant_access', access_code=data, _external=True))
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

@app.route('/validate_qr', methods=['POST'])
def validate_qr():
    qr_code = request.json.get('qr_code')
    if qr_code == 'unrestricted':
        return jsonify({'status': 'success', 'message': 'Access granted'})
    elif qr_code in temporary_qr_codes:
        temporary_qr_codes.remove(qr_code)
        return jsonify({'status': 'success', 'message': 'Access granted'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid QR code'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)