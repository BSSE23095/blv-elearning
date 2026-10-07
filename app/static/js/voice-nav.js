/*
 * Voice command navigation (Section 3.2). Captures audio via the browser
 * MediaRecorder API, sends it to /voice/command (Google Speech Recognition
 * + Levenshtein fallback on the backend), and maps the returned intent to
 * a navigation action. Falls back to a typed command box (POSTed to
 * /voice/command-text, which runs the same matcher) if the microphone is
 * unavailable or permission is denied.
 */
(function () {
    let mediaRecorder;
    let audioChunks = [];

    function setStatus(msg) {
        const statusEl = document.getElementById('voice-status');
        if (statusEl) statusEl.textContent = msg;
    }

    function clickFirst(selector) {
        const el = document.querySelector(selector);
        if (el) { el.click(); return true; }
        return false;
    }

    function handleIntent(intent) {
        switch (intent) {
            case 'go_home':
                window.location.href = '/';
                break;
            case 'list_courses':
                window.location.href = '/';
                break;
            case 'open_course':
                // No course name is captured by voice, so "open course" opens
                // the first course on the home page; from anywhere else it
                // goes home first so the learner can choose.
                if (!clickFirst('a.btn[aria-label^="Open course:"]')) {
                    window.location.href = '/';
                }
                break;
            case 'next_module':
                document.querySelector('a[aria-label="Next module"]')?.click();
                break;
            case 'previous_module':
                document.querySelector('a[aria-label="Previous module"]')?.click();
                break;
            case 'read_content':
                document.getElementById('btn-read-module')?.click();
                break;
            case 'stop_audio':
                document.getElementById('btn-stop')?.click();
                break;
            case 'start_quiz':
                document.querySelector('a[aria-label="Start module quiz"]')?.click();
                break;
            case 'repeat':
                document.getElementById('btn-play')?.click();
                break;
            case 'describe_diagram':
                window.location.href = '/diagram/';
                break;
            case 'help':
                document.getElementById('btn-hear-commands')?.click();
                break;
            case 'increase_speed':
                bumpSpeed(0.1);
                break;
            case 'decrease_speed':
                bumpSpeed(-0.1);
                break;
            case 'read_info':
                // Home page: read the first course's info. Module page: read
                // the module content. Anywhere else: read the main heading
                // and first paragraph, so the command does something useful
                // on every page rather than only the ones built for it.
                if (clickFirst('.btn-read-info')) break;
                if (clickFirst('#btn-read-module')) break;
                readPageFallback();
                break;
            default:
                setStatus("Sorry, I didn't recognize that command.");
                if (window.speakText) window.speakText("Sorry, I didn't recognize that command.", {simplify: false});
        }
    }

    function readPageFallback() {
        const heading = document.querySelector('#main-content h2');
        const para = document.querySelector('#main-content p');
        const text = [heading?.textContent, para?.textContent].filter(Boolean).join('. ');
        if (text && window.speakText) {
            window.speakText(text, { simplify: false });
        } else {
            setStatus('Nothing to read on this page.');
        }
    }

    function bumpSpeed(delta) {
        const slider = document.getElementById('speed-slider');
        if (!slider) return;
        let val = parseFloat(slider.value) + delta;
        val = Math.max(0.5, Math.min(2.0, val));
        slider.value = val.toFixed(1);
        slider.dispatchEvent(new Event('input'));
    }

    function applyRecognitionResult(data) {
        if (data.error) {
            setStatus('Error: ' + data.error);
            return;
        }
        if (data.recognized) {
            setStatus(`Heard: "${data.transcript}" → ${data.intent}`);
            handleIntent(data.intent);
        } else {
            setStatus(`Heard: "${data.transcript}" — no matching command found.`);
        }
    }

    async function sendAudioForRecognition(blob) {
        setStatus('Processing your command...');
        const formData = new FormData();
        formData.append('audio', blob, 'command.wav');

        try {
            const resp = await fetch('/voice/command', { method: 'POST', body: formData });
            applyRecognitionResult(await resp.json());
        } catch (err) {
            setStatus('Could not reach the voice recognition service.');
        }
    }

    async function sendTypedCommand(text) {
        setStatus('Processing your command...');
        try {
            const resp = await fetch('/voice/command-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            applyRecognitionResult(await resp.json());
        } catch (err) {
            setStatus('Could not reach the command service.');
        }
    }

    async function startListening() {
        const micBtn = document.getElementById('btn-mic');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus('Microphone not available. Use the typed command box below instead.');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                micBtn?.classList.remove('listening');
                const blob = new Blob(audioChunks, { type: 'audio/wav' });
                sendAudioForRecognition(blob);
                stream.getTracks().forEach((t) => t.stop());
            };

            mediaRecorder.start();
            micBtn?.classList.add('listening');
            setStatus('Listening... speak your command now.');
            setTimeout(() => {
                if (mediaRecorder.state === 'recording') mediaRecorder.stop();
            }, 4000);
        } catch (err) {
            micBtn?.classList.remove('listening');
            setStatus('Microphone permission denied or unavailable. Use the typed command box below instead.');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const panelToggle = document.getElementById('btn-voice-panel');
        const panel = document.getElementById('voice-panel');
        const micBtn = document.getElementById('btn-mic');
        const typedForm = document.getElementById('typed-command-form');
        const typedInput = document.getElementById('typed-command-input');

        panelToggle?.addEventListener('click', () => {
            panel.hidden = !panel.hidden;
        });

        micBtn?.addEventListener('click', startListening);

        typedForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = typedInput.value.trim();
            if (!text) return;
            sendTypedCommand(text);
            typedInput.value = '';
        });
    });
})();
