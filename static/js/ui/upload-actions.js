/**
 * 上传页四颗控件：下载模板、浏览文件、重置、上传。文案与图标只写这一处。
 */

import { BTN_FILE_SELECT, BTN_GHOST, BTN_UPLOAD_SUBMIT } from './classes.js?v=15';

const DOWNLOAD_ICON =
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>';

const REFRESH_ICON =
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>';

const UPLOAD_ICON =
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>';

export function uploadTemplateButtonHtml(id) {
    return `<button type="button" id="${id}" class="${BTN_GHOST}">${DOWNLOAD_ICON}下载模板</button>`;
}

export function uploadFileHintHtml(id) {
    return `<p id="${id}" class="text-[10px] text-ink-faint mb-6">或点击下方按钮选择文件</p>`;
}

export function uploadBrowseButtonHtml(id) {
    return `<button type="button" id="${id}" class="${BTN_FILE_SELECT}">${window.svgIcon('folder', 'w-3.5 h-3.5')}浏览文件</button>`;
}

export function uploadResetButtonHtml(id) {
    return `<button type="button" id="${id}" class="${BTN_GHOST}">${REFRESH_ICON}重置</button>`;
}

export function uploadSubmitLabelHtml(busy) {
    if (busy) {
        return `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`;
    }
    return `${UPLOAD_ICON}上传`;
}

export function uploadSubmitButtonHtml(id) {
    return `<button type="submit" id="${id}" disabled class="${BTN_UPLOAD_SUBMIT}">${uploadSubmitLabelHtml(false)}</button>`;
}
