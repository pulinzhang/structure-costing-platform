/**
 * 对话框宽度：拖左缘调整，记在本机。最大化时不改宽度。
 */

const STORAGE_KEY = 'llm_assistant_panel_width';
const DEFAULT_WIDTH = 440;
const MIN_WIDTH = 320;
const VIEWPORT_GUTTER = 0;

/**
 * @param {number} px
 * @returns {number}
 */
export function clampPanelWidth(px) {
    const max = Math.max(MIN_WIDTH, window.innerWidth - VIEWPORT_GUTTER);
    const value = Number.isFinite(px) ? px : DEFAULT_WIDTH;
    return Math.min(max, Math.max(MIN_WIDTH, Math.round(value)));
}

/**
 * @returns {number}
 */
export function readPanelWidth() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw == null || raw === '') return clampPanelWidth(DEFAULT_WIDTH);
        return clampPanelWidth(Number(raw));
    } catch {
        return clampPanelWidth(DEFAULT_WIDTH);
    }
}

/**
 * @param {number} px
 */
function writePanelWidth(px) {
    try {
        localStorage.setItem(STORAGE_KEY, String(clampPanelWidth(px)));
    } catch {
        // 宽度记不住不影响对话
    }
}

/**
 * @param {HTMLElement|null} panel
 * @param {boolean} maximized
 */
export function applyPanelWidth(panel, maximized) {
    if (!panel) return;
    const handle = panel.querySelector('#llmPanelResize');
    if (maximized) {
        panel.style.width = '';
        handle?.classList.add('hidden');
        return;
    }
    panel.style.width = `${readPanelWidth()}px`;
    handle?.classList.remove('hidden');
}

/**
 * @param {HTMLElement|null} panel
 * @param {{ isMaximized: () => boolean }} options
 */
export function bindPanelResize(panel, options) {
    const handle = panel?.querySelector('#llmPanelResize');
    if (!panel || !handle) return;

    handle.addEventListener('pointerdown', (event) => {
        if (options.isMaximized()) return;
        if (event.button != null && event.button !== 0) return;
        event.preventDefault();
        handle.setPointerCapture(event.pointerId);
        const startX = event.clientX;
        const startWidth = panel.getBoundingClientRect().width;
        const previousCursor = document.body.style.cursor;
        const previousSelect = document.body.style.userSelect;
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';

        const onMove = (ev) => {
            const next = clampPanelWidth(startWidth + (startX - ev.clientX));
            panel.style.width = `${next}px`;
        };
        const finish = (ev) => {
            if (handle.hasPointerCapture(ev.pointerId)) {
                handle.releasePointerCapture(ev.pointerId);
            }
            handle.removeEventListener('pointermove', onMove);
            handle.removeEventListener('pointerup', finish);
            handle.removeEventListener('pointercancel', finish);
            document.body.style.cursor = previousCursor;
            document.body.style.userSelect = previousSelect;
            writePanelWidth(panel.getBoundingClientRect().width);
        };
        handle.addEventListener('pointermove', onMove);
        handle.addEventListener('pointerup', finish);
        handle.addEventListener('pointercancel', finish);
    });

    window.addEventListener('resize', () => {
        if (options.isMaximized()) return;
        panel.style.width = `${readPanelWidth()}px`;
    });
}
