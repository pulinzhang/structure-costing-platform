/**
 * BOM 焊接费列表模板 — HUD 密表
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

const AUDIT_LABEL = {
    pending: { text: '待审', cls: 'bg-[#ffb74d]/15 text-[#ffb74d]' },
    approved: { text: '已审', cls: 'bg-[#4caf50]/15 text-[#4caf50]' },
    rejected: { text: '已驳回', cls: 'bg-[#ef5350]/15 text-[#ef5350]' },
};

const CALC_LABEL = {
    ok: { text: '正常', cls: 'text-[#8E8E93]' },
    partial: { text: '缺单价', cls: 'text-[#ffb74d]' },
    failed: { text: '失败', cls: 'text-[#ef5350]' },
};

export function l0WeldingFeeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5">
                                <div class="text-[#555555] text-[10px] tracking-wider">成品焊接费合计</div>
                                <div class="text-[22px] font-black text-[#FFFFFF] mt-1 tracking-tight tabular-nums leading-none">
                                    ¥ <span id="l0wfHudTotalFee">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2">仅成品 / 供货总成</div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5">
                                <div class="text-[#555555] text-[10px] tracking-wider">结果条数</div>
                                <div class="text-[22px] font-black text-[#FFFFFF] mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="l0wfHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1 font-bold">条</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2 flex justify-between">
                                    <span>版本</span>
                                    <span id="l0wfHudVersion" class="text-[#A1A1A6]">—</span>
                                </div>
                            </div>
                            <button type="button" id="l0wfHudPartialCard"
                                    class="text-left w-full p-3.5 relative overflow-hidden group transition-all duration-200 cursor-pointer
                                           bg-[#0D0D11]/80 border border-[#1E1E26] hover:border-[#2A2A35] focus:outline-none"
                                    title="点击筛选缺单价（partial）">
                                <div id="l0wfHudPartialGlow" class="hidden absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#555555] text-[10px] font-bold tracking-widest">缺单价待办</span>
                                    <span id="l0wfHudPartialDot" class="hidden w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#6E6E73] font-mono mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="l0wfHudPartial">—</span>
                                    <span class="text-[10px] ml-1 font-bold opacity-70">条</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#555555] mt-2">工艺行缺分年单价</div>
                            </button>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3.5">
                                <div class="text-[#555555] text-[10px] tracking-wider">审核进度</div>
                                <div class="text-[22px] font-black text-[#FFFFFF] mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="l0wfHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1 font-bold">条待审</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-2 flex justify-between">
                                    <span>已审核</span>
                                    <span class="text-[#A1A1A6] tabular-nums"><span id="l0wfHudApproved">—</span> 条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="l0wfBatchApproveBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="l0wfBatchReverseBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核
                            </button>
                            <button id="l0wfBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] transition-all">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="l0wfExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="l0wfCapsuleYear" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部年度</span>
                                <span id="l0wfCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="l0wfCapsuleModel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="l0wfCapsuleVersion" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部版本</span>
                                <span id="l0wfCapsulePartial" class="hidden bg-[#FF1E27]/15 border border-[#FF1E27]/40 text-[#FF1E27] px-2.5 py-1 rounded-md font-bold">缺单价筛选中</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="l0wfToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="l0wfAdvancedFilterLabel">展开高级筛选</span>
                                <span id="l0wfAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="l0wfSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020]"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="l0wfAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('l0wfYearFilter', '年度')}
                            ${filterSelect('l0wfLocationFilter', '基地')}
                            ${filterSelect('l0wfVehicleModelFilter', '项目')}
                            ${filterSelect('l0wfBomVersionFilter', '版本')}
                            ${filterSelect('l0wfAuditStatusFilter', '审核状态')}
                            ${filterInput('l0wfPartNumberFilter', '零件号', '短号或完整零件号')}
                            <button id="l0wfResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:text-[#FF1E27] hover:border-[#FF1E27]/50 transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量审核 / 反审核 / 删除须选定年度 + 基地 + 项目 + 版本。</p>
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1580px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 100px;">
                            <col style="width: 110px;">
                            <col style="width: 120px;">
                            <col style="width: 140px;">
                            <col style="width: 200px;">
                            <col style="width: 52px;">
                            <col style="width: 52px;">
                            <col style="width: 52px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">
                            <col style="width: 96px;">
                            <col style="width: 64px;">
                            <col style="width: 64px;">
                            <col style="width: 72px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地 / 年</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目 / 版本</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">焊接信息原文</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">工艺数</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">命中</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">缺单价</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">系统计算</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">其它费用</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">确认单价</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">计算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="l0wfTableBody"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3">
                        <span id="l0wfTotalLabel" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('l0wfPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="l0wfPagination"></div>
                </div>

                <div id="l0wfEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无成品焊接费数据</h5>
                    <p class="text-[10px] text-[#555555]">请先在计算页按年 / 基地 / 项目 / 版本生成；仅含成品，不含下级工艺</p>
                </div>
            </div>

            <!-- 查看详情抽屉 -->
            <div id="l0wfViewBackdrop" class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300" style="display:none;"></div>
            <div id="l0wfViewDrawer"
                 class="fixed inset-y-0 right-0 z-[85] w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col translate-x-full transition-transform duration-300"
                 style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                     style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                    <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                        <span class="w-0.5 h-3.5 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                        成品焊接费详情
                    </h5>
                    <button type="button" id="l0wfViewClose"
                            class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="l0wfViewDrawerContent">
                    <div class="bg-[#111111] border border-[#262626]">
                        <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                            <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">基本信息</h6>
                        </div>
                        <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('年度', 'l0wf-view-year')}
                            ${viewRow('基地', 'l0wf-view-location')}
                            ${viewRow('项目', 'l0wf-view-vehicle')}
                            ${viewRow('版本', 'l0wf-view-version')}
                            ${partNumberViewBlock('l0wf-view')}
                            ${viewRow('零件名称', 'l0wf-view-part-name')}
                            ${viewRow('顾客名称', 'l0wf-view-customer')}
                        </div>
                    </div>

                    <div class="bg-[#111111] border border-[#d32f2f]/30 shadow-[0_0_24px_rgba(211,47,47,0.08)]">
                        <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818] flex items-center gap-2">
                            <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                            <h6 class="text-[10px] font-semibold text-[#d32f2f] tracking-wider uppercase">单价构成</h6>
                        </div>
                        <div class="p-4">
                            <div class="grid grid-cols-3 gap-3 mb-4">
                                <div class="bg-[#0a0a0a] border border-[#2c2c2c] px-3 py-2.5">
                                    <div class="text-[9px] text-[#555555] tracking-[0.08em] uppercase mb-1">系统计算</div>
                                    <div id="l0wf-view-system-fee" class="text-[14px] font-mono font-bold tabular-nums text-[#C8C8D0] text-right">—</div>
                                </div>
                                <div class="bg-[#0a0a0a] border border-[#2c2c2c] px-3 py-2.5">
                                    <div class="text-[9px] text-[#555555] tracking-[0.08em] uppercase mb-1">其它费用</div>
                                    <div id="l0wf-view-other-fee" class="text-[14px] font-mono font-bold tabular-nums text-[#C8C8D0] text-right">—</div>
                                </div>
                                <div class="bg-[#1A080A] border border-[#FF1E27]/30 px-3 py-2.5">
                                    <div class="text-[9px] text-[#FF1E27]/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                    <div id="l0wf-view-final-fee" class="text-[15px] font-mono font-black tabular-nums text-[#FF1E27] text-right">—</div>
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${viewRow('工艺数', 'l0wf-view-process-count')}
                                ${viewRow('命中 / 缺单价', 'l0wf-view-match-stats')}
                                ${viewRow('计算状态', 'l0wf-view-calc-status')}
                                ${viewRow('备注', 'l0wf-view-remark')}
                                <div class="col-span-2 min-w-0">
                                    <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">计算说明</span>
                                    <span id="l0wf-view-calc-message" class="block text-xs text-[#cccccc] whitespace-pre-wrap break-words">—</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="bg-[#111111] border border-[#262626]">
                        <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818] flex items-center gap-2">
                            <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                            <h6 class="text-[10px] font-semibold text-[#d32f2f] tracking-wider uppercase">焊接信息原文</h6>
                        </div>
                        <div class="px-4 py-3">
                            <p id="l0wf-view-weld-info" class="text-[11px] text-[#6E6E73] leading-relaxed whitespace-pre-wrap break-words mb-0">—</p>
                        </div>
                    </div>

                    <div class="bg-[#111111] border border-[#262626]">
                        <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818] flex items-center gap-2">
                            <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                            <h6 class="text-[10px] font-semibold text-[#d32f2f] tracking-wider uppercase">工艺明细</h6>
                        </div>
                        <div class="overflow-x-auto" id="l0wfViewProcessItems">
                            <div class="px-4 py-6 text-[11px] text-[#616161]">加载中..</div>
                        </div>
                    </div>

                    <div class="bg-[#111111] border border-[#262626]">
                        <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                            <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">审核 / 元数据</h6>
                        </div>
                        <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('审核状态', 'l0wf-view-audit-status')}
                            ${viewRow('审核人', 'l0wf-view-audited-by')}
                            ${viewRow('审核时间', 'l0wf-view-audited-at')}
                            ${viewRow('审核意见', 'l0wf-view-audit-remark')}
                            ${viewRow('反审核人', 'l0wf-view-reverse-by')}
                            ${viewRow('反审核时间', 'l0wf-view-reverse-at')}
                            ${viewRow('反审核意见', 'l0wf-view-reverse-remark')}
                            ${viewRow('创建人', 'l0wf-view-created-by')}
                            ${viewRow('创建时间', 'l0wf-view-created-at')}
                            ${viewRow('修改人', 'l0wf-view-updated-by')}
                            ${viewRow('修改时间', 'l0wf-view-updated-at')}
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0 flex-wrap">
                    <button type="button" id="l0wfViewEditBtn"
                            class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                        编辑
                    </button>
                </div>
            </div>

            <!-- 编辑抽屉：其它费用 / 确认单价 -->
            <div id="l0wfEditBackdrop" class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" style="display:none;"></div>
            <div id="l0wfEditDrawer"
                 class="fixed inset-y-0 right-0 z-[85] w-[560px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col translate-x-full transition-transform duration-300"
                 style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333]">
                    <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                        <span class="w-0.5 h-3.5 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                        编辑成品焊接费
                    </h5>
                    <button type="button" id="l0wfEditClose"
                            class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6">
                    <form id="l0wfEditForm" class="space-y-5">
                        <input type="hidden" id="l0wfEditRecordId" value="">
                        <div class="bg-[#111111] border border-[#d32f2f]/30 p-4 shadow-[0_0_24px_rgba(211,47,47,0.08)]">
                            <label class="text-[10px] font-semibold text-[#d32f2f] uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                                <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                                单价构成
                            </label>
                            <div class="grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 items-end mb-4">
                                <div class="bg-[#0a0a0a] border border-[#2c2c2c] px-3 py-2.5">
                                    <div class="text-[9px] text-[#555555] tracking-[0.08em] uppercase mb-1">系统计算</div>
                                    <div id="l0wf-edit-system-fee" class="text-[15px] font-mono font-bold tabular-nums text-[#C8C8D0] text-right">—</div>
                                </div>
                                <div class="pb-3 text-[#555555] font-mono text-lg font-bold">+</div>
                                <div>
                                    <label class="text-[9px] text-[#555555] tracking-[0.08em] uppercase mb-1 block">
                                        其它费用 <span class="text-[#616161] normal-case">（可正可负）</span>
                                    </label>
                                    <input type="number" id="l0wfEditOtherFee" step="0.0001"
                                           class="w-full h-10 px-3 text-sm font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded tabular-nums text-right"
                                           placeholder="0.0000">
                                </div>
                                <div class="pb-3 text-[#555555] font-mono text-lg font-bold">=</div>
                                <div class="bg-[#1A080A] border border-[#FF1E27]/30 px-3 py-2.5 shadow-[0_0_16px_rgba(255,30,39,0.12)]">
                                    <div class="text-[9px] text-[#FF1E27]/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                    <div id="l0wf-edit-final-fee" class="text-[16px] font-mono font-black tabular-nums text-[#FF1E27] text-right">—</div>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">备注</label>
                                <textarea id="l0wfEditRemark" rows="3" maxlength="1000"
                                          class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded resize-none"
                                          placeholder="调整理由 / 原因"></textarea>
                            </div>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">基本信息（只读）</label>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${partNumberViewBlock('l0wf-edit')}
                                ${viewRow('零件名称', 'l0wf-edit-part-name')}
                                ${viewRow('年度', 'l0wf-edit-year')}
                                ${viewRow('基地', 'l0wf-edit-location')}
                                ${viewRow('项目', 'l0wf-edit-vehicle')}
                                ${viewRow('版本', 'l0wf-edit-version')}
                            </div>
                        </div>
                    </form>
                </div>
                <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                    <button type="button" id="l0wfEditCancel"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                    <button type="button" id="l0wfEditSubmit"
                            class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                        ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                        保存
                    </button>
                </div>
            </div>

            <!-- 批量审核抽屉 -->
            <div id="l0wfBatchAuditBackdrop" class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" style="display:none;"></div>
            <div id="l0wfBatchAuditDrawer"
                 class="fixed inset-y-0 right-0 z-[85] w-[420px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col translate-x-full transition-transform duration-300"
                 style="display:none;">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333]">
                    <h5 id="l0wfBatchAuditTitle" class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">批量审核</h5>
                    <button type="button" id="l0wfBatchAuditClose"
                            class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-5 space-y-4">
                    <p id="l0wfBatchAuditScope" class="text-[11px] text-[#9e9e9e]"></p>
                    <label class="block space-y-1.5">
                        <span id="l0wfBatchAuditRemarkLabel" class="text-[10px] text-[#6E6E73]">审核意见</span>
                        <textarea id="l0wfBatchAuditRemark" rows="4"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded-sm"
                                  placeholder="可选"></textarea>
                    </label>
                </div>
                <div class="px-5 py-3 border-t border-[#222] flex justify-end gap-2 shrink-0">
                    <button type="button" id="l0wfBatchAuditCancel"
                            class="h-8 px-4 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:text-white hover:border-[#9e9e9e]">取消</button>
                    <button type="button" id="l0wfBatchAuditSubmit"
                            class="h-8 px-4 text-[11px] bg-[#d32f2f] text-white rounded hover:bg-[#b71c1c]">确认</button>
                </div>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <select id="${id}" class="w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <input id="${id}" type="text" placeholder="${placeholder}"
               class="w-40 h-8 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#ffffff] placeholder:text-[#555] focus:outline-none focus:border-[#ff5252] rounded-sm">
    </label>`;
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-[#d32f2f] font-mono' : 'text-[#cccccc]'} truncate">—</span>
    </div>`;
}

function partNumberViewBlock(prefix) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">零件号</span>
        <span id="${prefix}-part-short"
              class="block text-xl font-mono font-bold tabular-nums text-white tracking-[0.14em] drop-shadow-[0_0_16px_rgba(211,47,47,0.18)]">—</span>
        <span id="${prefix}-part-number" class="block text-[11px] font-mono text-[#616161] tracking-wider mt-0.5 truncate"></span>
    </div>`;
}

/** 与 BOM viz 一致：数字末四位（501005123AA → 5123） */
function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/** 成品 / 供货总成短号展示 */
export function resolveL0ShortPartNumber(partNumber) {
    const full = String(partNumber || '').trim();
    if (!full) return '—';
    return shortPartNumber(full) || full;
}

export function updateL0WeldingFeeHud(summary = {}, versionLabel = '—') {
    const set = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const totalFee = summary.total_fee != null ? fmtNum(summary.total_fee, 4) : '—';
    set('l0wfHudTotalFee', totalFee);
    set('l0wfHudTotal', summary.total_count != null ? String(summary.total_count) : '—');
    set('l0wfHudPending', summary.pending_count != null ? String(summary.pending_count) : '—');
    set('l0wfHudApproved', summary.approved_count != null ? String(summary.approved_count) : '—');
    set('l0wfHudVersion', versionLabel || '—');

    const partial = Number(summary.partial_count) || 0;
    set('l0wfHudPartial', String(partial));
    document.getElementById('l0wfHudPartialGlow')?.classList.toggle('hidden', partial <= 0);
    document.getElementById('l0wfHudPartialDot')?.classList.toggle('hidden', partial <= 0);
    const partialValue = document.getElementById('l0wfHudPartial');
    if (partialValue) {
        partialValue.parentElement.classList.toggle('text-[#FF1E27]', partial > 0);
        partialValue.parentElement.classList.toggle('text-[#6E6E73]', partial <= 0);
    }
}

export function updateL0WeldingFeeFilterCapsules(state) {
    const idle = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';
    const active = 'bg-[#FF1E27]/10 border border-[#FF1E27]/40 text-[#FF1E27] px-2.5 py-1 rounded-md';
    const setCap = (id, emptyLabel, value) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value || emptyLabel;
        el.className = value ? active : idle;
    };
    setCap('l0wfCapsuleYear', '全部年度', state.year ? String(state.year) : '');
    setCap('l0wfCapsuleLocation', '全部基地', state.location || '');
    setCap('l0wfCapsuleModel', '全部项目', state.vehicle_model || '');
    setCap('l0wfCapsuleVersion', '全部版本', state.bom_version || '');
    document.getElementById('l0wfCapsulePartial')?.classList.toggle('hidden', !state.onlyPartial);

    const count = [state.year, state.location, state.vehicle_model, state.bom_version, state.audit_status, state.part_number]
        .filter(Boolean).length + (state.onlyPartial ? 1 : 0);
    const countEl = document.getElementById('l0wfAdvancedFilterCount');
    if (countEl) countEl.textContent = `(${count})`;
}

export function renderL0WeldingFeeRows(records) {
    if (!records.length) return '';
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    const canUpdate = typeof can === 'function' ? can('op:bom-l0-welding-fee-list:update') : true;
    return records.map((row) => {
        const audit = AUDIT_LABEL[row.audit_status] || { text: row.audit_status || '-', cls: 'text-[#8E8E93]' };
        const calc = CALC_LABEL[row.calc_status] || { text: row.calc_status || '-', cls: 'text-[#8E8E93]' };
        const shortNo = resolveL0ShortPartNumber(row.part_number);
        const systemFee = row.total_l0_welding_fee != null ? fmtNum(row.total_l0_welding_fee, 4) : '-';
        const otherFee = row.other_fee != null ? fmtNum(row.other_fee, 4) : '-';
        const finalFee = row.final_l0_welding_fee != null
            ? fmtNum(row.final_l0_welding_fee, 4)
            : systemFee;
        const approved = row.audit_status === 'approved';
        const weld = (row.weld_info_raw || '').trim();
        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[#F0F0F2] font-semibold truncate">${esc(row.location || '-')}</div>
                    <div class="text-[9px] text-[#555555]">${esc(row.year)}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[#C8C8D0] truncate">${esc(row.vehicle_model || '-')}</div>
                    <div class="text-[9px] text-[#555555]">${esc(row.bom_version || '-')}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[14px] font-bold text-[#F0F0F2]">${esc(shortNo)}</div>
                    <div class="text-[9px] text-[#3A3A42] truncate" title="${esc(row.part_number)}">${esc(row.part_number || '-')}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[#C8C8D0] truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '-')}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-[#555555] truncate" title="${esc(weld || '')}">${esc(weld || '—')}</div>
                </td>
                <td class="${numCell}">${esc(row.process_line_count ?? 0)}</td>
                <td class="${numCell}">${esc(row.matched_line_count ?? 0)}</td>
                <td class="${numCell} ${Number(row.missing_price_count) > 0 ? 'text-[#ffb74d]' : ''}">${esc(row.missing_price_count ?? 0)}</td>
                <td class="${numCell}">${esc(systemFee)}</td>
                <td class="${numCell}">${esc(otherFee)}</td>
                <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">${esc(finalFee)}</td>
                <td class="px-1 py-2 text-center text-[9px] ${calc.cls}">${calc.text}</td>
                <td class="px-1 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${audit.text}</span>
                </td>
                <td class="px-1 py-2 text-center">
                    <div class="inline-flex items-center justify-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                        <button type="button" data-action="detail" data-id="${esc(row.id)}"
                                class="w-7 h-7 inline-flex items-center justify-center rounded text-[#6E6E73] hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all"
                                title="明细">
                            ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                        </button>
                        ${canUpdate ? `
                        <button type="button" data-action="edit" data-id="${esc(row.id)}"
                                class="w-7 h-7 inline-flex items-center justify-center rounded text-[#6E6E73] hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}"
                                title="${approved ? '已审核，不可编辑' : '编辑'}">
                            ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                        </button>` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

export function renderL0WeldingFeePagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let html = `
        <button class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-wf-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);
    for (let i = start; i <= end; i++) {
        html += `<button class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${i === currentPage ? 'bg-[#FF1E27] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-wf-page="${i}">${i}</button>`;
    }
    html += `
        <button class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-wf-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return html;
}

export function renderFeeDetailItems(items) {
    if (!items?.length) {
        return `<div class="px-4 py-8 text-center text-[11px] text-[#555555]">无工艺明细</div>`;
    }
    const matchMap = {
        matched: { text: '已匹配', cls: 'text-[#4caf50]' },
        missing_price: { text: '缺单价', cls: 'text-[#ffb74d]' },
        unmapped: { text: '未映射', cls: 'text-[#8E8E93]' },
    };
    const rows = items.map((item) => {
        const m = matchMap[item.match_status] || { text: item.match_status || '-', cls: 'text-[#8E8E93]' };
        return `
            <tr class="border-b border-[#141418] hover:bg-[#161620] transition-colors">
                <td class="px-3 py-2 text-[10px] text-[#C8C8D0]">${esc(item.standard_process_name || item.process_token || '-')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-[#8E8E93]">${esc(fmtNum(item.process_qty, 4))} ${esc(item.process_qty_unit || '')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-[#8E8E93]">${item.unit_price != null ? esc(fmtNum(item.unit_price, 4)) : '-'}</td>
                <td class="px-3 py-2 text-[10px] text-[#555]">${esc(item.unit || '-')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-[#FF1E27]">${item.line_fee != null ? esc(fmtNum(item.line_fee, 4)) : '-'}</td>
                <td class="px-3 py-2 text-center text-[9px] ${m.cls}">${m.text}</td>
            </tr>
        `;
    }).join('');
    return `
        <table class="w-full border-collapse">
            <thead>
                <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                    <th class="px-3 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">标准工艺</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">过程量</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">单价</th>
                    <th class="px-3 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">单位</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">行费</th>
                    <th class="px-3 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">匹配</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}
