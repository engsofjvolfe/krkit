from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='web/static', static_url_path='/static')

MUSIC_DIR = '/home/jvolfe/Documents/krkit/songs'

@app.route('/songs', methods=['GET'])
def list_songs():
    songs = [f for f in os.listdir(MUSIC_DIR) if os.path.isfile(os.path.join(MUSIC_DIR, f))]
    return jsonify(songs)

@app.route('/play', methods=['POST'])
def play_song():
    song = request.json.get('song')
    if song and os.path.isfile(os.path.join(MUSIC_DIR, song)):
        song_path = os.path.join(MUSIC_DIR, song)
        os.system(f'vlc --one-instance --playlist-enqueue "{song_path}"')
        return jsonify({'status': 'success', 'message': f'Playing {song}'})
    else:
        return jsonify({'status': 'error', 'message': 'Song not found'}), 404

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
