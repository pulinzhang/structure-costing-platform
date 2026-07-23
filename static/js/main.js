/**
 * 汽车冲压件自动核价平台
 * 主 JavaScript 文件 — 全局工具层
 *
 * 前后端分离架构：纯 JavaScript SPA + Tailwind，无 HTMX。
 * 在 index.html 通过 <script type="module" src="js/main.js"> 直接加载
 * （传统 <script> 而非 ES Module，确保 window.* 在 DOMContentLoaded 之前就绪）。
 */

// ===== SVG 图标（替代 Bootstrap Icons） =====
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
    'search': `<svg class="inline-block w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>`,
    'file-earmark': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>`,
    'arrows-fullscreen': `<svg class="inline-block w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>`,
    'ruler': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12h20"/><path d="M4 12v3"/><path d="M8 12v2"/><path d="M12 12v4"/><path d="M16 12v2"/><path d="M20 12v3"/></svg>`,
};

const svgIcon = (name, extraClass = '') => {
    if (!SVG_ICONS[name]) return '';
    if (!extraClass) return SVG_ICONS[name];
    return SVG_ICONS[name].replace(/class="([^"]*)"/, (match, existingClass) => {
        return `class="${existingClass} ${extraClass}"`;
    });
};

// ===== 工具函数 =====

/**
 * HTML 转义（防止 XSS）
 * null / undefined 渲染为 '-'，与表格空值展示对齐。
 */
const esc = (value) => {
    if (value == null) return '-';
    return String(value).replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
};

/** 数字格式化 — 默认 2 位小数 */
const fmtNum = (value, digits = 2) => {
    if (value == null || Number.isNaN(value)) return '-';
    return Number(value).toFixed(digits);
};

/** 文件大小格式化 */
const formatFileSize = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// ===== Toast 通知 =====
//
// 仅支持三种状态：success / error / warning。
// 使用 Tailwind 任意值类构造 DOM，0 行 inline style（仅过渡属性由 JS 设置）。

const TOAST_STYLE = {
    success: { border: 'border-[#2e7d32]', icon: 'text-[#2e7d32]', path: 'M5 13l4 4L19 7' },
    error:   { border: 'border-[#c62828]', icon: 'text-[#c62828]', path: 'M6 18L18 6M6 6l12 12' },
    warning: { border: 'border-[#f57f17]', icon: 'text-[#f57f17]', path: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
};

function showToast(message, type = 'success') {
    // 'danger' 作为 'error' 的历史别名（早期代码混用，统一收口）
    if (type === 'danger') type = 'error';
    const style = TOAST_STYLE[type] || TOAST_STYLE.success;
    const toast = document.createElement('div');
    toast.setAttribute('role', 'alert');
    toast.className = `flex items-center justify-between gap-3 bg-[#1e1e1e] border ${style.border} border-l-[3px] px-4 py-3 rounded min-w-[260px] max-w-[400px] shadow-[0_8px_32px_rgba(0,0,0,0.5)] text-[13px] text-[#ffffff] font-medium`;

    const text = document.createElement('span');
    text.textContent = message;
    toast.appendChild(text);

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'text-[#9e9e9e] opacity-70 hover:opacity-100 transition-opacity';
    closeBtn.setAttribute('aria-label', '关闭');
    closeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>`;
    closeBtn.addEventListener('click', () => toast.remove());
    toast.appendChild(closeBtn);

    const container = getOrCreateToastContainer();
    container.appendChild(toast);

    // 4 秒淡出移除
    const dismissTimer = setTimeout(() => {
        toast.style.transition = 'opacity 0.3s, transform 0.3s';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(8px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
    toast.addEventListener('click', () => {
        clearTimeout(dismissTimer);
        toast.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'fixed top-4 right-4 flex flex-col gap-2 z-[9999]';
        document.body.appendChild(container);
    }
    return container;
}

// ===== HttpClient =====
//
// 统一封装 fetch：自动 query 序列化、JSON 头、超时、成功失败 toast、自动解包 { success, data, message }。

const HttpClient = (() => {
    const DEFAULT_TIMEOUT = 30000;

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

        try {
            const response = await fetch(fullUrl, init);
            clearTimeout(timer);
            const data = await parseResponse(response);

            if (data && typeof data === 'object' && 'success' in data) {
                if (data.success) {
                    return { ok: true, status: response.status, data: data.data, message: data.message };
                }
                const msg = data.message || data.detail || '请求失败';
                showToast(msg, 'error');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            if (!response.ok) {
                const msg = (data && (data.message || data.detail)) || `请求失败 (${response.status})`;
                showToast(msg, 'error');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            return { ok: true, status: response.status, data };
        } catch (error) {
            clearTimeout(timer);
            if (error.name === 'AbortError') {
                showToast('请求超时，请重试', 'error');
            } else if (!error.status) {
                showToast(error.message || '网络请求失败', 'error');
            }
            throw error;
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

// ===== 导出全局 =====
//
// 注意：main.js 必须以传统 <script> 而非 type="module" 加载，
// 这样 window.* 在 app.js / 各 page 模块运行之前已就绪。

window.HttpClient = HttpClient;
window.esc = esc;
window.fmtNum = fmtNum;
window.formatFileSize = formatFileSize;
window.showToast = showToast;
window.svgIcon = svgIcon;
