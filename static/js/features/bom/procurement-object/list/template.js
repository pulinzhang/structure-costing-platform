/**
 * 采购对象清单列表 — HUD 密表（对齐冲压零件价格一览）
 */

import { filterSelect, filterInput, HUD_SHELL, HUD_BAND, OPS_TH, BTN_GHOST, DRAWER_BACKDROP, BTN_SOLID_DANGER, HUD_FILTER } from '../../../../ui/classes.js?v=12';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';
import { AUDIT_LABELS, CONFIRM_LABELS, KIND_LABELS, SECTION_LABELS } from '../labels.js?v=4';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';
import { fmtPeriodRange, hasClosedPeriod } from '../../../common/period-ui.js?v=5';

export function procurementObjectListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: SECTION_LABELS.object,
                                pulse: true,
                                valueHtml: '<span id="poHudObject">—</span>',
                                unit: '条',
                            })}
                            ${hudKpiCardHtml({
                                title: KIND_LABELS.l0_degenerate,
                                valueHtml: '<span id="poHudDegenerate">—</span>',
                                unit: '件',
                            })}
                            ${hudKpiCardHtml({
                                title: SECTION_LABELS.other_leaf,
                                valueHtml: '<span id="poHudOther">—</span>',
                                unit: '条',
                            })}
                            ${hudKpiCardHtml({
                                title: '审核进度',
                                valueHtml: '<span id="poHudPending">—</span>',
                                unit: '条待审',
                                footer: [{ label: '已审', valueHtml: '<span id="poHudApproved">—</span> 条' }],
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'poMoreWrap',
                                btnId: 'poMoreBtn',
                                menuId: 'poMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'poBatchApproveBtn', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'poBatchReverseBtn', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'poBatchDeleteBtn', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="poExportBtn" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                    <p id="poQaBanner" class="hidden text-[10px] text-warn mt-1"></p>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="flex items-center gap-2 mb-3">
                        <button type="button" data-section="" class="po-section-tab h-7 px-3 text-[11px] font-semibold rounded-md border border-brand-hud text-brand-hud bg-brand-hud/10">全部</button>
                        <button type="button" data-section="object" class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-line-hud text-ink-muted">${SECTION_LABELS.object}</button>
                        <button type="button" data-section="other_leaf" title="螺母、胶、塑料等非冲压件，仅供核对，不列入采购对象"
                                class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-line-hud text-ink-muted">${SECTION_LABELS.other_leaf}</button>
                        <button type="button" data-section="anomaly" class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-line-hud text-ink-muted">${SECTION_LABELS.anomaly}</button>
                    </div>
                    ${filterBarHtml({
                        prefix: 'po',
                        capsules: [
                            { capsuleId: 'poCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'poCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'poCapsuleVersion', idleLabel: '全部版本' },
                        ],
                        fieldsHtml: [
                            filterSelect('poLocationFilter', '基地'),
                            filterSelect('poModelFilter', '项目'),
                            filterSelect('poVersionFilter', '版本'),
                            filterSelect('poKindFilter', '对象种类'),
                            filterSelect('poConfirmFilter', '确认'),
                            filterSelect('poAuditFilter', '审核'),
                            filterInput('poSupplierFilter', '供应商', '缩写/工商名称/ERP'),
                            filterSelect('poHasSupplierFilter', '是否指定供应商'),
                            filterSelect('poIncludeExpiredFilter', '是否已过期'),
                            filterInput('poPartFilter', '零件号', '零件号或总成'),
                            `<button id="poResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '版本 = 这棵树属于哪个版本；选 EC 版本是在数采购件，不是这次改了几个件。批量审核 / 反审核 / 删除须选定基地、项目；版本可选（默认全部版本）；不勾选行。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'po',
                    bodyClass: 'font-mono text-[11px]',
                    minWidth: '1560px',
                    colgroupHtml: `
                            <col style="width:3px">
                            <col style="width:88px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:96px">
                            <col style="width:88px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:88px">
                            <col style="width:88px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">Excel</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">总成短码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">供货总成</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">对象种类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">材料</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">确认</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">供应商</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">生失效</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">范围</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    loading: true,
                })}
            </div>
        </div>
        ${auditDrawerHtml()}
        ${confirmDrawerHtml()}
        ${detailDrawerHtml()}
    `;
}



function auditDrawerHtml() {
    return `
        <div id="poBatchAuditDrawerBackdrop" class="hidden ${DRAWER_BACKDROP}"></div>
        <div id="poBatchAuditDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-app-main border-l border-line-hud z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-app-elevated flex items-center justify-between">
                <h3 id="poBatchAuditDrawerTitle" class="text-sm font-semibold text-ink">批量审核</h3>
                <button type="button" id="poBatchAuditCloseBtn" class="text-ink-muted hover:text-ink">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="poBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="poBatchAuditFilterSummary"></div>
                <p id="poBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">操作人</label>
                    <div id="poBatchAuditOperatorDisplay" class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">—</div>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="poBatchAuditRemarkLabel">审核意见<span class="text-brand-hud">*</span></label>
                    <textarea id="poBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-hud rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2">
                <button type="button" id="poBatchAuditCancelBtn" class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded hover:text-ink">取消</button>
                <button type="button" id="poBatchAuditConfirmBtn" class="inline-flex items-center gap-1.5 bg-brand-hud text-ink-onbrand px-4 py-2 text-[11px] font-semibold rounded hover:bg-brand-hover">确认提交</button>
            </div>
        </div>
        <div id="poBatchDeleteDrawerBackdrop" class="hidden ${DRAWER_BACKDROP}"></div>
        <div id="poBatchDeleteDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-app-main border-l border-line-hud z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-app-elevated flex items-center justify-between">
                <h3 class="text-sm font-semibold text-ink">批量删除</h3>
                <button type="button" id="poBatchDeleteCloseBtn" class="text-ink-muted hover:text-ink">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 p-6 space-y-4">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="poBatchDeleteSummary"></div>
                <p class="text-[11px] text-ink-dim">按范围整单删除：无已审时连清单头一并清除（与重新生成前覆盖一致）；有已审则只删待审行与核对区，清单头保留。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2">
                <button type="button" id="poBatchDeleteCancelBtn" class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded">取消</button>
                <button type="button" id="poBatchDeleteConfirmBtn" class="${BTN_SOLID_DANGER}">确认删除</button>
            </div>
        </div>
    `;
}

function confirmDrawerHtml() {
    return `
        <div id="poConfirmDrawerBackdrop" class="hidden ${DRAWER_BACKDROP}"></div>
        <div id="poConfirmDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-app-main border-l border-line-hud z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-app-elevated flex items-center justify-between">
                <h3 class="text-sm font-semibold text-ink">确认采购对象</h3>
                <button type="button" id="poConfirmCloseBtn" class="text-ink-muted hover:text-ink">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 p-6 space-y-4">
                <input type="hidden" id="poConfirmId">
                <div id="poConfirmPart" class="text-[12px] text-ink font-mono"></div>
                <label class="space-y-1 block">
                    <span class="text-[10px] text-ink-dim">确认状态</span>
                    <select id="poConfirmStatus" class="w-full ${HUD_FILTER}">
                        <option value="pending">待定</option>
                        <option value="outsourced">外发</option>
                        <option value="in_house">自制</option>
                    </select>
                </label>
                <label class="space-y-1 block" id="poConfirmSupplierWrap">
                    <span class="text-[10px] text-ink-dim">供应商</span>
                    <input type="hidden" id="poConfirmSupplier" value="">
                    <div class="relative">
                        <input id="poConfirmSupplierSearch" type="text" autocomplete="off"
                               placeholder="输入缩写、工商名称或 ERP 匹配"
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-hud disabled:text-ink-dim">
                        <div id="poConfirmSupplierMenu"
                             class="hidden absolute left-0 right-0 top-full mt-1 max-h-48 overflow-y-auto bg-app-main border border-line z-[90]"></div>
                    </div>
                    <p class="text-[10px] text-ink-faint">点选匹配结果，不必一次拉全量。找不到请到供应商一览补档（#/supplier-list），或用内部号到 ERP 联查。自制会清空供应商。</p>
                </label>
                <label class="space-y-1 block">
                    <span class="text-[10px] text-ink-dim">确认备注</span>
                    <textarea id="poConfirmRemark" rows="3" class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink focus:outline-none focus:border-brand-hud rounded resize-none"></textarea>
                </label>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex justify-end gap-2">
                <button type="button" id="poConfirmCancelBtn" class="inline-flex items-center bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] rounded">取消</button>
                <button type="button" id="poConfirmSaveBtn" class="inline-flex items-center bg-brand-hud text-ink-onbrand px-4 py-2 text-[11px] font-semibold rounded">保存确认</button>
            </div>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div id="poDetailDrawerBackdrop" class="hidden ${DRAWER_BACKDROP}"></div>
        <div id="poDetailDrawer" class="hidden fixed top-0 right-0 h-full w-[480px] max-w-full bg-app-main border-l border-line-hud z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-app-elevated flex items-center justify-between">
                <h3 class="text-sm font-semibold text-ink">采购对象详情</h3>
                <button type="button" id="poDetailCloseBtn" class="text-ink-muted hover:text-ink">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div id="poDetailBody" class="flex-1 overflow-y-auto p-6 text-[12px] text-ink-muted space-y-2 font-mono"></div>
        </div>
    `;
}

function consecutiveRowSpans(records, keyOf) {
    const spans = records.map(() => 1);
    let start = 0;
    while (start < records.length) {
        const key = keyOf(records[start]);
        if (!key) {
            start += 1;
            continue;
        }
        let end = start + 1;
        while (end < records.length && keyOf(records[end]) === key) end += 1;
        spans[start] = end - start;
        for (let index = start + 1; index < end; index += 1) spans[index] = 0;
        start = end;
    }
    return spans;
}

function excelTraceHtml(records, start, span) {
    const group = records.slice(start, start + span);
    const first = group[0];
    const filename = first.excel_filename || '—';
    const rowNumbers = group
        .map((item) => item.excel_row)
        .filter((value) => value != null);
    let rowLabel = '行 —';
    if (rowNumbers.length) {
        const lowest = Math.min(...rowNumbers);
        const highest = Math.max(...rowNumbers);
        rowLabel = lowest === highest ? `行 ${lowest}` : `行 ${lowest}–${highest}`;
    }
    return `
        <div class="text-[10px] text-ink-muted truncate" title="${esc(first.excel_filename || '')}">${esc(filename)}</div>
        <div class="text-[9px] text-ink-faint">${esc(rowLabel)}</div>`;
}

export function renderProcurementObjectRows(records) {
    if (!records || records.length === 0) {
        return `<tr><td colspan="14" class="py-10 text-center text-ink-muted text-[12px]">暂无数据</td></tr>`;
    }
    const kindLabel = KIND_LABELS;
    const sectionLabel = SECTION_LABELS;
    const confirmLabel = CONFIRM_LABELS;
    const excelSpans = consecutiveRowSpans(records, (row) => row.excel_filename || '');
    const l0Spans = consecutiveRowSpans(
        records,
        (row) => (row.l0_part_number ? `${row.l0_part_number}\0${row.l0_part_name || ''}` : ''),
    );
    const mergeCell = 'px-2 py-2 overflow-hidden align-middle border-r border-line-hud';
    return records.map((row, index) => {
        const confirmBtn = row.section === 'object'
            ? `<button type="button" data-action="confirm" data-id="${esc(row.id)}"
                    class="inline-flex items-center justify-center w-7 h-7 rounded-sm opacity-0 group-hover:opacity-100 focus:opacity-100 text-ink-faint hover:text-brand-hud hover:bg-app-rowhover"
                    title="确认" aria-label="确认">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>`
            : '';
        const excelSpan = excelSpans[index];
        const l0Span = l0Spans[index];
        const excelTd = excelSpan > 0
            ? `<td class="${mergeCell}" rowspan="${excelSpan}">${excelTraceHtml(records, index, excelSpan)}</td>`
            : '';
        const l0Td = l0Span > 0
            ? `<td class="${mergeCell}" rowspan="${l0Span}">${partShortCodeCellHtml(row.l0_part_number)}</td>
               <td class="${mergeCell}" rowspan="${l0Span}">${partNumberNameCellHtml(row.l0_part_number, row.l0_part_name)}</td>`
            : '';
        const periodTd = periodCellHtml(row);
        return `
        <tr class="group relative font-mono text-[11px] border-b border-line-subtle hover:bg-app-rowhover transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-brand-hud opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            ${excelTd}
            ${l0Td}
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                ${partShortCodeCellHtml(row.part_number)}
            </td>
            <td class="px-2 py-2 overflow-hidden">
                ${partNumberNameCellHtml(
                    row.part_number,
                    row.part_name,
                    row.internal_number
                        ? `<div class="text-[9px] text-ink-faint truncate" title="内部号（ERP）">${esc(row.internal_number)}</div>`
                        : '',
                )}
            </td>
            <td class="px-2 py-2 text-[10px] text-ink-muted">${esc(kindLabel[row.object_kind] || sectionLabel[row.section] || row.section)}</td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-ink-muted">
                <div class="truncate">${esc(row.material || '—')}</div>
                <div class="text-[9px] text-ink-faint">${esc(row.thickness_text || '')}</div>
            </td>
            <td class="px-2 py-2 text-[10px] text-ink-muted">${esc(confirmLabel[row.confirm_status] || row.confirm_status)}</td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-ink-muted">
                ${row.section === 'object'
                    ? (row.supplier_name
                        ? `<div class="truncate text-ink-muted" title="${esc(row.supplier_name)}">${esc(row.supplier_name)}</div>`
                        : `<span class="text-ink-faint">未指定</span>`)
                    : `<span class="text-ink-faint">—</span>`}
            </td>
            <td class="px-2 py-2 text-[10px] text-ink-muted">${esc(AUDIT_LABELS[row.audit_status] || row.audit_status)}</td>
            ${periodTd}
            <td class="px-2 py-2 text-[9px] text-ink-faint truncate">${esc(row.location)} · ${esc(row.vehicle_model)} · ${esc(row.bom_version)}</td>
            <td class="px-1 py-2 text-center sticky right-0 z-[2] brabus-bg-grid group-hover:bg-app-rowhover">
                ${confirmBtn}
                <button type="button" data-action="detail" data-id="${esc(row.id)}"
                        class="inline-flex items-center justify-center w-7 h-7 rounded-sm opacity-0 group-hover:opacity-100 focus:opacity-100 text-ink-faint hover:text-ink-muted hover:bg-app-rowhover"
                        title="详情" aria-label="详情">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>
            </td>
        </tr>`;
    }).join('');
}

function periodCellHtml(row) {
    const periodText = fmtPeriodRange(
        row.effective_year,
        row.effective_month,
        row.expiry_year,
        row.expiry_month,
    );
    const periodClass = hasClosedPeriod(
        row.effective_year,
        row.effective_month,
        row.expiry_year,
        row.expiry_month,
    )
        ? 'text-brand-hud'
        : 'text-ink-muted';
    return `<td class="px-2 py-2 text-[10px] whitespace-nowrap ${periodClass}">${esc(periodText)}</td>`;
}

