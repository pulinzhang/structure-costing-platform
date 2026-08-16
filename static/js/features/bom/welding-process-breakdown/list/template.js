/**
 * BOM 焊接工艺拆解 — 列表模板（HUD 密表，可编辑）
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

const AUDIT_LABEL = {
    pending: { text: '待审', cls: 'text-[#ffb74d] bg-[#ffb74d]/15' },
    approved: { text: '已审', cls: 'text-[#4caf50] bg-[#4caf50]/15' },
};

const MAP_LABEL = {
    ready: { text: '已对齐', cls: 'text-[#4caf50]' },
    ambiguous: { text: '待定', cls: 'text-[#ffb74d]' },
    unmapped: { text: '未映射', cls: 'text-[#ef5350]' },
};

const ROLLUP_LABEL = {
    own: '本节点',
    rolled_in_parent: '已计入父级',
    orphan_child: '父级缺失',
};

const EVIDENCE_STATUS_LABEL = {
    match: { text: '一致', cls: 'text-[#4caf50]' },
    mismatch: { text: '差额', cls: 'text-[#ef5350]' },
    no_child: { text: '无旁证', cls: 'text-[#8E8E93]' },
    skipped: { text: '跳过', cls: 'text-[#555555]' },
    l0_only: { text: '仅L0', cls: 'text-[#ffb74d]' },
    orphan_only: { text: '仅下级', cls: 'text-[#ffb74d]' },
};

/** 兜底；优先用接口 filters.standard_process_names */
const FALLBACK_STANDARD_PROCESS_NAMES = [
    '焊点',
    '植/螺柱/凸焊',
    '铆接',
    'CO2焊缝',
    '折边/点焊胶',
    '电镀',
    '电泳（盐雾试验要求≤244H）',
    '电泳（盐雾试验要求244H-720H）',
    '电泳（盐雾试验要求＞720H）',
    '压铆',
    '打铆钉',
    '二维码',
    '套袋',
];

export function weldingProcessBreakdownListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono flex-1 min-w-0">
                            ${hudCard('wpbHudTotal', '主表', '条')}
                            ${hudCard('wpbHudL0', 'L0 总成', '条')}
                            ${hudCard('wpbHudPending', '待审', '条')}
                            ${hudCard('wpbHudApproved', '已审', '条')}
                            ${hudCard('wpbHudZeroProcess', 'L0 · 工艺数=0', '条', true, 'filter-zero-process', 'wpbHudZeroProcessCard')}
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="btnWpbBatchApprove" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="btnWpbBatchReverse" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核
                            </button>
                            <button id="btnWpbBatchDelete" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 transition-all">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="btnWpbExport" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出L0核对
                            </button>
                        </div>
                    </div>
                    <p class="text-[10px] text-[#8E8E93] leading-relaxed">
                        <span class="text-[#ffb74d]">计费口径：</span>焊接加工费<strong class="font-semibold text-[#F0F0F2]">只认 L0 供货总成</strong>过程量。
                        <span class="text-[#555555]">旁证（L1 / L2）仅供参考，不得作为计费依据。</span>
                        <span class="text-[#F0F0F2]">异常排查：</span>筛「层级 = L0」+「工艺数 = 0」；有异常时点 HUD「L0 · 工艺数=0」一键筛。
                        「导出L0核对」= 按当前筛选导出 L0 主表+工艺明细（主表纵向合并、不含审核）。
                        主表来自材料清单（只读）；待审时可改明细过程量与标准工艺。
                    </p>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="wpbCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="wpbCapsuleModel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="wpbCapsuleVersion" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部版本</span>
                                <span id="wpbCapsuleLevel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部层级</span>
                                <span id="wpbCapsuleProcessCount" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部工艺数</span>
                                <span id="wpbCapsuleAudit" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部审核</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="wpbToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="wpbAdvancedFilterLabel">展开高级筛选</span>
                            </button>
                            <button type="button" id="btnWpbFilter"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="wpbAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('wpbLocationFilter', '基地')}
                            ${filterSelect('wpbModelFilter', '项目')}
                            ${filterSelect('wpbVersionFilter', '版本')}
                            ${filterSelect('wpbAuditFilter', '审核状态')}
                            ${levelFilterSelect()}
                            ${processCountFilterSelect()}
                            <div class="flex flex-col gap-1">
                                <label class="text-[9px] tracking-[0.08em] text-[#555555]">零件号</label>
                                <input id="wpbPartNumberFilter" type="text" autocomplete="off"
                                       placeholder="模糊…"
                                       class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all w-40">
                            </div>
                            <button id="wpbResetFilterBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量审核 / 反审核 / 删除须选定基地 + 项目 + 版本。异常：层级 L0 + 工艺数 = 0。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[1280px] bg-transparent table-fixed border-collapse">
                        <colgroup>
                            <col style="width:2px">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:6%">
                            <col style="width:18%">
                            <col style="width:5%">
                            <col style="width:7%">
                            <col style="width:20%">
                            <col style="width:8%">
                            <col style="width:6%">
                            <col style="width:5%">
                            <col style="width:7%">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">版本</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#6E6E73]">零件</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">层级</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">装配用量</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">焊接原文</th>
                                <th class="px-2 py-2 text-center text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]" title="有效工艺明细行数">工艺数</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">解析</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">核对</th>
                            </tr>
                        </thead>
                        <tbody id="wpbTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]" id="wpbPaginationContainer">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="wpbTotalCount" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('wpbPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="wpbPaginationBtns"></div>
                </div>

                <div id="wpbEmptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无拆解数据</h5>
                    <p class="text-[10px] text-[#555555]">请先在「焊接工艺拆解」页从 BOM 生成</p>
                </div>

                <div id="wpbLoadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        ${detailDrawerHtml()}
        ${batchDrawerHtml()}
    `;
}

function hudCard(id, label, unit, warn = false, action = null, cardId = null) {
    const border = warn ? 'border-[#ffb74d]/30' : 'border-[#1E1E26]';
    const labelCls = warn ? 'text-[#ffb74d]/80' : 'text-[#555555]';
    const valueCls = warn ? 'text-[#ffb74d]' : 'text-[#FFFFFF]';
    const idAttr = cardId ? ` id="${cardId}"` : '';
    // 可点卡片由 updateWpbHud 按 count 开关 data-clickable
    const clickable = action
        ? `${idAttr} data-action="${action}" data-clickable="0" class="bg-[#0D0D11]/80 border ${border} p-3 backdrop-blur-sm opacity-60 cursor-default transition-colors"`
        : `${idAttr} class="bg-[#0D0D11]/80 border ${border} p-3 backdrop-blur-sm"`;
    return `
        <div${clickable}
             style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
            <div class="${labelCls} text-[10px] tracking-wider">${label}</div>
            <div class="text-[18px] font-bold ${valueCls} mt-1 tabular-nums">
                <span id="${id}">—</span>
                <span class="text-[10px] text-[#555555] ml-1">${unit}</span>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-[#555555]" for="${id}">${label}</label>
            <select id="${id}"
                    class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all min-w-[7rem]">
                <option value="">全部</option>
            </select>
        </div>
    `;
}

function levelFilterSelect() {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-[#555555]" for="wpbLevelFilter">层级</label>
            <select id="wpbLevelFilter"
                    class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all min-w-[9rem]">
                <option value="">全部</option>
                <option value="0">L0 供货总成</option>
                <option value="1">L1 分总成</option>
            </select>
        </div>
    `;
}

function processCountFilterSelect() {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-[#555555]" for="wpbProcessCountFilter">工艺数</label>
            <select id="wpbProcessCountFilter"
                    class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all min-w-[9rem]">
                <option value="">全部</option>
                <option value="0">= 0（异常）</option>
            </select>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="wpbDetailBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[600px] max-w-full bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="wpbDetailDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase min-w-0">
                    <span class="w-0.5 h-3.5 bg-[#d32f2f] shrink-0 shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                    <span id="wpbDetailTitle" class="truncate">拆解明细</span>
                </h5>
                <button type="button" id="wpbCloseDetailDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all shrink-0">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4" id="wpbDetailBody"></div>
        </div>
    `;
}

function batchDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="wpbBatchBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="wpbBatchDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span class="w-0.5 h-3.5 bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                    <span id="wpbBatchTitle">批量操作</span>
                </h5>
                <button type="button" id="wpbCloseBatchDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="wpbBatchMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="wpbBatchScopeSummary"></div>
                <p id="wpbBatchHint" class="text-[11px] text-[#616161]"></p>
                <div id="wpbBatchRemarkWrap">
                    <label class="text-[10px] text-[#777777] mb-1 block" id="wpbBatchRemarkLabel">审核意见</label>
                    <textarea id="wpbBatchRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] rounded resize-none"
                              placeholder=""></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex justify-end gap-2 shrink-0">
                <button type="button" id="wpbCancelBatch"
                        class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:text-white transition-all">取消</button>
                <button type="button" id="wpbConfirmBatch"
                        class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">确认</button>
            </div>
        </div>
    `;
}

export function updateWpbHud(summary) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val == null ? '—' : String(val);
    };
    set('wpbHudTotal', summary?.total_count);
    set('wpbHudL0', summary?.l0_count);
    set('wpbHudPending', summary?.pending_count);
    set('wpbHudApproved', summary?.approved_count);
    const zeroProcess = Number(summary?.l0_zero_process_count) || 0;
    set('wpbHudZeroProcess', zeroProcess);
    const zeroEl = document.getElementById('wpbHudZeroProcess');
    if (zeroEl) {
        zeroEl.className = zeroProcess > 0 ? 'text-[#ef5350]' : '';
    }
    const card = document.getElementById('wpbHudZeroProcessCard');
    if (!card) return;
    const canClick = zeroProcess > 0;
    card.dataset.clickable = canClick ? '1' : '0';
    card.title = canClick ? '点击筛选：层级 L0 + 工艺数=0' : '';
    card.classList.toggle('opacity-60', !canClick);
    card.classList.toggle('opacity-100', canClick);
    card.classList.toggle('cursor-default', !canClick);
    card.classList.toggle('cursor-pointer', canClick);
    card.classList.toggle('hover:border-[#FF1E27]/40', canClick);
}

export function updateWpbCapsules(state) {
    const setCap = (id, emptyLabel, value) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value || emptyLabel;
    };
    setCap('wpbCapsuleLocation', '全部基地', state.location);
    setCap('wpbCapsuleModel', '全部项目', state.vehicleModel);
    setCap('wpbCapsuleVersion', '全部版本', state.bomVersion);
    const levelMap = { 0: 'L0 供货总成', 1: 'L1 分总成' };
    const levelLabel = state.level == null || Number.isNaN(state.level)
        ? null
        : (levelMap[state.level] || `L${state.level}`);
    setCap('wpbCapsuleLevel', '全部层级', levelLabel);
    const processCountLabel = state.processLineCountEq === 0
        ? (state.level === 0 ? 'L0 · 工艺数=0' : '工艺数 = 0')
        : null;
    setCap('wpbCapsuleProcessCount', '全部工艺数', processCountLabel);
    const auditMap = { pending: '待审', approved: '已审' };
    setCap('wpbCapsuleAudit', '全部审核', auditMap[state.auditStatus] || state.auditStatus);
}

export function renderWpbTableRows(records) {
    if (!records.length) return '';
    return records.map((row) => {
        const audit = AUDIT_LABEL[row.audit_status] || { text: row.audit_status || '-', cls: 'text-[#8E8E93]' };
        const lineCount = Number(row.process_line_count) || 0;
        const isZeroProcess = lineCount === 0;
        const weld = row.weld_info_raw || '';
        // 关键列：对齐零件价格「单件成本」KPI 格；0 仍红字警示
        const countCell =
            'px-2 py-1.5 text-center font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20';
        const countTitle = isZeroProcess
            ? (row.level === 0 ? 'L0 工艺数=0，计费异常' : '工艺数=0')
            : `工艺数 ${lineCount}`;
        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100"
                data-node-id="${row.id}">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.location)}</td>
                <td class="px-2 py-2 text-[#F0F0F2] font-semibold truncate">${esc(row.vehicle_model)}</td>
                <td class="px-2 py-2 text-[#C8C8D0] truncate">${esc(row.bom_version)}</td>
                <td class="px-2 py-2 overflow-hidden">${wpbPartInfoCell(row)}</td>
                <td class="px-2 py-2 text-center text-[#8E8E93]">L${esc(row.level)}</td>
                <td class="px-2 py-2 text-right tabular-nums text-[#8E8E93]">${esc(fmtQty(row.assembly_qty))}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-[#8E8E93] truncate" title="${esc(weld)}">${esc(weld)}</div>
                </td>
                <td class="${countCell}" title="${esc(countTitle)}">
                    <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${lineCount}</span>
                </td>
                <td class="px-2 py-2 text-center text-[10px] text-[#8E8E93]">${esc(row.parse_status)}</td>
                <td class="px-2 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${audit.text}</span>
                </td>
                <td class="px-1 py-2 text-center">
                    <button type="button" data-action="detail" data-node-id="${row.id}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded text-[#6E6E73] hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                            title="查看 / 编辑">
                        ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/** 与 BOM viz 一致：数字末四位 */
function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/**
 * 与 BOM viz 分总成/焊接件一致：
 * - 无 -N → 数字末四位
 * - 有 -N → 末四位 + 字母尾 + -N（501005123AA-1 → 5123AA-1）
 */
function shortWeldPartNumber(partNumber) {
    if (!partNumber) return null;
    const raw = String(partNumber).trim();
    if (!raw) return null;
    const match = raw.match(/(\d{4,})([A-Za-z]*)(-\d+)\s*$/);
    if (match) {
        const digitsTail = match[1].slice(-4);
        const letters = match[2] || '';
        const dashSuffix = match[3];
        return `${digitsTail}${letters}${dashSuffix}`;
    }
    return shortPartNumber(raw);
}

/** L0/供货 → 末四位；其余焊接分总成 → shortWeldPartNumber（同 viz） */
function resolveWpbShortPartNumber(row) {
    const full = row?.part_number || '';
    const isSupply = Number(row?.level) === 0 || row?.node_role === 'supply';
    if (isSupply) return shortPartNumber(full) || full;
    return shortWeldPartNumber(full) || full;
}

/** 列表单元格：短号主角，完整号 + 名称次要（对齐零件价格一览） */
function wpbPartInfoCell(row) {
    const full = row.part_number || '';
    const shortNo = resolveWpbShortPartNumber(row);
    const name = row.part_name || '';
    const nameLine = name
        ? `<div class="text-[9px] text-[#555555] mt-0.5 truncate" title="${esc(name)}">${esc(name)}</div>`
        : '';
    if (shortNo && shortNo !== full) {
        return `
            <div class="text-[14px] font-mono font-bold tabular-nums text-[#F0F0F2] tracking-[0.08em] leading-none"
                 title="${esc(full)}">${esc(shortNo)}</div>
            <div class="text-[9px] font-mono text-[#3A3A42] tracking-wide mt-0.5 truncate" title="${esc(full)}">${esc(full)}</div>
            ${nameLine}`;
    }
    return `
        <div class="text-[10px] font-mono text-[#8E8E93] tracking-wide truncate" title="${esc(full)}">${esc(full) || '—'}</div>
        ${nameLine}`;
}

export function renderWpbDetailBody(node, {
    canEdit = false,
    standardProcessNames = FALLBACK_STANDARD_PROCESS_NAMES,
} = {}) {
    if (!node) return '<p class="text-[11px] text-[#616161]">无数据</p>';
    const isPending = node.audit_status === 'pending';
    const editable = canEdit && isPending;
    const lines = Array.isArray(node.lines) ? node.lines : [];
    const processNames = (Array.isArray(standardProcessNames) && standardProcessNames.length)
        ? standardProcessNames
        : FALLBACK_STANDARD_PROCESS_NAMES;

    const nodeReadonly = `
            <div class="text-[10px] text-[#555555] font-mono mt-2">
                装配用量 ${esc(fmtQty(node.assembly_qty))}${node.assembly_qty_unit ? ' ' + esc(node.assembly_qty_unit) : ''}
                <span class="text-[#3A3A42]"> · 主表来自 BOM，只读</span>
                ${!isPending ? ' · 已审锁定，明细须反审核后可编辑' : ''}
            </div>
            ${Number(node.level) === 0 ? `
            <p class="text-[10px] text-[#ffb74d] mt-2 leading-relaxed border border-[#ffb74d]/25 bg-[#1A1710] px-2.5 py-1.5">
                本行为 L0 供货总成：焊接加工费以此处过程量为准，请仔细核对原文与明细。旁证不可信。
            </p>` : `
            <p class="text-[10px] text-[#555555] mt-2 leading-relaxed">
                本行为 L${esc(node.level)}：不计费真相；加工费请以所属 L0 为准。
            </p>`}
            ${node.qa_note ? `<p class="text-[10px] text-[#ffb74d] mt-2">${esc(node.qa_note)}</p>` : ''}
        `;

    const linesHtml = lines.length
        ? lines.map((ln) => renderLineCard(ln, editable, processNames)).join('')
        : '<p class="text-[11px] text-[#616161]">无明细行</p>';

    const evidenceHtml = renderEvidencePanel(node.evidence);

    return `
        <div class="space-y-3">
            <div class="bg-[#0c0c0c] border border-[#1a1a1a] p-3 space-y-2">
                <div class="text-[14px] font-bold text-[#F0F0F2] font-mono">${esc(node.part_number)}</div>
                <div class="text-[12px] text-[#9e9e9e]">${esc(node.part_name)}</div>
                <div class="text-[10px] text-[#555555] font-mono">
                    ${esc(node.location)} · ${esc(node.customer_name || '—')} · ${esc(node.vehicle_model)} · ${esc(node.bom_version)}
                    · L${esc(node.level)}
                </div>
                <div>
                    <div class="text-[9px] tracking-[0.08em] text-[#555555] mb-1">焊接原文</div>
                    <p class="text-[12px] text-[#C8C8D0] leading-relaxed whitespace-pre-wrap break-words">${esc(node.weld_info_raw)}</p>
                </div>
                ${nodeReadonly}
            </div>
            ${evidenceHtml}
            <div class="flex items-center gap-2">
                <span class="w-0.5 h-3 bg-[#d32f2f]"></span>
                <span class="text-[10px] tracking-[0.12em] text-[#9e9e9e]">明细 · 单件过程量</span>
                <span class="text-[10px] font-mono text-[#484848]">${lines.length}</span>
            </div>
            <div class="space-y-2">${linesHtml}</div>
        </div>
    `;
}

function evidenceStatusBadge(status) {
    const meta = EVIDENCE_STATUS_LABEL[status] || { text: status || '—', cls: 'text-[#8E8E93]' };
    return `<span class="text-[10px] font-medium ${meta.cls}">${esc(meta.text)}</span>`;
}

function renderEvidencePanel(evidence) {
    if (!evidence || !Array.isArray(evidence.items) || !evidence.items.length) {
        return `
            <div class="bg-[#0c0c0c] border border-[#1a1a1a] p-3">
                <div class="flex items-center gap-2 mb-1">
                    <span class="w-0.5 h-3 bg-[#ffb74d]"></span>
                    <span class="text-[10px] tracking-[0.12em] text-[#9e9e9e]">旁证核对（仅参考）</span>
                </div>
                <p class="text-[10px] text-[#555555]">暂无旁证展示。计费仍以 L0 为准，请人工核对 L0 原文。</p>
            </div>
        `;
    }
    const summaryCls = evidence.has_mismatch ? 'text-[#ef5350]' : 'text-[#8E8E93]';
    const itemsHtml = evidence.items.map((item) => {
        const rows = [];
        if (item.child_status && item.child_status !== 'skipped') {
            rows.push(`
                <div class="border-t border-[#1A1A22] pt-1.5 mt-1.5">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[10px] text-[#6E6E73]">子件紧固件</span>
                        ${evidenceStatusBadge(item.child_status)}
                    </div>
                    <p class="text-[10px] text-[#8E8E93] leading-relaxed mt-0.5 break-words">${esc(item.child_detail || '—')}</p>
                </div>
            `);
        }
        if (item.l1_status) {
            rows.push(`
                <div class="border-t border-[#1A1A22] pt-1.5 mt-1.5">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[10px] text-[#6E6E73]">L1 滚乘旁证</span>
                        ${evidenceStatusBadge(item.l1_status)}
                    </div>
                    <p class="text-[10px] text-[#8E8E93] leading-relaxed mt-0.5 break-words">${esc(item.l1_detail || '—')}</p>
                </div>
            `);
        }
        if (item.l2_status && item.l2_status !== 'skipped') {
            rows.push(`
                <div class="border-t border-[#1A1A22] pt-1.5 mt-1.5">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[10px] text-[#6E6E73]">L2 路径旁证</span>
                        ${evidenceStatusBadge(item.l2_status)}
                    </div>
                    <p class="text-[10px] text-[#8E8E93] leading-relaxed mt-0.5 break-words">${esc(item.l2_detail || '—')}</p>
                </div>
            `);
        }
        const qtyLabel = item.source_process_qty != null
            ? `原文 ${_fmtEvidenceQty(item.source_process_qty)}`
            : '原文无此工艺';
        return `
            <div class="border border-[#1E1E26] bg-[#0A0A0E] p-2.5 space-y-1">
                <div class="flex items-center justify-between gap-2">
                    <span class="text-[12px] font-semibold text-[#F0F0F2]">${esc(item.process_token)}</span>
                    <span class="text-[10px] font-mono text-[#8E8E93]">${esc(qtyLabel)}</span>
                </div>
                ${rows.join('') || '<p class="text-[10px] text-[#555555]">无可展示旁证链</p>'}
            </div>
        `;
    }).join('');

    return `
        <div class="bg-[#0c0c0c] border border-[#1a1a1a] p-3 space-y-2">
            <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                    <span class="w-0.5 h-3 bg-[#ffb74d]"></span>
                    <span class="text-[10px] tracking-[0.12em] text-[#9e9e9e]">旁证核对（仅参考 · 不可信）</span>
                </div>
                <span class="text-[10px] ${summaryCls}">${esc(evidence.summary || '')}</span>
            </div>
            <p class="text-[9px] text-[#ffb74d]/90 leading-relaxed">
                原始清单中 L1 口径不严谨，旁证差额常见且不能用于计费。焊接加工费必须按 L0 过程量计算；请仔细核对 L0 原文与明细。
            </p>
            <p class="text-[9px] text-[#555555] leading-relaxed">
                差额说明 = 原文 − 旁证，仅作抽检提示，不改正文过程量。
            </p>
            <div class="space-y-2">${itemsHtml}</div>
        </div>
    `;
}

function _fmtEvidenceQty(value) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (Number.isFinite(n)) return String(n);
    return String(value);
}

function renderLineCard(ln, editable, processNames) {
    const mapMeta = MAP_LABEL[ln.map_status] || { text: ln.map_status || '-', cls: 'text-[#8E8E93]' };
    const mapText = esc(mapMeta.text);
    const rollup = ROLLUP_LABEL[ln.rollup_flag] || ln.rollup_flag;
    if (!editable) {
        const qtySec = ln.process_qty_secondary != null
            ? ` / ${esc(fmtQty(ln.process_qty_secondary))}${esc(ln.process_qty_secondary_unit || '')}`
            : '';
        return `
            <div class="border border-[#1E1E26] bg-[#0c0c0c] p-3 space-y-1.5">
                <div class="flex items-center justify-between gap-2">
                    <span class="text-[12px] font-semibold text-[#F0F0F2]">#${esc(ln.line_no)} ${esc(ln.process_token)}</span>
                    <span class="text-[10px] ${mapMeta.cls}">${mapText}</span>
                </div>
                <div class="text-[10px] text-[#555555] font-mono truncate" title="${esc(ln.matched_span)}">${esc(ln.matched_span)}</div>
                <div class="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div><span class="text-[#555555]">单件过程量</span><div class="text-[#C8C8D0]">${esc(fmtQty(ln.process_qty))} ${esc(ln.process_qty_unit)}${qtySec}</div></div>
                    <div><span class="text-[#555555]">标准工艺</span><div class="text-[#FF1E27]/90">${esc(ln.standard_process_name || '—')}${ln.standard_process_unit ? ` <span class="text-[#8E8E93]">· ${esc(ln.standard_process_unit)}</span>` : ''}</div></div>
                    <div><span class="text-[#555555]">rollup</span><div class="text-[#8E8E93]">${esc(rollup)}</div></div>
                    <div><span class="text-[#555555]">子件校验</span><div class="text-[#8E8E93]">${esc(ln.qty_check_status)}${ln.qty_check_detail ? ' · ' + esc(ln.qty_check_detail) : ''}</div></div>
                </div>
            </div>
        `;
    }

    const stdOptions = ['<option value="">自动（按原文 token）</option>']
        .concat(processNames.map((name) => {
            const selected = ln.standard_process_name === name ? ' selected' : '';
            return `<option value="${esc(name)}"${selected}>${esc(name)}</option>`;
        }))
        .join('');

    return `
        <div class="border border-[#1E1E26] bg-[#0c0c0c] p-3 space-y-2" data-line-card="${ln.id}">
            <div class="flex items-center justify-between gap-2">
                <span class="text-[12px] font-semibold text-[#F0F0F2]">#${esc(ln.line_no)} ${esc(ln.process_token)}</span>
                <span class="text-[10px] ${mapMeta.cls}">${mapText}</span>
            </div>
            <div class="text-[10px] text-[#555555] font-mono truncate">${esc(ln.matched_span)}</div>
            <div class="grid grid-cols-2 gap-2">
                <div>
                    <label class="text-[9px] text-[#555555] mb-1 block">过程量</label>
                    <input data-field="process_qty" type="text" value="${esc(ln.process_qty)}"
                           class="w-full h-8 px-2 text-xs font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[9px] text-[#555555] mb-1 block">单位</label>
                    <input data-field="process_qty_unit" type="text" value="${esc(ln.process_qty_unit || '')}"
                           class="w-full h-8 px-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[9px] text-[#555555] mb-1 block">副过程量</label>
                    <input data-field="process_qty_secondary" type="text" value="${esc(ln.process_qty_secondary ?? '')}"
                           class="w-full h-8 px-2 text-xs font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[9px] text-[#555555] mb-1 block">副单位</label>
                    <input data-field="process_qty_secondary_unit" type="text" value="${esc(ln.process_qty_secondary_unit || '')}"
                           class="w-full h-8 px-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div class="col-span-2">
                    <label class="text-[9px] text-[#555555] mb-1 block">标准工艺</label>
                    <select data-field="standard_process_name"
                            class="w-full h-8 px-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                        ${stdOptions}
                    </select>
                    <div class="mt-1 text-[10px] font-mono text-[#8E8E93]">标准单位 ${esc(ln.standard_process_unit || '—')}（与过程量单位对照）</div>
                </div>
            </div>
            <div class="text-[10px] text-[#555555]">rollup ${esc(rollup)} · 子件 ${esc(ln.qty_check_status)}${ln.qty_check_detail ? ' · ' + esc(ln.qty_check_detail) : ''}</div>
            <div class="flex justify-end">
                <button type="button" data-action="save-line" data-line-id="${ln.id}"
                        class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-3 py-1 text-[10px] font-medium rounded hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                    保存明细
                </button>
            </div>
        </div>
    `;
}

export function renderWpbPagination(page, totalPages) {
    if (totalPages <= 1) return '';
    let html = '';
    const btn = (p, label, disabled = false, active = false) => {
        const base = 'min-w-[28px] h-7 px-2 text-[10px] font-mono rounded-sm border transition-all';
        const cls = active
            ? `${base} bg-[#FF1E27] border-[#FF1E27] text-white`
            : disabled
                ? `${base} border-[#1A1A22] text-[#3A3A42] cursor-not-allowed`
                : `${base} border-[#2A2A35] text-[#8E8E93] hover:border-[#FF1E27]/50 hover:text-white`;
        return `<button type="button" class="${cls}" data-page="${p}" ${disabled ? 'disabled' : ''}>${label}</button>`;
    };
    html += btn(Math.max(1, page - 1), '‹', page <= 1);
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + 4);
    for (let p = start; p <= end; p += 1) {
        html += btn(p, String(p), false, p === page);
    }
    html += btn(Math.min(totalPages, page + 1), '›', page >= totalPages);
    return html;
}

function fmtQty(value) {
    if (value == null || value === '') return '-';
    if (typeof fmtNum === 'function') return fmtNum(value, 4).replace(/\.?0+$/, '') || '0';
    return String(value);
}
