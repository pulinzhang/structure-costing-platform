/**
 * 冲压检具费列表 — Brabus Carbon & Precision Dark
 * 布局对齐零件列表：HUD + 胶囊筛选（默认收起）
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_FILTER, FILTER_LABEL, BTN_GHOST, HUD_BAND, OPS_TH, BTN_SOLID, BTN_SOLID_DANGER } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=4';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=6';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}



export function gaugeFeeListTemplate() {
    const canDelete = canOp('op:stamping-gauge-fee:delete');
    const canExport = canOp('op:stamping-gauge-fee:export');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: '检具费合计',
                                pulse: true,
                                valueHtml: '<span id="gflHudTotalFee">—</span>',
                                unit: '万',
                                meta: '当前筛选',
                            })}
                            ${hudKpiCardHtml({
                                title: '档案',
                                valueHtml: '<span id="gflHudTotal">—</span>',
                                unit: '条',
                                metaHtml: '生效 <span id="gflHudEffectiveCount">—</span><span class="text-ink-faint mx-1">/</span>失效 <span id="gflHudInvalidCount">—</span>',
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${canDelete ? moreMenuShellHtml({
                                wrapId: 'gflMoreWrap',
                                btnId: 'gflMoreBtn',
                                menuId: 'gflMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'gflDeleteScopeBtn', label: '批量删除', danger: true }),
                            }) : ''}
                            ${canExport ? `
                            <button type="button" id="gflExportBtn"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>` : ''}
                        </div>
                    </div>
                    <div class="text-[11px] font-mono text-ink-faint truncate">
                        查询范围：<span id="gflHudScope" class="text-ink-muted">全部范围</span>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'gfl',
                        searchId: 'gflSearchBtn',
                        capsules: [
                            { capsuleId: 'gflCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'gflCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'gflCapsuleStatus', idleLabel: '全部状态' },
                        ],
                        fieldsHtml: [
                            filterSelect('gflLocation', '基地'),
                            filterSelect('gflVehicle', '项目'),
                            filterInput('gflPartNumber', '零件号', '短号或完整零件号'),
                            `<label class="space-y-1">
                                <span class="${FILTER_LABEL}">状态</span>
                                <select id="gflStatus"
                                        class="w-32 ${HUD_FILTER}">
                                    <option value="">全部</option>
                                    <option value="effective">生效</option>
                                    <option value="invalid">失效</option>
                                </select>
                            </label>`,
                            `<button id="gflResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '筛选均可选。批量删除须同时选定基地和项目。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'gfl',
                    bodyId: 'gflTableBody',
                    minWidth: '1000px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 80px;">
                            <col style="width: 80px;">
                            <col style="width: 72px;">
                            <col style="width: 160px;">
                            <col style="width: 110px;">
                            <col style="width: 110px;">
                            <col style="width: 72px;">
                            <col style="width: 88px;">`,
                    headHtml: `
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">检具费（万）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">分摊（万台）</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无检具费', hint: '先选基地 + 项目下载模板并上传' },
                    loading: true,
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="gflEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="gflEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">编辑检具费</h5>
                </div>
                <button type="button" id="gflCloseEdit" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="gflEditForm" class="space-y-4">
                    <input type="hidden" id="gflEditId" value="">
                    <p id="gflEditScope" class="text-[11px] font-mono text-ink-muted"></p>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">检具费（万元） <span class="text-brand-hud">*</span></label>
                        <input type="text" id="gflEditGaugeFee" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 0.8" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">项目分摊数量（万台） <span class="text-brand-hud">*</span></label>
                        <input type="text" id="gflEditAllocQty" required inputmode="numeric"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 10" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">状态 <span class="text-brand-hud">*</span></label>
                        <select id="gflEditStatus" required
                                class="w-full ${HUD_FILTER}">
                            <option value="effective">生效</option>
                            <option value="invalid">失效</option>
                        </select>
                    </div>
                    <p class="text-[10px] text-ink-dim">基地、项目、零件号不可改；名称以模具布点为准。</p>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="gflCancelEdit"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="gflSubmitEdit"
                        class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="gflDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[380px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="gflDeleteDrawer" style="display:none;">
            <div class="px-5 py-3.5 border-b border-line bg-app-surface">
                <h5 class="text-xs font-semibold text-ink" id="gflDeleteTitle">确认删除</h5>
            </div>
            <div class="p-5 text-[12px] text-ink-muted">
                <input type="hidden" id="gflDeleteId" value="">
                <input type="hidden" id="gflDeleteMode" value="">
                <p id="gflDeleteHint"></p>
                <p class="mt-2 text-[11px] text-ink-dim">不影响冲压工艺。</p>
            </div>
            <div class="mt-auto px-5 py-3 border-t border-line flex justify-end gap-2">
                <button type="button" id="gflCancelDelete" class="${BTN_GHOST}">取消</button>
                <button type="button" id="gflConfirmDelete" class="${BTN_SOLID_DANGER}">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:stamping-gauge-fee:update');
    const canDelete = canOp('op:stamping-gauge-fee:delete');
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
    return records
        .map((record) => {
            const isEffective = record.status === 'effective';
            const statusClass = isEffective
                ? 'text-ok bg-ok/20 px-1.5 py-0.5'
                : 'text-ink-muted bg-app-elevated px-1.5 py-0.5';
            const scope = `${record.location} / ${record.vehicle_model} / ${record.part_number}`;
            const editBtn = canUpdate
                ? opsIconButtonHtml({
                    action: 'edit',
                    extraClass: 'edit-btn',
                    title: '编辑',
                    icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                    attrs: `data-id="${esc(record.id)}"`,
                })
                : '';
            const deleteBtn = canDelete
                ? opsIconButtonHtml({
                    action: 'delete',
                    extraClass: 'delete-btn',
                    danger: true,
                    title: '删除',
                    icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                    attrs: `data-id="${esc(record.id)}" data-scope="${esc(scope)}"`,
                })
                : '';
            return hudRowHtml({
                cellsHtml: `
            <td class="px-2 py-2 overflow-hidden text-[12px] font-semibold text-ink truncate" title="${esc(record.location)}">${esc(record.location)}</td>
            <td class="px-2 py-2 overflow-hidden text-[14px] font-bold text-ink truncate" title="${esc(record.vehicle_model)}">${esc(record.vehicle_model)}</td>
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(record.part_number)}</td>
            <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(record.part_number, record.part_name)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">${esc(fmtNum(record.gauge_fee, 4))}</td>
            <td class="${numCell}">${esc(fmtNum(record.allocation_qty, 0))}</td>
            <td class="px-1 py-2 text-center"><span class="text-[9px] font-medium ${statusClass}">${esc(record.status_label || record.status)}</span></td>`,
                opsHtml: `${editBtn}${deleteBtn}`,
            });
        })
        .join('');
}

export function updateGaugeFeeHudScope() {
    const location = document.getElementById('gflLocation')?.value || '';
    const vehicle = document.getElementById('gflVehicle')?.value || '';
    const part = document.getElementById('gflPartNumber')?.value.trim() || '';
    const scopeEl = document.getElementById('gflHudScope');
    if (scopeEl) {
        const bits = [location, vehicle].filter(Boolean);
        if (part) bits.push(part);
        scopeEl.textContent = bits.length ? bits.join(' · ') : '全部范围';
    }
}

export function updateGaugeFeeHud(summary) {
    const data = summary && typeof summary === 'object' ? summary : {};
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const hasCount = data.total_count != null;
    setText('gflHudTotalFee', hasCount ? fmtNum(data.total_gauge_fee, 4) : '—');
    setText('gflHudEffectiveCount', hasCount ? String(data.effective_count ?? 0) : '—');
    setText('gflHudTotal', hasCount ? String(data.total_count) : '—');
    setText('gflHudInvalidCount', hasCount ? String(data.invalid_count ?? 0) : '—');
    updateGaugeFeeHudScope();
}

