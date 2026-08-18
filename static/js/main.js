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
    'spinner': `<svg class="inline-block w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>`,
    'file-inbox': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
    'chart': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`,
    'clipboard-list': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"/></svg>`,
    'refresh': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`,
    'information': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
    'clock': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
    'folder': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>`,
    'copy': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"/></svg>`,
    'arrows-split': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>`,
    'pencil': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
    'archive': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>`,
    'calculator': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 10h8"/><path d="M8 14h2"/><path d="M14 14h2"/><path d="M8 18h2"/><path d="M14 18h2"/></svg>`,
    'file-earmark-text': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
    'user': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>`,
    'shield': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>`,
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

/**
 * 固定小数位字符串（不经 Number）；非法返回 null。
 * @param {unknown} value
 * @param {number} digits
 * @param {{ allowNegative?: boolean }} [options]
 */
const formatDecimalFixed = (value, digits = 2, options = {}) => {
    const allowNegative = Boolean(options.allowNegative);
    if (value == null || value === '') return null;
    if (typeof value === 'number' && Number.isNaN(value)) return null;
    let text = String(value).trim().replace(/,/g, '').replace(/，/g, '');
    if (!text) return null;
    const negative = text.startsWith('-');
    if (negative) {
        if (!allowNegative) return null;
        text = text.slice(1);
    }
    if (!/^\d+(\.\d+)?$/.test(text)) return null;
    const places = Math.max(0, Number(digits) || 0);
    const [intPart, frac = ''] = text.split('.');
    const padded = `${frac}${'0'.repeat(places + 1)}`.slice(0, places + 1);
    let fracN = places > 0 ? Number.parseInt(padded.slice(0, places) || '0', 10) : 0;
    let carry = 0;
    if (places > 0 && padded.charAt(places) >= '5') {
        fracN += 1;
        const limit = 10 ** places;
        if (fracN >= limit) {
            fracN = 0;
            carry = 1;
        }
    }
    const intValue = BigInt(intPart || '0') + BigInt(carry);
    const sign = negative && intValue !== 0n ? '-' : '';
    if (places === 0) return `${sign}${intValue.toString()}`;
    return `${sign}${intValue.toString()}.${String(fracN).padStart(places, '0')}`;
};

/**
 * 解析表单金额/费率输入为固定小数位字符串；空串返回 null。
 * @param {unknown} raw
 * @param {number} digits
 * @param {{ allowNegative?: boolean }} [options]
 */
const parseDecimalInput = (raw, digits = 2, options = {}) => {
    const text = String(raw ?? '').trim().replace(/,/g, '').replace(/，/g, '');
    if (!text) return null;
    return formatDecimalFixed(text, digits, { allowNegative: Boolean(options.allowNegative) });
};

/**
 * 十进制字符串乘以 10^exp（exp 可为负，表示除以 10^|exp|），再量化到 outDigits。
 * 用于 ‰→小数、%→小数等换算，不经 Number。
 * @param {string} value
 * @param {number} exp
 * @param {number} outDigits
 * @param {{ allowNegative?: boolean }} [options]
 */
const scaleDecimalByPow10 = (value, exp, outDigits, options = {}) => {
    const workDigits = Math.max(0, Number(outDigits) || 0) + Math.abs(Number(exp) || 0) + 2;
    const normalized = formatDecimalFixed(value, workDigits, {
        allowNegative: Boolean(options.allowNegative),
    });
    if (normalized == null) return null;
    const negative = normalized.startsWith('-');
    const body = negative ? normalized.slice(1) : normalized;
    const [intPart, frac = ''] = body.split('.');
    const digitText = `${intPart}${frac}`;
    let work = BigInt(digitText || '0');
    let scale = frac.length - Number(exp);
    const places = Math.max(0, Number(outDigits) || 0);
    if (scale < places) {
        work *= 10n ** BigInt(places - scale);
        scale = places;
    }
    if (scale > places) {
        const extra = scale - places;
        const div = 10n ** BigInt(extra);
        const rem = work % div;
        work = work / div + (rem * 2n >= div ? 1n : 0n);
    }
    const sign = negative && work !== 0n ? '-' : '';
    if (places === 0) return `${sign}${work.toString()}`;
    const pow = 10n ** BigInt(places);
    const i = work / pow;
    const f = work % pow;
    return `${sign}${i.toString()}.${f.toString().padStart(places, '0')}`;
};

/** 数字格式化 — 默认 2 位小数；十进制字符串不经 Number，避免金额尾差 */
const fmtNum = (value, digits = 2) => {
    const formatted = formatDecimalFixed(value, digits, { allowNegative: true });
    return formatted == null ? '-' : formatted;
};

/** 给已规范的固定小数字符串加千分位（仅展示用） */
const withThousandsSep = (fixedDecimalStr) => {
    if (fixedDecimalStr == null || fixedDecimalStr === '') return fixedDecimalStr;
    const text = String(fixedDecimalStr);
    const negative = text.startsWith('-');
    const body = negative ? text.slice(1) : text;
    const [intPart, frac] = body.split('.');
    const withSep = String(intPart || '0').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    const sign = negative ? '-' : '';
    return frac != null ? `${sign}${withSep}.${frac}` : `${sign}${withSep}`;
};

/**
 * 比较两个十进制字符串；a>b → 1，相等 → 0，a<b → -1；非法 → null。
 * @param {unknown} a
 * @param {unknown} b
 * @param {number} [digits=6]
 */
const compareDecimalStrings = (a, b, digits = 6) => {
    const left = formatDecimalFixed(a, digits, { allowNegative: true });
    const right = formatDecimalFixed(b, digits, { allowNegative: true });
    if (left == null || right == null) return null;
    const toScaled = (s) => {
        const negative = s.startsWith('-');
        const body = negative ? s.slice(1) : s;
        const [i, f = ''] = body.split('.');
        const scaled = BigInt(i || '0') * (10n ** BigInt(digits))
            + BigInt((f + '0'.repeat(digits)).slice(0, digits));
        return negative ? -scaled : scaled;
    };
    const l = toScaled(left);
    const r = toScaled(right);
    if (l > r) return 1;
    if (l < r) return -1;
    return 0;
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
    closeBtn.innerHTML = svgIcon('x-lg', 'w-[14px] h-[14px]');
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

    function buildAuthHeaders(skipAuth) {
        if (skipAuth) return {};
        try {
            const raw = localStorage.getItem('brabus_user');
            if (!raw) return {};
            const session = JSON.parse(raw);
            if (session && session.token) {
                return {
                    'X-Token': session.token,
                    Authorization: `Bearer ${session.token}`,
                };
            }
        } catch (_) { /* ignore */ }
        return {};
    }

    function redirectOnUnauthorized(fullUrl, skipAuth, message) {
        if (skipAuth || String(fullUrl).includes('/api/auth/login')) return;
        try { localStorage.removeItem('brabus_user'); } catch (_) {}
        if (!window.location.pathname.startsWith('/login')) {
            showToast(message || '登录已失效，请重新登录', 'error');
            window.location.href = '/login';
        }
    }

    function parseDownloadFilename(contentDisposition, defaultFilename) {
        if (!contentDisposition) return defaultFilename;
        const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
        if (utf8Match && utf8Match[1]) {
            try {
                return decodeURIComponent(utf8Match[1].trim());
            } catch (_) { /* fall through */ }
        }
        const plainMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
        if (plainMatch && plainMatch[1]) {
            const raw = plainMatch[1].replace(/['"]/g, '').trim();
            try {
                return decodeURIComponent(raw);
            } catch (_) {
                return raw || defaultFilename;
            }
        }
        return defaultFilename;
    }

    async function request(method, url, { params, body, headers, timeout, skipAuth } = {}) {
        const methodUpper = String(method || 'GET').toUpperCase();
        const query = { ...(params || {}) };
        // GET 加时间戳，避免浏览器/代理缓存旧数据
        if (methodUpper === 'GET') {
            query._t = Date.now();
        }
        const fullUrl = buildUrl(url, query);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout || DEFAULT_TIMEOUT);

        const init = {
            method: methodUpper,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...buildAuthHeaders(skipAuth),
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

            // token 失效：清本地会话并回登录页
            if (response.status === 401) {
                const msg = (data && (data.message || data.detail)) || '未登录';
                redirectOnUnauthorized(fullUrl, skipAuth, msg);
                const err = new Error(msg);
                err.status = 401;
                throw err;
            }

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
                showToast('请求超时（后端可能仍在处理），请稍后刷新确认结果', 'error');
            } else if (!error.status) {
                showToast(error.message || '网络请求失败', 'error');
            }
            throw error;
        }
    }

    /**
     * 文件下载（Excel 等）：带 token，返回 blob，不走 JSON 解包。
     */
    async function download(url, { params, headers, timeout, skipAuth, defaultFilename } = {}) {
        const query = { ...(params || {}), _t: Date.now() };
        const fullUrl = buildUrl(url, query);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout || 120000);

        try {
            const response = await fetch(fullUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    ...buildAuthHeaders(skipAuth),
                    ...(headers || {}),
                },
                signal: controller.signal,
            });
            clearTimeout(timer);

            if (response.status === 401) {
                let msg = '未登录';
                try {
                    const data = await response.json();
                    msg = (data && (data.message || data.detail)) || msg;
                } catch (_) { /* ignore */ }
                redirectOnUnauthorized(fullUrl, skipAuth, msg);
                const err = new Error(msg);
                err.status = 401;
                throw err;
            }

            if (!response.ok) {
                let msg = `下载失败 (${response.status})`;
                try {
                    const data = await response.json();
                    msg = (data && (data.message || data.detail)) || msg;
                } catch (_) { /* ignore */ }
                showToast(msg, 'error');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            const filename = parseDownloadFilename(
                response.headers.get('Content-Disposition'),
                defaultFilename || 'download.xlsx',
            );
            const blob = await response.blob();
            return { ok: true, status: response.status, blob, filename };
        } catch (error) {
            clearTimeout(timer);
            if (error.name === 'AbortError') {
                showToast('下载超时，请稍后重试', 'error');
            } else if (!error.status) {
                showToast(error.message || '下载失败', 'error');
            }
            throw error;
        }
    }

    return {
        get:      (url, opts) => request('GET',    url, opts),
        post:     (url, body, opts) => request('POST',   url, { ...(opts || {}), body }),
        put:      (url, body, opts) => request('PUT',    url, { ...(opts || {}), body }),
        patch:    (url, body, opts) => request('PATCH',  url, { ...(opts || {}), body }),
        delete:   (url, opts) => request('DELETE', url, opts),
        download: (url, opts) => download(url, opts),
    };
})();

// ===== 导出全局 =====
//
// 注意：main.js 必须以传统 <script> 而非 type="module" 加载，
// 这样 window.* 在 app.js / 各 page 模块运行之前已就绪。

window.HttpClient = HttpClient;
window.esc = esc;
window.fmtNum = fmtNum;
window.formatDecimalFixed = formatDecimalFixed;
window.parseDecimalInput = parseDecimalInput;
window.scaleDecimalByPow10 = scaleDecimalByPow10;
window.withThousandsSep = withThousandsSep;
window.compareDecimalStrings = compareDecimalStrings;
window.formatFileSize = formatFileSize;
window.showToast = showToast;
window.svgIcon = svgIcon;
