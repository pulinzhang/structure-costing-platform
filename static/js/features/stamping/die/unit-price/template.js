/**
 * 冲压模具单价档案 — HUD 密表 + 抽屉增改
 */

import { HUD_SHELL, DRAWER_BACKDROP, DRAWER_SHELL, HUD_BAND, OPS_TH, filterSelect, BTN_GHOST, FILTER_LABEL, HUD_FILTER, BTN_SOLID_DANGER, BTN_HUD_CREATE, BTN_SOLID } from '../../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';


function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

export function dieUnitPriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div>
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">模具单价</h2>
                            <p class="text-[11px] text-ink-faint">按基地 + 项目维护钢板模 / 级进模单价与分摊台数，不必先有冲压工艺</p>
                        </div>
                        <button type="button" id="dupAddBtn"
                                class="${BTN_HUD_CREATE}">
                            ${window.svgIcon('plus', 'w-3 h-3')}
                            新增
                        </button>
                    </div>
                </div>
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'dupList',
                        capsules: [
                            { capsuleId: 'dupListCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'dupListCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'dupListCapsuleStatus', idleLabel: '全部状态' },
                        ],
                        fieldsHtml: [
                            filterSelect('dupListLocation', '基地'),
                            filterSelect('dupListVehicle', '项目'),
                            `<label class="space-y-1">
                                <span class="${FILTER_LABEL}">状态</span>
                                <select id="dupListStatus" class="w-32 ${HUD_FILTER}">
                                    <option value="">全部</option>
                                    <option value="effective">生效</option>
                                    <option value="invalid">失效</option>
                                </select>
                            </label>`,
                            `<button id="dupListResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'dupList',
                    bodyId: 'dupTableBody',
                    minWidth: '920px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">
                            <col style="width: 120px;">
                            <col style="width: 120px;">
                            <col style="width: 100px;">
                            <col style="width: 72px;">
                            <col style="width: 120px;">
                            <col style="width: 88px;">`,
                    headHtml: `
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">钢板模（万/吨）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">级进模（万/吨）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">分摊（万台）</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">更新</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        className: 'py-16',
                        html: `<div class="text-ink-faint mb-2">${window.svgIcon('inbox')}</div>
                    <p class="text-[12px] text-ink-muted mb-1">暂无模具单价</p>
                    <p class="text-[11px] text-ink-faint">按基地 + 项目新增档案；新项目可直接填写</p>`,
                    },
                    loading: {
                        html: `<div class="w-5 h-5 border-2 border-line border-brand-hud rounded-full animate-spin"></div>
                    <span class="text-[11px] text-ink-faint">加载中</span>`,
                        className: 'flex-col gap-2 bg-app-hud',
                    },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity" id="dupEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dupEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="dupEditTitle">新增模具单价</h5>
                </div>
                <button type="button" id="dupCloseEdit" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="dupEditForm" class="space-y-4">
                    <input type="hidden" id="dupEditId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">基地 <span class="text-brand-hud">*</span></label>
                        <select id="dupEditLocation" required
                                class="w-full ${HUD_FILTER}">
                            <option value="">请选择</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">项目 <span class="text-brand-hud">*</span></label>
                        <input id="dupEditVehicle" name="vehicle_model" list="dupEditVehicleOptions" required
                               placeholder="已有项目可下拉，新项目请直接填写"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                        <datalist id="dupEditVehicleOptions"></datalist>
                        <p id="dupEditScopeHint" class="text-[10px] text-ink-dim mt-1">已有项目可下拉，新项目请直接填写。同一基地+项目只能有一条。</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">钢板模单价（万元/吨） <span class="text-brand-hud">*</span></label>
                        <input type="text" id="dupEditPlatePrice" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 3.36" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">级进模单价（万元/吨） <span class="text-brand-hud">*</span></label>
                        <input type="text" id="dupEditProgressivePrice" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 5.15" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">项目分摊数量（万台） <span class="text-brand-hud">*</span></label>
                        <input type="text" id="dupEditAllocQty" required inputmode="numeric"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 10" value="10" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">状态 <span class="text-brand-hud">*</span></label>
                        <select id="dupEditStatus" required
                                class="w-full ${HUD_FILTER}">
                            <option value="effective">生效</option>
                            <option value="invalid">失效</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="dupCancelEdit"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="dupSubmitEdit"
                        class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="dupDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[380px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dupDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5">
                    <span class="w-[3px] h-3.5 bg-danger inline-block"></span>
                    确认删除
                </h5>
                <button type="button" id="dupCloseDelete" class="w-8 h-8 text-ink-dim hover:text-ink">✕</button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="dupDeleteId" value="">
                <p class="text-[12px] text-ink-muted mb-2">确定删除 <span id="dupDeleteScope" class="font-mono text-ink"></span> 的模具单价？</p>
                <p class="text-[11px] text-ink-dim">只删档案，不影响模具布点。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="dupCancelDelete"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="dupConfirmDelete"
                        class="${BTN_SOLID_DANGER}">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:stamping-die-unit-price:update');
    const canDelete = canOp('op:stamping-die-unit-price:delete');
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';

    return records
        .map((record) => {
            const isEffective = record.status === 'effective';
            const statusClass = isEffective
                ? 'text-ok bg-ok/20 px-1.5 py-0.5'
                : 'text-ink-muted bg-app-elevated px-1.5 py-0.5';
            const updated = formatDateTime(record.updated_at);
            const scope = `${record.location} / ${record.vehicle_model}`;
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
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[12px] font-semibold text-ink truncate" title="${esc(record.location)}">${esc(record.location)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate" title="${esc(record.vehicle_model)}">${esc(record.vehicle_model)}</div>
            </td>
            <td class="${numCell}">${esc(fmtNum(record.steel_plate_unit_price, 4))}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">${esc(fmtNum(record.progressive_die_unit_price, 4))}</td>
            <td class="${numCell}">${esc(fmtNum(record.allocation_qty, 0))}</td>
            <td class="px-1 py-2 text-center">
                <span class="text-[9px] font-medium ${statusClass}">${esc(record.status_label || record.status)}</span>
            </td>
            <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">
                <div>${esc(record.updated_by || '—')}</div>
                <div>${esc(updated)}</div>
            </td>`,
                opsHtml: `${editBtn}${deleteBtn}`,
            });
        })
        .join('');
}


function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value);
    if (text.length >= 16) return text.slice(0, 16).replace('T', ' ');
    return text;
}
