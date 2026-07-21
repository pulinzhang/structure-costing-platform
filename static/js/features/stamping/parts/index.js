/**
 * Parts Page
 * 零件列表页面逻辑 — Brabus Dark Industrial
 */

import { partsTemplate } from './template.js';
// esc / fmtNum 已通过 window 导出；window.svgIcon 通过 window.window.svgIcon 访问

const PARTS_CONFIG = {
    DEFAULT_PAGE_SIZE: 10,
    PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
    SEARCH_DEBOUNCE_MS: 400,
    STORAGE_KEY: 'parts_page_size',
};

const partsState = {
    currentPage: 1,
    pageSize: 10,
    isLoading: false,
    searchTimer: null,
    vehicleOptions: [],
    versionOptions: [],
};

export const PartsPage = {
    /**
     * 初始化零件列表页面
     */
    init() {
        this.initState();
        this.bindEvents();
        this.bindDrawerEvents();
        this.loadParts(1);
    },

    /**
     * 初始化状态
     */
    initState() {
        const savedSize = localStorage.getItem(PARTS_CONFIG.STORAGE_KEY);
        partsState.pageSize = PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(parseInt(savedSize))
            ? parseInt(savedSize)
            : PARTS_CONFIG.DEFAULT_PAGE_SIZE;

        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) pageSizeSelect.value = partsState.pageSize;
    },

    /**
     * 绑定事件（使用 #pageContent 事件委托，避免 innerHTML 重建丢失监听器）
     */
    bindEvents() {
        const pageContent = document.getElementById('pageContent');

        // 搜索输入（防抖）
        pageContent?.addEventListener('input', (e) => {
            if (!e.target.matches('#searchInput')) return;
            clearTimeout(partsState.searchTimer);
            partsState.searchTimer = setTimeout(() => this.loadParts(1), PARTS_CONFIG.SEARCH_DEBOUNCE_MS);
        });

        // 车型筛选 → 联动：选中车型后重置版本下拉，再重新加载
        pageContent?.addEventListener('change', (e) => {
            if (e.target.id === 'vehicleModelFilter') {
                const versionFilter = document.getElementById('versionFilter');
                if (versionFilter) versionFilter.value = '';
                this.loadParts(1);
            }
            if (e.target.id === 'versionFilter') this.loadParts(1);
        });

        // 每页条数
        pageContent?.addEventListener('change', (e) => {
            if (!e.target.matches('#pageSizeSelect')) return;
            const newSize = parseInt(e.target.value, 10);
            if (newSize && PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(newSize)) {
                partsState.pageSize = newSize;
                localStorage.setItem(PARTS_CONFIG.STORAGE_KEY, String(newSize));
                this.loadParts(1);
            }
        });

        // 操作按钮（查看 / 删除）
        pageContent?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            const id = Number(btn.getAttribute('data-id'));
            const action = btn.getAttribute('data-action');
            if (action === 'detail') this.showDetail(id);
            else if (action === 'delete') this.deletePart(id);
        });

        // 分页按钮（事件委托到 #pageContent，彻底解决 innerHTML 重建后监听器丢失问题）
        pageContent?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-page]');
            if (!btn || btn.disabled) return;
            const targetPage = parseInt(btn.getAttribute('data-page'), 10);
            if (!Number.isNaN(targetPage) && targetPage >= 1) this.loadParts(targetPage);
        });
    },

    /**
     * 加载零件列表
     */
    async loadParts(page = 1) {
        if (partsState.isLoading) return;
        partsState.isLoading = true;
        partsState.currentPage = page;

        const searchInput = document.getElementById('searchInput');
        const vehicleModelFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');
        const totalCount = document.getElementById('totalCount');
        const partsTableBody = document.getElementById('partsTableBody');
        const pagination = document.getElementById('pagination');

        const params = {
            page: page,
            size: partsState.pageSize,
        };

        const partNumber = searchInput?.value.trim();
        const vehicleModel = vehicleModelFilter?.value;
        const version = versionFilter?.value;
        if (partNumber) params.part_number = partNumber;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        if (version) params.version = version;

        try {
            const result = await HttpClient.get('/api/stamping/parts/list', { params });
            const pageInfo = result.data?.data ?? result.data ?? {};


            // 联动：更新车型 / 版本下拉选项
            this.updateFilterOptions(pageInfo.filters);

            this.renderParts(pageInfo.list || []);
            this.renderPagination(pageInfo);
            if (totalCount) totalCount.textContent = `共 ${pageInfo.total || 0} 个零件`;
        } catch (error) {
            console.error('加载零件列表失败:', error);
            if (partsTableBody) {
                partsTableBody.innerHTML = `
                    <tr><td colspan="9">
                        <div class="p-4 bg-[#0a0a0a] border border-[#2c2c2c] text-[#d32f2f] text-xs text-center">
                            加载失败: ${esc(error.message)}
                        </div>
                    </td></tr>
                `;
            }
        } finally {
            partsState.isLoading = false;
        }
    },

    /**
     * 更新筛选下拉选项（联动）
     */
    updateFilterOptions(filters = {}) {
        const vehicleFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');

        // 记录当前选中值
        const currentVehicle = vehicleFilter?.value || '';
        const currentVersion = versionFilter?.value || '';

        // 更新车型下拉（避免重复添加）
        if (vehicleFilter && filters.vehicle_models) {
            const savedVehicle = vehicleFilter.value;
            vehicleFilter.innerHTML = `<option value="">全部车型</option>` +
                filters.vehicle_models.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
            vehicleFilter.value = savedVehicle || currentVehicle;
        }

        // 更新版本下拉（根据当前选中的车型过滤版本）
        if (versionFilter && filters.versions) {
            const versionsToShow = filters.versions;
            versionFilter.innerHTML = `<option value="">全部版本</option>` +
                versionsToShow.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
            versionFilter.value = currentVersion;
        }
    },

    /**
     * 渲染零件列表
     */
    renderParts(parts) {
        const partsTableBody = document.getElementById('partsTableBody');
        if (!partsTableBody) return;

        if (!parts || parts.length === 0) {
            partsTableBody.innerHTML = `
                <tr><td colspan="9">
                    <div class="flex flex-col items-center justify-center py-14">
                        <div class="w-10 h-10 bg-[#262626] flex items-center justify-center mb-3">
                            <svg class="w-5 h-5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                        </div>
                        <h5 class="text-xs font-medium text-[#9e9e9e] mb-1">暂无零件数据</h5>
                        <p class="text-[11px] text-[#616161]">请联系管理员导入工艺文件</p>
                    </div>
                </td></tr>
            `;
            return;
        }

        partsTableBody.innerHTML = parts.map((part, index) => this.renderRow(part, index)).join('');
    },

    /**
     * 渲染单行
     */
    renderRow(part, index) {
        const thickness = fmtNum(part.thickness, 2);
        const partWeight = fmtNum(part.part_weight, 3);
        const processCount = part.process_count != null ? part.process_count : '—';
        const sketchUrl = part.sketch_url || '';

        const thumbnailCell = sketchUrl
            ? `<div class="sketch-thumbnail" onclick="PartsPage.showDetail(${part.id})" title="点击查看详情">
                    <img src="/uploads/${esc(sketchUrl)}" alt="零件图纸" onerror="this.style.display='none';this.nextElementSibling&&(this.nextElementSibling.style.display='flex')">
                    <div class="zoom-overlay">
                        ${window.svgIcon('search')}
                    </div>
               </div>`
            : `<div class="sketch-thumbnail-placeholder" onclick="PartsPage.showDetail(${part.id})" title="点击查看详情">
                    ${window.svgIcon('file-earmark')}
               </div>`;

        return `
            <tr class="group border-b border-[#222222] hover:bg-[rgba(255,255,255,0.02)] transition-colors duration-100">
                <td class="px-4 py-3.5">
                    <div class="flex items-center justify-center">
                        ${thumbnailCell}
                    </div>
                </td>
                <td class="px-4 py-3.5">
                    <span class="text-xs font-semibold text-white font-mono tracking-wide">${esc(part.part_number)}</span>
                </td>
                <td class="px-4 py-3.5 text-xs text-[#9e9e9e]">${esc(part.part_name) || '—'}</td>
                <td class="px-4 py-3.5 text-center">
                    <span class="inline-block px-2 py-0.5 bg-[#262626] text-[10px] font-semibold uppercase tracking-wider text-[#9e9e9e] rounded-sm">${esc(part.vehicle_model) || '—'}</span>
                </td>
                <td class="px-4 py-3.5 text-center text-xs text-[#616161]">${esc(part.version) || '—'}</td>
                <td class="px-4 py-3.5 text-xs text-[#9e9e9e]">${esc(part.material) || '—'}</td>
                <td class="px-4 py-3.5 table-num-cell">${thickness}</td>
                <td class="px-4 py-3.5 table-num-cell">${partWeight}</td>
                <td class="px-4 py-3.5 table-num-cell">${processCount}</td>
                <td class="px-4 py-3.5">
                    <div class="flex items-center justify-center gap-1">
                        <button class="table-action-btn" data-action="detail" data-id="${part.id}" title="查看详情">
                            ${window.svgIcon('eye')}
                        </button>
                        <button class="table-action-btn" data-action="delete" data-id="${part.id}" title="删除">
                            ${window.svgIcon('trash')}
                        </button>
                    </div>
                </td>
            </tr>
        `;
    },

    /**
     * 渲染分页
     */
    renderPagination(pageInfo) {
        const { total, page, total_pages, has_next, has_prev } = pageInfo;
        const pagination = document.getElementById('pagination');
        if (!pagination) return;

        if (!total_pages || total_pages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        const win = 2;
        const pages = new Set([1, total_pages]);
        for (let i = Math.max(1, page - win); i <= Math.min(total_pages, page + win); i++) {
            pages.add(i);
        }
        const sortedPages = Array.from(pages).sort((a, b) => a - b);

        let html = `
            <nav class="flex items-center justify-center gap-1">
                <button class="p-2 text-[#616161] hover:text-white hover:bg-[#262626] disabled:opacity-30 disabled:pointer-events-none transition-all duration-150 rounded-sm"
                        data-page="${page - 1}" ${!has_prev ? 'disabled' : ''}>
                    ${window.svgIcon('chevron-left')}
                </button>
        `;

        let lastPage = 0;
        for (const p of sortedPages) {
            if (lastPage && p - lastPage > 1) {
                html += `<span class="px-2 text-[#616161]">...</span>`;
            }
            const isActive = p === page;
            html += `
                <button class="min-w-[2rem] h-8 px-2 text-xs font-medium rounded-sm transition-all duration-150
                    ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#9e9e9e] hover:text-white hover:bg-[#262626]'}"
                    data-page="${p}">
                    ${p}
                </button>
            `;
            lastPage = p;
        }

        html += `
            <button class="p-2 text-[#616161] hover:text-white hover:bg-[#262626] disabled:opacity-30 disabled:pointer-events-none transition-all duration-150 rounded-sm"
                    data-page="${page + 1}" ${!has_next ? 'disabled' : ''}>
                ${window.svgIcon('chevron-right')}
            </button>
            </nav>
        `;

        pagination.innerHTML = html;
    },

    /**
     * 显示详情（使用自定义抽屉）
     */
    async showDetail(partId) {
        const drawer = document.getElementById('partDrawer');
        const backdrop = document.getElementById('partDrawerBackdrop');
        const contentEl = document.getElementById('partDrawerContent');
        const titleEl = document.getElementById('partDrawerTitle');

        if (!drawer || !contentEl) {
            console.error('抽屉元素不存在');
            return;
        }

        // 设置标题
        if (titleEl) titleEl.textContent = '零件详情';

        // 显示加载状态
        contentEl.innerHTML = `
            <div class="flex items-center justify-center py-16">
                <div class="w-7 h-7 border-2 border-[#2a2a2a] border-t-[#d32f2f] rounded-full animate-spin"></div>
            </div>
        `;

        // 显示抽屉
        drawer.style.display = 'flex';
        backdrop && (backdrop.style.display = 'block');
        requestAnimationFrame(() => drawer.classList.remove('translate-x-full'));

        try {
            const result = await HttpClient.get(`/api/stamping/parts/${partId}`);
            const part = result.data?.data ?? result.data ?? result;
            contentEl.innerHTML = this.renderDetailContent(part);

            // 重置保存按钮为未激活状态
            const btn = document.getElementById('saveProcessBtn');
            if (btn) {
                btn.dataset.active = 'false';
                btn.className = 'btn-save-default';
            }

            // 绑定工序表格行内编辑事件
            this._bindProcessEditEvents(part.id);

            // 绑定图纸查看按钮
            this._bindSketchModal(part);

        } catch (error) {
            contentEl.innerHTML = `
                <div class="p-4 m-4 bg-[#0a0a0a] border border-[#2c2c2c]">
                    <div class="flex items-center gap-2 text-[#d32f2f]">
                        ${window.svgIcon('exclamation-circle')}
                        <span class="text-xs font-medium">${esc(error.message) || '加载失败'}</span>
                    </div>
                </div>
            `;
        }
    },

    /**
     * 渲染详情抽屉内容（与模态框共用同一套模板）
     */
    renderDetailContent(part) {
        const sketchUrl = part.sketch_url || '';
        const fullSketchUrl = sketchUrl ? `/uploads/${sketchUrl}` : '';

        const rows = [
            ['零件号', esc(part.part_number)],
            ['零件名称', esc(part.part_name)],
            ['车型', esc(part.vehicle_model)],
            ['版本', esc(part.version)],
            ['材料', esc(part.material)],
            ['厚度', part.thickness != null ? `${part.thickness} mm` : '-'],
        ];
        const rowsRight = [
            ['重量', part.part_weight != null ? `${part.part_weight} kg` : '-'],
            ['板材尺寸', (part.sheet_length && part.sheet_width) ? `${part.sheet_length}x${part.sheet_width}` : '-'],
            ['每辆车用量', esc(part.parts_per_sheet)],
            ['板材类型', esc(part.sheet_type)],
            ['吨位', part.tonnage ? `${part.tonnage}T` : '-'],
            ['模具类型', esc(part.die_type)],
        ];
        // 核心成本字段 → Brabus 红高亮
        const coreCostFields = new Set(['重量', '吨位', '模具类型']);
        const tableRow = ([label, value], valueClass = '') => {
            const isCore = coreCostFields.has(label);
            const tdClass = isCore
                ? 'text-[11px] font-mono font-semibold text-[#d32f2f] tracking-[0.05em]'
                : `text-[11px] text-[#6b6b6b] tracking-wider ${valueClass}`;
            return `
            <tr class="border-b border-[#161616] last:border-b-0">
                <th class="px-4 py-3 text-left text-[9px] font-medium uppercase tracking-[0.18em] text-[#4d4d4d] w-28">${label}</th>
                <td class="px-4 py-3 ${tdClass}" ${isCore ? 'style="text-shadow:0 0 10px rgba(211,47,47,0.3)"' : ''}>${value}</td>
            </tr>`;
        };

        // 模具类型选项（与成本系数对应）
        const dieTypeOptions = [
            { value: 'progressive', label: '级进模（80%）' },
            { value: 'single', label: '单干模具（100%）' },
            { value: 'shared', label: '共模（50%）' },
            { value: 'progressive_shared', label: '级进共模（40%）' },
        ];
        // 根据 cost_ratio 反查 die_type（数据库只存 cost_ratio）
        const ratioToDieType = { 0.8: 'progressive', 1.0: 'single', 0.5: 'shared', 0.4: 'progressive_shared' };
        const deriveDieType = (p) => {
            if (p.die_type) return p.die_type;
            return ratioToDieType[p.cost_ratio] || 'single';
        };

        // 工序行（可编辑）
        const processes = part.processes || [];
        const processRows = processes.length
            ? processes.map((p, idx) => {
                const processId = p.id ?? idx;
                const dieTypeVal = deriveDieType(p);
                return `
                <tr class="border-b border-[#161616] last:border-b-0 group hover:bg-[#0e0e0e] transition-colors duration-200 process-row" data-process-id="${processId}">
                    <td class="px-4 py-4 text-[10px] text-[#4a4a4a] font-mono tracking-[0.06em]">${p.process_order ?? '—'}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-mono tracking-[0.06em]">${esc(p.process_seq)}</td>
                    <td class="px-4 py-4 text-[11px] text-[#888888] font-medium tracking-[0.05em]">${esc(p.process_code)}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-[#777777] tracking-[0.06em]">${p.die_sets ?? '—'}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-[#777777] tracking-[0.06em]">${p.tonnage ? `${p.tonnage}T` : '—'}</td>
                    <td class="px-4 py-4">
                        <select
                            class="die-type-select"
                            data-process-id="${processId}"
                            data-field="die_type">
                            ${dieTypeOptions.map(o => `
                                <option value="${o.value}" ${o.value === dieTypeVal ? 'selected' : ''}>${o.label}</option>
                            `).join('')}
                        </select>
                    </td>
                </tr>`;
            }).join('')
            : `<tr><td colspan="6" class="px-4 py-12 text-center text-[11px] text-[#333333] tracking-[0.15em]">暂无工序数据</td></tr>`;

        return `
            <div class="flex flex-col h-full" style="background: linear-gradient(175deg, #0a0a0a 0%, #090909 100%);">
                <!-- 顶部信息区域 -->
                <div class="flex gap-3 p-4">
                    <!-- 左侧：基本信息 -->
                    <div class="flex-1" style="background:#111111; border-top:1px solid #282828; border-left:1px solid #262626; border-right:1px solid #181818; border-bottom:1px solid #101010; box-shadow:2px 2px 8px rgba(0,0,0,0.5), -1px -1px 0 rgba(255,255,255,0.015) inset; overflow:hidden;">
                        <div class="px-4 py-3 flex items-center justify-between" style="background:#0c0c0c; border-bottom:1px solid #181818;">
                            <div class="flex items-center gap-2">
                                <span class="text-[#353535]">${window.svgIcon('info-circle')}</span>
                                <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">基本信息</span>
                            </div>
                            ${sketchUrl ? `
                            <button type="button" id="openSketchModal" class="flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[9px] text-[#333333] hover:text-[#888888] border transition-all duration-200 tracking-wide group" style="border-color:#1c1c1c; hover:border-color:#2e2e2e;">
                                <svg class="w-3.5 h-3.5 text-[#2d2d2d] group-hover:text-[#888888] transition-colors duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M12 12l3-3m0 0l3 3m-3-3v9" />
                                </svg>
                                <span class="group-hover:text-[#555555] transition-colors duration-200">查看图纸</span>
                            </button>` : ''}
                        </div>
                        <table class="w-full">${rows.map(r => tableRow(r, false)).join('')}</table>
                    </div>
                    <!-- 右侧：补充信息 -->
                    <div class="flex-1" style="background:#111111; border-top:1px solid #282828; border-left:1px solid #262626; border-right:1px solid #181818; border-bottom:1px solid #101010; box-shadow:2px 2px 8px rgba(0,0,0,0.5), -1px -1px 0 rgba(255,255,255,0.015) inset; overflow:hidden;">
                        <div class="px-4 py-3 flex items-center gap-2" style="background:#0c0c0c; border-bottom:1px solid #181818;">
                            <span class="text-[#353535]">${window.svgIcon('ruler')}</span>
                            <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">尺寸参数</span>
                        </div>
                        <table class="w-full">${rowsRight.map(r => tableRow(r)).join('')}</table>
                    </div>
                </div>

                <!-- 工序列表（无图纸块，顶部直接衔接） -->
                <div class="flex-1 mx-4 mb-4 flex flex-col min-h-0 shrink-0" style="max-height: calc(100vh - 420px);">
                    <div class="px-4 py-3 flex items-center justify-between shrink-0" style="background:#0c0c0c; border-top:1px solid #262626; border-left:1px solid #282828; border-right:1px solid #181818; border-bottom:1px solid #161616; box-shadow:2px 2px 8px rgba(0,0,0,0.4), -1px 0 0 rgba(255,255,255,0.012) inset;">
                        <div class="flex items-center gap-2">
                            <span class="text-[#353535]">${window.svgIcon('list-ol')}</span>
                            <span class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.22em]">工序列表</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <select id="batchDieTypeSelect" class="die-type-select" style="width:148px;">
                                <option value="">批量修改模具类型</option>
                                ${dieTypeOptions.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
                            </select>
                            <button type="button" id="applyBatchDieType" class="h-9 px-4 text-[10px] bg-[#111111] text-[#555555] border-none focus:outline-none rounded-sm transition-all duration-200 hover:text-[#d32f2f] hover:shadow-[0_0_10px_rgba(211,47,47,0.1)] tracking-wide">
                                批量应用
                            </button>
                        </div>
                    </div>
                    <div class="flex-1 overflow-y-auto flex flex-col" style="background:#111111; border-left:1px solid #252525; border-right:1px solid #161616; border-bottom:1px solid #0f0f0f; box-shadow:3px 3px 12px rgba(0,0,0,0.6), -1px 0 0 rgba(255,255,255,0.01) inset; scrollbar-width:thin; scrollbar-color:#1e1e1e #090909;">
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
                            <tbody id="processTableBody" style="background:#111111;">${processRows}</tbody>
                        </table>
                    </div>
                </div>

                <!-- 保存按钮与规则栏 -->
                ${processes.length > 0 ? `
                <div class="mx-4 mb-4 mt-auto shrink-0">
                    <!-- 规则铭牌 -->
                    <div class="flex items-center justify-center gap-3 py-2.5 mb-3" style="background:#080808; border:1px solid #141414; box-shadow:0 1px 0 rgba(255,255,255,0.02) inset, 0 2px 6px rgba(0,0,0,0.5);">
                        <span class="text-[8px] text-[#2e2e2e] tracking-[0.2em] uppercase">成本规则</span>
                        <span class="text-[8px] text-[#1e1e1e]">•</span>
                        <span class="text-[10px] text-[#444444]"><span class="text-[#666666] font-medium tracking-wide">级进模</span> <span class="text-[#d32f2f] font-semibold tracking-wider">80%</span></span>
                        <span class="text-[8px] text-[#1e1e1e]">•</span>
                        <span class="text-[10px] text-[#444444]"><span class="text-[#666666] font-medium tracking-wide">单干模具</span> <span class="text-[#d32f2f] font-semibold tracking-wider">100%</span></span>
                        <span class="text-[8px] text-[#1e1e1e]">•</span>
                        <span class="text-[10px] text-[#444444]"><span class="text-[#666666] font-medium tracking-wide">共模</span> <span class="text-[#d32f2f] font-semibold tracking-wider">50%</span></span>
                        <span class="text-[8px] text-[#1e1e1e]">•</span>
                        <span class="text-[10px] text-[#444444]"><span class="text-[#666666] font-medium tracking-wide">级进共模</span> <span class="text-[#d32f2f] font-semibold tracking-wider">40%</span></span>
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
    },

    /**
     * 绑定图纸查看模态框
     */
    _bindSketchModal(part) {
        const sketchUrl = part.sketch_url || '';
        const fullSketchUrl = sketchUrl ? `/uploads/${sketchUrl}` : '';
        if (!sketchUrl) return;

        document.getElementById('openSketchModal')?.addEventListener('click', () => {
            const modal = document.createElement('div');
            modal.id = 'sketchModal';
            modal.className = 'fixed inset-0 z-[100] flex items-center justify-center';
            modal.innerHTML = `
                <div class="absolute inset-0 bg-black/90 backdrop-blur-sm" id="sketchModalBackdrop"></div>
                <div class="relative z-10 max-w-4xl w-full mx-8 max-h-[85vh] flex flex-col">
                    <button type="button" id="closeSketchModal" class="absolute -top-10 right-0 flex items-center gap-1.5 text-[10px] text-[#555555] hover:text-white transition-colors tracking-wider group">
                        <span class="group-hover:text-[#d32f2f] transition-colors">关闭</span>
                        <svg class="w-3.5 h-3.5 group-hover:text-[#d32f2f] transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                    <div class="flex-1 overflow-auto bg-[#0d0d0d] border border-[#222222] rounded-sm shadow-2xl">
                        <img src="${fullSketchUrl}" alt="零件图纸" class="w-full h-full object-contain">
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            const closeModal = () => {
                modal.style.opacity = '0';
                modal.style.transition = 'opacity 200ms ease-out';
                setTimeout(() => modal.remove(), 200);
            };

            document.getElementById('closeSketchModal')?.addEventListener('click', closeModal);
            document.getElementById('sketchModalBackdrop')?.addEventListener('click', closeModal);
            const escHandler = (e) => {
                if (e.key === 'Escape') { closeModal(); document.removeEventListener('keydown', escHandler); }
            };
            document.addEventListener('keydown', escHandler);
        });
    },

    /**
     * 绑定工序表格行内编辑事件
     */
    _bindProcessEditEvents(partId) {
        const tbody = document.getElementById('processTableBody');
        if (!tbody) return;

        // 模具类型下拉变化 → 激活保存按钮
        tbody.addEventListener('change', (e) => {
            const sel = e.target.closest('.die-type-select');
            if (!sel) return;
            this._activateSaveButton();
        });

        // 批量修改模具类型
        document.getElementById('applyBatchDieType')?.addEventListener('click', () => {
            const batchVal = document.getElementById('batchDieTypeSelect')?.value;
            if (!batchVal) return;
            tbody.querySelectorAll('.die-type-select').forEach(sel => {
                sel.value = batchVal;
                sel.dispatchEvent(new Event('change'));
            });
        });

        // 保存修改
        document.getElementById('saveProcessBtn')?.addEventListener('click', async () => {
            await this._saveProcessEdits(partId);
        });
    },

    /**
     * 激活保存按钮（感知到用户修改时调用）
     */
    _activateSaveButton() {
        const btn = document.getElementById('saveProcessBtn');
        if (!btn || btn.dataset.active === 'true') return;
        btn.dataset.active = 'true';
        btn.className = 'btn-save-active';
    },

    /**
     * 收集所有工序编辑数据
     */
    _collectProcessEdits() {
        const ratioMap = { progressive: 0.8, single: 1.0, shared: 0.5, progressive_shared: 0.4 };
        const tbody = document.getElementById('processTableBody');
        if (!tbody) return [];
        const rows = tbody.querySelectorAll('.process-row');
        return Array.from(rows).map(row => {
            const processId = row.dataset.processId;
            const sel = row.querySelector('.die-type-select');
            const dieType = sel?.value ?? 'single';
            const costRatio = ratioMap[dieType] ?? 1.0;
            return { id: parseInt(processId), cost_ratio: costRatio };
        });
    },

    /**
     * 保存工序修改
     */
    async _saveProcessEdits(partId) {
        const btn = document.getElementById('saveProcessBtn');
        const processes = this._collectProcessEdits();
        console.log('[DEBUG] 提交工序数据:', JSON.stringify(processes, null, 2));
        if (processes.length === 0) return;
        btn.disabled = true;
        btn.innerHTML = `<svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>保存中...`;
        try {
            const response = await HttpClient.put(`/api/stamping/parts/${partId}/processes`, processes);
            console.log('[DEBUG] 保存成功:', response);
            showToast('工序参数已保存', 'success');
            const btn = document.getElementById('saveProcessBtn');
            if (btn) {
                btn.dataset.active = 'false';
                btn.className = 'btn-save-default';
            }
            this.loadParts(partsState.currentPage);
            this.showDetail(partId);
        } catch (error) {
            console.error('保存失败:', error);
            showToast(error.message || '保存失败', 'danger');
            btn.disabled = false;
            btn.innerHTML = `<span class="tracking-[0.2em]">保存</span>`;
        }
    },

    /**
     * 删除零件
     */
    async deletePart(partId) {
        if (!confirm('确定要删除这个零件吗？')) return;
        try {
            await HttpClient.delete(`/api/stamping/parts/${partId}`);
            showToast('删除成功', 'success');
            this.loadParts(partsState.currentPage);
        } catch (error) {
            console.error('删除失败:', error);
            showToast(error.message || '删除失败', 'danger');
        }
    },

    /**
     * 绑定抽屉事件（详情抽屉、图纸预览抽屉）
     */
    bindDrawerEvents() {
        // 关闭详情抽屉
        document.getElementById('closePartDrawer')?.addEventListener('click', () => {
            const drawer = document.getElementById('partDrawer');
            const backdrop = document.getElementById('partDrawerBackdrop');
            if (!drawer) return;
            drawer.classList.add('translate-x-full');
            if (backdrop) backdrop.style.display = 'none';
            drawer.addEventListener('transitionend', () => {
                drawer.style.display = 'none';
            }, { once: true });
        });

        // 点击遮罩关闭详情抽屉
        document.getElementById('partDrawerBackdrop')?.addEventListener('click', () => {
            const drawer = document.getElementById('partDrawer');
            const backdrop = document.getElementById('partDrawerBackdrop');
            if (!drawer) return;
            drawer.classList.add('translate-x-full');
            if (backdrop) backdrop.style.display = 'none';
            drawer.addEventListener('transitionend', () => {
                drawer.style.display = 'none';
            }, { once: true });
        });

        // ESC 键关闭详情抽屉或图片预览
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // 优先关闭图片预览
                const previewModal = document.getElementById('imagePreviewModal');
                if (previewModal && previewModal.style.display !== 'none') {
                    this.closeImagePreview();
                    return;
                }
                // 其次关闭详情抽屉
                const drawer = document.getElementById('partDrawer');
                const backdrop = document.getElementById('partDrawerBackdrop');
                if (drawer && drawer.style.display !== 'none') {
                    drawer.classList.add('translate-x-full');
                    if (backdrop) backdrop.style.display = 'none';
                    drawer.addEventListener('transitionend', () => {
                        drawer.style.display = 'none';
                    }, { once: true });
                }
            }
        });

        // 关闭图纸预览抽屉（已移除，改用详情抽屉）
    },
};

/**
 * 页面导出 - 用于 app.js 注册
 */
export const pageConfig = {
    render: partsTemplate,
    init: () => PartsPage.init(),
};
