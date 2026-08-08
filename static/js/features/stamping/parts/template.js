/**
 * Parts Template
 * 零件列表页面 — Brabus Carbon & Precision Dark
 *
 * 熵增管控规则：
 * - detailTableRow(valueClass) 的 valueClass 参数已被 CORE_COST_FIELDS 接管，传值无意义，已移除
 * - 所有面板使用 CSS 类（brabus-panel / brabus-panel-header / brabus-table-wrapper）
 * - SVG 统一使用 window.svgIcon 工具函数
 * - CORE_COST_FIELDS 定义在 renderDetailContent 之前，detailTableRow 中引用
 */

export function partsTemplate() {
    return `
        <!-- 筛选栏 -->
        <div class="bg-[#1e1e1e] border border-[#2c2c2c] p-3 mb-3">
            <div class="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center">
                <div class="flex-1 min-w-0">
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        </div>
                        <input type="text"
                               id="searchInput"
                               placeholder="搜索零件号或名称..."
                               class="w-full h-9 pl-9 pr-4 text-xs bg-[#0a0a0a] border border-[#2c2c2c] placeholder:text-[#616161] text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-all">
                    </div>
                </div>

                <div class="flex flex-row flex-wrap gap-2 items-center">
                    <select id="locationFilter"
                            class="w-32 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部基地</option>
                    </select>

                    <select id="supplierFilter"
                            class="w-36 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部供应商</option>
                    </select>

                    <select id="vehicleModelFilter"
                            class="w-36 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部车型</option>
                    </select>

                    <select id="versionFilter"
                            class="w-28 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部版本</option>
                    </select>

                    <div class="hidden lg:block w-px h-6 bg-[#222222]"></div>

                    <div class="flex items-center gap-1.5">
                        <label class="text-[10px] text-[#616161] whitespace-nowrap">每页</label>
                        <select id="pageSizeSelect"
                                class="w-16 h-9 px-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>

                    <div class="text-[10px] text-[#616161] whitespace-nowrap" id="totalCount">
                        共 0 个零件
                    </div>
                </div>
            </div>
        </div>

        <!-- 表格面板 -->
        <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
            <div class="overflow-x-auto">
                <table class="w-full" id="partsTable">
                    <thead>
                        <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap w-14">图纸</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">零件号</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">零件名称</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">基地</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">供应商</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">车型</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">版本</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">材料</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">厚度</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">重量</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">工序</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">来源文件</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">操作</th>
                        </tr>
                    </thead>
                    <tbody id="partsTableBody" class="divide-y divide-[#222222]">
                        <tr>
                            <td colspan="13">
                                <div class="flex flex-col items-center justify-center py-14">
                                    <div class="w-10 h-10 bg-[#262626] flex items-center justify-center mb-3">
                                        <svg class="w-5 h-5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                                    </div>
                                    <h5 class="text-xs font-medium text-[#9e9e9e] mb-1">暂无零件数据</h5>
                                    <p class="text-[11px] text-[#616161]">请先上传工艺文件</p>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="flex items-center justify-between px-4 py-3 border-t border-[#222222]">
                <div></div>
                <nav>
                    <ul class="flex justify-center mb-0" id="pagination"></ul>
                </nav>
            </div>
        </div>

        <!-- 零件详情抽屉（图纸 + 信息 + 工序，表格保持可见） -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="partDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-50 w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="partDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <!-- 拖拽条 -->
            <div class="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-[#d32f2f]/50 transition-colors z-10"></div>

            <!-- 头部（固定不滚动） -->
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

// CORE_COST_FIELDS 已在文件顶部定义
const CORE_COST_FIELDS = new Set(['材料', '重量', '可制件数', '模具类型']);

const DIE_TYPE_OPTIONS = [
    { value: 'progressive', label: '级进模（80%）' },
    { value: 'single', label: '单干模具（100%）' },
    { value: 'shared', label: '共模（50%）' },
    { value: 'progressive_shared', label: '级进共模（40%）' },
];

// 数据库只存 cost_ratio，反查 die_type
const RATIO_TO_DIE_TYPE = { 0.8: 'progressive', 1.0: 'single', 0.5: 'shared', 0.4: 'progressive_shared' };
const deriveDieType = (p) => p.die_type || RATIO_TO_DIE_TYPE[p.cost_ratio] || 'single';

/**
 * 详情表格行 — 由 CORE_COST_FIELDS 决定强调样式
 * valueClass 参数已废弃（由 CORE_COST_FIELDS 全权接管）
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

function renderProcessRow(p, idx, derivedDieType) {
    const processId = p.id ?? idx;
    // 根据 cost_ratio 推导出 die_type 值，用于选中下拉框
    const ratioMap = { 0.8: 'progressive', 1.0: 'single', 0.5: 'shared', 0.4: 'progressive_shared' };
    const currentDieType = p.die_type || ratioMap[p.cost_ratio] || 'single';
    const currentLabel = derivedDieType(p);

    return `
                <tr class="border-b border-[#161616] last:border-b-0 group hover:bg-[#0e0e0e] transition-colors duration-200 process-row" data-process-id="${processId}">
                    <td class="px-4 py-4 text-[10px] text-[#4a4a4a] font-mono tracking-[0.06em]">${p.process_order ?? '—'}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-mono tracking-[0.06em]">${esc(p.process_seq)}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-medium tracking-[0.05em]">${esc(p.process_code)}</td>
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

export function renderDetailContent(part) {
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
        ['自动化', part.automation ? '是' : '否'],
    ];
    // 右侧面板字段 — CORE_COST_FIELDS 会在 detailTableRow 中自动生效（材料/重量/模具类型）
    const derivedDieType = (p) => {
        const ratio = p.cost_ratio;
        if (ratio === 0.8) return '级进模（80%）';
        if (ratio === 1.0) return '单干模具（100%）';
        if (ratio === 0.5) return '共模（50%）';
        if (ratio === 0.4) return '级进共模（40%）';
        return part.die_type || '单干模具（100%）';
    };
    const rowsRight = [
        ['厚度', part.thickness != null ? `${part.thickness} mm` : '-'],
        ['重量', part.part_weight != null ? `${part.part_weight} kg` : '-'],
        ['板材尺寸', (part.sheet_length && part.sheet_width) ? `${part.sheet_length}x${part.sheet_width}` : '-'],
        ['可制件数', esc(part.parts_per_sheet)],
        ['板材类型', esc(part.sheet_type)],
        ['模具类型', part.cost_ratio != null ? `${(part.cost_ratio * 100).toFixed(0)}%` : esc(part.die_type)],
        ['备注', esc(part.remark ?? '-')],
    ];

    const processes = part.processes || [];
    const processRows = processes.length
        ? processes.map((p, idx) => renderProcessRow(p, idx, derivedDieType)).join('')
        : `<tr><td colspan="6" class="px-4 py-12 text-center text-[11px] text-[#333333] tracking-[0.15em]">暂无工序数据</td></tr>`;

    return `
        <div class="h-full min-h-full flex flex-col" style="background: linear-gradient(175deg, #0a0a0a 0%, #090909 100%);">
            <!-- 顶部信息区域 -->
            <div class="flex gap-3 p-4">
                <!-- 左侧：基本信息 -->
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
                <!-- 右侧：尺寸参数 -->
                <div class="flex-1 brabus-panel">
                    <div class="brabus-panel-header flex items-center gap-2">
                        <span class="text-[#353535]">${svgIcon('ruler')}</span>
                        <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">尺寸参数</span>
                    </div>
                    <table class="w-full">${rowsRight.map(detailTableRow).join('')}</table>
                </div>
            </div>

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
