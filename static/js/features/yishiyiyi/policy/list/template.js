/**
 * Steel Price Policy Download Template
 * 钢价政策下载页面 — Brabus Carbon & Precision Dark
 * 用于测试部门核对数据，主子表联合查询导出 Excel
 */

import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    pageSizeSelectHtml,
} from '../../../../page-size.js?v=2';

export function policyDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <!-- 页面主面板 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <!-- 面板头部：标题 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">加减价政策导出</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnDeletePolicy"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#c62828]/15 hover:border-[#c62828]/60 hover:text-[#d45858] hover:shadow-[0_0_8px_rgba(198,40,40,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('trash', 'w-3 h-3')}
                            删除
                        </button>
                        <button id="btnExportPolicy"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#d32f2f]/10 hover:border-[#d32f2f]/60 hover:text-[#d32f2f] hover:shadow-[0_0_8px_rgba(211,47,47,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出 Excel
                        </button>
                    </div>
                </div>

                <!-- 筛选工具栏 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('policyDownloadYear', '年度')}
                        ${filterSelect('policyDownloadMonth', '月份')}
                        ${filterSelect('policyDownloadCategory', '分类')}
                        ${filterInputWithDatalist('policyDownloadGrade', '牌号', 'policyGradeOptions')}
                        ${filterInputWithDatalist('policyDownloadMill', '钢厂', 'steelMillOptions')}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreview"
                                class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <!-- 提示信息 -->
                <div class="px-5 py-3 border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#888888] leading-5">
                            <span class="text-[#9e9e9e] font-medium">说明：</span>
                            根据所选条件导出钢价政策主子表数据。政策主表（年度、月份、钢厂、大类、类型、牌号等）与阶梯明细表（厚度区间、宽度区间、加减价等）联合查询，结果用于测试部门核对数据。删除时须选择年度与月份，钢厂可选（不选则删除该年月全部钢厂数据）。
                        </p>
                    </div>
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
                    <!-- 已选条件：嵌入式仪表盘风格 -->
                    <div class="mb-3 px-3 py-2 rounded-sm relative"
                         style="background: linear-gradient(180deg, #0f0f0f 0%, #0c0c0c 100%); border: 1px solid #1a1a1a; box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);">
                        <!-- 顶部高光线 -->
                        <div class="absolute top-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #2a2a2a 50%, transparent 100%);"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-[#484848]">已选条件：</span>
                            <span id="selectedConditions" class="text-[#888888] ml-2 font-medium tracking-wide">请选择筛选条件</span>
                        </div>
                        <!-- 底部暗线 -->
                        <div class="absolute bottom-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #151515 50%, transparent 100%);"></div>
                    </div>

                    <!-- 预览表格 -->
                    <div class="bg-[#141414] border border-[#222222] rounded-sm overflow-hidden"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 2px 8px rgba(0,0,0,0.3);">
                        <div class="overflow-x-auto max-h-[400px]">
                            <table class="w-full min-w-[1600px]">
                                <thead>
                                    <tr class="border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #0c0c0c 0%, #0a0a0a 100%);">
                                        <!-- 主表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">政策ID</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">年度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">月份</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">钢种大类</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">政策类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">牌号类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">牌号/范围</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">基准厚度</th>
                                        <!-- 子表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">明细ID</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">子分组</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">厚度条件</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">宽度条件</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">锌层条件</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">加减价</th>
                                        <th class="px-3 py-2 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">基准</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">排序</th>
                                        <!-- 追溯字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">文件名</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">行号</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">列号</th>
                                    </tr>
                                </thead>
                                <tbody id="policyPreviewBody" class="divide-y divide-[#1a1a1a]">
                                    <tr>
                                        <td colspan="20" class="px-4 py-8 text-center text-[#616161] text-xs">
                                            请选择条件后点击"查询"查看数据
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- 分页 -->
                    <div class="flex items-center justify-between mt-4 gap-3">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="text-[11px] text-[#616161]">
                                共 <span id="recordCount" class="text-[#9e9e9e] font-mono">0</span> 条记录
                            </div>
                            ${pageSizeSelectHtml('policyPageSize', DEFAULT_PREVIEW_PAGE_SIZE, PREVIEW_PAGE_SIZE_OPTIONS)}
                        </div>
                        <div class="flex items-center gap-0.5" id="policyPagination"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 加载遮罩 -->
        <div id="downloadLoading" class="hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] rounded p-6 flex flex-col items-center gap-3"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.8);">
                <div class="w-6 h-6 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                <span class="text-[11px] text-[#9e9e9e]">正在生成 Excel...</span>
            </div>
        </div>
    `;
}

// ===== 辅助函数 =====

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <select id="${id}" class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="h-7 w-32 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#ffffff] placeholder:text-[#616161] rounded-sm focus:outline-none focus:border-[#ff5252]">
    </label>`;
}

/**
 * 带输入搜索的下拉选择器（使用 datalist 实现）
 * @param {string} id - 输入框 ID
 * @param {string} label - 标签文本
 * @param {string} datalistId - datalist 的 ID
 */
function filterInputWithDatalist(id, label, datalistId) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <input type="text" id="${id}" list="${datalistId}" disabled
               class="w-44 h-7 pl-2.5 pr-3 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] placeholder:text-[#505050] focus:outline-none focus:border-[#ff5252] focus:text-[#d0d0d0] transition-all rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
               placeholder="请先选择分类">
        <datalist id="${datalistId}"></datalist>
    </label>`;
}

/**
 * 渲染预览数据行
 */
export function renderPolicyRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return `
            <tr>
                                        <td colspan="20" class="px-4 py-8 text-center text-[#616161] text-xs">
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
        <tr class="group border-b border-[#181818] transition-colors duration-150 hover:bg-[#ffffff]/[0.015]">
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.policy_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.year || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.month || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.steel_mill || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.category_name || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(formatPolicyType(record.policy_type))}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.grade_type || '')}</td>
            <td class="px-3 py-2 text-[11px] font-medium text-[#a0a0a0] whitespace-nowrap">${esc(record.grade_value || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono text-right tabular-nums">${esc(formatDecimal(record.base_thickness))}</td>
            
            <!-- 明细 -->
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.item_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.target_sub_group || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap font-mono">${thickCond}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap font-mono">${widthCond}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap font-mono">${zincCond}</td>
            <td class="px-3 py-2 text-right font-mono tabular-nums whitespace-nowrap ${getPriceAdjustClass(record.price_adjustment)}">${esc(formatPriceAdjust(record.price_adjustment))}</td>
            <td class="px-3 py-2 text-[11px] text-center whitespace-nowrap text-[#484848]">${baseMark}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.sort_order || '0')}</td>
            <!-- 追溯字段 -->
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.excel_filename || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_row ?? '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_col ?? '')}</td>
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
        return 'text-[#444444]';
    }
    if (numeric > 0) return 'text-[#E0E0E0]';
    return 'text-[#C62828]';
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
