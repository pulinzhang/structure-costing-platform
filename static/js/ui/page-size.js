/**
 * 列表分页控件：页码 1 2 3 4 + 每页条数。
 * - 常规列表：默认 10，可选 10 / 20 / 50 / 100
 * - 一事一议预览页：默认 200，可选 10 / 20 / 50 / 100 / 200
 */

import { BTN_PAGINATION_CURRENT } from './classes.js?v=13';
import { clearCurrentTableRows } from './table-row.js?v=4';
import { isPhoneLayout } from './record-list.js?v=6';

/** 手机分页固定 10，不提供每页条数。 */
export const PHONE_PAGE_SIZE = 10;

export const PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100]);
export const DEFAULT_PAGE_SIZE = 10;

export const PREVIEW_PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100, 200]);
export const DEFAULT_PREVIEW_PAGE_SIZE = 200;

const PAGINATION_BTN_CLASS = 'page-btn';

const HUD_BAR_CLASS =
    'flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-3 py-2.5 border-t border-line-subtle bg-app-hud sm:px-5';

export function normalizePageSize(
    value,
    options = PAGE_SIZE_OPTIONS,
    fallback = DEFAULT_PAGE_SIZE,
) {
    if (isPhoneLayout()) return PHONE_PAGE_SIZE;
    const size = Number.parseInt(value, 10);
    return options.includes(size) ? size : fallback;
}

/**
 * 分页栏「每页」下拉 HTML（放在「共 N 条」旁）。
 * @param {string} selectId
 * @param {number} [currentSize]
 * @param {readonly number[]} [options]
 */
function pageSizeSelectHtml(
    selectId,
    currentSize = DEFAULT_PAGE_SIZE,
    options = PAGE_SIZE_OPTIONS,
) {
    const fallback = options.includes(DEFAULT_PAGE_SIZE)
        ? DEFAULT_PAGE_SIZE
        : (options[0] ?? DEFAULT_PAGE_SIZE);
    const size = normalizePageSize(currentSize, options, fallback);
    const optionHtml = options
        .map((n) => `<option value="${n}"${n === size ? ' selected' : ''}>${n}</option>`)
        .join('');
    return `
        <label class="record-page-size inline-flex items-center gap-1.5 shrink-0">
            <span class="text-[10px] font-mono text-ink-faint">每页</span>
            <select id="${selectId}"
                    class="h-6 min-w-[3.25rem] pl-1.5 pr-5 text-[10px] font-mono bg-app-main border border-line-hud text-ink-muted appearance-none cursor-pointer focus:outline-none focus:border-brand-hud rounded-[2px] hud-filter">
                ${optionHtml}
            </select>
        </label>`;
}

/**
 * 完整分页栏：左侧信息 + 每页条数，右侧页码。
 * @param {{
 *   wrapperClass?: string,
 *   wrapperId?: string,
 *   infoId?: string,
 *   infoHtml?: string,
 *   selectId: string,
 *   buttonsId: string,
 *   currentSize?: number,
 *   options?: readonly number[],
 * }} spec
 */
export function paginationBarHtml(spec) {
    const wrapperClass = spec.wrapperClass || HUD_BAR_CLASS;
    const idAttr = spec.wrapperId ? ` id="${spec.wrapperId}"` : '';
    const infoHtml = spec.infoHtml
        ?? `<span id="${spec.infoId}" class="text-[10px] font-mono text-ink-faint"></span>`;
    const currentSize = spec.currentSize ?? DEFAULT_PAGE_SIZE;
    const options = spec.options ?? PAGE_SIZE_OPTIONS;
    return `
        <div class="record-pager ${wrapperClass}"${idAttr}>
            <div class="record-pager-meta flex items-center gap-3 shrink-0">
                ${infoHtml}
                ${pageSizeSelectHtml(spec.selectId, currentSize, options)}
            </div>
            <div class="record-pager-pages flex items-center gap-0.5" id="${spec.buttonsId}"></div>
        </div>`;
}

/**
 * 绑定每页条数变更；变更后回调（通常 reload 第 1 页）。
 */
function bindPageSizeSelect(
    selectId,
    {
        getSize,
        setSize,
        onChange,
        options = PAGE_SIZE_OPTIONS,
        defaultSize = DEFAULT_PAGE_SIZE,
    },
) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.value = String(normalizePageSize(getSize(), options, defaultSize));
    select.addEventListener('change', () => {
        const next = normalizePageSize(select.value, options, defaultSize);
        select.value = String(next);
        setSize(next);
        onChange(next);
    });
}

/**
 * 手机分页：上一页 / 当前页 / 下一页，按钮铺满一行。
 * @param {number} page
 * @param {number} pages
 * @param {string} btnClass
 */
function renderPhonePageButtons(page, pages, btnClass) {
    const idle =
        'flex-1 h-10 border border-line-hud text-[12px] text-ink bg-transparent';
    const disabledCls =
        'flex-1 h-10 border border-line-hud text-[12px] text-ink-faint cursor-not-allowed opacity-40';
    const prevCls = page === 1 ? disabledCls : idle;
    const nextCls = page === pages ? disabledCls : idle;
    return `
        <button type="button" class="${btnClass} ${prevCls}"
                data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>上一页</button>
        <span class="shrink-0 min-w-[4.5rem] text-center text-[12px] font-mono tabular-nums text-ink">${page} / ${pages}</span>
        <button type="button" class="${btnClass} ${nextCls}"
                data-page="${page + 1}" ${page === pages ? 'disabled' : ''}>下一页</button>`;
}

/**
 * 页码按钮（左右箭头 + 最多 5 个数字 + 省略）。
 * @param {number} currentPage
 * @param {number} totalPages
 * @param {string} [btnClass]
 */
function renderPageButtons(currentPage, totalPages, btnClass = PAGINATION_BTN_CLASS) {
    const pages = Number(totalPages) || 0;
    const page = Number(currentPage) || 1;
    if (pages <= 1) return '';
    if (isPhoneLayout()) return renderPhonePageButtons(page, pages, btnClass);
    const idle =
        'flex items-center justify-center w-6 h-6 text-[10px] text-ink-dim hover:text-ink hover:bg-app-surface';
    const disabledCls =
        'flex items-center justify-center w-6 h-6 text-[10px] text-ink-faint cursor-not-allowed';
    const activeCls = BTN_PAGINATION_CURRENT;
    let buttons = `
        <button type="button" class="${btnClass} ${page === 1 ? disabledCls : idle} transition-all"
                data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>
            ${typeof window.svgIcon === 'function' ? window.svgIcon('chevron-left', 'w-3 h-3') : ''}
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(pages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    if (startPage > 1) {
        buttons += `<button type="button" class="${btnClass} ${idle}" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-ink-faint text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === page;
        buttons += `<button type="button" class="${btnClass} ${isActive ? activeCls : idle}" data-page="${i}">${i}</button>`;
    }
    if (endPage < pages) {
        if (endPage < pages - 1) buttons += `<span class="px-0.5 text-ink-faint text-[9px]">…</span>`;
        buttons += `<button type="button" class="${btnClass} ${idle}" data-page="${pages}">${pages}</button>`;
    }
    buttons += `
        <button type="button" class="${btnClass} ${page === pages ? disabledCls : idle} transition-all"
                data-page="${page + 1}" ${page === pages ? 'disabled' : ''}>
            ${typeof window.svgIcon === 'function' ? window.svgIcon('chevron-right', 'w-3 h-3') : ''}
        </button>`;
    return buttons;
}

export function paintPagination(buttonsId, currentPage, totalPages) {
    const el = document.getElementById(buttonsId);
    if (!el) return;
    el.innerHTML = renderPageButtons(currentPage, totalPages);
}

function bindPaginationButtons(buttonsId, onPage) {
    const el = document.getElementById(buttonsId);
    if (!el) return;
    el.addEventListener('click', (event) => {
        const btn = event.target.closest(`.${PAGINATION_BTN_CLASS}`);
        if (!btn || btn.disabled) return;
        const page = Number.parseInt(btn.dataset.page, 10);
        if (!Number.isFinite(page) || page < 1) return;
        clearCurrentTableRows();
        onPage(page);
    });
}

export function bindPagination({
    selectId,
    buttonsId,
    getSize,
    setSize,
    onPage,
    options = PAGE_SIZE_OPTIONS,
    defaultSize = DEFAULT_PAGE_SIZE,
}) {
    if (isPhoneLayout()) {
        const before = Number(getSize());
        setSize(PHONE_PAGE_SIZE);
        if (before !== PHONE_PAGE_SIZE) onPage(1);
    }
    bindPageSizeSelect(selectId, {
        getSize,
        setSize,
        onChange: () => {
            clearCurrentTableRows();
            onPage(1);
        },
        options,
        defaultSize,
    });
    bindPaginationButtons(buttonsId, onPage);
}
