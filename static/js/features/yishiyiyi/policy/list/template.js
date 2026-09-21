/**
 * Steel Price Policy Download Template
 * 钢价政策下载页面 — Brabus Carbon & Precision Dark
 * 用于测试部门核对数据，主子表联合查询Excel
 */

import { filterSelect, filterInputWithDatalist, HUD_LED, BTN_GHOST, BTN_FILTER_SEARCH, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=12';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    paginationBarHtml,
} from '../../../../ui/page-size.js?v=6';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';

export function policyDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <!-- 页面主面板 -->
            <div class="bg-app-surface border border-line overflow-hidden w-full max-w-full">

                <!-- 面板头部：标题 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-line-subtle">
                    <div class="flex items-center gap-3">
                        <div class="${HUD_LED}"></div>
                        <h2 class="text-[12px] font-semibold text-ink-muted tracking-wide">加减价政策列表</h2>
                    </div>
                    <div class="flex items-center gap-1.5">
                        ${moreMenuShellHtml({
                            wrapId: 'policyMoreWrap',
                            btnId: 'policyMoreBtn',
                            menuId: 'policyMoreMenu',
                            itemsHtml: moreMenuItemHtml({ id: 'btnDeletePolicy', label: '删除', danger: true }),
                        })}
                        <button id="btnExportPolicy"
                                class="${BTN_GHOST}">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            Excel
                        </button>
                    </div>
                </div>

                <!-- 筛选工具栏 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-app-surface">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('policyDownloadYear', '年度')}
                        ${filterSelect('policyDownloadMonth', '月份')}
                        ${filterInputWithDatalist('policyDownloadMill', '钢厂', 'policyMillOptions', {
                            placeholder: '输入搜索或选择钢厂',
                        })}
                        ${filterSelect('policyDownloadCategory', '钢种大类')}
                        ${filterInputWithDatalist('policyDownloadGrade', '牌号', 'policyGradeOptions', {
                            placeholder: '请先选择钢种大类',
                            disabled: true,
                        })}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreview"
                                class="${BTN_FILTER_SEARCH}">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <!-- 提示信息 -->
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="bg-app-deep border border-line-subtle rounded p-3">
                        <p class="text-[11px] text-ink-muted leading-5">
                            <span class="text-ink-muted font-medium">说明：</span>
                            打开默认当年；年度、月份、钢厂、钢种大类、牌号为可选筛（一事一议按月定价）。导出须选定年度和月份。删除须选择年度与月份，钢厂可选（不选则删除该年月全部钢厂数据）。
                        </p>
                    </div>
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
                    <!-- 已选条件：嵌入式仪表盘风格 -->
                    <div class="mb-3 px-3 py-2 rounded-sm relative">
                        <!-- 顶部高光线 -->
                        <div class="absolute top-0 left-0 right-0 h-px"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-ink-faint">已选条件：</span>
                            <span id="selectedConditions" class="text-ink-muted ml-2 font-medium tracking-wide">全部</span>
                        </div>
                        <!-- 底部暗线 -->
                        <div class="absolute bottom-0 left-0 right-0 h-px"></div>
                    </div>

                    <!-- 预览表格 -->
                    <div class="bg-app-main border border-line-subtle rounded-sm overflow-hidden">
                        <div class="overflow-x-auto max-h-[400px] brabus-bg-grid">
                            <table class="w-full min-w-[1600px]">
                                <thead>
                                    <tr class="border-b border-app-surface">
                                        <!-- 主表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">政策ID</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">年度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">月份</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢种大类</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">政策类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">牌号类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">牌号/范围</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基准厚度</th>
                                        <!-- 子表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">明细ID</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">子分组</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">厚度条件</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">宽度条件</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">锌层条件</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">加减价</th>
                                        <th class="px-3 py-2 text-center text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基准</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">排序</th>
                                        <!-- 追溯字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">文件名</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">行号</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">列号</th>
                                    </tr>
                                </thead>
                                <tbody id="policyPreviewBody" class="divide-y divide-line-subtle">
                                    <tr>
                                        <td colspan="20" class="px-4 py-8 text-center text-ink-dim text-xs">
                                            当前筛选下暂无数据；打开默认当年，筛选项只作收窄
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- 分页 -->
                    ${paginationBarHtml({ infoHtml: `<div class="text-[11px] text-ink-dim">共 <span id="recordCount" class="text-ink-muted font-mono">0</span> 条记录</div>`, selectId: 'policyPageSize', buttonsId: 'policyPagination', currentSize: DEFAULT_PREVIEW_PAGE_SIZE, options: PREVIEW_PAGE_SIZE_OPTIONS, wrapperClass: 'flex items-center justify-between mt-4 gap-3' })}
                </div>
            </div>
        </div>

        <!-- 加载遮罩 -->
        <div id="downloadLoading" class="hidden ${DRAWER_BACKDROP} flex items-center justify-center">
            <div class="bg-app-surface border border-line rounded p-6 flex flex-col items-center gap-3">
                <div class="w-6 h-6 border-2 border-line border-brand rounded-full animate-spin"></div>
                <span class="text-[11px] text-ink-muted">正在生成 Excel...</span>
            </div>
        </div>
    `;
}

// ===== 辅助函数 =====


/**
 * 渲染预览数据行
 */
export function renderPolicyRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return `
            <tr>
                                        <td colspan="20" class="px-4 py-8 text-center text-ink-dim text-xs">
                                            无数据
                                        </td>
                                    </tr>
                                `;
    }
    return records.map((record) => {
        // 格式化厚度条件
        const thickCond = formatThicknessCondition(record);
        // 格式化宽度条件
        const widthCond = formatWidthCondition(record);
        // 格式化锌层克重条件
        const zincCond = formatZincCoatingCondition(record);
        // 基准标记
        const baseMark = record.is_base === 1 ? '✓' : '';

        return `
        <tr class="group border-b border-line-subtle transition-colors duration-150 hover:bg-ink/[0.015]">
            <td class="px-3 py-2 text-[11px] text-ink-faint whitespace-nowrap font-mono text-right tabular-nums">${esc(record.policy_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-dim whitespace-nowrap font-mono text-right tabular-nums">${esc(fmtYear(record.year))}</td>
            <td class="px-3 py-2 text-[11px] text-ink-dim whitespace-nowrap font-mono text-right tabular-nums">${esc(fmtMonth(record.month))}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(record.steel_mill || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(record.category_name || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(formatPolicyType(record.policy_type))}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(record.grade_type || '')}</td>
            <td class="px-3 py-2 text-[11px] font-medium text-ink-muted whitespace-nowrap">${esc(record.grade_value || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap font-mono text-right tabular-nums">${esc(formatDecimal(record.base_thickness))}</td>
            
            <!-- 明细 -->
            <td class="px-3 py-2 text-[11px] text-ink-faint whitespace-nowrap font-mono text-right tabular-nums">${esc(record.item_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(record.target_sub_group || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap font-mono">${thickCond}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap font-mono">${widthCond}</td>
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap font-mono">${zincCond}</td>
            <td class="px-3 py-2 text-right font-mono tabular-nums whitespace-nowrap ${getPriceAdjustClass(record.price_adjustment)}">${esc(formatPriceAdjust(record.price_adjustment))}</td>
            <td class="px-3 py-2 text-[11px] text-center whitespace-nowrap text-ink-faint">${baseMark}</td>
            <td class="px-3 py-2 text-[11px] text-ink-dim whitespace-nowrap font-mono text-right tabular-nums">${esc(record.sort_order || '0')}</td>
            <!-- 追溯字段 -->
            <td class="px-3 py-2 text-[11px] text-ink-muted whitespace-nowrap">${esc(record.excel_filename || '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-dim whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_row ?? '')}</td>
            <td class="px-3 py-2 text-[11px] text-ink-dim whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_col ?? '')}</td>
        </tr>`;
    }).join('');
}

function formatPolicyType(type) {
    const map = {
        'THICKNESS': '厚度加减价',
        'WIDTH': '宽度加价',
    };
    return map[type] || type || '';
}

/**
 * 通用区间格式化函数（数学区间写法，如 2.0 ≤ t ≤ 5.0）
 * @param {string} variable - 变量名
 * @param {number|null} minVal - 最小值
 * @param {string|null} minOp - 最小值运算符（'>=' 或 '>'）
 * @param {number|null} maxVal - 最大值
 * @param {string|null} maxOp - 最大值运算符（'<=' 或 '<'）
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的条件字符串
 */
function formatInterval(variable, minVal, minOp, maxVal, maxOp, decimals) {
    const fmt = (v) => {
        if (v === null || v === undefined) return '';
        const num = Number(v);
        return Number.isNaN(num) ? '' : num.toFixed(decimals);
    };

    const minSymbol = (op) => {
        if (op === '>=') return '≤';
        if (op === '>') return '<';
        return '';
    };
    const maxSymbol = (op) => {
        if (op === '<=') return '≤';
        if (op === '<') return '<';
        return '';
    };

    const hasMin = minVal != null && minOp;
    const hasMax = maxVal != null && maxOp;

    // 两者都有：2.0 ≤ t ≤ 5.0
    if (hasMin && hasMax) {
        return `${fmt(minVal)} ${minSymbol(minOp)} ${variable} ${maxSymbol(maxOp)} ${fmt(maxVal)}`;
    }

    // 只有下限：2.0 ≤ t
    if (hasMin) {
        return `${fmt(minVal)} ${minSymbol(minOp)} ${variable}`;
    }

    // 只有上限：t ≤ 5.0
    if (hasMax) {
        return `${variable} ${maxSymbol(maxOp)} ${fmt(maxVal)}`;
    }

    return '-';
}

function formatThicknessCondition(record) {
    return formatInterval(
        't',
        record.thick_min,
        record.thick_min_operator,
        record.thick_max,
        record.thick_max_operator,
        2
    );
}

function formatWidthCondition(record) {
    return formatInterval(
        'w',
        record.width_min,
        record.width_min_operator,
        record.width_max,
        record.width_max_operator,
        0
    );
}

function formatZincCoatingCondition(record) {
    return formatInterval(
        'z',
        record.zinc_coating_min,
        record.zinc_coating_min_operator,
        record.zinc_coating_max,
        record.zinc_coating_max_operator,
        0
    );
}

function formatDecimal(value, digits = 2) {
    if (value === null || value === undefined) return '';
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return '';
    return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

/**
 * 加减价色（BRABUS 极客风）：加→冷钛白，减→暗红，无变动→低饱和灰
 */
function getPriceAdjustClass(value) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric) || numeric === 0) {
        return 'text-ink-dim';
    }
    if (numeric > 0) return 'text-ink';
    return 'text-danger';
}

/**
 * 加减价显示：>0 → +160.00；<0 → -40.00；0/空 → --
 */
function formatPriceAdjust(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric) || numeric === 0) {
        return '--';
    }
    const absText = Math.abs(numeric).toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
    return numeric > 0 ? `+${absText}` : `-${absText}`;
}
