/**
 * Parts Template
 * 零件列表页面 —Brabus Carbon & Precision Dark
 * 布局对齐加工费列表：HUD + 胶囊筛选（默认收起） 级联查询
 *
 * 明细抽屉 / renderDetailContent 保持不变
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function partsTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <!-- HUD + 操作 -->
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">基地</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="partsHudLocation">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">个</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">车型</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="partsHudVehicle">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">种</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">版本</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="partsHudVersion">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">个</span>
                                </div>
                            </div>
                            <!-- 零件号：重点指标 -->
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">零件号</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7), 0 0 25px rgba(255,30,39,0.3);">
                                    <span id="partsHudPartNumber">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-1">去重后件数</div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">冲压工厂</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="partsHudSupplier">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">个</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="partsBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 hover:shadow-[0_0_12px_rgba(198,40,40,0.2)] transition-all duration-200">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="partsExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                    <div class="text-[11px] font-mono text-[#555555] truncate">
                        查询范围：<span id="partsHudScope" class="text-[#8E8E93]">全部范围</span>
                    </div>
                </div>

                <!-- 战术胶囊筛选栏：默认收起-->
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-xl font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="partsCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="partsCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部车型</span>
                                <span id="partsCapsuleVersion" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部版本</span>
                                <span id="partsCapsuleSupplier" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部工厂</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="partsToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="partsAdvancedFilterLabel">展开高级筛选</span>
                                <span id="partsAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="partsSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <!-- 高级筛选面板（默认折叠；级联：基地 → 车型 → 版本 → 冲压工厂）-->
                    <div id="partsAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('locationFilter', '基地')}
                            ${filterSelect('vehicleModelFilter', '车型')}
                            ${filterSelect('versionFilter', '版本')}
                            ${filterSelect('supplierFilter', '冲压工厂')}
                            ${filterInput('searchInput', '零件号', '短号或完整零件号')}
                            <button id="partsResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">筛选均可选；级联为基地 → 车型 → 版本 → 冲压工厂。批量删除须基地、车型、版本；冲压工厂可选。导出须选定基地。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[1580px] bg-transparent" id="partsTable">
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0 w-0"></th>
                                <th class="px-3 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap w-14">图纸</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#A1A1A6] whitespace-nowrap">零件号</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">零件名称</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">基地</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">车型</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">版本</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap border-r border-[#22222A]">冲压工厂</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">材料</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">利废</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">废料副产品</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">摆剪</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">厚度</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">重量</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">工序</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">来源文件</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="partsTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="partsTotalLabel" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('partsPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="pagination"></div>
                </div>

                <div id="partsEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无零件数据</h5>
                    <p class="text-[10px] text-[#555555]">请先上传工艺文件</p>
                </div>

                <div id="partsLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        <!-- 零件详情抽屉（图级+ 信息 + 工序，表格保持可见） -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="partDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="partDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <!-- 拖拽条-->
            <div class="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-[#d32f2f]/50 transition-colors z-10"></div>

            <!-- 头部（固定不滚动）-->
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase" id="partDrawerTitle">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    零件详情
                </h5>
                <button type="button" id="closePartDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <!-- 可滚动内容区 -->
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="partDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <div class="flex items-center justify-center py-16">
                    <div class="w-7 h-7 border-2 border-[#2a2a2a] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" class="w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="h-8 w-36 px-2.5 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#ffffff] placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27] transition-colors">
    </label>`;
}

/**
 * 同步战术胶囊：基地 / 车型 / 版本 / 工厂 + 高级筛选已启用数量
 */
export function updatePartsFilterCapsules() {
    const location = document.getElementById('locationFilter')?.value || '';
    const supplier = document.getElementById('supplierFilter')?.value || '';
    const vehicle = document.getElementById('vehicleModelFilter')?.value || '';
    const version = document.getElementById('versionFilter')?.value || '';
    const part = document.getElementById('searchInput')?.value.trim() || '';

    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const locationEl = document.getElementById('partsCapsuleLocation');
    const supplierEl = document.getElementById('partsCapsuleSupplier');
    const vehicleEl = document.getElementById('partsCapsuleVehicle');
    const versionEl = document.getElementById('partsCapsuleVersion');
    const countEl = document.getElementById('partsAdvancedFilterCount');
    const scopeEl = document.getElementById('partsHudScope');

    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? activeCapsule : idleCapsule;
    }
    if (supplierEl) {
        supplierEl.textContent = supplier || '全部工厂';
        supplierEl.className = supplier ? activeCapsule : idleCapsule;
    }
    if (vehicleEl) {
        vehicleEl.textContent = vehicle || '全部车型';
        vehicleEl.className = vehicle ? activeCapsule : idleCapsule;
    }
    if (versionEl) {
        versionEl.textContent = version || '全部版本';
        versionEl.className = version ? activeCapsule : idleCapsule;
    }

    const advancedActive = [location, supplier, vehicle, version, part].filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;

    if (scopeEl) {
        const parts = [location, vehicle, version, supplier].filter(Boolean);
        scopeEl.textContent = parts.length ? parts.join(' · ') : '全部范围';
    }
}

export function updatePartsHud(summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const fmt = (value) => Number(value || 0).toLocaleString('zh-CN');
    setText('partsHudLocation', fmt(data.location_count));
    setText('partsHudSupplier', fmt(data.stamping_supplier_count));
    setText('partsHudVehicle', fmt(data.vehicle_model_count));
    setText('partsHudPartNumber', fmt(data.part_number_count));
    setText('partsHudVersion', fmt(data.version_count));
}

export function renderPartsPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button type="button" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}
                class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button type="button" data-page="1" class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button type="button" data-page="${i}"
            class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#FFFFFF] text-[#0a0a0a] font-bold' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
        buttons += `<button type="button" data-page="${totalPages}" class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]">${totalPages}</button>`;
    }
    buttons += `
        <button type="button" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}
                class="flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}

// CORE_COST_FIELDS 决定详情表强调样开
const CORE_COST_FIELDS = new Set(['材料', '重量', '可制件数', '模具类型']);

const DIE_TYPE_OPTIONS = [
    { value: 'progressive', label: '级进模（80%）' },
    { value: 'single', label: '单干模具（100%）' },
    { value: 'shared', label: '共模（50%）' },
    { value: 'progressive_shared', label: '级进共模（40%）' },
];

/**
 * 详情表格表—用CORE_COST_FIELDS 决定强调样式
 */
function detailTableRow([label, value]) {
    const isCore = CORE_COST_FIELDS.has(label);
    const tdClass = isCore
        ? 'text-[11px] font-mono font-semibold text-[#d32f2f] tracking-[0.05em]'
        : 'text-[11px] text-[#6b6b6b] tracking-wider';
    const tdStyle = isCore ? ' style="text-shadow:0 0 10px rgba(211,47,47,0.3)"' : '';
    return `
            <tr class="border-b border-[#161616] last:border-b-0">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">${label}</th>
                <td class="px-4 py-3 ${tdClass}"${tdStyle}>${value}</td>
            </tr>`;
}

function renderOffalRows(part, canUpdate) {
    const isOn = Boolean(part.is_offal_nested);
    const source = part.offal_source || '';
    if (!canUpdate) {
        return [
            detailTableRow(['是否利废', isOn ? '是' : '否']),
            detailTableRow(['利用哪类废料', esc(source)]),
            detailTableRow(['废料副产品', part.is_scrap_byproduct ? '是' : '否']),
            detailTableRow(['摆剪工序', part.has_swing_shear ? '是' : '否']),
        ].join('');
    }
    const knobX = isOn ? '16px' : '2px';
    const trackBg = isOn ? '#d32f2f' : '#1a1a1a';
    const trackBorder = isOn ? '#d32f2f' : '#2c2c2c';
    return `
            <tr class="border-b border-[#161616]">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">是否利废</th>
                <td class="px-4 py-3">
                    <div class="flex items-center gap-2.5 flex-wrap">
                        <button type="button" id="offalNestedToggle" role="switch"
                                aria-checked="${isOn ? 'true' : 'false'}"
                                data-on="${isOn ? '1' : '0'}"
                                class="relative h-5 w-9 shrink-0 rounded-full border focus:outline-none focus:border-[#ff5252]"
                                style="background:${trackBg}; border-color:${trackBorder};">
                            <span id="offalNestedKnob"
                                  class="absolute top-0.5 h-3.5 w-3.5 rounded-full bg-[#ffffff] pointer-events-none"
                                  style="left:0; transform:translateX(${knobX}); transition:transform 150ms ease;"></span>
                        </button>
                        <span id="offalNestedLabel" class="text-[11px] text-[#9e9e9e] tracking-wide">${isOn ? '是' : '否'}</span>
                        <button type="button" id="saveOffalBtn" data-active="false"
                                class="h-7 px-3 text-[10px] text-[#555555] border border-[#2c2c2c] bg-transparent rounded-sm hover:text-[#d32f2f] hover:border-[#d32f2f]/50 transition-all tracking-wide">
                            保存利废
                        </button>
                    </div>
                    <p class="mt-1.5 text-[9px] text-[#555555] leading-relaxed">从废料里捡成品；材料按成品净重 × 废料单价。改后须重算零件价格才生效。</p>
                </td>
            </tr>
            <tr id="offalSourceRow" class="border-b border-[#161616] ${isOn ? '' : 'hidden'}">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">利用哪类废料</th>
                <td class="px-4 py-3">
                    <input type="text" id="offalSourceInput" maxlength="50"
                           value="${esc(source)}"
                           placeholder="如：侧围（可空）"
                           class="w-full h-8 px-2 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                </td>
            </tr>
            <tr class="border-b border-[#161616]">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">废料副产品</th>
                <td class="px-4 py-3 text-[11px] text-[#6b6b6b] tracking-wider">${part.is_scrap_byproduct ? '是' : '否'}</td>
            </tr>
            <tr class="border-b border-[#161616]">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">摆剪工序</th>
                <td class="px-4 py-3 text-[11px] text-[#6b6b6b] tracking-wider">${part.has_swing_shear ? '是' : '否'}</td>
            </tr>`;
}

/**
 * Excel 单元格溯源：文件 + 表页 + 表+ 零件号列（与 BOM 防扯皮对齐）
 */
function renderExcelProvenance(part) {
    const filename = part?.excel_filename || '';
    const sheet = part?.excel_sheet_name || '';
    const row = part?.excel_row;
    const col = part?.excel_part_col;
    const hasCell = Boolean(sheet) || row != null || col != null;
    if (!filename && !hasCell) {
        return `
            <div class="mx-4 mb-4 border border-[#262626] bg-[#111111] p-3">
                <p class="text-[10px] uppercase tracking-[0.14em] text-[#d32f2f] mb-1.5 flex items-center gap-2">
                    <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                    Excel 溯源
                </p>
                <p class="text-[12px] text-[#616161]">无单元格溯源（请重新上传工艺文件生成）</p>
            </div>
        `;
    }
    const colHint = col != null ? `第${col} 列（零件号）` : null;
    const rowHint = row != null ? `第${row} 行` : null;
    const locator = [
        sheet ? `表「${sheet}」` : null,
        rowHint,
        colHint,
    ].filter(Boolean).join(' · ');
    const cellHint = hasCell
        ? `<p class="text-[11px] text-[#888888]">${esc(locator || '—')}</p>`
        : `<p class="text-[11px] text-[#616161]">仅有文件名（该批数据上传时尚未落表页/行列；请再上传一次工艺文件，或已由运维回填）</p>`;
    return `
        <div class="mx-4 mb-4 border border-[#d32f2f]/25 bg-[#111111] p-3"
             style="box-shadow: 0 0 20px rgba(211,47,47,0.06), inset 0 1px 0 rgba(211,47,47,0.05);">
            <p class="text-[10px] uppercase tracking-[0.14em] text-[#d32f2f] mb-2 flex items-center gap-2">
                <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                Excel 溯源
            </p>
            <p class="text-[12px] text-[#cfcfcf] font-mono break-all mb-1">${esc(filename || '—')}</p>
            ${cellHint}
        </div>
    `;
}

function renderProcessRow(p, idx) {
    const processId = p.id ?? idx;
    const ratioMap = { 0.8: 'progressive', 1: 'single', 0.5: 'shared', 0.4: 'progressive_shared' };
    const ratioKey = Number(p.cost_ratio);
    const currentDieType = p.die_type || ratioMap[ratioKey] || 'single';

    return `
                <tr class="border-b border-[#161616] last:border-b-0 group hover:bg-[#0e0e0e] transition-colors duration-200 process-row" data-process-id="${processId}">
                    <td class="px-4 py-4 text-[10px] text-[#4a4a4a] font-mono tracking-[0.06em]">${p.process_order ?? '—'}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-mono tracking-[0.06em]">${esc(p.process_seq)}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-medium tracking-[0.05em]">${esc(p.process_code)}</td>
                    <td class="px-4 py-4 text-[11px] text-[#C8C8D0] font-mono tracking-[0.04em]">${esc(p.die_number)}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-[#777777] tracking-[0.06em]">${p.die_sets ?? '—'}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-[#777777] tracking-[0.06em]">${p.tonnage ? `${p.tonnage}T` : '—'}</td>
                    <td class="px-4 py-4">
                        <div class="flex items-center gap-2">
                            <select class="die-type-select h-7 px-2 text-[10px] bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm" data-original-die-type="${currentDieType}">
                                ${DIE_TYPE_OPTIONS.map(o => `<option value="${o.value}" ${o.value === currentDieType ? 'selected' : ''}>${o.label}</option>`).join('')}
                            </select>
                            <span class="text-[9px] font-mono text-[#555555] tracking-[0.05em]" title="模具成本比例">${p.cost_ratio != null ? `${(p.cost_ratio * 100).toFixed(0)}%` : '—'}</span>
                        </div>
                    </td>
                </tr>`;
}

export function renderDetailContent(part, options = {}) {
    const canUpdate = options.canUpdate !== false;
    const sketchUrl = part.sketch_url || '';

    const rows = [
        ['零件号', esc(part.part_number)],
        ['零件名称', esc(part.part_name)],
        ['采购基地', esc(part.location)],
        ['冲压供应商', esc(part.stamping_supplier)],
        ['车型', esc(part.vehicle_model)],
        ['版本', esc(part.version)],
        ['材料', esc(part.material)],
        ['工艺方法', esc(part.process_method ?? '-')],
        ['自动化', esc(part.automation ?? '-')],
    ];
    const rowsRightTop = [
        ['厚度', part.thickness != null ? `${part.thickness} mm` : '-'],
        ['重量', part.part_weight != null ? `${part.part_weight} kg` : '-'],
        ['板材尺寸', (part.sheet_length && part.sheet_width) ? `${part.sheet_length}x${part.sheet_width}` : '-'],
        ['可制件数', esc(part.parts_per_sheet)],
        ['板材类型', esc(part.sheet_type)],
    ];
    const rowsRightBottom = [
        ['模具类型', part.cost_ratio != null ? `${(part.cost_ratio * 100).toFixed(0)}%` : esc(part.die_type)],
        ['备注', esc(part.remark ?? '-')],
    ];

    const processes = part.processes || [];
    const processRows = processes.length
        ? processes.map((p, idx) => renderProcessRow(p, idx)).join('')
        : `<tr><td colspan="7" class="px-4 py-12 text-center text-[11px] text-[#333333] tracking-[0.15em]">暂无工序数据</td></tr>`;

    return `
        <div class="h-full min-h-full flex flex-col" style="background: linear-gradient(175deg, #0a0a0a 0%, #090909 100%);">
            <!-- 顶部信息区域 -->
            <div class="flex gap-3 p-4">
                <!-- 左侧：基本信息-->
                <div class="flex-1 brabus-panel">
                    <div class="brabus-panel-header flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-[#353535]">${svgIcon('info-circle')}</span>
                            <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">基本信息</span>
                        </div>
                        ${sketchUrl ? `
                        <button type="button" id="openSketchModal" class="flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[9px] text-[#333333] hover:text-[#888888] border border-[#1c1c1c] hover:border-[#2e2e2e] transition-all duration-200 tracking-wide group">
                            ${svgIcon('arrows-fullscreen', 'w-3.5 h-3.5 text-[#2d2d2d] group-hover:text-[#888888] transition-colors duration-200')}
                            <span class="group-hover:text-[#555555] transition-colors duration-200">查看图纸</span>
                        </button>` : ''}
                    </div>
                    <table class="w-full">${rows.map(detailTableRow).join('')}</table>
                </div>
                <!-- 右侧：尺寸参数-->
                <div class="flex-1 brabus-panel">
                    <div class="brabus-panel-header flex items-center gap-2">
                        <span class="text-[#353535]">${svgIcon('ruler')}</span>
                        <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">尺寸参数</span>
                    </div>
                    <table class="w-full">${rowsRightTop.map(detailTableRow).join('')}${renderOffalRows(part, canUpdate)}${rowsRightBottom.map(detailTableRow).join('')}</table>
                </div>
            </div>

            ${renderExcelProvenance(part)}

            <!-- 工序列表 -->
            <div class="mx-4 mb-4 flex flex-col shrink-0">
                <div class="brabus-section-header flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-[#353535]">${svgIcon('list-ol')}</span>
                        <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">工序列表</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <select id="batchDieTypeSelect" class="die-type-select" style="width:148px;">
                            <option value="">批量修改模具类型</option>
                            ${DIE_TYPE_OPTIONS.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
                        </select>
                        <button type="button" id="applyBatchDieType" class="h-9 px-4 text-[10px] bg-[#111111] text-[#555555] border-none focus:outline-none rounded-sm transition-all duration-200 hover:text-[#d32f2f] hover:shadow-[0_0_10px_rgba(211,47,47,0.1)] tracking-wide">
                            批量应用
                        </button>
                    </div>
                </div>
                <div class="brabus-table-wrapper">
                    <table class="w-full">
                        <thead class="shrink-0">
                            <tr style="background:#0c0c0c; border-bottom:1px solid #1a1a1a;">
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">序</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">工序号</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">代号</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">模具编号</th>
                                <th class="px-4 py-2.5 text-right text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">模数</th>
                                <th class="px-4 py-2.5 text-right text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">吨位</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-[#353535]">模具类型</th>
                            </tr>
                        </thead>
                        <tbody id="processTableBody">${processRows}</tbody>
                    </table>
                </div>
            </div>

            <!-- 保存按钮与规则栏 -->
            ${processes.length > 0 ? `
            <div class="mx-4 mb-6 mt-4">
                <!-- 成本规则 -->
                <div class="flex items-center justify-center gap-4 py-2 mb-3 bg-[#0a0a0a] border border-[#1a1a1a] rounded-sm">
                    <span class="text-[7px] text-[#2a2a2a] tracking-[0.15em] uppercase">成本规则</span>
                    <span class="text-[7px] text-[#1e1e1e]">·</span>
                    <span class="text-[9px] text-[#3a3a3a]"><span class="text-[#555555]">级进模</span> <span class="text-[#8a3030] font-medium">80%</span></span>
                    <span class="text-[7px] text-[#1e1e1e]">·</span>
                    <span class="text-[9px] text-[#3a3a3a]"><span class="text-[#555555]">单干模具</span> <span class="text-[#8a3030] font-medium">100%</span></span>
                    <span class="text-[7px] text-[#1e1e1e]">·</span>
                    <span class="text-[9px] text-[#3a3a3a]"><span class="text-[#555555]">共模</span> <span class="text-[#8a3030] font-medium">50%</span></span>
                    <span class="text-[7px] text-[#1e1e1e]">·</span>
                    <span class="text-[9px] text-[#3a3a3a]"><span class="text-[#555555]">级进共模</span> <span class="text-[#8a3030] font-medium">40%</span></span>
                </div>
                <!-- 保存按钮 -->
                <div class="flex justify-center">
                    <button type="button" id="saveProcessBtn"
                            data-active="false"
                            class="btn-save-default">
                        <span class="tracking-[0.2em]">保存</span>
                    </button>
                </div>
            </div>` : ''}
        </div>
    `;
}
