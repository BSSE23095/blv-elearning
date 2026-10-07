/*
 * Low-vision accommodations (Section 3.2):
 * - High contrast toggle (black-on-white)
 * - A+/A- font scaling between 14pt and 28pt via a CSS root variable
 * - Each change plays a short voice confirmation so the user doesn't have
 *   to wonder whether the tap registered.
 */
(function () {
    const MIN_FONT = 14;
    const MAX_FONT = 28;
    const STEP = 2;

    function currentFontSize() {
        const val = getComputedStyle(document.documentElement)
            .getPropertyValue('--font-size-base').trim();
        return parseInt(val, 10) || 18;
    }

    function setFontSize(px) {
        px = Math.max(MIN_FONT, Math.min(MAX_FONT, px));
        document.documentElement.style.setProperty('--font-size-base', px + 'px');
        return px;
    }

    function confirmVoice(message) {
        if (window.speakText) {
            window.speakText(message, { simplify: false });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const contrastBtn = document.getElementById('btn-contrast');
        const fontPlusBtn = document.getElementById('btn-font-plus');
        const fontMinusBtn = document.getElementById('btn-font-minus');

        if (contrastBtn) {
            contrastBtn.addEventListener('click', () => {
                document.body.classList.toggle('high-contrast');
                const isOn = document.body.classList.contains('high-contrast');
                confirmVoice(isOn ? 'High contrast mode on.' : 'High contrast mode off.');
            });
        }

        if (fontPlusBtn) {
            fontPlusBtn.addEventListener('click', () => {
                const newSize = setFontSize(currentFontSize() + STEP);
                confirmVoice(`Font size increased to ${newSize} points.`);
            });
        }

        if (fontMinusBtn) {
            fontMinusBtn.addEventListener('click', () => {
                const newSize = setFontSize(currentFontSize() - STEP);
                confirmVoice(`Font size decreased to ${newSize} points.`);
            });
        }

        // Keyboard shortcut reference (H, R, S, Q, plus arrow keys), per paper.
        // Left/Right move between modules (mirrors the next_module /
        // previous_module voice intents and the swipe gestures); Up/Down
        // adjust playback speed (mirrors increase_speed / decrease_speed).
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            switch (e.key.toLowerCase()) {
                case 'h':
                    window.location.href = '/';
                    break;
                case 'r':
                    document.getElementById('btn-play')?.click();
                    break;
                case 's':
                    document.getElementById('btn-stop')?.click();
                    break;
                case 'q':
                    document.querySelector('a[aria-label="Start module quiz"]')?.click();
                    break;
                case 'arrowright':
                    document.querySelector('a[aria-label="Next module"]')?.click();
                    break;
                case 'arrowleft':
                    document.querySelector('a[aria-label="Previous module"]')?.click();
                    break;
                case 'arrowup': {
                    e.preventDefault();
                    const upSlider = document.getElementById('speed-slider');
                    if (upSlider) {
                        upSlider.value = Math.min(2.0, parseFloat(upSlider.value) + 0.1).toFixed(1);
                        upSlider.dispatchEvent(new Event('input'));
                    }
                    break;
                }
                case 'arrowdown': {
                    e.preventDefault();
                    const downSlider = document.getElementById('speed-slider');
                    if (downSlider) {
                        downSlider.value = Math.max(0.5, parseFloat(downSlider.value) - 0.1).toFixed(1);
                        downSlider.dispatchEvent(new Event('input'));
                    }
                    break;
                }
            }
        });

        const hearCommandsBtn = document.getElementById('btn-hear-commands');
        if (hearCommandsBtn) {
            hearCommandsBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch('/voice/intents');
                    const intents = await resp.json();
                    const phrases = Object.values(intents).map(p => p[0]).join(', ');
                    confirmVoice('Available commands: ' + phrases);
                } catch (e) {
                    confirmVoice('Could not load the command list.');
                }
            });
        }
    });
})();
