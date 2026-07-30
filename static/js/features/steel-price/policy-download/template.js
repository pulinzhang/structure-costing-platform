/**
 * Steel Price Policy Download Template
 * 钢价政策下载页面 — Brabus Carbon & Precision Dark
 * 用于测试部门核对数据，主子表联合查询导出 Excel
 */

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
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">钢价政策导出</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnExportPolicy"
                                class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-sm hover:bg-[#b71c1c] transition-all duration-150">
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
                        ${filterSelect('policyDownloadMill', '钢厂')}
                    </div>
                </div>

                <!-- 提示信息 -->
                <div class="px-5 py-3 border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#888888] leading-5">
                            <span class="text-[#9e9e9e] font-medium">说明：</span>
                            根据所选条件导出钢价政策主子表数据。政策主表（年度、月份、钢厂、大类、类型、牌号等）与阶梯明细表（厚度区间、宽度区间、加减价等）联合查询，结果用于测试部门核对数据。
                        </p>
                    </div>
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
                    <div class="text-[11px] text-[#616161] mb-3">
                        已选条件：
                        <span id="selectedConditions" class="text-[#9e9e9e] ml-2">请选择筛选条件</span>
                    </div>

                    <!-- 预览表格 -->
                    <div class="bg-[#1a1a1a] border border-[#2c2c2c] rounded overflow-hidden">
                        <div class="overflow-x-auto max-h-[400px]">
                            <table class="w-full min-w-[1600px]">
                                <thead>
                                    <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c] sticky top-0 z-10">
                                        <!-- 主表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">政策ID</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">年度</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">月份</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢种大类</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">政策类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">牌号类型</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">牌号/范围</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基准厚度</th>
                                        <!-- 子表字段 -->
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">明细ID</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">子分组</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度条件</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">宽度条件</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">加减价</th>
                                        <th class="px-3 py-2 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基准</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">排序</th>
                                    </tr>
                                </thead>
                                <tbody id="policyPreviewBody" class="divide-y divide-[#1d1d1d]">
                                    <tr>
                                        <td colspan="16" class="px-4 py-8 text-center text-[#616161] text-xs">
                                            请选择条件后点击"预览"查看数据
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- 操作按钮 -->
                    <div class="flex items-center justify-between mt-4">
                        <div class="text-[11px] text-[#616161]">
                            共 <span id="recordCount" class="text-[#9e9e9e] font-mono">0</span> 条记录
                        </div>
                        <div class="flex items-center gap-2">
                            <button id="btnPreview"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                预览
                            </button>
                        </div>
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

/**
 * 渲染预览数据行
 */
export function renderPolicyRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return `
            <tr>
                <td colspan="16" class="px-4 py-8 text-center text-[#616161] text-xs">
                    无数据
                </td>
            </tr>
        `;
    }
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1;
        // 格式化厚度条件
        const thickCond = formatThicknessCondition(record);
        // 格式化宽度条件
        const widthCond = formatWidthCondition(record);
        // 基准标记
        const baseMark = record.is_base === 1 ? '✓' : '';

        return `
        <tr class="group transition-colors duration-150 ${isEven ? 'bg-[rgba(255,255,255,0.012)]' : ''}">
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.policy_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.year || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.month || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.steel_mill || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.category_name || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(formatPolicyType(record.policy_type))}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.grade_type || '')}</td>
            <td class="px-3 py-2 text-[11px] font-medium text-[#b0b0b0] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.grade_value || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(formatDecimal(record.base_thickness))}</td>
            <!-- 明细 -->
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.item_id || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.target_sub_group || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${thickCond}</td>
            <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${widthCond}</td>
            <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#d32f2f] whitespace-nowrap border-b border-[#1d1d1d]">${esc(formatPriceAdjust(record.price_adjustment))}</td>
            <td class="px-3 py-2 text-[11px] text-center whitespace-nowrap border-b border-[#1d1d1d] ${record.is_base === 1 ? 'text-[#2e7d32]' : 'text-[#484848]'}">${baseMark}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.sort_order || '0')}</td>
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

function formatThicknessCondition(record) {
    const parts = [];
    if (record.thick_min !== null && record.thick_min !== undefined && record.thick_min_operator) {
        parts.push(`${record.thick_min_operator}${formatDecimal(record.thick_min)}`);
    }
    if (record.thick_max !== null && record.thick_max !== undefined && record.thick_max_operator) {
        parts.push(`${record.thick_max_operator}${formatDecimal(record.thick_max)}`);
    }
    return parts.join(', ') || '-';
}

function formatWidthCondition(record) {
    const parts = [];
    if (record.width_min !== null && record.width_min !== undefined && record.width_min_operator) {
        parts.push(`${record.width_min_operator}${formatDecimal(record.width_min)}`);
    }
    if (record.width_max !== null && record.width_max !== undefined && record.width_max_operator) {
        parts.push(`${record.width_max_operator}${formatDecimal(record.width_max)}`);
    }
    return parts.join(', ') || '-';
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

function formatPriceAdjust(value) {
    if (value === null || value === undefined) return '-';
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return '-';
    return numeric >= 0 ? `+${numeric}` : `${numeric}`;
}
