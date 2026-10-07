/*
 * Audio control bar: play, pause, stop, speed slider (0.5x-2.0x).
 * Exposes window.speakText(text, options) globally so any page/template
 * can trigger TTS through the same audio element and control bar.
 */
(function () {
    let audioEl;
    let currentSpeed = 1.0;

    async function speakText(text, options = {}) {
        if (!text || !text.trim()) return;
        const simplify = options.simplify !== undefined ? options.simplify : true;

        try {
            const resp = await fetch('/tts/speak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, simplify, speed: currentSpeed }),
            });
            const data = await resp.json();
            if (data.error) {
                console.error('TTS error:', data.error);
                return;
            }

            audioEl.src = `data:${data.mime_type};base64,${data.audio_base64}`;
            audioEl.playbackRate = currentSpeed;
            audioEl.play();
        } catch (err) {
            console.error('Failed to fetch TTS audio:', err);
        }
    }

    window.speakText = speakText;

    document.addEventListener('DOMContentLoaded', () => {
        audioEl = document.getElementById('tts-audio');
        const playBtn = document.getElementById('btn-play');
        const pauseBtn = document.getElementById('btn-pause');
        const stopBtn = document.getElementById('btn-stop');
        const speedSlider = document.getElementById('speed-slider');
        const speedDisplay = document.getElementById('speed-display');

        playBtn?.addEventListener('click', () => audioEl.play());
        pauseBtn?.addEventListener('click', () => audioEl.pause());
        stopBtn?.addEventListener('click', () => {
            audioEl.pause();
            audioEl.currentTime = 0;
        });

        speedSlider?.addEventListener('input', () => {
            currentSpeed = parseFloat(speedSlider.value);
            audioEl.playbackRate = currentSpeed;
            speedDisplay.textContent = currentSpeed.toFixed(1) + 'x';
        });
    });
})();
