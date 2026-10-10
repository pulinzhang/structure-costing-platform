/**
 * 错误提示框：停到用户关闭，正文可选中，可复制全文。
 * 各页只传 id 前缀和标题；禁止再复制遮罩、正文和复制按钮。
 * 引用明细是无框列表，路径能对上侧栏时给出跳转。
 */

import { pageMeta } from '../features/index.js?v=56';

const DEFAULT_MESSAGE = '操作失败';
const COPY_IDLE = '复制这段文字';
const COPY_DONE = '已复制';
const COPY_SELECTED = '已选中';
const FOOT_LINE = '以上数据仍在使用，不能删除。';

const PAGE_BY_CRUMB = new Map();
for (const [page, meta] of Object.entries(pageMeta)) {
    const crumbs = meta.breadcrumb;
    if (!Array.isArray(crumbs) || !crumbs.length) continue;
    PAGE_BY_CRUMB.set(crumbs.join(' → '), `#/${page}`);
}

function escapeHtml(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function icon(name, extraClass) {
    return typeof window.svgIcon === 'function' ? window.svgIcon(name, extraClass) : '';
}

function menuParts(menu) {
    return String(menu || '').split(/\s*(?:→|›)\s*/).map((part) => part.trim()).filter(Boolean);
}

/** 话术里的侧栏路径对到 pageMeta；对不上则不给跳转。 */
function hashForMenu(menu) {
    const parts = menuParts(menu);
    if (!parts.length) return '';
    const exact = PAGE_BY_CRUMB.get(parts.join(' → '));
    if (exact) return exact;
    const last = parts[parts.length - 1];
    const parents = parts.slice(0, -1);
    for (const [page, meta] of Object.entries(pageMeta)) {
        if (meta.title !== last) continue;
        const crumbs = meta.breadcrumb || [];
        if (parents.every((part, index) => crumbs[index] === part)) return `#/${page}`;
    }
    return '';
}

function headingFrom(line) {
    return String(line || '').replace(/[，,]\s*原因如下[:：]?$/, '').trim();
}

/**
 * @param {string} text
 * @returns {{ count: string, label: string, path: string, note: string }}
 */
function parseItem(text) {
    let path = '';
    let body = text;
    const pathMatch = text.match(/^(.*)，请到「(.+)」处理$/);
    if (pathMatch) {
        body = pathMatch[1];
        path = pathMatch[2];
    }
    const countMatch = body.match(/^有\s*(\d+)\s*条\s*([^，]+)(?:，(.+))?$/);
    if (countMatch) {
        return {
            count: countMatch[1],
            label: countMatch[2].trim(),
            path,
            note: (countMatch[3] || '').trim(),
        };
    }
    const tableMatch = body.match(/^被\s+(\S+)\s+表引用\s*(\d+)\s*条(?:，(.+))?$/);
    if (tableMatch) {
        return {
            count: tableMatch[2],
            label: tableMatch[1],
            path,
            note: (tableMatch[3] || '').trim(),
        };
    }
    return { count: '', label: body, path, note: '' };
}

/**
 * @param {string} message
 */
function parseReason(message) {
    const lines = String(message).split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const items = [];
    const prose = [];
    for (const line of lines) {
        const bullet = line.match(/^[-•]\s+(.+)$/);
        if (bullet) items.push(parseItem(bullet[1]));
        else prose.push(line);
    }
    if (!items.length) {
        return { heading: '', lead: '', items: [], extras: [], fallback: message };
    }
    const extras = prose.slice(1).filter((line) => line !== FOOT_LINE);
    return {
        heading: headingFrom(prose[0]),
        lead: `请处理完以下 ${items.length} 项关联数据后再尝试删除：`,
        items,
        extras,
        fallback: '',
    };
}

function countHtml(count) {
    const value = Number(count);
    if (!Number.isFinite(value)) return '';
    return `<span class="inline-flex items-baseline gap-0.5" title="${escapeHtml(String(value))} 条关联">
        <span class="font-mono text-[15px] font-bold tabular-nums leading-none text-brand">${escapeHtml(String(value))}</span>
        <span class="text-[10px] text-ink-muted">条</span>
    </span>`;
}

function breadcrumbHtml(path) {
    const parts = menuParts(path);
    if (!parts.length) return '';
    const trail = parts.map((part) => escapeHtml(part)).join(' <span class="text-ink-faint" aria-hidden="true">›</span> ');
    return `<p class="mt-1 text-[10px] leading-relaxed text-ink-muted">路径：${trail}</p>`;
}

function goButtonHtml(item) {
    const hash = hashForMenu(item.path);
    if (!hash) return '';
    return `<a href="${escapeHtml(hash)}" data-error-go
               class="inline-flex shrink-0 items-center rounded-[2px] px-2 py-1 text-[10px] text-ink-faint transition-colors hover:bg-brand hover:text-ink-onbrand"
               aria-label="去处理${escapeHtml(item.label)}">去处理</a>`;
}

function rowHtml(item) {
    const note = item.note && !item.path
        ? `<p class="mt-1 text-[10px] leading-relaxed text-ink-muted">${escapeHtml(item.note)}</p>`
        : '';
    return `<li data-error-row class="border-b border-line-subtle transition-colors duration-100 last:border-b-0 hover:bg-app-rowhover data-[current=1]:bg-app-rowhover">
        <div class="flex items-center justify-between gap-4 px-5 py-3.5">
            <div class="min-w-0">
                <div class="flex min-w-0 items-baseline gap-2">
                    <span class="min-w-0 text-xs font-medium text-ink">${escapeHtml(item.label)}</span>
                    ${countHtml(item.count)}
                </div>
                ${breadcrumbHtml(item.path)}
                ${note}
            </div>
            ${goButtonHtml(item)}
        </div>
    </li>`;
}

function reasonHtml(parsed) {
    if (!parsed.items.length) {
        return `<p class="m-0 whitespace-pre-wrap break-words px-5 py-3 text-xs leading-relaxed text-ink">${escapeHtml(parsed.fallback)}</p>`;
    }
    const rows = parsed.items.map(rowHtml).join('');
    const extras = parsed.extras.length
        ? `<p class="mt-3 text-[11px] text-ink-faint">${escapeHtml(parsed.extras.join(''))}</p>`
        : '';
    return `<ul class="m-0 list-none border-t border-line-subtle p-0">${rows}</ul>${extras}`;
}

function dialogIds(prefix) {
    const base = String(prefix || '').trim();
    return {
        dialog: `${base}Dialog`,
        backdrop: `${base}Backdrop`,
        panel: `${base}Panel`,
        title: `${base}Title`,
        lead: `${base}Lead`,
        body: `${base}Body`,
        close: `${base}CloseBtn`,
        copy: `${base}CopyBtn`,
        ok: `${base}OkBtn`,
    };
}

/**
 * @param {{ prefix: string, title: string }} opts
 * @returns {string}
 */
export function errorDialogHtml({ prefix, title }) {
    const id = dialogIds(prefix);
    const heading = String(title || '').trim() || DEFAULT_MESSAGE;
    return `
        <div id="${escapeHtml(id.dialog)}"
             class="hidden fixed inset-0 z-[100] flex items-center justify-center p-4"
             role="alertdialog"
             aria-modal="true"
             aria-labelledby="${escapeHtml(id.title)}"
             aria-describedby="${escapeHtml(id.lead)} ${escapeHtml(id.body)}">
            <div id="${escapeHtml(id.backdrop)}" class="absolute inset-0 bg-overlay/70 backdrop-blur-sm"></div>
            <div id="${escapeHtml(id.panel)}"
                 tabindex="-1"
                 style="box-shadow: 0 30px 60px rgb(var(--overlay) / 0.8)"
                 class="relative flex w-[560px] max-w-[92vw] flex-col overflow-hidden rounded-[2px] border border-line bg-app-main outline-none">
                <span class="pointer-events-none absolute left-0 right-0 top-0 h-[2px] bg-gradient-to-r from-brand to-transparent" aria-hidden="true"></span>
                <div class="flex items-start justify-between gap-3 px-5 pb-3 pt-4">
                    <div class="flex min-w-0 items-start gap-3">
                        <span class="mt-0.5 shrink-0 text-ink-dim" aria-hidden="true">
                            ${icon('exclamation-triangle', 'w-4 h-4')}
                        </span>
                        <div class="min-w-0">
                            <h6 id="${escapeHtml(id.title)}" class="mb-0 break-words text-[13px] font-semibold leading-snug tracking-wide text-ink">${escapeHtml(heading)}</h6>
                            <p id="${escapeHtml(id.lead)}" class="mt-1 hidden text-[11px] font-normal leading-relaxed text-ink-muted"></p>
                        </div>
                    </div>
                    <button type="button" id="${escapeHtml(id.close)}"
                            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-[2px] text-ink-dim transition-colors hover:bg-app-elevated hover:text-ink"
                            aria-label="关闭">
                        ${icon('x-lg', 'w-4 h-4')}
                    </button>
                </div>
                <div id="${escapeHtml(id.body)}"
                     class="max-h-[360px] overflow-y-auto select-text"></div>
                <div class="flex items-center justify-between gap-3 border-t border-line-subtle px-5 py-3">
                    <button type="button" id="${escapeHtml(id.copy)}"
                            class="inline-flex items-center gap-1.5 px-0 py-1 text-[11px] text-ink-faint transition-colors hover:text-ink">
                        ${icon('copy', 'w-3.5 h-3.5')}
                        <span data-copy-label>${COPY_IDLE}</span>
                    </button>
                    <button type="button" id="${escapeHtml(id.ok)}"
                            class="inline-flex items-center px-1 py-1 text-[11px] text-ink-muted transition-colors hover:text-brand">确定</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * 渲染进页面后调用。框会挂到 document.body，避免被内容区 overflow 裁切。
 * @param {string} prefix
 * @returns {{ show: (message: string) => void, close: () => void, unbind: () => void }}
 */
export function bindErrorDialog(prefix) {
    const id = dialogIds(prefix);
    const dialog = document.getElementById(id.dialog);
    const body = document.getElementById(id.body);
    const panel = document.getElementById(id.panel);
    const titleEl = document.getElementById(id.title);
    const leadEl = document.getElementById(id.lead);
    const copyBtn = document.getElementById(id.copy);
    const copyLabel = copyBtn?.querySelector('[data-copy-label]');
    const closeBtn = document.getElementById(id.close);
    const okBtn = document.getElementById(id.ok);
    const backdrop = document.getElementById(id.backdrop);
    const defaultHeading = titleEl?.textContent?.trim() || DEFAULT_MESSAGE;
    if (dialog && dialog.parentElement !== document.body) {
        document.body.appendChild(dialog);
    }

    let text = '';

    function setCopyLabel(value) {
        if (copyLabel) copyLabel.textContent = value;
    }

    function close() {
        dialog?.classList.add('hidden');
        if (body) body.innerHTML = '';
        if (titleEl) titleEl.textContent = defaultHeading;
        if (leadEl) {
            leadEl.textContent = '';
            leadEl.classList.add('hidden');
        }
        setCopyLabel(COPY_IDLE);
        text = '';
    }

    function show(message) {
        const next = String(message || '').trim() || DEFAULT_MESSAGE;
        text = next;
        if (!dialog || !body) return;
        const parsed = parseReason(next);
        if (titleEl) titleEl.textContent = parsed.heading || defaultHeading;
        if (leadEl) {
            leadEl.textContent = parsed.lead;
            leadEl.classList.toggle('hidden', !parsed.lead);
        }
        body.innerHTML = reasonHtml(parsed);
        setCopyLabel(COPY_IDLE);
        dialog.classList.remove('hidden');
        panel?.focus();
    }

    function onEscape(event) {
        if (event.key !== 'Escape') return;
        if (!dialog || dialog.classList.contains('hidden')) return;
        event.preventDefault();
        event.stopPropagation();
        close();
    }

    function onBodyClick(event) {
        const target = event.target;
        if (!(target instanceof Element) || !body) return;
        const row = target.closest('[data-error-row]');
        if (row && body.contains(row)) {
            body.querySelectorAll('[data-error-row][data-current="1"]').forEach((item) => {
                if (item !== row) item.removeAttribute('data-current');
            });
            row.setAttribute('data-current', '1');
        }
        const go = target.closest('[data-error-go]');
        if (!go || !body.contains(go)) return;
        const href = go.getAttribute('href') || '';
        if (!href) return;
        event.preventDefault();
        close();
        if (window.location.hash !== href) window.location.hash = href;
    }

    async function copyText() {
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            setCopyLabel(COPY_DONE);
            window.setTimeout(() => {
                if (copyLabel && copyLabel.isConnected && copyLabel.textContent === COPY_DONE) {
                    setCopyLabel(COPY_IDLE);
                }
            }, 1600);
        } catch (_error) {
            if (!body) return;
            const range = document.createRange();
            range.selectNodeContents(body);
            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(range);
            setCopyLabel(COPY_SELECTED);
        }
    }

    closeBtn?.addEventListener('click', close);
    okBtn?.addEventListener('click', close);
    backdrop?.addEventListener('click', close);
    copyBtn?.addEventListener('click', copyText);
    body?.addEventListener('click', onBodyClick);
    document.addEventListener('keydown', onEscape, true);

    return {
        show,
        close,
        unbind() {
            document.removeEventListener('keydown', onEscape, true);
            closeBtn?.removeEventListener('click', close);
            okBtn?.removeEventListener('click', close);
            backdrop?.removeEventListener('click', close);
            copyBtn?.removeEventListener('click', copyText);
            body?.removeEventListener('click', onBodyClick);
            dialog?.remove();
            text = '';
        },
    };
}

const DELETE_ERROR_PREFIX = 'appDeleteError';

/** 全站删除失败共用一个提示框。由应用壳挂上，HttpClient 的删除请求来调。 */
export function installDeleteErrorDialog() {
    if (document.getElementById(`${DELETE_ERROR_PREFIX}Dialog`)) return;
    const holder = document.createElement('div');
    holder.innerHTML = errorDialogHtml({ prefix: DELETE_ERROR_PREFIX, title: '删除失败' });
    const node = holder.firstElementChild;
    if (!node) return;
    document.body.appendChild(node);
    const bound = bindErrorDialog(DELETE_ERROR_PREFIX);
    window.showDeleteError = (message) => bound.show(message);
}
