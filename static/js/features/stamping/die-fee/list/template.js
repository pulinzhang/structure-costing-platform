import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function dieFeeListTemplate() {
    return `
        <div class="space-y-3 w-full font-sans antialiased">
            <div class="flex items-end justify-between gap-3 flex-wrap pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">冲压模具费列表</h1>
                <div class="flex items-end gap-2 flex-wrap">
                    <label class="space-y-1">
                        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.12em]">年度</span>
                        <input id="dieFeeYear" type="number" min="2000" max="2100"
                               class="w-24 h-8 px-2 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] focus:outline-none focus:border-[#ff5252]">
                    </label>
                    <label class="space-y-1">
                        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.12em]">基地</span>
                        <select id="dieFeeLocation" class="h-8 px-2 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="">请选择</option>
                        </select>
                    </label>
                    <label class="space-y-1">
                        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.12em]">项目</span>
                        <select id="dieFeeVehicle" class="h-8 px-2 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="">请选择</option>
                        </select>
                    </label>
                    <input id="dieFeePartNumber" placeholder="零件号" class="h-8 px-2 w-36 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    <select id="dieFeeAuditStatus" class="h-8 px-2 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                        <option value="">全部状态</option>
                        <option value="pending">待审</option>
                        <option value="approved">已审核</option>
                        <option value="rejected">已驳回</option>
                    </select>
                    <button type="button" id="dieFeeOnlyZeroBtn" class="h-8 px-3 text-[10px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white">最终为 0</button>
                    <button type="button" id="dieFeeSearchBtn" class="h-8 px-3 text-[10px] bg-[#d32f2f] text-white hover:bg-[#b71c1c]">查询</button>
                    <button type="button" id="dieFeeExportBtn" class="h-8 px-3 text-[10px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white">导出</button>
                    <button type="button" id="dieFeeApproveBtn" class="h-8 px-3 text-[10px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white">审核</button>
                    <button type="button" id="dieFeeReverseBtn" class="h-8 px-3 text-[10px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white">反审核</button>
                    <button type="button" id="dieFeeDeleteScopeBtn" class="h-8 px-3 text-[10px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-[#ef5350]">删未审核</button>
                </div>
            </div>
            <div id="dieFeeHud" class="text-[10px] font-mono text-[#555555]"></div>
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="overflow-x-auto bg-[#0A0A0E]">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1100px;">
                        <colgroup>
                            <col style="width: 8px">
                            <col style="width: 140px">
                            <col style="width: 140px">
                            <col style="width: 90px">
                            <col style="width: 110px">
                            <col style="width: 110px">
                            <col style="width: 120px">
                            <col style="width: 80px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">生产方式</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">系统模具费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">调整金额</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">最终模具费</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="dieFeeTbody"></tbody>
                    </table>
                </div>
                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3">
                        <span id="dieFeeTotal" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('dieFeePageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="dieFeePagination"></div>
                </div>
            </div>
        </div>
        <div id="dieFeeDrawerBackdrop" class="hidden fixed inset-0 z-[80] bg-black/70"></div>
        <div id="dieFeeDrawer" class="hidden fixed inset-y-0 right-0 z-[85] w-[560px] max-w-[95vw] bg-[#111111] border-l border-[#2a2a2a] flex flex-col translate-x-full">
            <div class="px-5 py-3 border-b border-[#222] flex items-center justify-between">
                <h2 class="text-[11px] text-[#b0b0b0] tracking-wider">模具费明细</h2>
                <button type="button" id="dieFeeDrawerClose" class="text-[#707070] hover:text-white">关闭</button>
            </div>
            <div id="dieFeeDrawerBody" class="flex-1 overflow-y-auto p-5 text-[11px] text-[#9e9e9e]"></div>
        </div>
    `;
}

export function renderDieFeeRows(items, { canUpdate, canDelete }) {
    if (!items.length) {
        return `<tr><td colspan="8" class="py-16 text-center text-[#555555]">暂无数据</td></tr>`;
    }
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    return items.map((row) => {
        const pending = row.audit_status !== 'approved';
        const statusLabel = row.audit_status === 'approved' ? '已审核' : (row.audit_status === 'rejected' ? '已驳回' : '待审');
        const statusClass = row.audit_status === 'approved' ? 'text-[#4caf50]' : 'text-[#ffb74d]';
        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[14px] font-bold text-[#F0F0F2] truncate" title="${esc(row.part_number)}">${esc(row.part_number)}</div>
                    <div class="text-[9px] text-[#555555] truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '-')}</div>
                </td>
                <td class="px-2 py-2 text-[10px] text-[#8E8E93] truncate">${esc(row.production_mode || '-')}</td>
                <td class="${numCell}">${esc(fmtNum(row.die_fee, 4))}</td>
                <td class="${numCell}">${row.adjustment_amount == null ? '-' : esc(fmtNum(row.adjustment_amount, 4))}</td>
                <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">${esc(fmtNum(row.final_die_fee, 4))}</td>
                <td class="px-1 py-2 text-center text-[9px] ${statusClass}">${statusLabel}</td>
                <td class="px-1 py-2 text-center">
                    <button type="button" data-action="detail" data-id="${esc(row.id)}"
                        class="w-7 h-7 inline-flex items-center justify-center text-[#777] hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100">详</button>
                    ${canUpdate && pending ? `<button type="button" data-action="edit" data-id="${esc(row.id)}"
                        class="w-7 h-7 inline-flex items-center justify-center text-[#777] hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100">改</button>` : ''}
                    ${canDelete && pending ? `<button type="button" data-action="delete" data-id="${esc(row.id)}"
                        class="w-7 h-7 inline-flex items-center justify-center text-[#777] hover:text-[#ef5350] opacity-0 group-hover:opacity-100 focus:opacity-100">删</button>` : ''}
                </td>
            </tr>`;
    }).join('');
}
