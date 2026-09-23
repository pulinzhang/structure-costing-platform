/**
 * 操作前确认：全站一个。
 * 各页只调 confirmAction，禁止再写 window.confirm。
 */

const DEFAULT_TITLE = '确认删除';
const DEFAULT_CONFIRM = '删除';
const DEFAULT_CANCEL = '取消';

/**
 * @typedef {Object} ConfirmAskOptions
 * @property {string} [title]
 * @property {string} [confirmLabel]
 * @property {string} [cancelLabel]
 * @property {string} [lead] 说明句。不传时用 message
 * @property {Array<{ label?: string, value?: string }>} [specs]
 * @property {string} [note] 规格表下的补充
 */

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

function dialogIds(prefix) {
    const base = String(prefix || '').trim();
    return {
        dialog: `${base}Dialog`,
        backdrop: `${base}Backdrop`,
        panel: `${base}Panel`,
        title: `${base}Title`,
        lead: `${base}Lead`,
        specs: `${base}Specs`,
        reason: `${base}Reason`,
        close: `${base}CloseBtn`,
        cancel: `${base}CancelBtn`,
        ok: `${base}OkBtn`,
    };
}

/**
 * @param {Array<{ label?: string, value?: string }>} specs
 * @returns {string}
 */
function specsHtml(specs) {
    const rows = specs.map((spec) => {
        const label = String(spec?.label || '').trim();
        if (!label) return '';
        const value = String(spec?.value ?? '').trim() || '—';
        return `<li data-spec class="border-b border-line-subtle transition-colors duration-100 last:border-b-0 hover:bg-app-rowhover">
            <div class="flex items-baseline gap-3 px-5 py-3.5">
                <dt class="w-16 shrink-0 text-[10px] text-ink-faint">${escapeHtml(label)}</dt>
                <dd class="m-0 min-w-0 flex-1 truncate font-mono text-xs font-medium text-ink" title="${escapeHtml(value)}">${escapeHtml(value)}</dd>
            </div>
        </li>`;
    }).join('');
    if (!rows) return '';
    return `<ul class="m-0 list-none border-t border-line-subtle p-0">${rows}</ul>`;
}

/**
 * @param {string} prefix
 * @returns {string}
 */
function confirmDialogHtml(prefix) {
    const id = dialogIds(prefix);
    return `
        <div id="${escapeHtml(id.dialog)}"
             class="hidden fixed inset-0 z-[100] flex items-center justify-center p-4"
             role="alertdialog"
             aria-modal="true"
             aria-labelledby="${escapeHtml(id.title)}"
             aria-describedby="${escapeHtml(id.lead)} ${escapeHtml(id.reason)}">
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
                            <h6 id="${escapeHtml(id.title)}" class="mb-0 break-words text-[13px] font-semibold leading-snug tracking-wide text-ink">${DEFAULT_TITLE}</h6>
                            <p id="${escapeHtml(id.lead)}" class="mt-1 hidden whitespace-pre-wrap break-words text-[11px] font-normal leading-relaxed text-ink-muted"></p>
                        </div>
                    </div>
                    <button type="button" id="${escapeHtml(id.close)}"
                            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-[2px] text-ink-dim transition-colors hover:bg-app-elevated hover:text-ink"
                            aria-label="关闭">
                        ${icon('x-lg', 'w-4 h-4')}
                    </button>
                </div>
                <div class="max-h-[360px] overflow-y-auto">
                    <div id="${escapeHtml(id.specs)}" class="hidden"></div>
                    <p id="${escapeHtml(id.reason)}"
                       class="m-0 hidden whitespace-pre-wrap break-words px-5 py-3 text-xs leading-relaxed text-ink"></p>
                </div>
                <div class="flex items-center justify-end gap-4 border-t border-line-subtle px-5 py-3">
                    <button type="button" id="${escapeHtml(id.cancel)}"
                            class="inline-flex items-center px-1 py-1 text-[11px] text-ink transition-colors hover:text-ink">${DEFAULT_CANCEL}</button>
                    <button type="button" id="${escapeHtml(id.ok)}"
                            class="inline-flex items-center px-1 py-1 text-[11px] text-ink-muted transition-colors hover:text-brand">${DEFAULT_CONFIRM}</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * @param {string} prefix
 * @returns {{ ask: (message: string, options?: ConfirmAskOptions) => Promise<boolean> }}
 */
function bindConfirmDialog(prefix) {
    const id = dialogIds(prefix);
    const dialog = document.getElementById(id.dialog);
    const title = document.getElementById(id.title);
    const lead = document.getElementById(id.lead);
    const specs = document.getElementById(id.specs);
    const reason = document.getElementById(id.reason);
    const closeBtn = document.getElementById(id.close);
    const cancelBtn = document.getElementById(id.cancel);
    const okBtn = document.getElementById(id.ok);
    const backdrop = document.getElementById(id.backdrop);
    if (dialog && dialog.parentElement !== document.body) {
        document.body.appendChild(dialog);
    }

    /** @type {((accepted: boolean) => void) | null} */
    let pending = null;

    function finish(accepted) {
        const resolve = pending;
        pending = null;
        dialog?.classList.add('hidden');
        if (lead) {
            lead.textContent = '';
            lead.classList.add('hidden');
        }
        if (specs) {
            specs.innerHTML = '';
            specs.classList.add('hidden');
        }
        if (reason) {
            reason.textContent = '';
            reason.classList.add('hidden');
        }
        if (okBtn) okBtn.disabled = false;
        resolve?.(accepted);
    }

    /**
     * @param {string} message
     * @param {ConfirmAskOptions} [options]
     * @returns {Promise<boolean>}
     */
    function ask(message, options = {}) {
        if (pending) finish(false);
        const raw = String(message || '').trim();
        const specRows = Array.isArray(options.specs) ? options.specs : [];
        const specMarkup = specsHtml(specRows);
        let leadText = options.lead != null ? String(options.lead).trim() : raw;
        const noteText = String(options.note || '').trim();
        if (!leadText && !noteText && !specMarkup) leadText = raw || DEFAULT_TITLE;

        return new Promise((resolve) => {
            pending = resolve;
            if (title) title.textContent = String(options.title || '').trim() || DEFAULT_TITLE;
            const subtitle = specMarkup ? leadText : '';
            const bodyText = specMarkup ? noteText : (leadText || noteText);
            if (lead) {
                lead.textContent = subtitle;
                lead.classList.toggle('hidden', !subtitle);
            }
            if (specs) {
                specs.innerHTML = specMarkup;
                specs.classList.toggle('hidden', !specMarkup);
            }
            if (reason) {
                reason.textContent = bodyText;
                reason.classList.toggle('hidden', !bodyText);
                reason.classList.toggle('text-ink-muted', Boolean(specMarkup));
                reason.classList.toggle('text-ink', !specMarkup);
            }
            if (cancelBtn) cancelBtn.textContent = String(options.cancelLabel || '').trim() || DEFAULT_CANCEL;
            if (okBtn) okBtn.textContent = String(options.confirmLabel || '').trim() || DEFAULT_CONFIRM;
            dialog?.classList.remove('hidden');
            cancelBtn?.focus();
        });
    }

    function onKey(event) {
        if (!dialog || dialog.classList.contains('hidden')) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            finish(false);
            return;
        }
        if (event.key !== 'Enter') return;
        event.preventDefault();
        event.stopPropagation();
        finish(event.target === okBtn);
    }

    closeBtn?.addEventListener('click', () => finish(false));
    cancelBtn?.addEventListener('click', () => finish(false));
    okBtn?.addEventListener('click', () => finish(true));
    backdrop?.addEventListener('click', () => finish(false));
    document.addEventListener('keydown', onKey, true);

    return { ask };
}

const CONFIRM_PREFIX = 'appConfirm';

/** 全站操作前确认共用一个提示框。由应用壳挂上。 */
export function installConfirmDialog() {
    if (document.getElementById(`${CONFIRM_PREFIX}Dialog`)) return;
    const holder = document.createElement('div');
    holder.innerHTML = confirmDialogHtml(CONFIRM_PREFIX);
    const node = holder.firstElementChild;
    if (!node) return;
    document.body.appendChild(node);
    const bound = bindConfirmDialog(CONFIRM_PREFIX);
    window.confirmAction = (message, options) => bound.ask(message, options);
}
