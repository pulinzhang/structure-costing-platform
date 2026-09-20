/**
 * 总成核价一览 — Brabus Carbon & Precision Dark（对齐冲压零件价格一览 HUD）
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../more-menu.js?v=1';
import { CONFIRM_LABELS, KIND_LABELS } from '../../../bom/procurement-object/labels.js?v=2';
import {
    partShortCodeCellHtml,
    partNumberNameCellHtml,
    resolveBomNodeShortCode,
} from '../../../../part-identity.js?v=3';

export function assemblyCostListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <!-- HUD 战术数据看板 + 操作 -->
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            <!-- 1. 总成本：管理者靶心 -->
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">总成本</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums leading-none"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7), 0 0 25px rgba(255,30,39,0.3);">
                                    ¥ <span id="lacHudGrand">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-2">总费用合计</div>
                            </div>
                            <!-- 2. 总成规模 + 件均 -->
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">总成</div>
                                <div class="text-[22px] font-black text-[#FFFFFF] mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="lacHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1 font-bold">件</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2 flex items-center justify-between gap-2">
                                    <span>件均</span>
                                    <span class="text-[#A1A1A6] tabular-nums">¥ <span id="lacHudAvg">—</span></span>
                                </div>
                            </div>
                            <!-- 3. 成本构成：材料费 / 焊接费 -->
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">成本构成</div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2 space-y-1.5">
                                    <div class="flex items-center justify-between gap-2">
                                        <span>材料费</span>
                                        <span class="text-[#A1A1A6] tabular-nums whitespace-nowrap">¥ <span id="lacHudMaterial">—</span> <span id="lacHudMaterialShare" class="text-[#555555]">—</span></span>
                                    </div>
                                    <div class="flex items-center justify-between gap-2">
                                        <span>焊接费</span>
                                        <span class="text-[#A1A1A6] tabular-nums whitespace-nowrap">¥ <span id="lacHudWelding">—</span> <span id="lacHudWeldingShare" class="text-[#555555]">—</span></span>
                                    </div>
                                </div>
                            </div>
                            <!-- 4. 审核进度：待审 / 已审合并 -->
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">审核进度</div>
                                <div class="text-[22px] font-black text-[#FFFFFF] mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="lacHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1 font-bold">条待审</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2 flex items-center justify-between gap-2">
                                    <span>已审</span>
                                    <span class="text-[#A1A1A6] tabular-nums"><span id="lacHudApproved">—</span> 条</span>
                                </div>
                            </div>
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
                                            class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-[#1A080A] border border-[#FF1E27]/50 text-[#FF1E27] transition-all">
                                        财务（总成）
                                    </button>
                                    <button id="lacViewProcurementBtn" type="button"
                                            class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-transparent border border-[#2A2A35] text-[#6E6E73] hover:text-white transition-all">
                                        采购
                                    </button>
                                </div>
                            </div>
                            <div class="flex items-center gap-1.5 flex-wrap justify-end">
                            <button id="lacExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200"
                                    title="导出成品核价（一览 + 材料明细 + 焊接费 + 间接费用；金额为系统快照）">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                <span id="lacExportBtnLabel">总成核价</span>
                            </button>
                            <button id="lacExportBundleBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200"
                                    title="导出月度核对：成品核价（总成）+ 冲压零件核价 + 焊接费 + 加工费 + 钢材联动等。须选定年/月/基地/项目；版本可不选（空=该月全部）。">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                月度核对
                            </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 战术胶囊筛选栏 -->
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="lacCapsulePeriod" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部期间</span>
                                <span id="lacCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="lacCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="lacToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="lacAdvancedFilterLabel">展开高级筛选</span>
                                <span id="lacAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="lacSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="lacAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('lacYearFilter', '年度')}
                            ${filterSelect('lacMonthFilter', '月份')}
                            ${filterSelect('lacLocationFilter', '基地')}
                            ${filterSelect('lacVehicleModelFilter', '项目')}
                            ${filterSelect('lacBomVersionFilter', '版本')}
                            ${filterSelect('lacAuditFilter', '审核状态')}
                            ${filterSelect('lacCalcFilter', '计算状态')}
                            ${filterInput('lacPartNumberFilter', '零件号', '短号或完整零件号')}
                            <button id="lacResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量删除 / 审核 / 反审核 / 零件成本 / 月度核对须选定年度、月份、基地、项目；版本可不选（同月可有多个工程变更字）。反审核后可重新计算覆盖。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table id="lacDataTable" class="w-full table-fixed bg-transparent border-separate border-spacing-0" style="min-width: 1252px;">
                        <colgroup id="lacColgroup">
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
                            <col style="width:44px">
                        </colgroup>
                        <thead id="lacTableHead">
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">年月/基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#A1A1A6]">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#6E6E73]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目/版本</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">材料</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">焊接费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#6E6E73]">月总账</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">间接</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">总费用</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">核算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="lacTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'lacPageInfo', selectId: 'lacPageSize', buttonsId: 'lacPagination' })}

                <div id="lacEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无总成核价数据</h5>
                    <p class="text-[10px] text-[#555555]">请先完成总成核价计算，或调整筛选条件</p>
                </div>

                <div id="lacLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        ${batchAuditDrawerHtml()}
    `;
}

function batchAuditDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="lacBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="lacBatchAuditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="lacBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeLacBatchAuditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="lacBatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="lacBatchAuditFilterSummary"></div>
                <p id="lacBatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="lacBatchAuditOperatorLabel">操作人</label>
                    <div id="lacBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        —
                    </div>
                    <p class="text-[10px] text-[#555555] mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="lacBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="lacBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelLacBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmLacBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    确认提交
                </button>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" class="w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="h-8 w-32 px-2.5 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#ffffff] placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27] transition-colors">
    </label>`;
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
        return `<span class="text-[#ffb74d] font-bold text-[9px] px-1 bg-[#ffb74d]/10 border border-[#ffb74d]/25">部分</span>`;
    }
    if (status === 'failed') {
        return `<span class="text-[#FF1E27] font-bold text-[9px] px-1 bg-[#FF1E27]/10 border border-[#FF1E27]/25">失败</span>`;
    }
    return `<span class="text-[9px] text-[#555555]">${esc(status || '')}</span>`;
}

function auditBadge(status) {
    if (!status || status === 'pending') return '';
    if (status === 'approved') {
        return `<span class="text-[9px] text-[#555555]">已审</span>`;
    }
    return `<span class="text-[9px] text-[#555555]">${esc(status)}</span>`;
}

export function renderLacRows(records, view = 'finance') {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const num = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    const confirmLabel = CONFIRM_LABELS;
    return records.map((row) => {
        const ym = esc(fmtPeriod(row.year, row.month));
        const location = esc(row.location) || '—';
        const actionCell = `
            <td class="px-1 py-2 text-center align-middle sticky right-0 z-[2] brabus-bg-grid group-hover:bg-[#161620]">
                <button type="button"
                        class="btn-open-detail inline-flex items-center justify-center w-7 h-7 rounded-sm
                               opacity-0 group-hover:opacity-100 focus:opacity-100
                               text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all duration-100"
                        data-id="${esc(row.id)}" title="查看详情" aria-label="查看详情">
                    ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                </button>
                <button type="button"
                        class="btn-open-restore inline-flex items-center justify-center h-7 px-1.5 rounded-sm
                               opacity-0 group-hover:opacity-100 focus:opacity-100
                               text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all duration-100
                               text-[10px] tracking-wide"
                        data-year="${esc(row.year)}"
                        data-month="${esc(row.month)}"
                        data-part-number="${esc(row.part_number)}"
                        data-location="${esc(row.location || '')}"
                        data-vehicle-model="${esc(row.vehicle_model || '')}"
                        data-bom-version="${esc(row.bom_version || '')}"
                        title="计算过程" aria-label="计算过程">
                    计算过程
                </button>
            </td>`;
        if (view === 'procurement') {
            return `
        <tr class="lac-row group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-[#F0F0F2] text-[11px] tabular-nums">${ym}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
            </td>
            ${partIdentityTds(row)}
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#C8C8D0] text-[10px] truncate">${esc(KIND_LABELS[row.object_kind] || row.object_kind || '—')}</div>
                <div class="text-[#555555] text-[9px] mt-0.5">第${esc(row.level ?? 0)}层</div>
            </td>
            <td class="${num}">${fmtNum(row.material_amount, 4)}</td>
            <td class="${num}" title="数据为焊接费用（含电泳、黑漆等）">${Number(row.welding_amount) === 0 ? '' : fmtNum(row.welding_amount, 4)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${fmtNum(row.total_amount, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center text-[9px] text-[#8E8E93]">${esc(confirmLabel[row.confirm_status] || row.confirm_status || '—')}</td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(row.calc_status)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>
            ${actionCell}
        </tr>`;
        }
        return `
        <tr class="lac-row group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-[#F0F0F2] text-[11px] tabular-nums">${ym}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
            </td>
            ${partIdentityTds(row)}
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#C8C8D0] text-[10px] truncate" title="${esc(row.vehicle_model || '')}">${esc(row.vehicle_model || '—')}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 font-mono truncate">${esc(row.bom_version || '—')}</div>
            </td>
            <td class="${num}">${fmtNum(row.material_amount, 4)}</td>
            <td class="${num}">${fmtNum(row.welding_amount, 4)}</td>
            <td class="${num} text-[#C8C8D0] font-semibold">${fmtNum(row.total_amount, 4)}</td>
            <td class="${num}">${fmtNum(row.indirect_amount, 4)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${fmtNum(row.grand_total, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(row.calc_status)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>
            ${actionCell}
        </tr>`;
    }).join('');
}

export function updateLacTableHead(view = 'finance') {
    const head = document.getElementById('lacTableHead');
    if (!head) return;
    const table = document.getElementById('lacDataTable');
    const colgroup = document.getElementById('lacColgroup');
    const th = (label, extra = '') =>
        `<th class="px-2 py-2 text-[9px] font-medium tracking-[0.06em] text-[#555555] ${extra}">${label}</th>`;
    const identityHeads = `
                ${th('短代码', 'text-left tracking-[0.08em] text-[#A1A1A6]')}
                ${th('零件', 'text-left tracking-[0.08em] text-[#6E6E73]')}`;
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
            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                <th class="p-0"></th>
                ${th('年月/基地', 'text-left tracking-[0.08em]')}
                ${identityHeads}
                ${th('对象/层', 'text-left tracking-[0.08em]')}
                ${th('材料成本', 'text-right')}
                ${th('焊接费/电泳黑漆等', 'text-right leading-tight')}
                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">总成本</th>
                ${th('确认', 'text-center')}
                ${th('核算', 'text-center')}
                ${th('审核', 'text-center')}
                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
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
            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                <th class="p-0"></th>
                ${th('年月/基地', 'text-left tracking-[0.08em]')}
                ${identityHeads}
                ${th('项目/版本', 'text-left tracking-[0.08em]')}
                ${th('材料', 'text-right')}
                ${th('焊接费', 'text-right')}
                ${th('月总账', 'text-right text-[#6E6E73]')}
                ${th('间接', 'text-right')}
                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">总费用</th>
                ${th('核算', 'text-center')}
                ${th('审核', 'text-center')}
                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
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

export function updateLacFilterCapsules() {
    const year = document.getElementById('lacYearFilter')?.value || '';
    const month = document.getElementById('lacMonthFilter')?.value || '';
    const location = document.getElementById('lacLocationFilter')?.value || '';
    const vehicle = document.getElementById('lacVehicleModelFilter')?.value || '';
    const version = document.getElementById('lacBomVersionFilter')?.value || '';
    const audit = document.getElementById('lacAuditFilter')?.value || '';
    const calc = document.getElementById('lacCalcFilter')?.value || '';
    const part = document.getElementById('lacPartNumberFilter')?.value.trim() || '';

    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const periodEl = document.getElementById('lacCapsulePeriod');
    const locationEl = document.getElementById('lacCapsuleLocation');
    const vehicleEl = document.getElementById('lacCapsuleVehicle');
    const countEl = document.getElementById('lacAdvancedFilterCount');

    if (periodEl) {
        const periodText = fmtPeriod(year, month);
        if (periodText) {
            periodEl.textContent = periodText;
            periodEl.className = activeCapsule;
        } else {
            periodEl.textContent = '全部期间';
            periodEl.className = idleCapsule;
        }
    }
    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? activeCapsule : idleCapsule;
    }
    if (vehicleEl) {
        const label = vehicle
            ? (version ? `${vehicle}/${version}` : vehicle)
            : '全部项目';
        vehicleEl.textContent = label;
        vehicleEl.className = vehicle ? activeCapsule : idleCapsule;
    }

    const advancedActive = [year, month, location, vehicle, version, audit, calc, part]
        .filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;
}

