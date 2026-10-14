/**
 * BOM 焊接工艺拆解 — 列表模板（HUD 密表，可编辑）
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_GHOST, HUD_LED, BTN_SOLID, HUD_FILTER } from '../../../../ui/classes.js?v=15';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=7';
import {
    partShortCodeCellHtml,
    partNumberNameCellHtml,
    resolveBomNodeShortCode,
} from '../../../../domain/part-identity.js?v=5';

const PARSE_LABEL = {
    ok: '正常',
    partial: '部分识别',
    unparsed: '未识别',
    anomaly: '异常',
};

const AUDIT_LABEL = {
    pending: { text: '待审', cls: 'text-warn bg-warn/15' },
    approved: { text: '已审', cls: 'text-ok bg-ok/15' },
};

const EVIDENCE_STATUS_LABEL = {
    match: { text: '一致', cls: 'text-ok' },
    mismatch: { text: '有差额', cls: 'text-danger' },
    no_child: { text: '无可比对象', cls: 'text-ink-muted' },
    skipped: { text: '本链不适用', cls: 'text-ink-faint' },
    l0_only: { text: '仅本级有用量', cls: 'text-warn' },
    orphan_only: { text: '仅下级有量', cls: 'text-warn' },
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
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({ title: '拆解', valueHtml: '<span id="wpbHudTotal">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: 'L0 总成', valueHtml: '<span id="wpbHudL0">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '待审', valueHtml: '<span id="wpbHudPending">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '已审', valueHtml: '<span id="wpbHudApproved">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({
                                title: 'L0 · 工艺数为 0',
                                tone: 'warn',
                                id: 'wpbHudZeroProcessCard',
                                attrs: 'data-action="filter-zero-process" data-clickable="0"',
                                extraClass: 'opacity-60 cursor-default transition-colors',
                                valueHtml: '<span id="wpbHudZeroProcess">—</span>',
                                unit: '条',
                            })}
                        </div>
                        <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
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
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出L0核对
                            </button>
                        </div>
                    </div>
                    <p class="text-[10px] text-ink-muted leading-relaxed">
                        焊接费<strong class="font-semibold text-ink">只按 L0 供货总成</strong>的过程量计算。
                        <span class="text-ink-faint">L1、L2 只作参考，不计入金额。</span>
                        工艺数为 0 的供货总成，用上方「L0 · 工艺数为 0」筛选。
                        「导出L0核对」按当前筛选导出供货总成和工艺明细，不含审核状态。
                        拆解记录来自材料清单，不能修改。尚未审核时，可以修改明细里的过程量和标准工艺。
                    </p>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'wpb',
                        searchId: 'btnWpbFilter',
                        capsules: [
                            { capsuleId: 'wpbCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'wpbCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'wpbCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'wpbCapsuleLevel', idleLabel: '全部层级' },
                            { capsuleId: 'wpbCapsuleProcessCount', idleLabel: '全部工艺数' },
                            { capsuleId: 'wpbCapsuleAudit', idleLabel: '全部审核' },
                        ],
                        fieldsHtml: [
                            filterSelect('wpbLocationFilter', '基地'),
                            filterSelect('wpbModelFilter', '项目'),
                            filterSelect('wpbVersionFilter', '版本'),
                            filterSelect('wpbAuditFilter', '审核状态'),
                            levelFilterSelect(),
                            processCountFilterSelect(),
                            filterInput('wpbPartNumberFilter', '零件号', '模糊…', { widthClass: 'w-40' }),
                            `<button id="wpbResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量审核、反审核、删除要先选基地、项目、版本。异常是：L0 供货总成的工艺数是 0。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'wpb',
                    minWidth: '1280px',
                    colgroupHtml: `
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
                            <col style="width:7%">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">版本</th>
                                <th class="record-key px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">层级</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">装配用量</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">焊接原文</th>
                                <th class="px-2 py-2 text-center text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10" title="有效工艺明细行数">工艺数</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">解析</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '没有拆解数据', hint: '当前筛选下没有拆解数据。可在「焊接工艺拆解」从材料清单生成。' },
                    loading: true,
                })}
            </div>
        </div>

        ${detailDrawerHtml()}
        ${batchDrawerHtml()}
    `;
}

function levelFilterSelect() {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-ink-faint" for="wpbLevelFilter">层级</label>
            <select id="wpbLevelFilter"
                    class="min-w-[9rem] ${HUD_FILTER}">
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
            <label class="text-[9px] tracking-[0.08em] text-ink-faint" for="wpbProcessCountFilter">工艺数</label>
            <select id="wpbProcessCountFilter"
                    class="min-w-[9rem] ${HUD_FILTER}">
                <option value="">全部</option>
                <option value="0">= 0（异常）</option>
            </select>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="wpbDetailBackdrop" style="display:none"></div>
        <div id="wpbDetailDrawer"
             class="${DRAWER_SHELL} w-[720px] transform translate-x-full transition-transform duration-300 ease-in-out"
             style="display:none; height:100vh; height:100dvh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase min-w-0">
                    <span class="${HUD_LED}"></span>
                    <span id="wpbDetailTitle" class="truncate">拆解明细</span>
                </h5>
                <button type="button" id="wpbCloseDetailDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-ink-dim hover:text-ink hover:bg-brand transition-all shrink-0">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-5" id="wpbDetailBody"></div>
        </div>
    `;
}

function batchDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="wpbBatchBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="wpbBatchDrawer" style="display:none; max-height:100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="wpbBatchTitle">批量操作</span>
                </h5>
                <button type="button" id="wpbCloseBatchDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="wpbBatchMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="wpbBatchScopeSummary"></div>
                <p id="wpbBatchHint" class="text-[11px] text-ink-dim"></p>
                <div id="wpbBatchRemarkWrap">
                    <label class="text-[10px] text-ink-dim mb-1 block" id="wpbBatchRemarkLabel">审核意见</label>
                    <textarea id="wpbBatchRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink focus:outline-none focus:border-brand-active rounded resize-none"
                              placeholder=""></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex justify-end gap-2 shrink-0">
                <button type="button" id="wpbCancelBatch"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="wpbConfirmBatch"
                        class="${BTN_SOLID}">确认</button>
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
        zeroEl.className = zeroProcess > 0 ? 'text-danger' : '';
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
    card.classList.toggle('hover:border-brand-hud/40', canClick);
}

export function renderWpbTableRows(records, options = {}) {
    if (!records.length) return '';
    const canView = !!options.canView;
    const canEdit = !!options.canEdit;
    return records.map((row) => {
        const audit = AUDIT_LABEL[row.audit_status] || { text: row.audit_status || '-', cls: 'text-ink-muted' };
        const lineCount = Number(row.process_line_count) || 0;
        const isZeroProcess = lineCount === 0;
        const approved = row.audit_status === 'approved';
        const weld = row.weld_info_raw || '';
        // 关键列：对齐零件价格「单件成本」KPI 格；0 仍红字警示
        const countCell =
            'px-2 py-1.5 text-center font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20';
        const countTitle = isZeroProcess
            ? (row.level === 0 ? 'L0 工艺数=0，计费异常' : '工艺数=0')
            : `工艺数 ${lineCount}`;
        const viewBtn = canView
            ? opsIconButtonHtml({
                action: 'view-detail',
                title: '查看明细',
                icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
                attrs: `data-node-id="${row.id}"`,
            })
            : '';
        const editBtn = canEdit
            ? opsIconButtonHtml({
                action: 'edit-detail',
                extraClass: approved ? 'opacity-30 pointer-events-none' : '',
                title: approved ? '已审核，不可编辑' : '编辑明细',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                attrs: `data-node-id="${row.id}"`,
            })
            : '';
        const opsHtml = (viewBtn || editBtn) ? `${viewBtn}${editBtn}` : '—';
        const shortNo = resolveBomNodeShortCode(row.part_number, {
            level: row.level,
            nodeRole: row.node_role,
        });
        return hudRowHtml({
            attrs: `data-node-id="${row.id}"`,
            cellsHtml: `
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.location)}</td>
                <td class="px-2 py-2 text-ink font-semibold truncate">${esc(row.vehicle_model)}</td>
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.bom_version)}</td>
                <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(row.part_number, shortNo)}</td>
                <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(row.part_number, row.part_name)}</td>
                <td class="px-2 py-2 text-center text-ink-muted">L${esc(row.level)}</td>
                <td class="px-2 py-2 text-right tabular-nums text-ink-muted">${esc(fmtQty(row.assembly_qty))}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-ink-muted truncate" title="${esc(weld)}">${esc(weld)}</div>
                </td>
                <td class="${countCell}" title="${esc(countTitle)}">
                    <span>${lineCount}</span>
                </td>
                <td class="px-2 py-2 text-center text-[10px] text-ink-muted">${esc(PARSE_LABEL[row.parse_status] || (row.parse_status ? '状态不明' : '—'))}</td>
                <td class="px-2 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${audit.text}</span>
                </td>`,
            opsHtml,
        });
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
    if (!node) return '<p class="text-[11px] text-ink-dim">无数据</p>';
    const isPending = node.audit_status === 'pending';
    const editable = canEdit && isPending;
    const lines = Array.isArray(node.lines) ? node.lines : [];
    const processNames = (Array.isArray(standardProcessNames) && standardProcessNames.length)
        ? standardProcessNames
        : FALLBACK_STANDARD_PROCESS_NAMES;
    const level = Number(node.level);
    const audit = AUDIT_LABEL[node.audit_status] || { text: node.audit_status || '—', cls: 'text-ink-muted' };
    const qtyUnit = node.assembly_qty_unit ? ` ${esc(node.assembly_qty_unit)}` : '';
    const showSave = isPending && lines.length > 0;

    return `
        <div class="flex flex-col gap-3" id="wpbDetailRoot" data-editable="${editable ? '1' : '0'}">
            <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between gap-2 min-w-0">
                    <div class="text-[12px] text-ink-muted truncate min-w-0">${esc(node.part_name || '—')}</div>
                    <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
                        <span class="text-[10px] font-mono text-ink">L${esc(level)}</span>
                        <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${esc(audit.text)}</span>
                        <span class="text-[10px] font-mono text-ink-muted">装配 ${esc(fmtQty(node.assembly_qty))}${qtyUnit}</span>
                    </div>
                </div>
                <p class="text-[11px] text-ink-muted leading-relaxed whitespace-pre-wrap break-words">${esc(node.weld_info_raw || '—')}</p>
                ${node.qa_note ? `<p class="text-[10px] text-warn">${esc(node.qa_note)}</p>` : ''}
                ${!isPending ? '<p class="text-[9px] text-ink-faint">已审锁定；反审核后可改</p>' : ''}
            </div>
            ${renderProcessSection(lines, level, editable, processNames)}
            ${renderEvidencePanel(node.evidence)}
            ${showSave ? renderSaveBar(canEdit) : ''}
        </div>
    `;
}

function renderSaveBar(canSave) {
    return `
        <div class="flex items-center justify-end gap-3 pt-3 pb-1 border-t border-app-elevated">
            <p class="text-[9px] text-ink-faint mr-auto">有辅助量就按辅助量算，没有就按过程量。长度的毫米和厘米要换算；面积里的「平方」就是平方米。</p>
            <button type="button" id="wpbSaveAllLines" data-action="save-all-lines"
                    ${canSave ? '' : 'disabled'}
                    title="${canSave ? '' : '无编辑权限'}"
                    class="${BTN_SOLID} disabled:opacity-40 disabled:cursor-not-allowed">
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
                <span class="text-[10px] tracking-[0.12em] text-ink">${esc(title)}</span>
                <span class="text-[11px] font-mono font-bold text-danger">0 种</span>
            </div>
        `;
    }

    const cards = lines.map((ln) => renderProcessCard(ln, editable, processNames)).join('');
    return `
        <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2 px-0.5">
                <span class="text-[10px] tracking-[0.12em] text-ink">${esc(title)}</span>
                <span class="text-[12px] font-mono font-bold tabular-nums text-ink">
                    ${count}<span class="text-[10px] font-medium text-ink-muted ml-1">种</span>
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
            <div class="border border-line-hud bg-app-deep px-3 py-2 flex flex-col gap-1.5">
                <div class="flex items-baseline justify-between gap-2">
                    <span class="text-[12px] font-semibold text-ink">${esc(token)}</span>
                    <span class="text-[9px] font-mono text-ink-faint">#${esc(ln.line_no)}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
                    <div class="text-ink-faint">过程量</div>
                    <div class="text-right text-ink-muted">${esc(fmtQty(ln.process_qty))} ${esc(ln.process_qty_unit || '')}</div>
                    <div class="text-ink-faint">辅助量</div>
                    <div class="text-right text-ink-muted">${ln.process_qty_secondary != null ? `${esc(fmtQty(ln.process_qty_secondary))} ${esc(ln.process_qty_secondary_unit || '')}` : '—'}</div>
                    <div class="text-ink-faint">标准工艺</div>
                    <div class="text-right text-ink-muted">
                        ${esc(stdName || '—')}<span class="text-ink-muted ml-1">${esc(stdUnit)}</span>
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

    const inputCls = 'h-7 px-1.5 text-xs font-mono bg-app-deep border border-line text-ink focus:outline-none focus:border-brand-active';
    return `
        <div class="border border-line-hud bg-app-deep px-3 py-2 flex flex-col gap-1.5" data-line-card="${ln.id}">
            <div class="flex items-baseline justify-between gap-2">
                <span class="text-[12px] font-semibold text-ink">${esc(token)}</span>
                <span class="text-[9px] font-mono text-ink-faint">#${esc(ln.line_no)}</span>
            </div>
            <div class="grid grid-cols-[4rem_1fr_3rem] gap-x-2 gap-y-1.5 items-center text-[10px]">
                <span class="text-ink-faint">过程量</span>
                <input data-field="process_qty" type="text" inputmode="decimal" value="${esc(fmtQty(ln.process_qty))}"
                       class="${inputCls} w-full text-right text-ink-muted">
                <input data-field="process_qty_unit" type="text" value="${esc(ln.process_qty_unit || '')}"
                       class="${inputCls} w-full text-center text-ink-muted" placeholder="单位" title="过程量单位">

                <span class="text-ink-faint">辅助量</span>
                <input data-field="process_qty_secondary" type="text" inputmode="decimal"
                       value="${esc(ln.process_qty_secondary != null ? fmtQty(ln.process_qty_secondary) : '')}"
                       class="${inputCls} w-full text-right text-ink-muted" placeholder="无则空">
                <input data-field="process_qty_secondary_unit" type="text"
                       value="${esc(ln.process_qty_secondary_unit || '')}"
                       class="${inputCls} w-full text-center text-ink-muted" placeholder="单位" title="辅助量单位">

                <span class="text-ink-faint">标准工艺</span>
                <select data-field="standard_process_name"
                        class="w-full ${HUD_FILTER}">
                    ${stdOptions}
                </select>
                <span class="text-center font-mono text-[10px] text-ink-muted"
                      data-standard-unit data-fallback-unit="${esc(ln.standard_process_unit || '')}">${esc(stdUnit)}</span>
            </div>
        </div>
    `;
}

function evidenceStatusBadge(status) {
    const meta = EVIDENCE_STATUS_LABEL[status] || { text: status || '—', cls: 'text-ink-muted' };
    return `<span class="text-[10px] font-medium ${meta.cls}">${esc(meta.text)}</span>`;
}

function evidenceChainRow(label, status, detail) {
    if (!status || status === 'skipped') return '';
    const detailHtml = detail
        ? `<p class="text-[9px] text-ink-faint leading-relaxed mt-0.5 break-words">${esc(detail)}</p>`
        : '';
    return `
        <div class="flex flex-col gap-0.5 py-1.5 border-t border-line-subtle first:border-0 first:pt-0">
            <div class="flex items-center justify-between gap-2">
                <span class="text-[10px] text-ink-dim">${esc(label)}</span>
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
        ? '<span class="text-ink-faint">暂无数据</span>'
        : (evidence.has_mismatch || mismatchCount > 0)
            ? `<span class="text-danger">${mismatchCount || '存在'} 项差额</span>`
            : '<span class="text-ok">抽检一致</span>';

    let body;
    if (!hasItems) {
        body = `
            <p class="text-[10px] text-ink-faint leading-relaxed">
                这一行没有可对照的结构。算钱仍按这一行的过程量或辅助量。要整表核对，用「导出L0核对」。
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
                ? `<span class="font-mono tabular-nums text-ink-muted">原文 ${esc(fmtQty(item.source_process_qty))}</span>`
                : '<span class="text-ink-faint">原文无此工艺</span>';
            return `
                <div class="border border-line-hud bg-app-hud px-2.5 py-2">
                    <div class="flex items-center justify-between gap-2 mb-1">
                        <span class="text-[11px] font-medium text-ink-muted">${esc(item.process_token)}</span>
                        ${srcQty}
                    </div>
                    ${chains || '<p class="text-[9px] text-ink-faint">没有可对照的数据</p>'}
                </div>
            `;
        }).join('');
        body = `
            <p class="text-[9px] text-ink-faint leading-relaxed mb-2">
                对照数按材料清单结构推出来，用来抽查；<span class="text-ink-muted">不算钱、不改原来的数</span>。
                差额 = 原文过程量 − 对照算出来的数。L1 的差额需要人工核对。
            </p>
            <div class="flex flex-col gap-2">${rows}</div>
        `;
    }

    return `
        <details class="border border-line-subtle group">
            <summary class="cursor-pointer list-none px-3 py-2.5 flex items-center justify-between gap-2 select-none
                            text-[10px] text-ink-dim hover:text-ink-muted transition-colors
                            [&::-webkit-details-marker]:hidden">
                <span class="flex items-center gap-2 min-w-0">
                    <span class="text-ink-faint group-open:rotate-90 transition-transform inline-block shrink-0">▸</span>
                    <span class="text-ink-muted">结构对照</span>
                    <span class="text-ink-faint truncate">· 抽查用 · 不算钱</span>
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
