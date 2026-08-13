/**
 * 中标厚度价格导出页面模板
 * 必填：基地、年、月；输出基准价+厚度加减价一览（外发）
 */

export function winningThicknessDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">中标厚度价格导出</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnExportWinningThickness"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#d32f2f]/10 hover:border-[#d32f2f]/60 hover:text-[#d32f2f] hover:shadow-[0_0_8px_rgba(211,47,47,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出 Excel
                        </button>
                    </div>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('winningThicknessYear', '年度', true)}
                        ${filterSelect('winningThicknessMonth', '月份', true)}
                        ${filterSelect('winningThicknessLocation', '基地', true)}
                        ${filterSelect('winningThicknessCategory', '钢种', false)}
                        ${filterInput('winningThicknessGrade', '牌号', '输入牌号（模糊）')}
                        ${filterSelect('winningThicknessMill', '钢厂', false)}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreviewWinningThickness"
                                class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            预览
                        </button>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#888888] leading-5">
                            <span class="text-[#9e9e9e] font-medium">说明：</span>
                            必选基地、年度、月份。按该期中标钢材（基准价）匹配厚度加减价政策，展开全部厚度区间，
                            最终价 = 基准价 + 加减价 + 加工费。钢厂匹配规则与钢材联动计算一致。导出表供外发；溯源信息以小字弱化列展示。
                        </p>
                    </div>
                </div>

                <div class="p-5">
                    <div class="mb-3 px-3 py-2 rounded-sm relative"
                         style="background: linear-gradient(180deg, #0f0f0f 0%, #0c0c0c 100%); border: 1px solid #1a1a1a; box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);">
                        <div class="absolute top-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #2a2a2a 50%, transparent 100%);"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-[#484848]">已选条件：</span>
                            <span id="selectedWinningThicknessConditions" class="text-[#888888] ml-2 font-medium tracking-wide">请选择基地、年度、月份</span>
                        </div>
                        <div class="absolute bottom-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #151515 50%, transparent 100%);"></div>
                    </div>

                    <div class="bg-[#141414] border border-[#222222] rounded-sm overflow-hidden"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 2px 8px rgba(0,0,0,0.3);">
                        <div class="overflow-x-auto max-h-[400px]">
                            <table class="w-full min-w-[1400px]">
                                <thead>
                                    <tr class="border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #0c0c0c 0%, #0a0a0a 100%);">
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.12em] text-[#2a2a2a] whitespace-nowrap">基地/钢种</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">牌号</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">厚度范围</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">基准价</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">加减价</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">加工费</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">最终价</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.12em] text-[#2a2a2a] whitespace-nowrap">基价溯源</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.12em] text-[#2a2a2a] whitespace-nowrap">厚度溯源</th>
                                    </tr>
                                </thead>
                                <tbody id="winningThicknessPreviewBody" class="divide-y divide-[#1a1a1a]">
                                    <tr>
                                        <td colspan="10" class="px-4 py-8 text-center text-[#616161] text-xs">
                                            请选择基地、年度、月份后点击「预览」
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class="flex items-center justify-between mt-4">
                        <div class="text-[11px] text-[#616161]">
                            共 <span id="winningThicknessRecordCount" class="text-[#9e9e9e] font-mono">0</span> 条记录
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="winningThicknessDownloadLoading" class="hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] rounded p-6 flex flex-col items-center gap-3"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.8);">
                <div class="w-6 h-6 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                <span class="text-[11px] text-[#9e9e9e]">正在生成 Excel...</span>
            </div>
        </div>
    `;
}

function filterSelect(id, label, required) {
    const mark = required
        ? '<span class="text-[#d32f2f] ml-0.5">*</span>'
        : '';
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}${mark}</span>
        <select id="${id}" class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
            <option value="">${required ? '请选择' : '全部'}</option>
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
 * 渲染预览行
 */
export function renderWinningThicknessRows(records) {
    if (!records || !records.length) {
        return `
            <tr>
                <td colspan="10" class="px-4 py-8 text-center text-[#616161] text-xs">暂无数据</td>
            </tr>
        `;
    }

    return records.map(record => {
        const locationCategory = [record.location, record.category_name]
            .filter(Boolean)
            .join(' · ');

        const baseTrace = [
            record.base_price_id != null ? `ID:${esc(record.base_price_id)}` : '',
            record.base_excel_filename || '',
            record.base_sheet_name || '',
            record.base_excel_row != null ? `R${esc(record.base_excel_row)}` : '',
            record.base_excel_col != null ? `C${esc(record.base_excel_col)}` : '',
        ].filter(Boolean).join(' · ');

        const thickTrace = [
            record.thickness_policy_id != null ? `P:${esc(record.thickness_policy_id)}` : '',
            record.thickness_ladder_item_id != null ? `L:${esc(record.thickness_ladder_item_id)}` : '',
            record.thickness_excel_filename || '',
            record.thickness_excel_row != null ? `R${esc(record.thickness_excel_row)}` : '',
            record.thickness_excel_col != null ? `C${esc(record.thickness_excel_col)}` : '',
        ].filter(Boolean).join(' · ');

        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors">
                <td class="px-3 py-2 text-[9px] text-[#3a3a3a] whitespace-nowrap">${esc(locationCategory) || '—'}</td>
                <td class="px-3 py-2 text-[11px] text-[#9e9e9e]">${esc(record.grade)}</td>
                <td class="px-3 py-2 text-[11px] text-[#9e9e9e]">${esc(record.steel_mill)}</td>
                <td class="px-3 py-2 text-[11px] text-[#c8c8c8] font-mono whitespace-nowrap">${esc(record.thickness_range)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#ffffff]">${fmtNum(record.base_price, 2)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${fmtNum(record.thickness_adjustment, 2)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${fmtNum(record.processing_fee, 2)}</td>
                <td class="px-3 py-2 text-[12px] text-right font-mono tabular-nums font-semibold text-[#ffffff]">${fmtNum(record.final_price, 2)}</td>
                <td class="px-3 py-2 text-[9px] text-[#3a3a3a] max-w-[180px] truncate" title="${esc(baseTrace)}">${esc(baseTrace) || '—'}</td>
                <td class="px-3 py-2 text-[9px] text-[#3a3a3a] max-w-[180px] truncate" title="${esc(thickTrace)}">${esc(thickTrace) || '—'}</td>
            </tr>
        `;
    }).join('');
}
