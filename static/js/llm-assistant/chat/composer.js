/**
 * 输入框 + 发送
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
