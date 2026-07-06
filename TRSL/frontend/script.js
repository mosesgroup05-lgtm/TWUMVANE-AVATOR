// Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// Load available signs from database
async function loadAvailableSigns() {
    try {
        const response = await fetch(`${API_BASE_URL}/available-words`);
        const data = await response.json();
        
        if (data.success) {
            const signsContainer = document.getElementById('availableSigns');
            signsContainer.innerHTML = '';
            
            // Add words
            data.words.forEach(word => {
                const badge = document.createElement('span');
                badge.className = 'sign-badge badge bg-primary m-1';
                badge.textContent = word;
                badge.style.cursor = 'pointer';
                badge.addEventListener('click', () => {
                    document.getElementById('textInput').value += ' ' + word;
                });
                signsContainer.appendChild(badge);
            });
        }
    } catch (error) {
        console.error('Error loading signs:', error);
    }
}

// Translate function
async function translateText() {
    const textInput = document.getElementById('textInput').value.trim();
    
    if (!textInput) {
        alert('Please enter some text to translate');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: textInput })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        // Process the translation results
        processTranslation(data);
        
    } catch (error) {
        console.error('Translation error:', error);
        alert('Translation failed. Please try again.');
    }
}

// Process translation results
function processTranslation(data) {
    // Update translation details
    document.getElementById('originalText').textContent = data.original_text;
    document.getElementById('translationType').textContent = data.translation_type;
    
    const matchedCount = data.video_sequence.filter(v => v.has_video).length;
    const missingCount = data.video_sequence.filter(v => !v.has_video).length;
    
    document.getElementById('matchedCount').textContent = matchedCount;
    document.getElementById('missingCount').textContent = missingCount;
    
    // Display sequence
    const sequenceDisplay = document.getElementById('sequenceDisplay');
    sequenceDisplay.innerHTML = '';
    
    data.video_sequence.forEach((item, index) => {
        const badge = document.createElement('span');
        badge.className = `sign-badge badge m-1 ${item.has_video ? 'bg-success' : 'bg-danger'}`;
        badge.textContent = item.word;
        
        if (item.has_video) {
            badge.style.cursor = 'pointer';
            badge.addEventListener('click', () => playVideo(item.video_url, item.word, index));
        }
        
        sequenceDisplay.appendChild(badge);
    });
    
    // Store video sequence for navigation
    window.currentTranslation = data;
    window.currentIndex = 0;
    
    // Play first video if available
    const firstVideo = data.video_sequence.find(v => v.has_video);
    if (firstVideo) {
        playVideo(firstVideo.video_url, firstVideo.word, 0);
    }
}

// Play video
function playVideo(videoUrl, word, index) {
    const videoPlayer = document.getElementById('videoPlayer');
    videoPlayer.src = videoUrl;
    
    // Update current word display
    document.getElementById('currentWord').textContent = word;
    document.getElementById('currentIndex').textContent = index + 1;
    
    // Update progress
    const totalVideos = window.currentTranslation.video_sequence.filter(v => v.has_video).length;
    document.getElementById('totalVideos').textContent = totalVideos;
    
    const progress = ((index + 1) / totalVideos) * 100;
    document.getElementById('progressBar').style.width = `${progress}%`;
    
    // Highlight current sign
    const badges = document.querySelectorAll('.sign-badge');
    badges.forEach((badge, i) => {
        badge.classList.remove('active');
        if (i === index) {
            badge.classList.add('active');
        }
    });
    
    // Play the video
    videoPlayer.play();
}