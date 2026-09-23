/**
 * 输入框 + 发送 + 沿用范围条
 */

/**
 * @param {HTMLElement} root
 * @param {{
 *   canRun: boolean,
 *   busy?: boolean,
 *   onSubmit: (text: string) => void,
 *   onDismissCarry?: () => void,
 * }} options
 */
export function mountComposer(root, options) {
    const canRun = Boolean(options.canRun);
    const busy = Boolean(options.busy);

    root.dataset.canRun = canRun ? '1' : '0';
    root.dataset.busy = busy ? '1' : '0';
    root.innerHTML = `
<div id="llmComposerCarry" class="hidden mb-2 flex items-center gap-1 max-w-full">
  <span id="llmComposerCarryText" class="min-w-0 truncate text-[12px] leading-5 text-ink"></span>
  <button type="button" id="llmComposerCarryClear"
          class="shrink-0 w-5 h-5 inline-flex items-center justify-center rounded-full text-ink-faint hover:text-ink hover:bg-app-elevated"
          aria-label="不沿用上一问范围" title="不沿用">×</button>
</div>
<div class="rounded-2xl border border-line-subtle bg-app-surface focus-within:border-ink-muted transition-colors">
  <textarea id="llmComposerInput" rows="2"
            placeholder="${canRun ? '问一句…' : '无生成权限，仅可查看'}"
            title="Enter 发送，Shift+Enter 换行"
            class="block w-full resize-none bg-transparent px-3.5 pt-3 pb-1 min-h-16 text-[13px] leading-relaxed text-ink placeholder:text-ink-faint focus:outline-none disabled:opacity-50 max-h-40"></textarea>
  <div class="flex items-center justify-end px-2 pb-2">
    <button type="button" id="llmComposerSend" aria-label="发送" title="发送"
            class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-ink text-app-deep disabled:bg-ink/20 disabled:text-ink-muted disabled:cursor-not-allowed">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 19V5M6 12l6-6 6 6"/>
      </svg>
    </button>
  </div>
</div>`;

    const input = root.querySelector('#llmComposerInput');
    const sendBtn = root.querySelector('#llmComposerSend');

    const submit = () => {
        if (root.dataset.canRun === '0') return;
        if (root.dataset.busy === '1') return;
        if (sendBtn?.disabled) return;
        const text = String(input?.value || '').trim();
        if (!text) return;
        options.onSubmit(text);
        if (input) {
            input.value = '';
            fitComposerInput(input);
            input.focus();
        }
        syncComposerControls(root);
    };

    sendBtn?.addEventListener('click', submit);
    input?.addEventListener('input', () => {
        fitComposerInput(input);
        syncComposerControls(root);
    });
    input?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
        }
    });
    root.querySelector('#llmComposerCarryClear')?.addEventListener('click', () => {
        options.onDismissCarry?.();
    });
    if (input) fitComposerInput(input);
    syncComposerControls(root);
}

/**
 * @param {HTMLElement} root
 * @param {boolean} busy
 * @param {boolean} canRun
 */
export function setComposerBusy(root, busy, canRun) {
    if (!root) return;
    root.dataset.canRun = canRun ? '1' : '0';
    root.dataset.busy = busy ? '1' : '0';
    syncComposerControls(root);
}

/**
 * 空输入时发送钮保持灰圆，有字才亮起。
 * @param {HTMLElement} root
 */
function syncComposerControls(root) {
    const input = root.querySelector('#llmComposerInput');
    const sendBtn = root.querySelector('#llmComposerSend');
    const canRun = root.dataset.canRun !== '0';
    const busy = root.dataset.busy === '1';
    const hasText = Boolean(String(input?.value || '').trim());
    if (input) input.disabled = !canRun;
    if (sendBtn) sendBtn.disabled = !canRun || busy || !hasText;
}

/**
 * @param {HTMLTextAreaElement} input
 */
function fitComposerInput(input) {
    input.style.height = 'auto';
    const measured = input.scrollHeight;
    // 面板还是 hidden 时 scrollHeight 为 0，写进去会把两行高压没。
    if (measured <= 0) {
        input.style.height = '';
        return;
    }
    input.style.height = `${Math.min(measured, 160)}px`;
}

/**
 * @param {HTMLElement|null} root
 * @param {object|null|undefined} carry
 * @param {object|null|undefined} scope
 */
export function setComposerCarry(root, carry, scope) {
    const bar = root?.querySelector('#llmComposerCarry');
    const label = root?.querySelector('#llmComposerCarryText');
    if (!bar || !label) return;
    const text = formatCarryText(carry, scope);
    if (!text) {
        label.textContent = '';
        bar.setAttribute('title', '');
        bar.classList.add('hidden');
        return;
    }
    const shown = `沿用上一问：${text}`;
    label.textContent = shown;
    bar.setAttribute('title', shown);
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
