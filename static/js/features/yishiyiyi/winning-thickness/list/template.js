/**
 * 中标钢厂厚度价格列表 — 页面模板
 * 必填基地/年/月；中标基价叠厚度加减价后外发
 */

import { filterSelect, filterInputWithDatalist, HUD_LED, BTN_GHOST, BTN_FILTER_SEARCH, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    paginationBarHtml,
} from '../../../../ui/page-size.js?v=6';

export function winningThicknessDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-app-surface border border-line overflow-hidden w-full max-w-full">

                <div class="flex items-center justify-between px-5 py-3.5 border-b border-line-subtle">
                    <div class="flex items-center gap-3">
                        <div class="${HUD_LED}"></div>
                        <h2 class="text-[12px] font-semibold text-ink-muted tracking-wide">中标钢厂厚度价格列表</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnExportWinningThickness"
                                class="${BTN_GHOST}">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            Excel
                        </button>
                    </div>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-b border-app-surface">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('winningThicknessYear', '年度', false)}
                        ${filterSelect('winningThicknessMonth', '月份', false)}
                        ${filterSelect('winningThicknessLocation', '基地', false)}
                        ${filterSelect('winningThicknessMill', '钢厂', false)}
                        ${filterSelect('winningThicknessCategory', '分类', false)}
                        ${filterInputWithDatalist('winningThicknessGrade', '牌号', 'winningThicknessGradeOptions', { disabled: true, placeholder: '请先选择分类' })}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreviewWinningThickness"
                                class="${BTN_FILTER_SEARCH} h-7">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="bg-app-deep border border-line-subtle rounded p-3">
                        <p class="text-[11px] text-ink-muted leading-5">
                            <span class="text-ink-muted font-medium">说明：</span>
                            打开默认当年；年度、月份、基地等为可选筛（一事一议按月定价）。
                            以中标基价为据，按档案大类匹配 CATEGORY 厚度政策；
                            每个牌号展开全部厚度阶梯（一行一区间），最终价 = 基准价 + 厚度加减价 + 加工费。导出须选定年度和月份。
                        </p>
                    </div>
                </div>

                <div class="p-5">
                    <div class="mb-3 px-3 py-2 rounded-sm relative">
                        <div class="absolute top-0 left-0 right-0 h-px"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-ink-faint">已选条件：</span>
                            <span id="selectedWinningThicknessConditions" class="text-ink-muted ml-2 font-medium tracking-wide">全部</span>
                        </div>
                        <div class="absolute bottom-0 left-0 right-0 h-px"></div>
                    </div>

                    <div class="bg-app-main border border-line-subtle rounded-sm overflow-hidden">
                        <div class="overflow-x-auto max-h-[400px] brabus-bg-grid">
                            <table class="w-full min-w-[1400px]">
                                <thead>
                                    <tr class="border-b border-app-surface">
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基地/钢种</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">牌号</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">厚度范围</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基准价</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">加减价</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">加工费</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">最终价</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基价溯源</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">厚度溯源</th>
                                    </tr>
                                </thead>
                                <tbody id="winningThicknessPreviewBody" class="divide-y divide-line-subtle">
                                    <tr>
                                        <td colspan="10" class="px-4 py-8 text-center text-ink-dim text-xs">
                                            当前筛选下暂无数据；打开默认当年，筛选项只作收窄
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    ${paginationBarHtml({
                        infoHtml: `<div class="text-[11px] text-ink-dim">
                            共 <span id="winningThicknessRecordCount" class="text-ink-muted font-mono">0</span> 条阶梯行
                            <span class="text-ink-faint ml-2">（同牌号多行 = 各厚度区间）</span>
                        </div>`,
                        selectId: 'winningThicknessPageSize',
                        buttonsId: 'winningThicknessPagination',
                        currentSize: DEFAULT_PREVIEW_PAGE_SIZE,
                        options: PREVIEW_PAGE_SIZE_OPTIONS,
                        wrapperClass: 'flex items-center justify-between mt-4',
                    })}
                </div>
            </div>
        </div>

        <div id="winningThicknessDownloadLoading" class="hidden ${DRAWER_BACKDROP} flex items-center justify-center">
            <div class="bg-app-surface border border-line rounded p-6 flex flex-col items-center gap-3">
                <div class="w-6 h-6 border-2 border-line border-brand rounded-full animate-spin"></div>
                <span class="text-[11px] text-ink-muted">正在生成 Excel...</span>
            </div>
        </div>
    `;
}



/**
 * 渲染预览行（同牌号+钢厂+基价合并单元格，逐行展示厚度阶梯）
 */
export function renderWinningThicknessRows(records) {
    if (!records || !records.length) {
        return `
            <tr>
                <td colspan="10" class="px-4 py-8 text-center text-ink-dim text-xs">暂无数据</td>
            </tr>
        `;
    }

    const groups = groupLadderRecords(records);
    const numCell = 'px-3 py-2 text-[11px] text-right font-mono tabular-nums';
    const dimCell = 'px-3 py-2 text-[11px] text-ink-muted align-top';
    const traceCell = 'px-3 py-2 text-[9px] text-ink-faint max-w-[180px] truncate align-top';
    const sharedBorder = 'border-r border-line-subtle/60';

    return groups.map((group) => {
        const first = group[0];
        const locationCategory = [first.location, first.category_name]
            .filter(Boolean)
            .join(' · ');
        const baseTrace = formatBaseTrace(first);
        const rowspan = group.length;

        return group.map((record, index) => {
            const thickTrace = formatThicknessTrace(record);
            const isFirst = index === 0;
            const groupBorder = isFirst ? 'border-t border-line-subtle' : 'border-t border-line-subtle/40';

            const sharedPrefix = isFirst ? `
                <td class="px-3 py-2 text-[9px] text-ink-faint whitespace-nowrap ${sharedBorder}" rowspan="${rowspan}">${esc(locationCategory) || '—'}</td>
                <td class="${dimCell} ${sharedBorder}" rowspan="${rowspan}">${esc(first.grade)}</td>
                <td class="${dimCell} ${sharedBorder}" rowspan="${rowspan}">${esc(first.steel_mill)}</td>
            ` : '';

            const ladderCells = `
                <td class="px-3 py-2 text-[11px] text-ink-muted font-mono whitespace-nowrap">${esc(record.thickness_range)}</td>
            `;

            const sharedBasePrice = isFirst ? `
                <td class="${numCell} text-ink ${sharedBorder}" rowspan="${rowspan}">${fmtNum(first.base_price, 2)}</td>
            ` : '';

            const adjustmentCell = `
                <td class="${numCell} text-warn">${fmtNum(record.thickness_adjustment, 2)}</td>
            `;

            const sharedProcessing = isFirst ? `
                <td class="${numCell} text-ink-muted ${sharedBorder}" rowspan="${rowspan}">${fmtNum(first.processing_fee, 2)}</td>
            ` : '';

            const tailCells = `
                <td class="px-3 py-2 text-[12px] text-right font-mono tabular-nums font-semibold text-ink">${fmtNum(record.final_price, 2)}</td>
                ${isFirst ? `<td class="${traceCell} ${sharedBorder}" rowspan="${rowspan}" title="${esc(baseTrace)}">${esc(baseTrace) || '—'}</td>` : ''}
                <td class="${traceCell}" title="${esc(thickTrace)}">${esc(thickTrace) || '—'}</td>
            `;

            if (isFirst) {
                return `
                    <tr class="hover:bg-ink/[0.02] transition-colors ${groupBorder}">
                        ${sharedPrefix}
                        ${ladderCells}
                        ${sharedBasePrice}
                        ${adjustmentCell}
                        ${sharedProcessing}
                        ${tailCells}
                    </tr>
                `;
            }

            return `
                <tr class="hover:bg-ink/[0.02] transition-colors ${groupBorder}">
                    ${ladderCells}
                    ${adjustmentCell}
                    ${tailCells}
                </tr>
            `;
        }).join('');
    }).join('');
}

function groupLadderRecords(records) {
    const groups = [];
    let current = null;
    let currentKey = '';

    for (const record of records) {
        const key = [
            record.location || '',
            record.category_name || '',
            record.grade || '',
            record.steel_mill || '',
            record.base_price_id ?? '',
        ].join('|');
        if (!current || currentKey !== key) {
            current = [record];
            groups.push(current);
            currentKey = key;
        } else {
            current.push(record);
        }
    }
    return groups;
}

function formatBaseTrace(record) {
    return [
        record.base_price_id != null ? `ID:${record.base_price_id}` : '',
        record.base_excel_filename || '',
        record.base_sheet_name || '',
        record.base_excel_row != null ? `R${record.base_excel_row}` : '',
        record.base_excel_col != null ? `C${record.base_excel_col}` : '',
    ].filter(Boolean).join(' · ');
}

function formatThicknessTrace(record) {
    return [
        record.thickness_policy_id != null ? `P:${record.thickness_policy_id}` : '',
        record.thickness_ladder_item_id != null ? `L:${record.thickness_ladder_item_id}` : '',
        record.thickness_excel_filename || '',
        record.thickness_excel_row != null ? `R${record.thickness_excel_row}` : '',
        record.thickness_excel_col != null ? `C${record.thickness_excel_col}` : '',
    ].filter(Boolean).join(' · ');
}
