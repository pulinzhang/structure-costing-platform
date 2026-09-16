/**
 * 输入框 + 发送 + 沿用范围条
 */

/**
 * @param {HTMLElement} root
 * @param {{
 *   canRun: boolean,
 *   busy?: boolean,
 *   onSubmit: (text: string) => void,
 * }} options
 */
export function mountComposer(root, options) {
    const canRun = Boolean(options.canRun);
    const busy = Boolean(options.busy);

    root.innerHTML = `
<div id="llmComposerCarry" class="hidden mb-1.5 text-[10px] text-[#9e9e9e] truncate" title=""></div>
<div class="flex items-end gap-2">
  <textarea id="llmComposerInput" rows="2"
            placeholder="${canRun ? '输入问题，Enter 发送 / Shift+Enter 换行' : '无生成权限，仅可查看'}"
            class="flex-1 resize-none px-2 py-1.5 text-[11px] leading-relaxed bg-[#0a0a0a] border border-[#2c2c2c] text-[#F5F5F5] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252] rounded-sm disabled:opacity-50"
            ${!canRun || busy ? 'disabled' : ''}></textarea>
  <button type="button" id="llmComposerSend"
          class="shrink-0 h-9 px-3 text-[11px] font-medium bg-[#d32f2f] text-white hover:bg-[#b71c1c] disabled:opacity-40 disabled:cursor-not-allowed rounded-sm transition-colors"
          ${!canRun || busy ? 'disabled' : ''}>发送</button>
</div>`;

    const input = root.querySelector('#llmComposerInput');
    const sendBtn = root.querySelector('#llmComposerSend');

    const submit = () => {
        if (!canRun) return;
        if (sendBtn?.disabled) return;
        const text = String(input?.value || '').trim();
        if (!text) return;
        options.onSubmit(text);
        if (input) input.value = '';
    };

    sendBtn?.addEventListener('click', submit);
    input?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
        }
    });
}

/**
 * @param {HTMLElement} root
 * @param {boolean} busy
 * @param {boolean} canRun
 */
export function setComposerBusy(root, busy, canRun) {
    const input = root.querySelector('#llmComposerInput');
    const sendBtn = root.querySelector('#llmComposerSend');
    const disabled = !canRun || busy;
    if (input) input.disabled = disabled;
    if (sendBtn) sendBtn.disabled = disabled;
}

/**
 * @param {HTMLElement|null} root
 * @param {object|null|undefined} carry
 * @param {object|null|undefined} scope
 */
export function setComposerCarry(root, carry, scope) {
    const bar = root?.querySelector('#llmComposerCarry');
    if (!bar) return;
    const text = formatCarryText(carry, scope);
    if (!text) {
        bar.textContent = '';
        bar.setAttribute('title', '');
        bar.classList.add('hidden');
        return;
    }
    bar.textContent = `沿用：${text}`;
    bar.setAttribute('title', `沿用：${text}`);
    bar.classList.remove('hidden');
}

/**
 * @param {object|null|undefined} carry
 * @param {object|null|undefined} scope
 * @returns {string}
 */
function formatCarryText(carry, scope) {
    const parts = [];
    const filters = carry?.filters && typeof carry.filters === 'object' ? carry.filters : {};
    const location = filters.location || scope?.location;
    const vehicle = filters.vehicle_model || scope?.vehicle_model;
    const partNumber = filters.part_number || scope?.part_number;
    const scopeUnset = '未指定';
    if (location && location !== scopeUnset) parts.push(String(location));
    if (vehicle && vehicle !== scopeUnset) parts.push(String(vehicle));
    const period = formatCarryPeriod(carry?.time_range, scope);
    if (period) parts.push(period);
    if (partNumber) parts.push(String(partNumber));
    return parts.join(' · ');
}

/**
 * @param {{ start?: string, end?: string }|null|undefined} timeRange
 * @param {object|null|undefined} scope
 * @returns {string}
 */
function formatCarryPeriod(timeRange, scope) {
    const fmt = typeof window.fmtPeriod === 'function' ? window.fmtPeriod : fallbackPeriod;
    const start = parseYearMonth(timeRange?.start);
    const end = parseYearMonth(timeRange?.end);
    if (start && end) {
        const startText = fmt(start.year, start.month);
        const endText = fmt(end.year, end.month);
        return startText === endText ? startText : `${startText}–${endText}`;
    }
    if (scope?.year || scope?.month) {
        return fmt(scope.year, scope.month);
    }
    return '';
}

/**
 * @param {string|null|undefined} value
 * @returns {{ year: number, month: number }|null}
 */
function parseYearMonth(value) {
    const match = String(value || '').match(/^(\d{4})-(\d{2})$/);
    if (!match) return null;
    return { year: Number(match[1]), month: Number(match[2]) };
}

function fallbackPeriod(year, month) {
    if (!year) return '';
    if (!month) return `${year}年`;
    return `${year}年${String(month).padStart(2, '0')}月`;
}
