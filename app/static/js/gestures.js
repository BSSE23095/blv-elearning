/*
 * Touch gesture controls (Section 3.2), based on Kane, Bigham and
 * Wobbrock (2011). Five gestures via the Pointer Events API:
 *   - swipe right: next module
 *   - swipe left: previous module
 *   - swipe up: read aloud
 *   - swipe down: stop audio
 *   - long press: toggle voice panel
 */
(function () {
    const SWIPE_THRESHOLD = 50;      // px
    const LONG_PRESS_MS = 600;

    let startX = 0, startY = 0, startTime = 0;
    let longPressTimer = null;
    let longPressTriggered = false;

    function triggerLongPress() {
        longPressTriggered = true;
        document.getElementById('btn-voice-panel')?.click();
    }

    function handleSwipe(dx, dy) {
        if (Math.abs(dx) > Math.abs(dy)) {
            if (dx > SWIPE_THRESHOLD) {
                // swipe right -> next module
                document.querySelector('a[aria-label="Next module"]')?.click();
            } else if (dx < -SWIPE_THRESHOLD) {
                // swipe left -> previous module
                document.querySelector('a[aria-label="Previous module"]')?.click();
            }
        } else {
            if (dy < -SWIPE_THRESHOLD) {
                // swipe up -> read aloud
                document.getElementById('btn-read-module')?.click();
            } else if (dy > SWIPE_THRESHOLD) {
                // swipe down -> stop audio
                document.getElementById('btn-stop')?.click();
            }
        }
    }

    document.addEventListener('pointerdown', (e) => {
        startX = e.clientX;
        startY = e.clientY;
        startTime = Date.now();
        longPressTriggered = false;
        longPressTimer = setTimeout(triggerLongPress, LONG_PRESS_MS);
    });

    document.addEventListener('pointermove', (e) => {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
            clearTimeout(longPressTimer);
        }
    });

    document.addEventListener('pointerup', (e) => {
        clearTimeout(longPressTimer);
        if (longPressTriggered) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const elapsed = Date.now() - startTime;

        // Ignore very slow drags/clicks; treat as a deliberate swipe only
        // if it happened quickly enough to be a gesture, not a scroll.
        if (elapsed < 800 && (Math.abs(dx) > SWIPE_THRESHOLD || Math.abs(dy) > SWIPE_THRESHOLD)) {
            handleSwipe(dx, dy);
        }
    });
})();
