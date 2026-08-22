/**
 * Actions 渲染与执行（NAVIGATE 深链 / WORKFLOW 占位）
 */

import { can } from '../../permissions.js?v=9';

/**
 * @param {object[]} actions
 * @returns {string}
 */
export function renderActionsHtml(actions) {
    if (!Array.isArray(actions) || actions.length === 0) return '';

    const items = actions
        .map((action) => {
            if (!action || !action.action_id) return '';
            const permitted = !action.permission || can(action.permission);
            const disabled = !permitted;
            const title = disabled ? '无权限' : escAttr(action.label || action.action_id);
            return `<button type="button"
              data-llm-action-id="${escAttr(action.action_id)}"
              class="inline-flex items-center justify-center gap-1 px-2 py-1 text-[10px] font-medium border rounded-sm transition-colors
                     ${disabled
        ? 'border-[#2c2c2c] text-[#484848] cursor-not-allowed opacity-50'
        : 'border-[#d32f2f]/40 text-[#ff8a80] hover:bg-[#1A080A] hover:border-[#d32f2f]'}"
              ${disabled ? 'disabled' : ''}
              title="${title}">${esc(action.label || action.action_id)}</button>`;
        })
        .filter(Boolean)
        .join('');

    if (!items) return '';

    return `
<div class="mt-2 pt-2 border-t border-[#222222]">
  <div class="text-[9px] text-[#555555] tracking-wide mb-1.5">下一步</div>
  <div class="flex flex-wrap gap-1.5">${items}</div>
</div>`;
}

/**
 * @param {object} action
 * @param {{ onNavigate?: () => void }} [options]
 */
export function executeAction(action, options = {}) {
    if (!action) return;

    if (action.permission && !can(action.permission)) {
        window.showToast?.('无此操作权限', 'warning');
        return;
    }

    const type = String(action.type || 'NAVIGATE').toUpperCase();

    if (type === 'NAVIGATE') {
        const target = String(action.target || '').trim();
        if (!target) {
            window.showToast?.('跳转目标无效', 'warning');
            return;
        }
        window.location.hash = target.startsWith('#') ? target.slice(1) : target;
        if (typeof options.onNavigate === 'function') {
            options.onNavigate();
        }
        return;
    }

    if (type === 'REUSE_EXPLANATION') {
        const text = String(action.params?.text || action.label || '').trim();
        if (text && navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(text).then(
                () => window.showToast?.('已复制到剪贴板', 'success'),
                () => window.showToast?.('复制失败', 'error'),
            );
        }
        return;
    }

    if (type === 'WORKFLOW') {
        window.showToast?.('工作流动作即将上线', 'warning');
        return;
    }

    window.showToast?.('未知动作类型', 'warning');
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '-');
}

function escAttr(value) {
    return esc(value).replace(/'/g, '&#39;');
}
