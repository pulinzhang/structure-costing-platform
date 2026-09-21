/**
 * 上传拖拽区状态：用 data-dropzone-state 驱动 Tailwind，不再依赖 style.css。
 */

export function setDropzoneDragActive(el, active) {
    if (!el) return;
    if (active) {
        el.dataset.dropzoneState = 'drag';
        return;
    }
    el.dataset.dropzoneState = el.dataset.hasFile === '1' ? 'file' : 'idle';
}

export function setDropzoneFileSelected(el, selected) {
    if (!el) return;
    el.dataset.hasFile = selected ? '1' : '0';
    if (el.dataset.dropzoneState === 'drag') return;
    el.dataset.dropzoneState = selected ? 'file' : 'idle';
}
