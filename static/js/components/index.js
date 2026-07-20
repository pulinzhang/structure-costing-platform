/**
 * UI Components Module
 * 可复用的 UI 组件
 */

/**
 * 空状态组件
 */
export function emptyStateComponent(icon = 'inbox', title = '暂无数据', hint = '') {
    const iconMap = {
        inbox: `<svg class="inline-block w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`,
    };
    
    return `
        <div class="flex flex-col items-center justify-center py-16 text-slate-400">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <span class="text-slate-300">${iconMap[icon] || iconMap.inbox}</span>
            </div>
            <h5 class="text-slate-600 font-medium mb-1">${esc(title)}</h5>
            ${hint ? `<p class="text-sm text-slate-400">${esc(hint)}</p>` : ''}
        </div>
    `;
}

/**
 * 统计卡片组件
 */
export function statCardComponent(icon, value, label, color = 'slate') {
    const colorClass = {
        slate: 'bg-slate-100 text-slate-600',
        green: 'bg-green-50 text-green-600',
        amber: 'bg-amber-50 text-amber-600',
        sky: 'bg-sky-50 text-sky-600',
        red: 'bg-red-50 text-red-600',
    }[color] || 'bg-slate-100 text-slate-600';

    const iconMap = {
        'box': `<svg class="inline-block w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>`,
        'gear': `<svg class="inline-block w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`,
    };

    return `
        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-md flex items-center justify-center ${colorClass}">
                    ${iconMap[icon] || iconMap['box']}
                </div>
                <div>
                    <div class="text-xl font-semibold text-slate-900">${esc(value)}</div>
                    <div class="text-xs text-slate-500">${esc(label)}</div>
                </div>
            </div>
        </div>
    `;
}

/**
 * 加载动画组件
 */
export function loadingComponent(message = '加载中...') {
    return `
        <div class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-2 border-slate-200 border-t-slate-600 rounded-full animate-spin"></div>
        </div>
    `;
}

/**
 * 警告提示组件
 */
export function alertComponent(message, type = 'danger') {
    const iconMap = {
        danger: `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
        warning: `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
        success: `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>`,
        info: `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    };
    
    const styleMap = {
        danger: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-600' },
        warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-600' },
        success: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-600' },
        info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-600' },
    };
    
    const t = styleMap[type] || styleMap.danger;

    return `
        <div class="p-4 ${t.bg} border ${t.border} rounded-md">
            <div class="flex items-center gap-2 ${t.text}">
                ${iconMap[type] || iconMap.danger}
                <span class="text-sm font-medium">${esc(message)}</span>
            </div>
        </div>
    `;
}

/**
 * 分页组件
 */
export function paginationComponent(pageInfo) {
    const { total, page, total_pages, has_next, has_prev } = pageInfo;

    if (!total_pages || total_pages <= 1) {
        return '';
    }

    const window = 2;
    const pages = new Set([1, total_pages]);
    for (let i = Math.max(1, page - window); i <= Math.min(total_pages, page + window); i++) {
        pages.add(i);
    }
    const sortedPages = Array.from(pages).sort((a, b) => a - b);

    const chevronLeft = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg>`;
    const chevronRight = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>`;

    let html = `
        <nav class="flex items-center justify-center gap-1">
            <button class="p-2 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                    data-page="${page - 1}" ${!has_prev ? 'disabled' : ''}>
                ${chevronLeft}
            </button>
    `;

    let lastPage = 0;
    for (const p of sortedPages) {
        if (lastPage && p - lastPage > 1) {
            html += `<span class="px-2 text-slate-400">...</span>`;
        }
        const isActive = p === page;
        html += `
            <button class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors
                ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}"
                data-page="${p}">
                ${p}
            </button>
        `;
        lastPage = p;
    }

    html += `
        <button class="p-2 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                data-page="${page + 1}" ${!has_next ? 'disabled' : ''}>
            ${chevronRight}
        </button>
        </nav>
    `;

    return html;
}

/**
 * 表格单元格组件
 */
export function tableCellComponent(content, align = 'left', numeric = false) {
    if (numeric) {
        return `<td class="text-right font-mono tabular-nums whitespace-nowrap px-4 py-3 text-slate-800">${content}</td>`;
    }
    return `<td class="text-${align} px-4 py-3">${content}</td>`;
}

/**
 * 按钮组件
 */
export function buttonComponent(label, icon = '', variant = 'primary', onClick = null) {
    const variants = {
        primary: 'bg-slate-900 text-white hover:bg-slate-800',
        secondary: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50',
        ghost: 'text-slate-600 hover:bg-slate-100',
        danger: 'bg-red-600 text-white hover:bg-red-700',
    };
    const cls = variants[variant] || variants.primary;
    
    const iconMap = {
        'plus': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>`,
        'download': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>`,
        'upload': `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>`,
    };

    return `
        <button type="button"
                class="inline-flex items-center justify-center gap-2 ${cls} rounded-md px-4 py-2 text-sm font-medium transition-colors"
                ${onClick ? `onclick="${onClick}"` : ''}>
            ${icon && iconMap[icon] ? iconMap[icon] : ''}
            ${label}
        </button>
    `;
}
