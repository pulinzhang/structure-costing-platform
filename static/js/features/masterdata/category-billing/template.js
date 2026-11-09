/**
 * 计费管理 — 左分类列表，右费用勾选表
 */

import { HUD_SHELL, HUD_BAND, BTN_HUD_CREATE } from '../../../ui/classes.js?v=15';
import { hudTableHtml, hudRowHtml } from '../../../ui/hud-table.js?v=3';
import { basisLabel, formatChargeRate } from '../fee-archive/template.js?v=1';

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function categoryBillingTemplate() {
    return `
        <div class="cb-split">
            <aside class="${HUD_SHELL}">
                <div class="px-4 py-3 border-b border-line-subtle">
                    <h2 class="text-[13px] font-semibold text-ink tracking-wide">总成分类</h2>
                    <p class="mt-1 text-[11px] text-ink-faint">初始化已按现网勾好，可再改</p>
                </div>
                <div id="cbCategoryList" class="max-h-[70vh] overflow-y-auto"></div>
            </aside>
            <section class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="min-w-0">
                            <h2 id="cbFeeTitle" class="text-[13px] font-semibold text-ink tracking-wide">费用</h2>
                            <p id="cbFeeHint" class="mt-1 text-[11px] text-ink-faint">勾选后统一保存。计费率来自费用档案</p>
                        </div>
                        <button type="button" id="cbSaveBtn" class="${BTN_HUD_CREATE} disabled:opacity-40 disabled:cursor-not-allowed" disabled>
                            保存
                        </button>
                    </div>
                </div>
                ${hudTableHtml({
                    prefix: 'cb',
                    pagination: false,
                    minWidth: '640px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 44px;">
                            <col style="width: 34%;">
                            <col style="width: 16%;">
                            <col style="width: 16%;">
                            <col style="width: 18%;">`,
                    headHtml: `
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-center">
                                    <input type="checkbox" id="cbCheckAll" class="brabus-check" aria-label="全选费用" disabled>
                                </th>
                                <th class="record-key px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">费用</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">口径</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">计费率</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>`,
                    empty: {
                        title: '暂无费用',
                        hint: '先到费用档案维护',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </section>
        </div>
    `;
}

export function renderCategoryList(categories, activeId, counts) {
    const list = document.getElementById('cbCategoryList');
    if (!list) return;
    if (!categories.length) {
        list.innerHTML = '<p class="px-4 py-8 text-center text-[11px] text-ink-faint">先维护总成分类</p>';
        return;
    }
    list.innerHTML = categories.map((row) => {
        const selected = String(row.id) === String(activeId);
        const count = counts.get(String(row.id)) || 0;
        const dirty = counts.get(`dirty:${row.id}`) === 1;
        const meta = row.is_enabled
            ? `已选 ${count}${dirty ? ' · 未保存' : ''}`
            : '已停用';
        const buttonClass = selected
            ? 'cb-category w-full text-left px-4 py-3 border-b border-line-subtle bg-brand-hud/10 border-l-2 border-l-brand-hud'
            : 'cb-category w-full text-left px-4 py-3 border-b border-line-subtle border-l-2 border-l-transparent hover:bg-app-rowhover';
        const nameClass = row.is_enabled ? 'text-ink' : 'text-ink-faint';
        return `
            <button type="button" class="${buttonClass}" data-category="${esc(row.id)}">
                <div class="text-[13px] font-semibold ${nameClass} truncate">${esc(row.name)}</div>
                <div class="mt-0.5 text-[10px] font-mono text-ink-faint">${esc(meta)}</div>
            </button>`;
    }).join('');
}

export function renderFeeRows(fees, savedIds, readOnly) {
    if (!fees.length) return '';
    return fees.map((fee) => {
        const saved = savedIds.has(String(fee.id));
        const locked = readOnly || (!fee.is_enabled && !saved);
        const checked = saved ? ' checked' : '';
        const disabled = locked ? ' disabled' : '';
        const current = saved ? ' data-current="1"' : '';
        const nameClass = fee.is_enabled ? 'text-ink' : 'text-ink-faint';
        const status = fee.is_enabled ? '启用' : '已停用';
        return hudRowHtml({
            attrs: current,
            cellsHtml: `
            <td class="px-2 py-2 text-center">
                <input type="checkbox" class="cb-fee brabus-check" data-fee-id="${esc(fee.id)}"
                       aria-label="选用${esc(fee.name)}"${checked}${disabled}>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold ${nameClass} truncate" title="${esc(fee.name)}">${esc(fee.name)}</div>
                <div class="text-[10px] font-mono text-ink-faint truncate">${esc(fee.code)}</div>
            </td>
            <td class="px-2 py-2 text-[11px] text-ink-muted">${esc(basisLabel(fee.charge_basis))}</td>
            <td class="px-2 py-2 text-right text-[12px] font-mono text-ink">${esc(formatChargeRate(fee.charge_rate))}</td>
            <td class="px-2 py-2 text-[11px] ${fee.is_enabled ? 'text-ink' : 'text-ink-faint'}">${status}</td>`,
        });
    }).join('');
}

export function paintFeeHeading(category, readOnly) {
    const title = document.getElementById('cbFeeTitle');
    const hint = document.getElementById('cbFeeHint');
    if (title) title.textContent = category ? category.name : '费用';
    if (!hint) return;
    if (!category) {
        hint.textContent = '先在左侧选择总成分类';
        return;
    }
    if (!category.is_enabled) {
        hint.textContent = '该分类已停用。先到总成分类启用，再改勾选';
        return;
    }
    if (readOnly) {
        hint.textContent = '当前账号不能修改勾选';
        return;
    }
    hint.textContent = '五项已按现网勾好。改完点保存。计费率来自费用档案';
}
