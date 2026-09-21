/**
 * Stamping Part Cost List Template
 * 冲压零件价格一览—Brabus Carbon & Precision Dark
 * HUD：总成本为靶心；冲压件 / 成本构成 / 审核进度为辅卡
 */

import { HUD_SHELL, BTN_GHOST, OPS_ICON, filterSelect, filterInput, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, TH_KEY, TH_TEXT, TH_NUM, TH_FOCUS, HUD_BAND, OPS_TH, HUD_LED, BTN_SOLID } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=4';
import { hudTableHtml, hudRowHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

export function partCostListTemplate() {
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
                                valueHtml: '¥ <span id="costHudTotalCost">—</span>',
                                meta: '单件成本合计',
                            })}
                            ${hudKpiCardHtml({
                                title: '冲压件',
                                valueHtml: '<span id="costHudTotal">—</span>',
                                unit: '件',
                                footer: [{ label: '件均', valueHtml: '¥ <span id="costHudAvg">—</span>' }],
                            })}
                            ${hudKpiCardHtml({
                                title: '成本构成',
                                rows: [
                                    { label: '材料费', valueHtml: '¥ <span id="costHudMaterial">—</span> <span id="costHudMaterialShare" class="text-ink-faint">—</span>' },
                                    { label: '加工费', valueHtml: '¥ <span id="costHudProcessFee">—</span> <span id="costHudProcessFeeShare" class="text-ink-faint">—</span>' },
                                ],
                            })}
                            ${hudKpiCardHtml({
                                title: '审核进度',
                                valueHtml: '<span id="costHudPending">—</span>',
                                unit: '条待审',
                                footer: [{ label: '已审', valueHtml: '<span id="costHudApproved">—</span> 条' }],
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'costMoreWrap',
                                btnId: 'costMoreBtn',
                                menuId: 'costMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'costBatchApproveBtn', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'costBatchReverseBtn', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'costBatchDeleteBtn', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="costExportBtn" type="button"
                                    class="${BTN_GHOST}"
                                    title="须选定项目；按当前筛选导出冲压零件核价结果（含材料费、加工费、模具费、检具费）">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'cost',
                        searchId: 'costSearchBtn',
                        capsules: [
                            { capsuleId: 'costCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'costCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'costCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'costCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'costCapsuleSupplier', idleLabel: '全部工厂' },
                        ],
                        fieldsHtml: [
                            filterSelect('costYearFilter', '年度'),
                            filterSelect('costMonthFilter', '月份'),
                            filterSelect('costLocationFilter', '基地'),
                            filterSelect('costVehicleModelFilter', '项目'),
                            filterSelect('costVersionFilter', '版本'),
                            filterSelect('costSupplierFilter', '冲压工厂'),
                            filterSelect('costAuditFilter', '审核状态'),
                            filterInput('costPartNumberFilter', '零件号', '短号或完整零件号'),
                            `<button id="costResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量审核 / 反审核按整车签字（工厂筛不影响签字范围）。批量删除与导出可按工厂收窄。导出须选定项目。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'cost',
                    tableId: 'costDataTable',
                    colgroupId: 'costColgroup',
                    minWidth: '1215px',
                    colgroupHtml: `
                            <col style="width:3px">
                            <col style="width:72px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:64px">
                            <col style="width:52px">
                            <col style="width:128px">
                            <col class="cost-mass-col hidden" style="width:68px">
                            <col class="cost-mass-col hidden" style="width:58px">
                            <col class="cost-mass-col hidden" style="width:58px">
                            <col class="cost-mass-col hidden" style="width:54px">
                            <col style="width:88px">
                            <col style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:68px">
                            <col style="width:76px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:72px">
                            <col class="cost-fee-col hidden" style="width:58px">
                            <col class="cost-fee-col hidden" style="width:58px">
                            <col class="cost-fee-col hidden" style="width:64px">
                            <col class="cost-fee-col hidden" style="width:58px">
                            <col style="width:86px">
                            <col style="width:44px">
                            <col style="width:44px">
                            <col style="width:36px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="${TH_TEXT}">年月/基地</th>
                                <th class="${TH_KEY}">短代码</th>
                                <th class="${TH_TEXT}">零件</th>
                                <th class="${TH_TEXT}" title="本月核价快照；下月废料不足可改零件后再算下月">利废</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint" title="工艺含摆剪时，材料核算把系统摆剪吨价加进钢价；金额为当月快照">摆剪</th>
                                <th class="${TH_TEXT}">材质/规格</th>
                                <th class="cost-mass-col hidden ${TH_NUM}" title="预估单件材料消耗 M (kg)">消耗</th>
                                <th class="cost-mass-col hidden ${TH_NUM}" title="零件净量">净量</th>
                                <th class="cost-mass-col hidden ${TH_NUM}" title="废料重量 O = 材料消耗−净量">废料</th>
                                <th class="cost-mass-col hidden ${TH_NUM}">利用率</th>
                                <th class="${TH_NUM}" title="钢材吨价；P=吨价/1000 为 kg">
                                    <button type="button" id="costToggleMassCols"
                                            class="inline-flex items-center justify-center w-3.5 h-3.5 mr-0.5 align-middle border border-line-hud text-ink-faint hover:text-brand-hud hover:border-brand-hud/40 transition-colors"
                                            title="展开材料量（消耗 / 净量 / 废料 / 利用率）">+</button>
                                    钢材吨价
                                </th>
                                <th class="${TH_NUM}" title="废料吨价；Q=吨价/1000 为 kg">废料吨价</th>
                                <th class="cost-breakdown-col hidden ${TH_NUM}" title="①钢材采购（含损耗）">①采购</th>
                                <th class="cost-breakdown-col hidden ${TH_NUM}" title="②损耗废料扣除（回收率）">②损耗扣</th>
                                <th class="cost-breakdown-col hidden ${TH_NUM}" title="③边角废料扣除（回收率）">③边角扣</th>
                                <th class="cost-breakdown-col hidden ${TH_NUM}" title="废料扣除合计 ②+③">废料扣合计</th>
                                <th class="${TH_NUM}" title="R = ①−②−③">
                                    <button type="button" id="costToggleBreakdownCols"
                                            class="inline-flex items-center justify-center w-3.5 h-3.5 mr-0.5 align-middle border border-line-hud text-ink-faint hover:text-brand-hud hover:border-brand-hud/40 transition-colors"
                                            title="展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）">+</button>
                                    原材料R
                                </th>
                                <th class="${TH_NUM}">加工费</th>
                                <th class="${TH_NUM}" title="年度模具费最终价（元/件）；无档案为 0">模具费</th>
                                <th class="${TH_NUM}" title="检具费（万元）÷ 分摊万台 = 元/件；无档案为 0">检具费</th>
                                <th class="${TH_NUM}" title="直接成本 = R + 加工费 + 模具费 + 检具费">直接成本</th>
                                <th class="cost-fee-col hidden ${TH_NUM}" title="直接成本 × 仓储+包装管理费用率">仓储包装</th>
                                <th class="cost-fee-col hidden ${TH_NUM}" title="直接成本 × 管理费率">管理费</th>
                                <th class="cost-fee-col hidden ${TH_NUM}" title="直接成本 × 财务费率">财务费</th>
                                <th class="cost-fee-col hidden ${TH_NUM}" title="直接成本 × 税前利润率">税前利润</th>
                                <th class="${TH_FOCUS}" title="单件成本 = 直接成本 + 仓储包装 + 管理费 + 财务费 + 税前利润">
                                    <button type="button" id="costToggleFeeCols"
                                            class="inline-flex items-center justify-center w-3.5 h-3.5 mr-0.5 align-middle border border-brand-hud/30 text-brand-hud hover:text-brand-hud hover:border-brand-hud/60 transition-colors"
                                            title="展开费率项（仓储包装 / 管理费 / 财务费 / 税前利润）">+</button>
                                    单件成本
                                </th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">核算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无零件价格数据', hint: '请先完成零件价格计算，或调整筛选条件' },
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
             id="costBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="costBatchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="costBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeCostBatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="costBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="costBatchAuditFilterSummary"></div>
                <p id="costBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="costBatchAuditOperatorLabel">操作人</label>
                    <div id="costBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">
                        —
                    </div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="costBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="costBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelCostBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded hover:border-ink-muted hover:text-ink transition-all">取消</button>
                <button type="button" id="confirmCostBatchAuditBtn" class="${BTN_SOLID}">
                    确认提交
                </button>
            </div>
        </div>
    `;
}



export function renderCostRows(records, columnFlags = {}) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const massOpen = Boolean(columnFlags.massOpen);
    const breakdownOpen = Boolean(columnFlags.breakdownOpen);
    const feeOpen = Boolean(columnFlags.feeOpen);
    const massHidden = massOpen ? '' : 'hidden';
    const breakdownHidden = breakdownOpen ? '' : 'hidden';
    const feeHidden = feeOpen ? '' : 'hidden';
    return records.map((row) => {
        const fail = row.calc_status === 'failed';
        const ym = esc(fmtPeriod(row.year, row.month));
        const location = esc(row.location) || '—';
        const supplier = esc(row.stamping_supplier) || '—';
        const num = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
        const feeNum = 'px-2 py-2 font-mono text-[9px] text-right tabular-nums text-ink-faint';
        const actionTitle = fail ? '手工干预' : '查看详情';
        const actionIcon = fail
            ? window.svgIcon('pencil', 'w-3.5 h-3.5')
            : window.svgIcon('eye', 'w-3.5 h-3.5');
        const actionTone = fail
            ? 'text-brand-hud hover:text-brand-hud'
            : 'text-ink-faint hover:text-ink-muted';
        const actionBtn = `
            <button type="button"
                    class="btn-open-detail ${OPS_ICON} ${actionTone}"
                    data-action="open-detail"
                    data-id="${esc(row.id)}" title="${actionTitle}" aria-label="${actionTitle}">
                ${actionIcon}
            </button>`;
        return hudRowHtml({
            extraClass: 'cost-row',
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-ink text-[11px] tabular-nums">${ym}</div>
                <div class="text-ink-faint text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
                <div class="text-ink-faint text-[9px] leading-tight truncate" title="${supplier}">${supplier}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(row.part_number)}</td>
            <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(row.part_number, row.part_name)}</td>
            <td class="px-2 py-2 overflow-hidden">${offalCostCell(row)}</td>
            <td class="px-1 py-2 text-center">${swingShearCostCell(row)}</td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-ink-muted text-[10px] truncate" title="${esc(row.material || '')}">${esc(row.material || '—')}</div>
                <div class="text-ink text-[10px] mt-0.5 tabular-nums truncate" title="${esc(row.thickness || '')}">${esc(row.thickness || '—')}</div>
                <div class="text-ink-faint text-[9px] mt-0.5 tabular-nums truncate" title="${esc((row.sheet_length || '—') + ' × ' + (row.sheet_width || '—'))}">${esc(row.sheet_length || '—')} × ${esc(row.sheet_width || '—')}</div>
            </td>
            <td class="cost-mass-col ${massHidden} ${num}" title="${esc(fmtNum(row.blank_weight_kg, 7))}">${fmtNum(row.blank_weight_kg, 3)}</td>
            <td class="cost-mass-col ${massHidden} ${num}" title="${esc(fmtNum(row.finished_total_kg, 7))}">${fmtNum(row.finished_total_kg, 3)}</td>
            <td class="cost-mass-col ${massHidden} ${num}" title="${esc(fmtNum(row.scrap_weight_kg, 7))}">${fmtNum(row.scrap_weight_kg, 3)}</td>
            <td class="cost-mass-col ${massHidden} ${num}">${fmtNum(row.material_utilization_pct, 1)}</td>
            <td class="${num}" title="${esc(row.is_offal_nested ? '利废：成品净重 × 废料单价' : (row.steel_mill || ''))}">
                <div class="text-ink-muted">${esc(row.steel_ton_price || '—')}</div>
                ${row.is_offal_nested
                    ? `<div class="text-[9px] text-warn font-normal mt-0.5 truncate">废料价</div>`
                    : (row.steel_mill ? `<div class="text-[9px] text-ink-faint font-normal mt-0.5 truncate">${esc(row.steel_mill)}</div>` : '')}
            </td>
            <td class="${num}">${fmtNum(row.scrap_ton_price, 0)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.material_amount_sheet, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.loss_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.process_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.scrap_amount_sheet, 2)}</td>
            <td class="${num} text-ink-muted font-semibold">${fmtNum(row.material_net_per_part, 2)}</td>
            <td class="${num}">${fmtNum(row.process_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.die_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.gauge_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.direct_cost, 2)}</td>
            <td class="cost-fee-col ${feeHidden} ${feeNum}">${fmtNum(row.finished_warehouse_packaging_fee, 2)}</td>
            <td class="cost-fee-col ${feeHidden} ${feeNum}">${fmtNum(row.finished_management_fee, 2)}</td>
            <td class="cost-fee-col ${feeHidden} ${feeNum}">${fmtNum(row.finished_finance_fee, 2)}</td>
            <td class="cost-fee-col ${feeHidden} ${feeNum}">${fmtNum(row.finished_pretax_profit_fee, 2)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                <span>${fmtNum(row.unit_cost, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(fail)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>`,
            opsHtml: actionBtn,
        });
    }).join('');
}

const OPTIONAL_COL_WIDTH = {
    mass: 238,       // 68+58+58+54
    breakdown: 260,  // 64+64+64+68
    fee: 238,        // 58+58+64+58
};
/** 常显列宽合计（不含三组可折叠列） */
const TABLE_BASE_MIN_WIDTH = 1215;

/**
 * 同步可选列组显隐：材料量 / 成本分项 / 费率项（默认均收起）
 * @param {{ massOpen?: boolean, breakdownOpen?: boolean, feeOpen?: boolean }} flags
 */
export function syncOptionalColumnVisibility(flags = {}) {
    const massOpen = Boolean(flags.massOpen);
    const breakdownOpen = Boolean(flags.breakdownOpen);
    const feeOpen = Boolean(flags.feeOpen);

    _syncToggleGroup({
        colSelector: '.cost-mass-col',
        buttonId: 'costToggleMassCols',
        isOpen: massOpen,
        openTitle: '收起材料量',
        closedTitle: '展开材料量（消耗 / 净量 / 废料 / 利用率）',
    });
    _syncToggleGroup({
        colSelector: '.cost-breakdown-col',
        buttonId: 'costToggleBreakdownCols',
        isOpen: breakdownOpen,
        openTitle: '收起成本分项',
        closedTitle: '展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）',
    });
    _syncToggleGroup({
        colSelector: '.cost-fee-col',
        buttonId: 'costToggleFeeCols',
        isOpen: feeOpen,
        openTitle: '收起费率项',
        closedTitle: '展开费率项（仓储包装 / 管理费 / 财务费 / 税前利润）',
    });

    const table = document.getElementById('costDataTable');
    if (table) {
        let width = TABLE_BASE_MIN_WIDTH;
        if (massOpen) width += OPTIONAL_COL_WIDTH.mass;
        if (breakdownOpen) width += OPTIONAL_COL_WIDTH.breakdown;
        if (feeOpen) width += OPTIONAL_COL_WIDTH.fee;
        table.style.minWidth = `${width}px`;
    }
}

function _syncToggleGroup({ colSelector, buttonId, isOpen, openTitle, closedTitle }) {
    document.querySelectorAll(colSelector).forEach((el) => {
        el.classList.toggle('hidden', !isOpen);
    });
    const btn = document.getElementById(buttonId);
    if (btn) {
        btn.textContent = isOpen ? '−' : '+';
        btn.title = isOpen ? openTitle : closedTitle;
    }
}

function offalCostCell(row) {
    if (!row.is_offal_nested) {
        return '<span class="text-ink-faint">否</span>';
    }
    const source = row.offal_source ? esc(row.offal_source) : '';
    return `
        <div class="text-[10px] text-warn">是</div>
        <div class="text-[9px] text-ink-muted mt-0.5 truncate" title="${source}">${source || '—'}</div>`;
}

function swingShearCostCell(row) {
    if (!row.has_swing_shear) {
        return '<span class="text-ink-faint">否</span>';
    }
    const fee = fmtNum(row.swing_shear_fee_per_ton, 2);
    return `
        <div class="inline-flex flex-col items-center gap-0.5">
            <span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-ink-muted bg-app-deep border border-ink-muted/30">是</span>
            <span class="text-[9px] font-mono tabular-nums text-ink-muted" title="当月加到钢价上的元/吨">+${esc(fee)}</span>
        </div>`;
}

/** 用筛选汇总刷新 HUD（金额 / 件均 / 待审均为全量筛选结果，非本页） */
export function updatePartCostHud(total, summary) {
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
    const totalCost = toAmount(data.unit_cost_sum);
    const materialAmount = toAmount(data.material_net_per_part_sum);
    const processFeeAmount = toAmount(data.process_fee_amount_sum);

    setText('costHudTotalCost', fmtMoney(data.unit_cost_sum));
    setText('costHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText('costHudAvg', fmtMoney(data.avg_unit_cost));
    setText('costHudMaterial', fmtMoney(data.material_net_per_part_sum));
    setText('costHudMaterialShare', fmtShare(materialAmount, totalCost));
    setText('costHudProcessFee', fmtMoney(data.process_fee_amount_sum));
    setText('costHudProcessFeeShare', fmtShare(processFeeAmount, totalCost));
    setText('costHudPending', Number(data.pending_count ?? 0).toLocaleString('zh-CN'));
    setText('costHudApproved', Number(data.approved_count ?? 0).toLocaleString('zh-CN'));
}

/** 无错即隐：成功不占视觉；失败才露「失败。*/
function calcStatusBadge(isFailed) {
    if (!isFailed) return '';
    return `<span class="text-brand-hud font-bold text-[9px] px-1 bg-brand-hud/10 border border-brand-hud/25">失败</span>`;
}

/** 待审留白；已通过/驳回才轻核*/
function auditBadge(status) {
    if (!status || status === 'pending') return '';
    if (status === 'approved') {
        return `<span class="text-[9px] text-ink-faint">已审</span>`;
    }
    if (status === 'rejected') {
        return `<span class="text-[9px] text-danger">驳回</span>`;
    }
    return `<span class="text-[9px] text-ink-faint">${esc(status)}</span>`;
}
