/**
 * Parts Page
 * 零件列表页面逻辑 — Brabus Dark Industrial
 */

import { partsTemplate, renderDetailContent } from './template.js';
// esc / fmtNum / svgIcon / showToast / HttpClient 由 main.js 挂到 window

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
};

export const PartsPage = {
    /**
     * 初始化零件列表页面
     */
    init() {
        this.initState();
        this.bindEvents();
        this.bindDrawerEvents();
        this.applyPermissionUi();
        this.loadParts(1);
    },

    applyPermissionUi() {
        const canUpdate = typeof can === 'function' ? can('op:stamping-parts:update') : true;
        this.canUpdate = canUpdate;
        this.canDelete = typeof can === 'function' ? can('op:stamping-parts:delete') : true;
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
            if (e.target.id === 'locationFilter') {
                const supplierFilter = document.getElementById('supplierFilter');
                const vehicleModelFilter = document.getElementById('vehicleModelFilter');
                const versionFilter = document.getElementById('versionFilter');
                if (supplierFilter) supplierFilter.value = '';
                if (vehicleModelFilter) vehicleModelFilter.value = '';
                if (versionFilter) versionFilter.value = '';
                this.loadParts(1);
            }
            if (e.target.id === 'supplierFilter') {
                const vehicleModelFilter = document.getElementById('vehicleModelFilter');
                const versionFilter = document.getElementById('versionFilter');
                if (vehicleModelFilter) vehicleModelFilter.value = '';
                if (versionFilter) versionFilter.value = '';
                this.loadParts(1);
            }
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
        const locationFilter = document.getElementById('locationFilter');
        const supplierFilter = document.getElementById('supplierFilter');
        const vehicleModelFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');
        const totalCount = document.getElementById('totalCount');
        const partsTableBody = document.getElementById('partsTableBody');

        const params = {
            page: page,
            size: partsState.pageSize,
        };

        const partNumber = searchInput?.value.trim();
        const location = locationFilter?.value;
        const supplier = supplierFilter?.value;
        const vehicleModel = vehicleModelFilter?.value;
        const version = versionFilter?.value;
        if (partNumber) params.part_number = partNumber;
        if (location) params.location = location;
        if (supplier) params.stamping_supplier = supplier;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        if (version) params.version = version;

        try {
            const resp = await HttpClient.get('/api/stamping/parts/list', { params });
            // HttpClient 对 success:true 的响应返回 { ok, data: ApiResponse.data, message }
            // 后端 data 字段即 PageResult，故 resp.data 已是 PageResult
            const pageInfo = resp.data ?? {};
            const items = pageInfo.items || [];
            const total = pageInfo.total ?? 0;
            const totalPages = pageInfo.total_pages ?? 1;
            const hasNext = pageInfo.has_next ?? false;
            const hasPrev = pageInfo.has_prev ?? false;

            // 联动：更新筛选下拉选项
            this.updateFilterOptions(pageInfo.filters);

            this.renderParts(items);
            this.renderPagination({ total, page, total_pages: totalPages, has_next: hasNext, has_prev: hasPrev });
            if (totalCount) totalCount.textContent = `共 ${total} 个零件`;
        } catch (error) {
            console.error('加载零件列表失败:', error);
            if (partsTableBody) {
                partsTableBody.innerHTML = `
                <tr><td colspan="13">
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
        const locationFilter = document.getElementById('locationFilter');
        const supplierFilter = document.getElementById('supplierFilter');
        const vehicleFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');

        // 记录当前选中值
        const currentLocation = locationFilter?.value || '';
        const currentSupplier = supplierFilter?.value || '';
        const currentVehicle = vehicleFilter?.value || '';
        const currentVersion = versionFilter?.value || '';

        // 更新基地下拉
        if (locationFilter && filters.locations) {
            locationFilter.innerHTML = `<option value="">全部基地</option>` +
                filters.locations.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
            locationFilter.value = currentLocation;
        }

        // 更新供应商下拉（后端字段名: stamping_suppliers）
        if (supplierFilter && filters.stamping_suppliers) {
            supplierFilter.innerHTML = `<option value="">全部供应商</option>` +
                filters.stamping_suppliers.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
            supplierFilter.value = currentSupplier;
        }

        // 更新车型下拉（后端字段名: vehicle_models）
        if (vehicleFilter && filters.vehicle_models) {
            vehicleFilter.innerHTML = `<option value="">全部车型</option>` +
                filters.vehicle_models.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
            vehicleFilter.value = currentVehicle;
        }

        // 更新版本下拉（后端字段名: versions）
        if (versionFilter && filters.versions) {
            versionFilter.innerHTML = `<option value="">全部版本</option>` +
                filters.versions.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
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
                <tr><td colspan="13">
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
    renderRow(part) {
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
                <td class="px-4 py-3.5 text-center text-xs text-[#616161]">${esc(part.location) || '—'}</td>
                <td class="px-4 py-3.5 text-left text-xs text-[#9e9e9e]">${esc(part.stamping_supplier) || '—'}</td>
                <td class="px-4 py-3.5 text-center">
                    <span class="inline-block px-2 py-0.5 bg-[#262626] text-[10px] font-semibold uppercase tracking-wider text-[#9e9e9e] rounded-sm">${esc(part.vehicle_model) || '—'}</span>
                </td>
                <td class="px-4 py-3.5 text-center text-xs text-[#616161]">${esc(part.version) || '—'}</td>
                <td class="px-4 py-3.5 text-xs text-[#9e9e9e]">${esc(part.material) || '—'}</td>
                <td class="px-4 py-3.5 table-num-cell">${thickness}</td>
                <td class="px-4 py-3.5 table-num-cell">${partWeight}</td>
                <td class="px-4 py-3.5 table-num-cell">${processCount}</td>
                <td class="px-4 py-3.5 text-xs text-[#777777]">${esc(part.excel_filename) || '—'}</td>
                <td class="px-4 py-3.5">
                    <div class="flex items-center justify-center gap-1">
                        <button class="table-action-btn" data-action="detail" data-id="${part.id}" title="查看详情">
                            ${window.svgIcon('eye')}
                        </button>
                        ${this.canDelete !== false ? `
                        <button class="table-action-btn" data-action="delete" data-id="${part.id}" title="删除">
                            ${window.svgIcon('trash')}
                        </button>` : ''}
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
     * 渲染详情抽屉内容（模板逻辑见 ./template.js: renderDetailContent）
     */
    renderDetailContent(part) {
        return renderDetailContent(part);
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
                        ${window.svgIcon('x-lg', 'w-3.5 h-3.5 group-hover:text-[#d32f2f] transition-colors')}
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

        const canUpdate = this.canUpdate !== false;

        if (!canUpdate) {
            tbody.querySelectorAll('.die-type-select').forEach((sel) => {
                sel.disabled = true;
            });
            document.getElementById('applyBatchDieType')?.classList.add('hidden');
            document.getElementById('batchDieTypeSelect')?.closest('div')?.classList.add('opacity-40', 'pointer-events-none');
            document.getElementById('saveProcessBtn')?.classList.add('hidden');
            return;
        }

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
        if (this.canUpdate === false) {
            showToast('无编辑权限', 'warning');
            return;
        }
        const btn = document.getElementById('saveProcessBtn');
        const processes = this._collectProcessEdits();
        if (processes.length === 0) return;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-2">${window.svgIcon('spinner', 'w-3.5 h-3.5 animate-spin')}保存中...</span>`;
        try {
            const response = await HttpClient.put(`/api/stamping/parts/${partId}/processes`, processes);
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
        if (this.canDelete === false) {
            showToast('无删除权限', 'warning');
            return;
        }
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
