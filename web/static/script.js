document.addEventListener('DOMContentLoaded', () => {
    console.log('Document loaded, fetching songs...');
    fetchSongs();
    
    const confirmButton = document.getElementById('confirm-button');
    const cancelButton = document.getElementById('cancel-button');

    if (confirmButton) {
        confirmButton.addEventListener('click', () => {
            const modal = document.getElementById('modal');
            modal.classList.add('hidden');
            startCountdown();
        });
    }

    if (cancelButton) {
        cancelButton.addEventListener('click', () => {
            console.log('Modal hidden');
            const modal = document.getElementById('modal');
            modal.classList.add('hidden');
        });
    }

    const searchButton = document.getElementById('search-button');
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            const searchInput = document.getElementById('search-input').value.toLowerCase();
            const filteredSongs = songsData.filter(song => {
                const [author, songName] = song.toLowerCase().split(' - ');
                return author.includes(searchInput) || songName.includes(searchInput);
            });
            renderSongs(filteredSongs);
        });
    }
});

let selectedSong = '';
let countdownInterval;
let songsData = []; // Array para armazenar todas as músicas

async function fetchSongs() {
    console.log('Fetching songs...');
    try {
        const response = await fetch('/songs');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        let songs = await response.json();
        console.log('Fetched songs:', songs);
        songs = songs.sort(); // Ordena as músicas em ordem alfabética
        songsData = songs; // Salva todas as músicas ordenadas
        renderSongs(songs); // Renderiza todas as músicas ordenadas
        console.log('Songs fetched, sorted, and listed.');
    } catch (error) {
        console.error('Error fetching songs:', error);
    }
}

function renderSongs(songs) {
    const songList = document.getElementById('song-list');
    if (songList) {
        songList.innerHTML = '';
        songs.forEach(song => {
            const listItem = document.createElement('li');
            listItem.textContent = song;
            listItem.addEventListener('click', () => confirmSong(song));
            songList.appendChild(listItem);
        });
    } else {
        console.error('Error: song-list element not found');
    }
}

function confirmSong(song) {
    console.log('Song selected:', song);
    selectedSong = song;
    const modal = document.getElementById('modal');
    const confirmationText = document.getElementById('song-confirmation');
    const buttons = document.getElementById('buttons');
    
    if (modal && confirmationText && buttons) {
        confirmationText.textContent = `Você escolheu a música "${song}". Tem certeza que deseja executar?`;
        buttons.classList.remove('hidden');
        modal.classList.remove('hidden');
    } else {
        console.error('Error: modal elements not found');
    }
}

function startCountdown() {
    const countdownElement = document.getElementById('countdown');
    const countdownModal = document.getElementById('countdown-modal');
    const prepareMessage = document.getElementById('prepare-message');
    const playingMessage = document.getElementById('playing-message');
    const progressBar = document.querySelector('.progress-bar');

    if (countdownModal && countdownElement && prepareMessage && playingMessage && progressBar) {
        countdownModal.classList.remove('hidden');
        prepareMessage.classList.remove('hidden');
        countdownElement.classList.remove('hidden');
        playingMessage.classList.add('hidden');

        let countdown = 10;
        countdownElement.textContent = countdown;
        progressBar.classList.remove('red');
        progressBar.style.strokeDashoffset = '0';

        countdownInterval = setInterval(() => {
            countdown--;
            countdownElement.textContent = countdown;
            let offset = (283 / 10) * (10 - countdown); // 283 é o perímetro do círculo
            progressBar.style.strokeDashoffset = offset;

            if (countdown <= 3) {
                progressBar.classList.add('red');
            }

            if (countdown <= 0) {
                clearInterval(countdownInterval);
                playSong(selectedSong);
                countdownElement.classList.add('hidden');
                prepareMessage.classList.add('hidden');
                playingMessage.classList.remove('hidden');
            }
        }, 1000);
    } else {
        console.error('Error: countdown elements not found');
    }
}

async function playSong(song) {
    console.log('Playing song:', song);
    try {
        const response = await fetch('/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ song })
        });
        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error('Error playing song:', error);
    }
}

// Função para buscar músicas pelo autor ou nome da música
document.getElementById('search-button').addEventListener('click', () => {
    const searchInput = document.getElementById('search-input').value.toLowerCase();
    const filteredSongs = songsData.filter(song => {
        const [author, songName] = song.toLowerCase().split(' - ');
        return author.includes(searchInput) || songName.includes(searchInput);
    });
    renderSongs(filteredSongs);
});
