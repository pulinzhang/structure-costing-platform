/**
 * 总成核价一览 — Brabus Carbon & Precision Dark（对齐冲压零件价格一览 HUD）
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, BTN_GHOST, TH_ROW, OPS_TH, HUD_LED, BTN_SOLID } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=4';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=6';
import { CONFIRM_LABELS, KIND_LABELS } from '../../../bom/procurement-object/labels.js?v=4';
import {
    partShortCodeCellHtml,
    partNumberNameCellHtml,
    resolveBomNodeShortCode,
} from '../../../../domain/part-identity.js?v=5';

export function assemblyCostListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <!-- HUD 战术数据看板 + 操作 -->
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: '总成本',
                                pulse: true,
                                valueHtml: '¥ <span id="lacHudGrand">—</span>',
                                meta: '总费用合计',
                            })}
                            ${hudKpiCardHtml({
                                title: '总成',
                                valueHtml: '<span id="lacHudTotal">—</span>',
                                unit: '件',
                                footer: [{ label: '件均', valueHtml: '¥ <span id="lacHudAvg">—</span>' }],
                            })}
                            ${hudKpiCardHtml({
                                title: '成本构成',
                                rows: [
                                    { label: '材料费', valueHtml: '¥ <span id="lacHudMaterial">—</span> <span id="lacHudMaterialShare" class="text-ink-faint">—</span>' },
                                    { label: '焊接费', valueHtml: '¥ <span id="lacHudWelding">—</span> <span id="lacHudWeldingShare" class="text-ink-faint">—</span>' },
                                ],
                            })}
                            ${hudKpiCardHtml({
                                title: '审核进度',
                                valueHtml: '<span id="lacHudPending">—</span>',
                                unit: '条待审',
                                footer: [{ label: '已审', valueHtml: '<span id="lacHudApproved">—</span> 条' }],
                            })}
                        </div>
                        <div class="flex flex-col items-end gap-2 shrink-0">
                            <div class="flex items-center gap-1.5">
                                ${moreMenuShellHtml({
                                    wrapId: 'lacMoreWrap',
                                    btnId: 'lacMoreBtn',
                                    menuId: 'lacMoreMenu',
                                    itemsHtml: [
                                        moreMenuItemHtml({ id: 'lacBatchApproveBtn', label: '批量审核' }),
                                        moreMenuItemHtml({ id: 'lacBatchReverseBtn', label: '批量反审核' }),
                                        moreMenuItemHtml({ id: 'lacBatchDeleteBtn', label: '批量删除', danger: true }),
                                    ].join(''),
                                })}
                                <div class="flex items-center gap-1.5" role="group" aria-label="一览视图">
                                    <button id="lacViewFinanceBtn" type="button"
                                            class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-brand-hud/10 border border-brand-hud/50 text-brand-hud transition-all">
                                        财务（总成）
                                    </button>
                                    <button id="lacViewProcurementBtn" type="button"
                                            class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-transparent border border-line-hud text-ink-dim hover:text-ink transition-all">
                                        采购
                                    </button>
                                </div>
                            </div>
                            <div class="flex items-center gap-1.5 flex-wrap justify-end">
                            <button id="lacExportBtn" type="button"
                                    class="${BTN_GHOST}"
                                    title="导出成品核价（一览 + 材料明细 + 焊接费 + 间接费用；金额为系统快照）">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                <span id="lacExportBtnLabel">总成核价</span>
                            </button>
                            <button id="lacExportBundleBtn" type="button"
                                    class="${BTN_GHOST}"
                                    title="导出月度核对：成品核价（总成）+ 冲压零件核价 + 焊接费 + 加工费 + 钢材联动等。须选定年/月/基地/项目；版本可不选（空=该月全部）。">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                月度核对
                            </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'lac',
                        searchId: 'lacSearchBtn',
                        capsules: [
                            { capsuleId: 'lacCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'lacCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'lacCapsuleVehicle', idleLabel: '全部项目' },
                        ],
                        fieldsHtml: [
                            filterSelect('lacYearFilter', '年度'),
                            filterSelect('lacMonthFilter', '月份'),
                            filterSelect('lacLocationFilter', '基地'),
                            filterSelect('lacVehicleModelFilter', '项目'),
                            filterSelect('lacBomVersionFilter', '版本'),
                            filterSelect('lacAuditFilter', '审核状态'),
                            filterSelect('lacCalcFilter', '计算状态'),
                            filterInput('lacPartNumberFilter', '零件号', '短号或完整零件号'),
                            `<button id="lacResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量删除 / 审核 / 反审核 / 零件成本 / 月度核对须选定年度、月份、基地、项目；版本可不选（同月可有多个工程变更字）。反审核后可重新计算覆盖。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'lac',
                    tableId: 'lacDataTable',
                    colgroupId: 'lacColgroup',
                    theadId: 'lacTableHead',
                    minWidth: '1252px',
                    colgroupHtml: `
                            <col style="width:3px">
                            <col style="width:96px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:100px">
                            <col style="width:88px">
                            <col style="width:72px">
                            <col style="width:88px">
                            <col style="width:80px">
                            <col style="width:100px">
                            <col style="width:52px">
                            <col style="width:52px">
                            <col style="width:44px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">年月/基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-dim">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目/版本</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">材料</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">焊接费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-dim">月总账</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">间接</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">总费用</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">核算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无总成核价数据', hint: '请先完成总成核价计算，或调整筛选条件' },
                    loading: true,
                })}
            </div>
        </div>

        ${batchAuditDrawerHtml()}
    `;
}

function batchAuditDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="lacBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="lacBatchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="lacBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeLacBatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="lacBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="lacBatchAuditFilterSummary"></div>
                <p id="lacBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="lacBatchAuditOperatorLabel">操作人</label>
                    <div id="lacBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">
                        —
                    </div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="lacBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="lacBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelLacBatchAuditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmLacBatchAuditBtn" class="${BTN_SOLID}">
                    确认提交
                </button>
            </div>
        </div>
    `;
}



function partIdentityTds(row) {
    const shortNo = resolveBomNodeShortCode(row.part_number, { level: row.level });
    return `
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(row.part_number, shortNo)}</td>
            <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(row.part_number, row.part_name)}</td>`;
}

function calcStatusBadge(status) {
    if (status === 'ok') return '';
    if (status === 'partial') {
        return `<span class="text-warn font-bold text-[9px] px-1 bg-warn/10 border border-warn/40/25">部分</span>`;
    }
    if (status === 'failed') {
        return `<span class="text-brand-hud font-bold text-[9px] px-1 bg-brand-hud/10 border border-brand-hud/25">失败</span>`;
    }
    return `<span class="text-[9px] text-ink-faint">${esc(status || '')}</span>`;
}

function auditBadge(status) {
    if (!status || status === 'pending') return '';
    if (status === 'approved') {
        return `<span class="text-[9px] text-ink-faint">已审</span>`;
    }
    return `<span class="text-[9px] text-ink-faint">${esc(status)}</span>`;
}

export function renderLacRows(records, view = 'finance') {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const num = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
    const confirmLabel = CONFIRM_LABELS;
    return records.map((row) => {
        const ym = esc(fmtPeriod(row.year, row.month));
        const location = esc(row.location) || '—';
        const opsHtml = `${opsIconButtonHtml({
            extraClass: 'btn-open-detail',
            title: '查看详情',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
            attrs: `data-id="${esc(row.id)}"`,
        })}${opsIconButtonHtml({
            extraClass: 'btn-open-restore',
            title: '计算过程',
            icon: window.svgIcon('file-earmark-text', 'w-3.5 h-3.5'),
            attrs: `data-year="${esc(row.year)}" data-month="${esc(row.month)}" data-part-number="${esc(row.part_number)}" data-location="${esc(row.location || '')}" data-vehicle-model="${esc(row.vehicle_model || '')}" data-bom-version="${esc(row.bom_version || '')}"`,
        })}`;
        if (view === 'procurement') {
            return hudRowHtml({
                extraClass: 'lac-row',
                cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-ink text-[11px] tabular-nums">${ym}</div>
                <div class="text-ink-faint text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
            </td>
            ${partIdentityTds(row)}
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-ink-muted text-[10px] truncate">${esc(KIND_LABELS[row.object_kind] || row.object_kind || '—')}</div>
                <div class="text-ink-faint text-[9px] mt-0.5">第${esc(row.level ?? 0)}层</div>
            </td>
            <td class="${num}">${fmtNum(row.material_amount, 4)}</td>
            <td class="${num}" title="数据为焊接费用（含电泳、黑漆等）">${Number(row.welding_amount) === 0 ? '' : fmtNum(row.welding_amount, 4)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                <span>${fmtNum(row.total_amount, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center text-[9px] text-ink-muted">${esc(confirmLabel[row.confirm_status] || row.confirm_status || '—')}</td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(row.calc_status)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>`,
                opsHtml,
            });
        }
        return hudRowHtml({
            extraClass: 'lac-row',
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-ink text-[11px] tabular-nums">${ym}</div>
                <div class="text-ink-faint text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
            </td>
            ${partIdentityTds(row)}
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-ink-muted text-[10px] truncate" title="${esc(row.vehicle_model || '')}">${esc(row.vehicle_model || '—')}</div>
                <div class="text-ink-faint text-[9px] mt-0.5 font-mono truncate">${esc(row.bom_version || '—')}</div>
            </td>
            <td class="${num}">${fmtNum(row.material_amount, 4)}</td>
            <td class="${num}">${fmtNum(row.welding_amount, 4)}</td>
            <td class="${num} text-ink-muted font-semibold">${fmtNum(row.total_amount, 4)}</td>
            <td class="${num}">${fmtNum(row.indirect_amount, 4)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                <span>${fmtNum(row.grand_total, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(row.calc_status)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>`,
            opsHtml,
        });
    }).join('');
}

export function updateLacTableHead(view = 'finance') {
    const head = document.getElementById('lacTableHead');
    if (!head) return;
    const table = document.getElementById('lacDataTable');
    const colgroup = document.getElementById('lacColgroup');
    const th = (label, extra = '') =>
        `<th class="px-2 py-2 text-[9px] font-medium tracking-[0.06em] text-ink-faint ${extra}">${label}</th>`;
    const identityHeads = `
                ${th('短代码', 'text-left tracking-[0.08em] text-ink-muted')}
                ${th('零件', 'text-left tracking-[0.08em] text-ink-dim')}`;
    if (view === 'procurement') {
        if (table) table.style.minWidth = '1180px';
        if (colgroup) {
            colgroup.innerHTML = `
                            <col style="width:3px">
                            <col style="width:96px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:100px">
                            <col style="width:88px">
                            <col style="width:88px">
                            <col style="width:100px">
                            <col style="width:52px">
                            <col style="width:52px">
                            <col style="width:52px">
                            <col style="width:44px">`;
        }
        head.innerHTML = `
            <tr class="${TH_ROW}">
                <th class="p-0"></th>
                ${th('年月/基地', 'text-left tracking-[0.08em]')}
                ${identityHeads}
                ${th('对象/层', 'text-left tracking-[0.08em]')}
                ${th('材料成本', 'text-right')}
                ${th('焊接费/电泳黑漆等', 'text-right leading-tight')}
                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">总成本</th>
                ${th('确认', 'text-center')}
                ${th('核算', 'text-center')}
                ${th('审核', 'text-center')}
                <th class="${OPS_TH}" aria-label="操作"></th>
            </tr>`;
        return;
    }
    if (table) table.style.minWidth = '1252px';
    if (colgroup) {
        colgroup.innerHTML = `
                            <col style="width:3px">
                            <col style="width:96px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:100px">
                            <col style="width:88px">
                            <col style="width:72px">
                            <col style="width:88px">
                            <col style="width:80px">
                            <col style="width:100px">
                            <col style="width:52px">
                            <col style="width:52px">
                            <col style="width:44px">`;
    }
    head.innerHTML = `
            <tr class="${TH_ROW}">
                <th class="p-0"></th>
                ${th('年月/基地', 'text-left tracking-[0.08em]')}
                ${identityHeads}
                ${th('项目/版本', 'text-left tracking-[0.08em]')}
                ${th('材料', 'text-right')}
                ${th('焊接费', 'text-right')}
                ${th('月总账', 'text-right text-ink-dim')}
                ${th('间接', 'text-right')}
                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">总费用</th>
                ${th('核算', 'text-center')}
                ${th('审核', 'text-center')}
                <th class="${OPS_TH}" aria-label="操作"></th>
            </tr>`;
}

export function updateLacHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const fmtMoney = (value) => {
        const fixed = formatDecimalFixed(value, 2, { allowNegative: true });
        return fixed == null ? '—' : withThousandsSep(fixed);
    };
    const toAmount = (value) => {
        if (value == null || value === '') return null;
        const amount = Number(value);
        return Number.isFinite(amount) ? amount : null;
    };
    const fmtShare = (part, whole) => {
        if (part == null || whole == null || whole === 0) return '—';
        return `${((part / whole) * 100).toFixed(1)}%`;
    };
    const totalCount = Number(data.total_count ?? total ?? 0);
    const totalCost = toAmount(data.grand_total_sum);
    const materialAmount = toAmount(data.material_amount_sum);
    const weldingAmount = toAmount(data.welding_amount_sum);

    setText('lacHudGrand', fmtMoney(data.grand_total_sum));
    setText('lacHudTotal', totalCount.toLocaleString('zh-CN'));
    setText('lacHudAvg', fmtMoney(data.avg_grand_total));
    setText('lacHudMaterial', fmtMoney(data.material_amount_sum));
    setText('lacHudMaterialShare', fmtShare(materialAmount, totalCost));
    setText('lacHudWelding', fmtMoney(data.welding_amount_sum));
    setText('lacHudWeldingShare', fmtShare(weldingAmount, totalCost));
    setText('lacHudPending', Number(data.pending_count ?? 0).toLocaleString('zh-CN'));
    setText('lacHudApproved', Number(data.approved_count ?? 0).toLocaleString('zh-CN'));
}


