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
 * 手机分页：还有下一页时提示滑动；到最后一页在底部写「没有更多了」。
 * @param {number} page
 * @param {number} pages
 */
function renderPhoneLoadMore(page, pages) {
    if (page >= pages) {
        return '<p class="record-pager-more" data-phone-more="end">没有更多了</p>';
    }
    return '<p class="record-pager-more" data-phone-more="next">滑动加载更多</p>';
}

const phoneSessions = new Map();
let phoneMediaBound = false;

function pagerTbody(buttonsEl) {
    const pager = buttonsEl.closest('.record-pager');
    if (!pager) return null;
    let node = pager.previousElementSibling;
    while (node) {
        if (node.matches && node.matches('table')) {
            const body = node.querySelector('tbody');
            if (body) return body;
        }
        const nested = node.querySelector ? node.querySelector('tbody') : null;
        if (nested) return nested;
        node = node.previousElementSibling;
    }
    return null;
}

function observePhoneSentinel(session) {
    if (!session.observer) return;
    session.observer.disconnect();
    if (!isPhoneLayout()) return;
    const node = session.el.querySelector('[data-phone-more="next"]');
    if (node) session.observer.observe(node);
}

function pageScroller() {
    return document.scrollingElement || document.documentElement;
}

function rememberPhoneScroll(session, tbody) {
    const anchor = tbody?.querySelector('tr') || null;
    session.anchor = anchor;
    session.anchorTop = anchor ? anchor.getBoundingClientRect().top : null;
    session.scrollTop = pageScroller().scrollTop;
}

function keepPhonePose(pose) {
    const scroller = pageScroller();
    if (!scroller || !pose) return;
    const previous = scroller.style.scrollBehavior;
    scroller.style.scrollBehavior = 'auto';
    const anchor = pose.anchor;
    if (anchor && anchor.isConnected && pose.anchorTop != null) {
        const delta = anchor.getBoundingClientRect().top - pose.anchorTop;
        if (Math.abs(delta) > 1) scroller.scrollTop += delta;
    } else if (pose.scrollTop != null) {
        scroller.scrollTop = pose.scrollTop;
    }
    scroller.style.scrollBehavior = previous;
}

function keepPhoneScroll(session) {
    keepPhonePose(session);
}

function placeSnapshot(session, tbody) {
    const snap = session.snapshot || [];
    if (!snap.length || !tbody) return;
    if (tbody.firstElementChild === snap[0]) return;
    const frag = document.createDocumentFragment();
    snap.forEach((row) => frag.appendChild(row));
    tbody.insertBefore(frag, tbody.firstChild);
}

function finishPhoneAppend(session, tbody) {
    placeSnapshot(session, tbody);
    session.snapshot = null;
    session.appending = false;
    session.stacked = true;
    if (tbody) tbody.style.overflowAnchor = '';
    const pose = {
        anchor: session.anchor,
        anchorTop: session.anchorTop,
        scrollTop: session.scrollTop,
    };
    keepPhonePose(pose);
    requestAnimationFrame(() => keepPhonePose(pose));
}

function watchPhoneReplace(session, tbody) {
    if (session.mo) session.mo.disconnect();
    if (!tbody) {
        session.appending = false;
        session.snapshot = null;
        return;
    }
    tbody.style.overflowAnchor = 'none';
    const obs = new MutationObserver(() => {
        if (!session.appending || !session.snapshot) return;
        if (tbody.children.length === 0) {
            placeSnapshot(session, tbody);
            keepPhoneScroll(session);
            return;
        }
        const snap = session.snapshot;
        const holding = tbody.firstElementChild === snap[0] && tbody.children.length === snap.length;
        if (holding) {
            keepPhoneScroll(session);
            return;
        }
        obs.disconnect();
        session.mo = null;
        clearTimeout(session.timer);
        finishPhoneAppend(session, tbody);
    });
    session.mo = obs;
    obs.observe(tbody, { childList: true });
    clearTimeout(session.timer);
    session.timer = setTimeout(() => {
        if (!session.appending) return;
        obs.disconnect();
        session.mo = null;
        tbody.style.overflowAnchor = '';
        session.appending = false;
        session.snapshot = null;
        session.loading = false;
        session.wasAppend = false;
    }, 8000);
}

function requestPhoneNext(session) {
    if (!isPhoneLayout() || session.loading || session.appending) return;
    if (session.page >= session.pages) return;
    const tbody = pagerTbody(session.el);
    session.loading = true;
    session.appending = true;
    session.wasAppend = true;
    session.snapshot = tbody ? [...tbody.children] : [];
    rememberPhoneScroll(session, tbody);
    const sentinel = session.el.querySelector('[data-phone-more="next"]');
    if (sentinel) sentinel.textContent = '加载中';
    clearCurrentTableRows();
    watchPhoneReplace(session, tbody);
    try {
        session.onPage(session.page + 1);
    } catch (err) {
        session.loading = false;
        session.appending = false;
        session.wasAppend = false;
        session.snapshot = null;
        if (session.mo) session.mo.disconnect();
        session.mo = null;
        throw err;
    }
}

function sentinelStillVisible(session) {
    const node = session.el.querySelector('[data-phone-more="next"]');
    if (!node) return false;
    const rect = node.getBoundingClientRect();
    return rect.top < window.innerHeight + 200 && rect.bottom > -200;
}

function dropDetachedPhoneSessions() {
    const detached = [];
    phoneSessions.forEach((session, buttonsId) => {
        if (!session.el.isConnected) detached.push(buttonsId);
    });
    detached.forEach((buttonsId) => {
        const session = phoneSessions.get(buttonsId);
        session.observer?.disconnect();
        session.mo?.disconnect();
        clearTimeout(session.timer);
        phoneSessions.delete(buttonsId);
    });
}

function ensurePhoneMedia() {
    if (phoneMediaBound) return;
    phoneMediaBound = true;
    window.matchMedia('(max-width: 639.98px)').addEventListener('change', () => {
        dropDetachedPhoneSessions();
        phoneSessions.forEach((session) => {
            if (isPhoneLayout()) session.setSize(PHONE_PAGE_SIZE);
            session.stacked = false;
            session.loading = false;
            session.appending = false;
            session.wasAppend = false;
            session.snapshot = null;
            if (session.mo) session.mo.disconnect();
            session.mo = null;
            session.onPage(1);
        });
    });
}

function bindPhoneLoadMore(buttonsId, onPage, setSize) {
    const el = document.getElementById(buttonsId);
    if (!el) return;
    const previous = phoneSessions.get(buttonsId);
    if (previous) {
        previous.observer?.disconnect();
        previous.mo?.disconnect();
        clearTimeout(previous.timer);
    }
    const session = {
        el,
        onPage,
        setSize,
        page: 1,
        pages: 1,
        loading: false,
        appending: false,
        wasAppend: false,
        stacked: false,
        snapshot: null,
        observer: null,
        mo: null,
        timer: 0,
    };
    session.observer = new IntersectionObserver((entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        requestPhoneNext(session);
    }, { root: null, rootMargin: '200px' });
    phoneSessions.set(buttonsId, session);
    ensurePhoneMedia();
    observePhoneSentinel(session);
}

function notePhonePaint(buttonsId, currentPage, totalPages) {
    const session = phoneSessions.get(buttonsId);
    const el = document.getElementById(buttonsId);
    if (!session || !el || !isPhoneLayout()) return;
    const page = Number(currentPage) || 1;
    const pages = Number(totalPages) || 0;
    const prev = session.page;
    const grew = session.wasAppend && page > prev;
    if (session.wasAppend && page <= prev) {
        session.appending = false;
        session.snapshot = null;
        if (session.mo) session.mo.disconnect();
        session.mo = null;
    }
    session.el = el;
    session.page = page;
    session.pages = pages;
    session.wasAppend = false;
    session.loading = false;
    observePhoneSentinel(session);
    if (!grew) return;
    queueMicrotask(() => {
        if (session.loading || session.appending || !isPhoneLayout()) return;
        if (sentinelStillVisible(session)) requestPhoneNext(session);
    });
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
    if (isPhoneLayout()) {
        if (pages < 1) return '';
        return renderPhoneLoadMore(page, pages);
    }
    if (pages <= 1) return '';
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
    notePhonePaint(buttonsId, currentPage, totalPages);
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
    bindPhoneLoadMore(buttonsId, onPage, setSize);
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
