/**
 * 常见问题胶囊
 */

import { PROMPT_CATALOG } from '../prompts/catalog.js?v=7';

/**
 * @param {HTMLElement} root
 * @param {{
 *   disabled?: boolean,
 *   onPick: (item: object, text: string) => void,
 * }} options
 */
export function mountChips(root, options) {
    const disabled = Boolean(options.disabled);
    root.innerHTML = `
<div class="flex gap-1.5 min-w-max pb-1">
  ${PROMPT_CATALOG.map((item) => {
        const label = item.needs_part_number
            ? item.label.replace('{part_number}', '…')
            : item.label;
        const short = shorten(label, 18);
        return `<button type="button"
          class="shrink-0 px-2 py-1 text-[10px] border border-line text-ink-muted hover:border-brand-active hover:text-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed rounded-sm"
          data-prompt-id="${item.id}"
          title="${escAttr(label)}"
          ${disabled ? 'disabled' : ''}>${esc(short)}</button>`;
    }).join('')}
</div>`;

    root.querySelectorAll('[data-prompt-id]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-prompt-id');
            const item = PROMPT_CATALOG.find((p) => p.id === id);
            if (!item) return;
            options.onPick(item, item.label);
        });
    });
}

/**
 * @param {HTMLElement} root
 * @param {boolean} disabled
 */
export function setChipsDisabled(root, disabled) {
    root.querySelectorAll('button').forEach((btn) => {
        btn.disabled = Boolean(disabled);
    });
}

/**
 * @param {HTMLElement} root
 * @param {boolean} visible
 */
export function setChipsVisible(root, visible) {
    if (!root) return;
    root.classList.toggle('hidden', !visible);
}

function shorten(text, max) {
    const s = String(text || '');
    if (s.length <= max) return s;
    return `${s.slice(0, max - 1)}…`;
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function escAttr(value) {
    return esc(value).replace(/"/g, '&quot;');
}
