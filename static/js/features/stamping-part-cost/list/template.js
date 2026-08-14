/**
 * 冲压零件价格一览模板
 */

export function partCostListTemplate() {
    return `
        <div class="space-y-3 w-full font-sans antialiased text-[#bbb]">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between gap-3 flex-wrap">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('costYearFilter', '年度')}
                        ${filterSelect('costMonthFilter', '月份')}
                        ${filterSelect('costLocationFilter', '基地')}
                        ${filterSelect('costSupplierFilter', '冲压工厂')}
                        ${filterSelect('costAuditFilter', '审核状态')}
                        ${filterInput('costPartNumberFilter', '零件号')}
                        <button id="costSearchBtn" type="button"
                                class="h-8 px-3 text-[11px] bg-[#d32f2f] hover:bg-[#b71c1c] text-white rounded transition-colors">查询</button>
                        <button id="costResetBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:text-white hover:border-[#9e9e9e] transition-colors">重置</button>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <button id="costBatchApproveBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-colors">批量审核</button>
                        <button id="costBatchReverseBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-colors">批量反审核</button>
                        <button id="costBatchDeleteBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#ef5350] hover:text-[#ef5350] transition-colors">批量删除</button>
                        <button id="costExportBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-colors"
                                title="工艺清单格式：至R列公式 + 加工费 + 最终价">导出工艺清单</button>
                        <button id="costExportDetailBtn" type="button"
                                class="h-8 px-3 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-colors"
                                title="含溯源/审核字段的明细表">导出明细</button>
                    </div>
                </div>
                <div class="px-4 py-2 text-[10px] text-[#616161] border-b border-[#222222] flex items-center justify-between gap-3 flex-wrap">
                    <span>共 <span id="costTotalCount" class="text-[#9e9e9e] font-mono">0</span> 条 · 批量操作须选定年度、月份、基地、冲压工厂</span>
                    <span class="font-mono text-[10px] text-[#555555]"
                          title="ρ_steel=钢材密度；λ=材料损耗率；η=废料回收率；P/Q=元/kg">
                        R = M×P×(1+λ) − M×λ×η×Q − O×η×Q
                    </span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full min-w-[1800px]">
                        <thead>
                            <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                                <th class="px-3 py-2.5 text-left text-[10px] text-[#616161] uppercase tracking-wider">年月/基地</th>
                                <th class="px-3 py-2.5 text-left text-[10px] text-[#616161] uppercase tracking-wider">零件号</th>
                                <th class="px-3 py-2.5 text-left text-[10px] text-[#616161] uppercase tracking-wider">零件名</th>
                                <th class="px-3 py-2.5 text-left text-[10px] text-[#616161] uppercase tracking-wider">材质/料厚</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider" title="预估单件材料消耗(kg)">材料消耗kg</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider" title="废料重量=材料消耗−净重">废料kg</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider">利用率%</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider" title="钢材吨价；P=吨价/1000 元/kg">钢材吨价</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider" title="废料吨价；Q=吨价/1000 元/kg">废料吨价</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#ffffff]/70 uppercase tracking-wider bg-[#141414]" title="R = M×P×(1+λ) − M×λ×η×Q − O×η×Q">原材料成本 R</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider">加工费</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#ffffff]/70 uppercase tracking-wider bg-[#141414]">单件成本</th>
                                <th class="px-3 py-2.5 text-center text-[10px] text-[#616161] uppercase tracking-wider">状态</th>
                                <th class="px-3 py-2.5 text-center text-[10px] text-[#616161] uppercase tracking-wider">审核</th>
                                <th class="px-3 py-2.5 text-right text-[10px] text-[#616161] uppercase tracking-wider">操作</th>
                            </tr>
                        </thead>
                        <tbody id="costTableBody" class="divide-y divide-[#222222]">
                            <tr><td colspan="15" class="py-14 text-center text-[#616161]">加载中...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="flex items-center justify-between px-4 py-2 border-t border-[#222222]">
                    <span id="costPageInfo" class="text-[10px] text-[#616161]"></span>
                    <div id="costPagination" class="flex items-center gap-0.5"></div>
                </div>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <select id="${id}" class="w-28 h-8 pl-2.5 pr-7 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <input id="${id}" type="text" placeholder="零件号"
               class="w-36 h-8 px-2.5 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded">
    </label>`;
}

export function renderCostPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0]'}"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>‹</button>`;
    for (let i = 1; i <= totalPages && i <= 8; i++) {
        const active = i === currentPage;
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${active ? 'bg-[#d32f2f] text-white' : 'text-[#585858] hover:text-[#c0c0c0]'}" data-page="${i}">${i}</button>`;
    }
    buttons += `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>›</button>`;
    return buttons;
}
