/**
 * Stamping Part Cost List Template
 * 冲压零件价格一览 — Brabus Precision Assembly：材质分层 · 无竖线 · 装配槽
 */

/** 自定义暗色下拉（原生 select 弹出层无法换肤） */
function filterChip(id, label, emptyLabel = '全部') {
    return `
        <div class="relative cost-filter-chip" data-filter-id="${id}">
            <select id="${id}" class="hidden" data-empty-label="${emptyLabel}" aria-hidden="true" tabindex="-1">
                <option value="">${emptyLabel}</option>
            </select>
            <button type="button"
                    class="cost-filter-trigger flex items-center gap-1.5 h-[26px] bg-[#121216] border border-[#22222A] px-2 rounded-sm
                           hover:border-[#FF1E27]/35 transition-colors"
                    style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);"
                    aria-haspopup="listbox" aria-expanded="false">
                <span class="text-[#555555] text-[9px] font-mono shrink-0">${label}</span>
                <span class="cost-filter-label text-[#E8E8ED] text-[10px] font-mono whitespace-nowrap max-w-[7rem] truncate">全部</span>
                <span class="text-[#555555] text-[9px] leading-none">▾</span>
            </button>
            <div class="cost-filter-menu hidden absolute left-0 top-full mt-1 z-[50] min-w-[7.5rem] max-h-56 overflow-y-auto py-1
                        bg-[#121216] border border-[#22222A] shadow-[0_8px_24px_rgba(0,0,0,0.55)]"
                 role="listbox"></div>
        </div>`;
}

export function partCostListTemplate() {
    return `
        <div class="w-full max-w-full bg-[#08080A]">
            <div class="bg-[#0E0E12] border border-[#1A1A24] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.025);">

                <!-- HUD：哑光钛金层 -->
                <div class="px-5 py-2.5 border-b border-[#1A1A24] bg-[#0E0E12] flex items-center justify-between gap-4 font-mono text-[11px]">
                    <div class="flex items-center gap-6 divide-x divide-[#22222E] min-w-0">
                        <div class="flex items-center gap-2 shrink-0">
                            <span class="text-[#555555]">合计</span>
                            <span id="costHudTotal" class="text-[#F0F0F2] font-bold tabular-nums">—</span>
                            <span class="text-[#3A3A42]">条</span>
                        </div>
                        <div class="pl-6 flex items-center gap-2 shrink-0">
                            <span class="text-[#FF1E27]/80 font-semibold">均价</span>
                            <span class="inline-flex items-center px-2 py-0.5 bg-[#1A080A] border border-[#FF1E27]/20 text-[#FF1E27] font-black text-[12px] tabular-nums"
                                  style="text-shadow: 0 0 8px rgba(255,30,39,0.4);">
                                ￥<span id="costHudAvg">—</span>
                            </span>
                        </div>
                        <div class="pl-6 flex items-center gap-4 text-[#6E6E73] shrink-0">
                            <span>待审 <strong id="costHudPending" class="text-[#E8E8ED] font-semibold tabular-nums">—</strong></span>
                            <span>已审 <strong id="costHudApproved" class="text-[#E8E8ED] font-semibold tabular-nums">—</strong></span>
                        </div>
                    </div>

                    <div class="flex items-center gap-3 shrink-0">
                        <span class="text-[#2E2E36] text-[9px] hidden xl:inline"
                              title="ρ_steel=钢材密度；λ=材料损耗率；η=废料回收率；P/Q=元/kg">
                            R = M×P×(1+λ) − M×λ×η×Q − O×η×Q
                        </span>

                        <div id="costBatchBar"
                             class="hidden items-center gap-0.5 bg-[#121216] border border-[#22222A] px-1.5 py-0.5 rounded-sm">
                            <span class="text-[#555555] text-[9px] px-1">当前范围</span>
                            <button id="costBatchApproveBtn" type="button"
                                    class="px-2 py-0.5 text-[#8E8E93] hover:text-[#FF1E27] text-[10px] transition-colors">审核</button>
                            <button id="costBatchReverseBtn" type="button"
                                    class="px-2 py-0.5 text-[#8E8E93] hover:text-[#FF1E27] text-[10px] transition-colors">反审核</button>
                            <button id="costBatchDeleteBtn" type="button"
                                    class="px-2 py-0.5 text-[#8E8E93] hover:text-[#ef5350] text-[10px] transition-colors">删除</button>
                        </div>

                        <div class="relative" id="costExportWrap">
                            <button id="costExportMenuBtn" type="button"
                                    class="h-[26px] px-2.5 bg-[#121216] border border-[#22222A] text-[#8E8E93] hover:text-[#F0F0F2] hover:border-[#FF1E27]/40 text-[10px] rounded-sm transition-all"
                                    aria-haspopup="menu" aria-expanded="false" aria-controls="costExportMenu">
                                导出 ▾
                            </button>
                            <div id="costExportMenu"
                                 class="hidden absolute right-0 top-full mt-1 z-[40] min-w-[148px] py-1 bg-[#121216] border border-[#22222A] shadow-[0_8px_24px_rgba(0,0,0,0.55)]"
                                 role="menu">
                                <button type="button" id="costExportBtn" role="menuitem"
                                        class="w-full px-3.5 py-2 text-left text-[12px] text-[#9e9e9e] hover:bg-[#161620] hover:text-[#ffffff] transition-colors"
                                        title="工艺清单格式：业务列至最终价，末尾弱化溯源列">
                                    工艺清单
                                </button>
                                <button type="button" id="costExportDetailBtn" role="menuitem"
                                        class="w-full px-3.5 py-2 text-left text-[12px] text-[#9e9e9e] hover:bg-[#161620] hover:text-[#ffffff] transition-colors"
                                        title="明细表：业务字段 + 溯源/关联ID + 审核元数据">
                                    核算明细
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 控制台：胶囊筛选单元 -->
                <div class="px-5 py-2 border-b border-[#1A1A24] bg-[#0C0C10] flex items-center gap-3 font-mono">
                    <div class="flex items-center gap-1.5 flex-wrap min-w-0">
                        ${filterChip('costYearFilter', '年')}
                        ${filterChip('costMonthFilter', '月')}
                        ${filterChip('costLocationFilter', '基地')}
                        ${filterChip('costSupplierFilter', '工厂')}
                        ${filterChip('costAuditFilter', '审核')}
                        <div class="flex items-center gap-1.5 h-[26px] bg-[#121216] border border-[#22222A] px-2 rounded-sm
                                    focus-within:border-[#FF1E27]/35 transition-colors"
                             style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                            <span class="text-[#555555] text-[9px] font-mono shrink-0">零件</span>
                            <input id="costPartNumberFilter" type="text" placeholder="短号 / 完整号"
                                   class="w-28 bg-transparent text-[#E8E8ED] placeholder:text-[#3A3A42] text-[10px] font-mono focus:outline-none" />
                        </div>
                        <button id="costSearchBtn" type="button"
                                class="h-[26px] px-3 bg-[#1A080A] border border-[#FF1E27]/35 text-[#FF1E27] hover:bg-[#FF1E27] hover:text-[#0A0A0C] font-semibold text-[10px] rounded-sm transition-all">
                            查询
                        </button>
                        <button id="costResetBtn" type="button"
                                class="h-[26px] px-2 text-[#555555] hover:text-[#8E8E93] text-[10px] transition-colors">
                            重置
                        </button>
                    </div>
                </div>

                <!-- 表体：无竖线 · 仅极细横线 · 靠对齐呼吸 -->
                <div class="overflow-x-auto bg-[#0A0A0E]">
                    <table id="costDataTable" class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1116px;">
                        <colgroup id="costColgroup">
                            <col style="width:3px">
                            <col style="width:72px">
                            <col style="width:118px">
                            <col style="width:88px">
                            <col style="width:68px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:54px">
                            <col style="width:64px">
                            <col style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:68px">
                            <col style="width:76px">
                            <col style="width:58px">
                            <col style="width:86px">
                            <col style="width:44px">
                            <col style="width:44px">
                            <col style="width:36px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#1A1A24] bg-[#121218]">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">年月/基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#6E6E73]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">材质/厚</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="预估单件材料消耗 M (kg)">消耗</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="零件净重">净重</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料重量 O = 材料消耗−净重">废料</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">利用率%</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="钢材吨价；P=吨价/1000 元/kg">钢材吨价</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料吨价；Q=吨价/1000 元/kg">废料吨价</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="① 钢材采购（含损耗）">①采购</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="② 损耗废料扣除（回收率）">②损耗扣</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="③ 边角废料扣除（回收率）">③边角扣</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料扣除合计 ②+③">废料扣合计</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#6E6E73]" title="R = ①−②−③">
                                    <button type="button" id="costToggleBreakdownCols"
                                            class="inline-flex items-center justify-center w-3.5 h-3.5 mr-0.5 align-middle border border-[#22222A] text-[#555555] hover:text-[#FF1E27] hover:border-[#FF1E27]/40 transition-colors"
                                            title="展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）">+</button>
                                    原材料R
                                </th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">加工费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]" title="单件成本 = 原材料 R + 加工费">单件成本</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">核算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="costTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1A1A24] bg-[#0E0E12]">
                    <span id="costPageInfo" class="text-[10px] font-mono text-[#555555]"></span>
                    <div class="flex items-center gap-0.5" id="costPagination"></div>
                </div>

                <div id="costEmpty" class="hidden flex flex-col items-center justify-center py-14 bg-[#0A0A0E]">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 bg-[#121216] border border-[#22222A] rounded-sm">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无零件价格数据</h5>
                    <p class="text-[10px] text-[#555555]">请先完成零件价格计算，或调整筛选条件</p>
                </div>

                <div id="costLoading" class="hidden flex items-center justify-center py-14 bg-[#0A0A0E]">
                    <div class="w-5 h-5 border-2 border-[#22222A] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
    `;
}

export function renderCostRows(records, breakdownOpen = false) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const breakdownHidden = breakdownOpen ? '' : 'hidden';
    return records.map((row) => {
        const fail = row.calc_status === 'failed';
        const ym = `${esc(row.year)}-${esc(String(row.month).padStart(2, '0'))}`;
        const location = esc(row.location) || '—';
        const supplier = esc(row.stamping_supplier) || '—';
        const num = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
        const actionTitle = fail ? '手工干预' : '查看详情';
        const actionIcon = fail
            ? window.svgIcon('pencil', 'w-3.5 h-3.5')
            : window.svgIcon('eye', 'w-3.5 h-3.5');
        const actionTone = fail
            ? 'text-[#8A3030] hover:text-[#FF1E27]'
            : 'text-[#555555] hover:text-[#C8C8D0]';
        const actionBtn = `
            <button type="button"
                    class="btn-open-detail inline-flex items-center justify-center w-7 h-7 rounded-sm
                           opacity-0 group-hover:opacity-100 focus:opacity-100
                           ${actionTone} hover:bg-[#161620] transition-all duration-100"
                    data-id="${esc(row.id)}" title="${actionTitle}" aria-label="${actionTitle}">
                ${actionIcon}
            </button>`;
        return `
        <tr class="cost-row group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-[#F0F0F2] text-[11px] tabular-nums">${ym}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
                <div class="text-[#3A3A42] text-[9px] leading-tight truncate" title="${supplier}">${supplier}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">${partInfoCell(row.part_number, row.part_name)}</td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#8E8E93] text-[10px] truncate" title="${esc(row.material || '')}">${esc(row.material || '—')}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 tabular-nums">${fmtNum(row.thickness, 3)}</div>
            </td>
            <td class="${num}" title="${esc(fmtNum(row.blank_weight_kg, 7))}">${fmtNum(row.blank_weight_kg, 3)}</td>
            <td class="${num}" title="${esc(fmtNum(row.finished_total_kg, 7))}">${fmtNum(row.finished_total_kg, 3)}</td>
            <td class="${num}" title="${esc(fmtNum(row.scrap_weight_kg, 7))}">${fmtNum(row.scrap_weight_kg, 3)}</td>
            <td class="${num}">${fmtNum(row.material_utilization_pct, 1)}</td>
            <td class="${num}">${fmtNum(row.steel_ton_price, 0)}</td>
            <td class="${num}">${fmtNum(row.scrap_ton_price, 0)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.material_amount_sheet, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.loss_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.process_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.scrap_amount_sheet, 2)}</td>
            <td class="${num} text-[#C8C8D0] font-semibold">${fmtNum(row.material_net_per_part, 2)}</td>
            <td class="${num}">${fmtNum(row.process_fee_amount, 2)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${fmtNum(row.unit_cost, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(fail)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>
            <td class="px-1 py-2 text-center align-middle">${actionBtn}</td>
        </tr>`;
    }).join('');
}

/**
 * 同步成本分项列显隐（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）
 * @param {boolean} isOpen
 */
export function syncBreakdownColumnVisibility(isOpen) {
    document.querySelectorAll('.cost-breakdown-col').forEach((el) => {
        el.classList.toggle('hidden', !isOpen);
    });
    const btn = document.getElementById('costToggleBreakdownCols');
    if (btn) {
        btn.textContent = isOpen ? '−' : '+';
        btn.title = isOpen
            ? '收起成本分项'
            : '展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）';
    }
    const table = document.getElementById('costDataTable');
    if (table) {
        table.style.minWidth = isOpen ? '1376px' : '1116px';
    }
}

/**
 * 企业口语短号：取零件号数字段末 4 位（与 BOM / 加工费一致）。
 * 例：554002087AA → 2087；501006873AA → 6873
 */
export function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/** 列表单元格：短号主角，完整号 + 零件名次要 */
function partInfoCell(partNumber, partName) {
    const full = partNumber || '';
    const shortNo = shortPartNumber(full);
    const name = partName || '';
    const nameLine = name
        ? `<div class="text-[9px] text-[#555555] mt-0.5 truncate" title="${esc(name)}">${esc(name)}</div>`
        : '';
    if (shortNo) {
        return `
            <div class="text-[14px] font-mono font-bold tabular-nums text-[#F0F0F2] tracking-[0.08em] leading-none"
                 title="${esc(full)}">${esc(shortNo)}</div>
            <div class="text-[9px] font-mono text-[#3A3A42] tracking-wide mt-0.5 truncate" title="${esc(full)}">${esc(full)}</div>
            ${nameLine}`;
    }
    return `
        <div class="text-[10px] font-mono text-[#8E8E93] tracking-wide truncate" title="${esc(full)}">${esc(full) || '—'}</div>
        ${nameLine}`;
}

/** 用筛选汇总刷新 HUD（均价 / 待审 / 已审均为全量筛选结果，非本页） */
export function updatePartCostHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const avg = data.avg_unit_cost;
    const avgNumber = avg == null || avg === '' ? NaN : Number(avg);

    setText('costHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText(
        'costHudAvg',
        Number.isNaN(avgNumber)
            ? '—'
            : avgNumber.toLocaleString('zh-CN', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 4,
            })
    );
    setText('costHudPending', String(data.pending_count ?? 0));
    setText('costHudApproved', String(data.approved_count ?? 0));
}

export function renderCostPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#E8E8ED] text-[#0A0A0C] font-bold' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">…</span>`;
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}

/** 无错即隐：成功不占视觉；失败才露「失败」 */
function calcStatusBadge(isFailed) {
    if (!isFailed) return '';
    return `<span class="text-[#FF1E27] font-bold text-[9px] px-1 bg-[#FF1E27]/10 border border-[#FF1E27]/25">失败</span>`;
}

/** 待审留白；已通过/驳回才轻标 */
function auditBadge(status) {
    if (!status || status === 'pending') return '';
    if (status === 'approved') {
        return `<span class="text-[9px] text-[#555555]">已审</span>`;
    }
    if (status === 'rejected') {
        return `<span class="text-[9px] text-[#ef5350]">驳回</span>`;
    }
    return `<span class="text-[9px] text-[#555555]">${esc(status)}</span>`;
}
