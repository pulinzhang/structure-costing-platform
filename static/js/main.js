/**
 * 汽车冲压件自动核价平台
 * 主 JavaScript 文件
 * 前后端分离架构：纯 JavaScript，无 HTMX
 */

// ===== 全局配置 =====
const AppConfig = {
    debug: true,
};

// ===== SVG 图标辅助函数（替代 Bootstrap Icons） =====
// 图标 SVG 定义
const SVG_ICONS = {
    'file-earmark-excel': `<svg class="inline-block w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>`,
    'trash': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
    'eye': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
    'x-lg': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`,
    'chevron-left': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg>`,
    'chevron-right': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>`,
    'inbox': `<svg class="inline-block w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`,
    'list-ol': `<svg class="inline-block w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 6h11"/><path d="M10 12h11"/><path d="M10 18h11"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>`,
    'exclamation-circle': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
    'exclamation-triangle': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
    'check-circle': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>`,
    'info-circle': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    'box': `<svg class="inline-block w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>`,
    'gear': `<svg class="inline-block w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`,
    'plus': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>`,
    'download': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>`,
    'upload': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>`,
};

// 获取 SVG 图标
const svgIcon = (name, extraClass = '') => {
    if (!SVG_ICONS[name]) return '';
    if (extraClass) {
        return SVG_ICONS[name].replace(/class="[^"]*"/, `class="${extraClass}"`);
    }
    return SVG_ICONS[name];
};

// ===== 工具函数 =====

/** HTML 转义（防止 XSS）- 全局可用 */
const esc = (value) => {
    if (value == null) return '-';
    return String(value).replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
};

/** 数字格式化 - 全局可用 */
const fmtNum = (value, digits = 2) => {
    if (value == null || Number.isNaN(value)) return '-';
    return Number(value).toFixed(digits);
};

/** 文件大小格式化 */
const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// ===== 加载状态管理 =====
let loadingCount = 0;

function showLoading() {
    loadingCount++;
    let overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(overlay);
    }
    overlay.classList.add('visible');
}

function hideLoading() {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('visible');
        }
    }
}

// ===== Toast 通知（Tailwind 风格） =====
function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();

    // Tailwind 色彩映射
    const colorMap = {
        success: 'bg-green-600',
        danger:  'bg-red-600',
        warning: 'bg-amber-600',
        info:    'bg-sky-600',
        error:   'bg-red-600',
    };
    const bgClass = colorMap[type] || 'bg-slate-600';

    const toast = document.createElement('div');
    toast.className = `flex items-center justify-between gap-3 ${bgClass} text-white px-4 py-3 rounded-md shadow-lg`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <span class="text-sm font-medium">${escapeHtml(message)}</span>
        <button type="button" class="text-white/80 hover:text-white transition-colors" onclick="this.closest('[role=alert]').remove()">
            ${svgIcon('x-lg')}
        </button>
    `;

    toastContainer.appendChild(toast);

    // 自动移除
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container fixed top-4 right-4 flex flex-col gap-2';
        document.body.appendChild(container);
    }
    return container;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ===== HttpClient =====
const HttpClient = (() => {
    const DEFAULT_TIMEOUT = 30000;

    let pendingRequests = 0;

    function trackStart() {
        pendingRequests++;
    }

    function trackEnd() {
        pendingRequests = Math.max(0, pendingRequests - 1);
    }

    function buildUrl(url, params) {
        if (!params) return url;
        const usp = new URLSearchParams();
        for (const [key, value] of Object.entries(params)) {
            if (value === undefined || value === null || value === '') continue;
            usp.append(key, String(value));
        }
        const qs = usp.toString();
        if (!qs) return url;
        return url.includes('?') ? `${url}&${qs}` : `${url}?${qs}`;
    }

    async function parseResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json();
        }
        const text = await response.text();
        try { return JSON.parse(text); } catch { return text; }
    }

    async function request(method, url, { params, body, headers, timeout } = {}) {
        const fullUrl = buildUrl(url, params);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout || DEFAULT_TIMEOUT);

        const init = {
            method,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...(headers || {}),
            },
            signal: controller.signal,
        };

        if (body !== undefined && body !== null) {
            if (body instanceof FormData || body instanceof Blob || body instanceof ArrayBuffer) {
                init.body = body;
            } else {
                init.headers['Content-Type'] = init.headers['Content-Type'] || 'application/json';
                init.body = typeof body === 'string' ? body : JSON.stringify(body);
            }
        }

        trackStart();
        try {
            const response = await fetch(fullUrl, init);
            clearTimeout(timer);
            const data = await parseResponse(response);

            if (data && typeof data === 'object' && 'success' in data) {
                if (data.success) {
                    return { ok: true, status: response.status, data: data.data, message: data.message };
                }
                const msg = data.message || data.detail || '请求失败';
                showToast(msg, 'danger');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            if (!response.ok) {
                const msg = (data && (data.message || data.detail)) || `请求失败 (${response.status})`;
                showToast(msg, 'danger');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            return { ok: true, status: response.status, data };
        } catch (error) {
            clearTimeout(timer);
            let message = error.message || '网络请求失败';
            if (error.name === 'AbortError') message = '请求超时，请重试';
            if (message !== error.message) {
                showToast(message, 'danger');
            }
            throw error;
        } finally {
            trackEnd();
        }
    }

    return {
        get:    (url, opts) => request('GET',    url, opts),
        post:   (url, body, opts) => request('POST',   url, { ...(opts || {}), body }),
        put:    (url, body, opts) => request('PUT',    url, { ...(opts || {}), body }),
        patch:  (url, body, opts) => request('PATCH',  url, { ...(opts || {}), body }),
        delete: (url, opts) => request('DELETE', url, opts),
    };
})();

// ===== FileUploader（Tailwind 风格预览） =====
class FileUploader {
    constructor(options = {}) {
        this.dropZone = options.dropZone;
        this.inputElement = options.inputElement;
        this.previewElement = options.previewElement;
        this.maxSize = options.maxSize || 50 * 1024 * 1024;
        this.allowedTypes = options.allowedTypes || ['.xlsx', '.xls', '.csv'];

        this.init();
    }

    init() {
        if (this.dropZone) {
            this.setupDragAndDrop();
        }
        if (this.inputElement) {
            this.inputElement.addEventListener('change', (e) => this.handleFileSelect(e));
        }
    }

    setupDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.remove('dragover');
            });
        });

        this.dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.processFiles(files);
        });
    }

    handleFileSelect(event) {
        const files = event.target.files;
        this.processFiles(files);
    }

    processFiles(files) {
        for (const file of files) {
            if (!this.validateFile(file)) {
                continue;
            }
            this.onFileSelected(file);
        }
    }

    validateFile(file) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!this.allowedTypes.includes(ext)) {
            showToast(`不支持的文件类型: ${ext}`, 'warning');
            return false;
        }

        if (file.size > this.maxSize) {
            showToast(`文件过大: ${file.name} (最大 ${this.formatFileSize(this.maxSize)})`, 'warning');
            return false;
        }

        return true;
    }

    onFileSelected(file) {
        console.log('文件已选择:', file.name, this.formatFileSize(file.size));

        if (this.previewElement) {
            this.previewElement.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-sky-50 border border-sky-200 rounded-md">
                    <span class="text-green-600">${svgIcon('file-earmark-excel')}</span>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium text-slate-900 truncate">${escapeHtml(file.name)}</div>
                        <div class="text-xs text-slate-500">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
            `;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// ===== 分页（Tailwind 风格） =====

// ===== 表格排序（Tailwind 风格） =====

// ===== 搜索过滤 =====
function filterTable(tableId, searchInputId) {
    const input = document.getElementById(searchInputId);
    const filter = input.value.toLowerCase();
    const table = document.getElementById(tableId);
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (const row of rows) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    }
}

// ===== 侧边栏子菜单（纯 JS） =====

// ===== DOM 加载完成后初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    // 初始化已移除（侧边栏菜单在 app.js 中处理）
});

// ===== 导出全局函数 =====
window.AppConfig = AppConfig;
window.HttpClient = HttpClient;
window.Http = HttpClient;
window.esc = esc;
window.fmtNum = fmtNum;
window.formatFileSize = formatFileSize;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showToast = showToast;
window.confirmAction = confirmAction;
window.FileUploader = FileUploader;
window.filterTable = filterTable;
window.svgIcon = svgIcon;
