/**
 * BOM 焊接工艺拆解 — 列表模板（HUD 密表，可编辑）
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../more-menu.js?v=1';
import {
    partShortCodeCellHtml,
    partNumberNameCellHtml,
    resolveBomNodeShortCode,
} from '../../../../part-identity.js?v=3';

const AUDIT_LABEL = {
    pending: { text: '待审', cls: 'text-[#ffb74d] bg-[#ffb74d]/15' },
    approved: { text: '已审', cls: 'text-[#4caf50] bg-[#4caf50]/15' },
};

const EVIDENCE_STATUS_LABEL = {
    match: { text: '一致', cls: 'text-[#4caf50]' },
    mismatch: { text: '有差额', cls: 'text-[#ef5350]' },
    no_child: { text: '无可比对象', cls: 'text-[#8E8E93]' },
    skipped: { text: '本链不适用', cls: 'text-[#555555]' },
    l0_only: { text: '仅本节点有量', cls: 'text-[#ffb74d]' },
    orphan_only: { text: '仅下级有量', cls: 'text-[#ffb74d]' },
};

const EVIDENCE_CHAIN_LABEL = {
    child: '子件紧固件',
    l1: 'L1 用量滚乘',
    l2: 'L2 路径汇总',
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
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'wpbMoreWrap',
                                btnId: 'wpbMoreBtn',
                                menuId: 'wpbMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'btnWpbBatchApprove', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'btnWpbBatchReverse', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'btnWpbBatchDelete', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
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
                                <span id="wpbCapsuleLevel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">L0 供货总成</span>
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
                            <col style="width:8%">
                            <col style="width:14%">
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
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#A1A1A6]">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">层级</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">装配用量</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">焊接原文</th>
                                <th class="px-2 py-2 text-center text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]" title="有效工艺明细行数">工艺数</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">解析</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="wpbTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'wpbTotalCount', selectId: 'wpbPageSize', buttonsId: 'wpbPaginationBtns', wrapperId: 'wpbPaginationContainer' })}

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
                <option value="0" selected>L0 供货总成</option>
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
        <div id="wpbDetailDrawer"
             class="fixed top-0 right-0 z-[85] w-[720px] max-w-full bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             style="display:none; height:100vh; height:100dvh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
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
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-5" id="wpbDetailBody"></div>
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

export function renderWpbTableRows(records, options = {}) {
    if (!records.length) return '';
    const canView = !!options.canView;
    const canEdit = !!options.canEdit;
    return records.map((row) => {
        const audit = AUDIT_LABEL[row.audit_status] || { text: row.audit_status || '-', cls: 'text-[#8E8E93]' };
        const lineCount = Number(row.process_line_count) || 0;
        const isZeroProcess = lineCount === 0;
        const approved = row.audit_status === 'approved';
        const weld = row.weld_info_raw || '';
        // 关键列：对齐零件价格「单件成本」KPI 格；0 仍红字警示
        const countCell =
            'px-2 py-1.5 text-center font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20';
        const countTitle = isZeroProcess
            ? (row.level === 0 ? 'L0 工艺数=0，计费异常' : '工艺数=0')
            : `工艺数 ${lineCount}`;
        const viewBtn = canView ? `
                    <button type="button" data-action="view-detail" data-node-id="${row.id}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all"
                            title="查看明细" aria-label="查看明细">
                        ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                    </button>` : '';
        const editBtn = canEdit ? `
                    <button type="button" data-action="edit-detail" data-node-id="${row.id}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}"
                            title="${approved ? '已审核，不可编辑' : '编辑明细'}"
                            aria-label="${approved ? '已审核，不可编辑' : '编辑明细'}">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : '';
        const ops = (viewBtn || editBtn) ? `
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${viewBtn}${editBtn}
                </div>` : '<span class="text-[#3A3A42]">—</span>';
        const shortNo = resolveBomNodeShortCode(row.part_number, {
            level: row.level,
            nodeRole: row.node_role,
        });
        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100"
                data-node-id="${row.id}">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.location)}</td>
                <td class="px-2 py-2 text-[#F0F0F2] font-semibold truncate">${esc(row.vehicle_model)}</td>
                <td class="px-2 py-2 text-[#C8C8D0] truncate">${esc(row.bom_version)}</td>
                <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(row.part_number, shortNo)}</td>
                <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(row.part_number, row.part_name)}</td>
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
                <td class="px-1 py-2 text-center">${ops}</td>
            </tr>
        `;
    }).join('');
}

/** 与导出 Excel 标准单位目录对齐（仅前端即时展示） */
const STANDARD_PROCESS_UNIT = {
    焊点: '个',
    '植/螺柱/凸焊': '个',
    铆接: '个',
    CO2焊缝: 'CM',
    '折边/点焊胶': 'MM',
    电镀: '平方',
    '电泳（盐雾试验要求≤244H）': '平方',
    '电泳（盐雾试验要求244H-720H）': '平方',
    '电泳（盐雾试验要求＞720H）': '平方',
    压铆: '个',
    打铆钉: '个',
    二维码: '个',
    套袋: '个',
};

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
    const level = Number(node.level);
    const audit = AUDIT_LABEL[node.audit_status] || { text: node.audit_status || '—', cls: 'text-[#8E8E93]' };
    const qtyUnit = node.assembly_qty_unit ? ` ${esc(node.assembly_qty_unit)}` : '';
    const showSave = isPending && lines.length > 0;

    return `
        <div class="flex flex-col gap-3" id="wpbDetailRoot" data-editable="${editable ? '1' : '0'}">
            <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between gap-2 min-w-0">
                    <div class="text-[12px] text-[#C8C8D0] truncate min-w-0">${esc(node.part_name || '—')}</div>
                    <div class="flex items-center gap-1.5 shrink-0">
                        <span class="text-[10px] font-mono text-[#F0F0F2]">L${esc(level)}</span>
                        <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${esc(audit.text)}</span>
                        <span class="text-[10px] font-mono text-[#8E8E93]">装配 ${esc(fmtQty(node.assembly_qty))}${qtyUnit}</span>
                    </div>
                </div>
                <p class="text-[11px] text-[#9e9e9e] leading-relaxed whitespace-pre-wrap break-words">${esc(node.weld_info_raw || '—')}</p>
                ${node.qa_note ? `<p class="text-[10px] text-[#ffb74d]">${esc(node.qa_note)}</p>` : ''}
                ${!isPending ? '<p class="text-[9px] text-[#555555]">已审锁定；反审核后可改</p>' : ''}
            </div>
            ${renderProcessSection(lines, level, editable, processNames)}
            ${renderEvidencePanel(node.evidence)}
            ${showSave ? renderSaveBar(canEdit) : ''}
        </div>
    `;
}

function renderSaveBar(canSave) {
    return `
        <div class="flex items-center justify-end gap-3 pt-3 pb-1 border-t border-[#262626]">
            <p class="text-[9px] text-[#555555] mr-auto">有辅助量则核价用辅助量，否则用过程量；长度 mm↔cm，面积 平方≡m2/平方米</p>
            <button type="button" id="wpbSaveAllLines" data-action="save-all-lines"
                    ${canSave ? '' : 'disabled'}
                    title="${canSave ? '' : '无编辑权限'}"
                    class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                保存全部工艺
            </button>
        </div>
    `;
}

/** 标准工艺变更时刷新标准单位展示 */
export function refreshWpbLineDerived(card) {
    if (!card) return;
    const stdName = card.querySelector('[data-field="standard_process_name"]')?.value?.trim();
    const unitEl = card.querySelector('[data-standard-unit]');
    if (unitEl) {
        const fromSelect = stdName ? (STANDARD_PROCESS_UNIT[stdName] || '') : '';
        unitEl.textContent = fromSelect || unitEl.dataset.fallbackUnit || '—';
    }
}

function renderProcessSection(lines, level, editable, processNames) {
    const count = lines.length;
    const title = `L${level} 工艺`;

    if (!count) {
        return `
            <div class="flex items-center justify-between px-1 py-1">
                <span class="text-[10px] tracking-[0.12em] text-[#F0F0F2]">${esc(title)}</span>
                <span class="text-[11px] font-mono font-bold text-[#ef5350]">0 种</span>
            </div>
        `;
    }

    const cards = lines.map((ln) => renderProcessCard(ln, editable, processNames)).join('');
    return `
        <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2 px-0.5">
                <span class="text-[10px] tracking-[0.12em] text-[#F0F0F2]">${esc(title)}</span>
                <span class="text-[12px] font-mono font-bold tabular-nums text-[#F0F0F2]">
                    ${count}<span class="text-[10px] font-medium text-[#8E8E93] ml-1">种</span>
                </span>
            </div>
            <div class="flex flex-col gap-2">${cards}</div>
        </div>
    `;
}

function renderProcessCard(ln, editable, processNames) {
    const token = ln.process_token || '—';
    const stdName = ln.standard_process_name || '';
    const stdUnit = ln.standard_process_unit
        || (stdName ? STANDARD_PROCESS_UNIT[stdName] : '')
        || '—';

    if (!editable) {
        return `
            <div class="border border-[#1E1E26] bg-[#0c0c0c] px-3 py-2 flex flex-col gap-1.5">
                <div class="flex items-baseline justify-between gap-2">
                    <span class="text-[12px] font-semibold text-[#F0F0F2]">${esc(token)}</span>
                    <span class="text-[9px] font-mono text-[#555555]">#${esc(ln.line_no)}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
                    <div class="text-[#555555]">过程量</div>
                    <div class="text-right text-[#C8C8D0]">${esc(fmtQty(ln.process_qty))} ${esc(ln.process_qty_unit || '')}</div>
                    <div class="text-[#555555]">辅助量</div>
                    <div class="text-right text-[#C8C8D0]">${ln.process_qty_secondary != null ? `${esc(fmtQty(ln.process_qty_secondary))} ${esc(ln.process_qty_secondary_unit || '')}` : '—'}</div>
                    <div class="text-[#555555]">标准工艺</div>
                    <div class="text-right text-[#C8C8D0]">
                        ${esc(stdName || '—')}<span class="text-[#8E8E93] ml-1">${esc(stdUnit)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    const stdOptions = ['<option value="">自动（按原文）</option>']
        .concat(processNames.map((name) => {
            const selected = ln.standard_process_name === name ? ' selected' : '';
            return `<option value="${esc(name)}"${selected}>${esc(name)}</option>`;
        }))
        .join('');

    const inputCls = 'h-7 px-1.5 text-xs font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]';
    return `
        <div class="border border-[#1E1E26] bg-[#0c0c0c] px-3 py-2 flex flex-col gap-1.5" data-line-card="${ln.id}">
            <div class="flex items-baseline justify-between gap-2">
                <span class="text-[12px] font-semibold text-[#F0F0F2]">${esc(token)}</span>
                <span class="text-[9px] font-mono text-[#555555]">#${esc(ln.line_no)}</span>
            </div>
            <div class="grid grid-cols-[4rem_1fr_3rem] gap-x-2 gap-y-1.5 items-center text-[10px]">
                <span class="text-[#555555]">过程量</span>
                <input data-field="process_qty" type="text" inputmode="decimal" value="${esc(fmtQty(ln.process_qty))}"
                       class="${inputCls} w-full text-right text-[#C8C8D0]">
                <input data-field="process_qty_unit" type="text" value="${esc(ln.process_qty_unit || '')}"
                       class="${inputCls} w-full text-center text-[#8E8E93]" placeholder="单位" title="过程量单位">

                <span class="text-[#555555]">辅助量</span>
                <input data-field="process_qty_secondary" type="text" inputmode="decimal"
                       value="${esc(ln.process_qty_secondary != null ? fmtQty(ln.process_qty_secondary) : '')}"
                       class="${inputCls} w-full text-right text-[#C8C8D0]" placeholder="无则空">
                <input data-field="process_qty_secondary_unit" type="text"
                       value="${esc(ln.process_qty_secondary_unit || '')}"
                       class="${inputCls} w-full text-center text-[#8E8E93]" placeholder="单位" title="辅助量单位">

                <span class="text-[#555555]">标准工艺</span>
                <select data-field="standard_process_name"
                        class="h-7 px-1.5 text-[10px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#C8C8D0] focus:outline-none focus:border-[#ff5252] w-full">
                    ${stdOptions}
                </select>
                <span class="text-center font-mono text-[10px] text-[#8E8E93]"
                      data-standard-unit data-fallback-unit="${esc(ln.standard_process_unit || '')}">${esc(stdUnit)}</span>
            </div>
        </div>
    `;
}

function evidenceStatusBadge(status) {
    const meta = EVIDENCE_STATUS_LABEL[status] || { text: status || '—', cls: 'text-[#8E8E93]' };
    return `<span class="text-[10px] font-medium ${meta.cls}">${esc(meta.text)}</span>`;
}

function evidenceChainRow(label, status, detail) {
    if (!status || status === 'skipped') return '';
    const detailHtml = detail
        ? `<p class="text-[9px] text-[#555555] leading-relaxed mt-0.5 break-words">${esc(detail)}</p>`
        : '';
    return `
        <div class="flex flex-col gap-0.5 py-1.5 border-t border-[#141418] first:border-0 first:pt-0">
            <div class="flex items-center justify-between gap-2">
                <span class="text-[10px] text-[#6E6E73]">${esc(label)}</span>
                ${evidenceStatusBadge(status)}
            </div>
            ${detailHtml}
        </div>
    `;
}

/**
 * 结构旁证：默认折叠。
 * 用途=抽检提示；不计费，不改正文过程量。详细核对请导出。
 */
function renderEvidencePanel(evidence) {
    const hasItems = evidence && Array.isArray(evidence.items) && evidence.items.length;
    const mismatchCount = hasItems
        ? evidence.items.filter((item) => (
            item.child_status === 'mismatch'
            || item.l1_status === 'mismatch'
            || item.l2_status === 'mismatch'
        )).length
        : 0;
    const summaryRight = !hasItems
        ? '<span class="text-[#555555]">暂无数据</span>'
        : (evidence.has_mismatch || mismatchCount > 0)
            ? `<span class="text-[#ef5350]">${mismatchCount || '存在'} 项差额</span>`
            : '<span class="text-[#4caf50]">抽检一致</span>';

    let body;
    if (!hasItems) {
        body = `
            <p class="text-[10px] text-[#555555] leading-relaxed">
                当前节点无可展示的结构旁证。计费仍以本节点过程量 / 辅助量为准；需要全量核对时请使用「导出L0核对」。
            </p>
        `;
    } else {
        const rows = evidence.items.map((item) => {
            const chains = [
                evidenceChainRow(EVIDENCE_CHAIN_LABEL.child, item.child_status, item.child_detail),
                evidenceChainRow(EVIDENCE_CHAIN_LABEL.l1, item.l1_status, item.l1_detail),
                evidenceChainRow(EVIDENCE_CHAIN_LABEL.l2, item.l2_status, item.l2_detail),
            ].filter(Boolean).join('');
            const srcQty = item.source_process_qty != null
                ? `<span class="font-mono tabular-nums text-[#8E8E93]">原文 ${esc(fmtQty(item.source_process_qty))}</span>`
                : '<span class="text-[#555555]">原文无此工艺</span>';
            return `
                <div class="border border-[#1E1E26] bg-[#0A0A0E] px-2.5 py-2">
                    <div class="flex items-center justify-between gap-2 mb-1">
                        <span class="text-[11px] font-medium text-[#C8C8D0]">${esc(item.process_token)}</span>
                        ${srcQty}
                    </div>
                    ${chains || '<p class="text-[9px] text-[#555555]">无可比链路</p>'}
                </div>
            `;
        }).join('');
        body = `
            <p class="text-[9px] text-[#555555] leading-relaxed mb-2">
                旁证由 BOM 结构推算，用于抽检；<span class="text-[#8E8E93]">不计费、不改正文</span>。
                差额 = 原文过程量 − 旁证推算值。L1 口径常见不严谨，差额需人工判断。
            </p>
            <div class="flex flex-col gap-2">${rows}</div>
        `;
    }

    return `
        <details class="border border-[#1a1a1a] group">
            <summary class="cursor-pointer list-none px-3 py-2.5 flex items-center justify-between gap-2 select-none
                            text-[10px] text-[#6E6E73] hover:text-[#C8C8D0] transition-colors
                            [&::-webkit-details-marker]:hidden">
                <span class="flex items-center gap-2 min-w-0">
                    <span class="text-[#3A3A42] group-open:rotate-90 transition-transform inline-block shrink-0">▸</span>
                    <span class="text-[#8E8E93]">结构旁证</span>
                    <span class="text-[#3A3A42] truncate">· 抽检用 · 不计费</span>
                </span>
                <span class="shrink-0 font-mono">${summaryRight}</span>
            </summary>
            <div class="px-3 pb-3 pt-0">${body}</div>
        </details>
    `;
}


function fmtQty(value) {
    if (value == null || value === '') return '—';
    if (typeof fmtNum === 'function') return fmtNum(value, 4);
    return String(value);
}
