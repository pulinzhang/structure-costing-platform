/**
 * Parts Page
 * 零件列表 —对齐加工费计算结果列表：进入即加载、筛选均可选、级联联动、批量删除
 * 明细抽屉逻辑保持不变
 */

import {
    partsTemplate,
    renderDetailContent,
    updatePartsFilterCapsules,
    updatePartsHud,
    renderPartsPagination,
} from './template.js?v=19';
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    bindPageSizeSelect,
    normalizePageSize,
} from '../../../../page-size.js?v=2';

const CASCADE_API = '/api/stamping/filters/cascade';
const PARTS_API = '/api/stamping/parts';

const PARTS_CONFIG = {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    STORAGE_KEY: 'parts_page_size',
};

const partsState = {
    currentPage: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    isLoading: false,
    advancedOpen: false,
};

export const PartsPage = {
    init() {
        this.initState();
        this.bindEvents();
        this.bindDrawerEvents();
        this.applyPermissionUi();
        this.loadCascadeFilters().then(() => this.loadParts(1));
    },

    applyPermissionUi() {
        this.canUpdate = typeof can === 'function' ? can('op:stamping-parts:update') : true;
        this.canDelete = typeof can === 'function' ? can('op:stamping-parts:delete') : true;
        this.canExport = typeof can === 'function' ? can('op:stamping-parts:export') : true;
        if (!this.canDelete) {
            document.getElementById('partsBatchDeleteBtn')?.classList.add('hidden');
        }
        if (!this.canExport) {
            document.getElementById('partsExportBtn')?.classList.add('hidden');
        }
    },

    initState() {
        const savedSize = localStorage.getItem(PARTS_CONFIG.STORAGE_KEY);
        partsState.pageSize = normalizePageSize(savedSize);

        bindPageSizeSelect('partsPageSize', {
            getSize: () => partsState.pageSize,
            setSize: (size) => {
                partsState.pageSize = size;
                localStorage.setItem(PARTS_CONFIG.STORAGE_KEY, String(size));
            },
            onChange: () => this.loadParts(1),
        });
    },

    setAdvancedOpen(isOpen) {
        partsState.advancedOpen = isOpen;
        document.getElementById('partsAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
        const label = document.getElementById('partsAdvancedFilterLabel');
        if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
    },

    bindEvents() {
        const pageContent = document.getElementById('pageContent');

        document.getElementById('partsSearchBtn')?.addEventListener('click', () => this.loadParts(1));
        document.getElementById('partsResetBtn')?.addEventListener('click', () => this.resetFilters());
        document.getElementById('partsToggleAdvancedFilter')?.addEventListener('click', () => {
            this.setAdvancedOpen(!partsState.advancedOpen);
        });
        document.getElementById('partsBatchDeleteBtn')?.addEventListener('click', () => this.batchDelete());
        document.getElementById('partsExportBtn')?.addEventListener('click', () => this.exportExcel());

        pageContent?.addEventListener('change', (e) => {
            const cascadeResets = {
                locationFilter: ['supplierFilter', 'vehicleModelFilter', 'versionFilter'],
                supplierFilter: ['vehicleModelFilter', 'versionFilter'],
                vehicleModelFilter: ['versionFilter'],
            };
            if (cascadeResets[e.target.id]) {
                this.resetDependentFilters(cascadeResets[e.target.id]);
                this.loadCascadeFilters().then(() => this.loadParts(1));
                return;
            }
            if (e.target.id === 'versionFilter') {
                updatePartsFilterCapsules();
                this.loadParts(1);
                return;
            }
        });

        pageContent?.addEventListener('input', (e) => {
            if (e.target.id === 'searchInput') updatePartsFilterCapsules();
        });

        pageContent?.addEventListener('keydown', (e) => {
            if (e.target.id === 'searchInput' && e.key === 'Enter') {
                e.preventDefault();
                this.loadParts(1);
            }
        });

        pageContent?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (btn) {
                e.stopPropagation();
                const id = Number(btn.getAttribute('data-id'));
                const action = btn.getAttribute('data-action');
                if (action === 'detail') this.showDetail(id);
                else if (action === 'delete') this.deletePart(id);
                return;
            }
            const pageBtn = e.target.closest('button[data-page]');
            if (pageBtn && !pageBtn.disabled) {
                const targetPage = parseInt(pageBtn.getAttribute('data-page'), 10);
                if (!Number.isNaN(targetPage) && targetPage >= 1) this.loadParts(targetPage);
            }
        });
    },

    resetDependentFilters(ids) {
        ids.forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    },

    fillSelect(id, values = []) {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        select.innerHTML =
            '<option value="">全部</option>' +
            values.map((value) => {
                const text = String(value);
                return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
            }).join('');
    },

    async loadCascadeFilters() {
        try {
            const params = {
                location: document.getElementById('locationFilter')?.value || '',
                stamping_supplier: document.getElementById('supplierFilter')?.value || '',
                vehicle_model: document.getElementById('vehicleModelFilter')?.value || '',
            };
            const res = await HttpClient.get(CASCADE_API, { params });
            const filters = res.data || {};
            this.fillSelect('locationFilter', filters.locations || []);
            this.fillSelect('supplierFilter', filters.stamping_suppliers || []);
            this.fillSelect('vehicleModelFilter', filters.vehicle_models || []);
            this.fillSelect('versionFilter', filters.versions || []);
            updatePartsFilterCapsules();
        } catch (error) {
            console.error('加载级联筛选失败', error);
            showToast(error.message || '加载筛选失败', 'error');
        }
    },

    resetFilters() {
        ['locationFilter', 'supplierFilter', 'vehicleModelFilter', 'versionFilter'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const searchEl = document.getElementById('searchInput');
        if (searchEl) searchEl.value = '';
        this.loadCascadeFilters().then(() => this.loadParts(1));
    },

    collectScopeFilters() {
        return {
            location: document.getElementById('locationFilter')?.value || '',
            stamping_supplier: document.getElementById('supplierFilter')?.value || '',
            vehicle_model: document.getElementById('vehicleModelFilter')?.value || '',
            version: document.getElementById('versionFilter')?.value || '',
        };
    },

    requireScope(actionLabel) {
        const filters = this.collectScopeFilters();
        if (!filters.location || !filters.stamping_supplier || !filters.vehicle_model || !filters.version) {
            this.setAdvancedOpen(true);
            showToast(`${actionLabel}须同时选择基地、冲压工厂、车型和版本`, 'warning');
            return null;
        }
        return filters;
    },

    requireScopeForBatchDelete() {
        return this.requireScope('批量删除');
    },

    showEmptyHint(title, hint) {
        const empty = document.getElementById('partsEmpty');
        if (!empty) return;
        empty.classList.remove('hidden');
        const titleEl = empty.querySelector('h5');
        const hintEl = empty.querySelector('p');
        if (titleEl) titleEl.textContent = title;
        if (hintEl) hintEl.textContent = hint;
    },

    async loadParts(page = 1) {
        if (partsState.isLoading) return;

        partsState.isLoading = true;
        partsState.currentPage = page;

        const loading = document.getElementById('partsLoading');
        const empty = document.getElementById('partsEmpty');
        const body = document.getElementById('partsTableBody');
        if (body) body.innerHTML = '';
        empty?.classList.add('hidden');
        loading?.classList.remove('hidden');

        const scope = this.collectScopeFilters();
        const partNumber = document.getElementById('searchInput')?.value.trim();
        const params = {
            page,
            size: partsState.pageSize,
        };
        if (scope.location) params.location = scope.location;
        if (scope.stamping_supplier) params.stamping_supplier = scope.stamping_supplier;
        if (scope.vehicle_model) params.vehicle_model = scope.vehicle_model;
        if (scope.version) params.version = scope.version;
        if (partNumber) params.part_number = partNumber;

        try {
            const resp = await HttpClient.get(`${PARTS_API}/list`, { params });
            const pageInfo = resp.data ?? {};
            const items = pageInfo.items || [];
            const total = pageInfo.total ?? 0;
            const totalPages = pageInfo.total_pages ?? 1;

            updatePartsHud(pageInfo.filters?.summary || null);

            const totalLabel = document.getElementById('partsTotalLabel');
            if (totalLabel) {
                const partCount = pageInfo.filters?.summary?.part_number_count;
                const displayCount = partCount != null ? partCount : total;
                totalLabel.textContent = `全${displayCount} 个零件（去重）`;
            }

            if (!items.length) {
                this.showEmptyHint('暂无零件数据', '请先上传工艺文件');
            } else {
                this.renderParts(items);
            }

            const pagination = document.getElementById('pagination');
            if (pagination) {
                pagination.innerHTML = renderPartsPagination(page, totalPages);
            }
        } catch (error) {
            console.error('加载零件列表失败:', error);
            showToast(error.message || '加载失败', 'error');
            this.showEmptyHint('加载失败', esc(error.message) || '请稍后重试');
            updatePartsHud(null);
        } finally {
            loading?.classList.add('hidden');
            partsState.isLoading = false;
        }
    },

    renderParts(parts) {
        const partsTableBody = document.getElementById('partsTableBody');
        if (!partsTableBody) return;
        partsTableBody.innerHTML = parts.map((part) => this.renderRow(part)).join('');
    },

    renderRow(part) {
        const thickness = fmtNum(part.thickness, 2);
        const partWeight = fmtNum(part.part_weight, 3);
        const processCount = part.process_count != null ? part.process_count : '—';
        const sketchUrl = part.sketch_url || '';
        const cell = 'px-3 py-3 border-b border-[#17171C] font-mono text-[11px]';
        const muted = 'text-[#8E8E93]';

        const thumbnailCell = sketchUrl
            ? `<div class="sketch-thumbnail" title="图纸预览">
                    <img src="/uploads/${esc(sketchUrl)}" alt="零件图纸" onerror="this.style.display='none';this.nextElementSibling&&(this.nextElementSibling.style.display='flex')">
                    <div class="zoom-overlay">${window.svgIcon('search')}</div>
               </div>`
            : `<div class="sketch-thumbnail-placeholder" title="无图级>
                    ${window.svgIcon('file-earmark')}
               </div>`;

        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#17171C] hover:bg-gradient-to-r hover:from-[#FF1E27]/10 hover:via-[#121218] hover:to-transparent transition-all duration-150"
                data-id="${esc(part.id)}">
                <td class="p-0 w-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#FF1E27] opacity-0 group-hover:opacity-100 transition-all"
                         style="box-shadow: 0 0 10px #FF1E27;"></div>
                </td>
                <td class="${cell}">
                    <div class="flex items-center justify-center">${thumbnailCell}</div>
                </td>
                <td class="${cell} font-sans whitespace-nowrap">
                    <span class="text-[12px] font-semibold text-white font-mono tracking-wide group-hover:text-[#FF1E27] transition-colors">${esc(part.part_number)}</span>
                </td>
                <td class="${cell} ${muted} font-sans">${esc(part.part_name) || '—'}</td>
                <td class="${cell} ${muted}">${esc(part.location) || '—'}</td>
                <td class="${cell} ${muted} font-sans">${esc(part.stamping_supplier) || '—'}</td>
                <td class="${cell} ${muted}">${esc(part.vehicle_model) || '—'}</td>
                <td class="${cell} ${muted} border-r border-[#22222A]">${esc(part.version) || '—'}</td>
                <td class="${cell} ${muted} font-sans">${esc(part.material) || '—'}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${thickness}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${partWeight}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${processCount}</td>
                <td class="${cell} text-[10px] text-[#555555] max-w-[160px] truncate" title="${esc(part.excel_filename || '')}">${esc(part.excel_filename) || '—'}</td>
                <td class="px-1 py-2 text-center align-middle">
                    <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                        <button type="button" class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all" data-action="detail" data-id="${part.id}" title="查看详情" aria-label="查看详情">
                            ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                        </button>
                        ${this.canDelete !== false ? `
                        <button type="button" class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all" data-action="delete" data-id="${part.id}" title="删除" aria-label="删除">
                            ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                        </button>` : ''}
                    </div>
                </td>
            </tr>
        `;
    },

    async batchDelete() {
        if (this.canDelete === false) {
            showToast('无删除权限', 'warning');
            return;
        }
        const filters = this.requireScopeForBatchDelete();
        if (!filters) return;

        if (!window.confirm(
            `确定批量删除零件吗？\n\n基地: ${filters.location}\n工厂: ${filters.stamping_supplier}\n车型: ${filters.vehicle_model}\n版本: ${filters.version}\n\n将同时删除关联工序，此操作不可恢复！`,
        )) {
            return;
        }

        const btn = document.getElementById('partsBatchDeleteBtn');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
                删除中..
            `;
        }

        try {
            const body = {
                location: filters.location,
                stamping_supplier: filters.stamping_supplier,
                vehicle_model: filters.vehicle_model,
                version: filters.version,
            };

            const res = await HttpClient.post(`${PARTS_API}/batch-delete`, body);
            const result = res.data || {};
            const deleted = result.deleted_count ?? 0;
            showToast(res.message || `已删除${deleted} 个零件`, deleted > 0 ? 'success' : 'warning');
            await this.loadCascadeFilters();
            if (deleted > 0) {
                await this.loadParts(1);
            }
        } catch (error) {
            showToast(error.message || '批量删除失败', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    },

    async showDetail(partId) {
        const drawer = document.getElementById('partDrawer');
        const backdrop = document.getElementById('partDrawerBackdrop');
        const contentEl = document.getElementById('partDrawerContent');
        const titleEl = document.getElementById('partDrawerTitle');

        if (!drawer || !contentEl) {
            console.error('抽屉元素不存在');
            return;
        }

        if (titleEl) titleEl.textContent = '零件详情';

        contentEl.innerHTML = `
            <div class="flex items-center justify-center py-16">
                <div class="w-7 h-7 border-2 border-[#2a2a2a] border-t-[#d32f2f] rounded-full animate-spin"></div>
            </div>
        `;

        drawer.style.display = 'flex';
        backdrop && (backdrop.style.display = 'block');
        requestAnimationFrame(() => drawer.classList.remove('translate-x-full'));

        try {
            const result = await HttpClient.get(`${PARTS_API}/${partId}`);
            const part = result.data?.data ?? result.data ?? result;
            contentEl.innerHTML = renderDetailContent(part);

            const btn = document.getElementById('saveProcessBtn');
            if (btn) {
                btn.dataset.active = 'false';
                btn.className = 'btn-save-default';
            }

            this._bindProcessEditEvents(part.id);
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

        tbody.addEventListener('change', (e) => {
            const sel = e.target.closest('.die-type-select');
            if (!sel) return;
            this._activateSaveButton();
        });

        document.getElementById('applyBatchDieType')?.addEventListener('click', () => {
            const batchVal = document.getElementById('batchDieTypeSelect')?.value;
            if (!batchVal) return;
            tbody.querySelectorAll('.die-type-select').forEach((sel) => {
                sel.value = batchVal;
                sel.dispatchEvent(new Event('change'));
            });
        });

        document.getElementById('saveProcessBtn')?.addEventListener('click', async () => {
            await this._saveProcessEdits(partId);
        });
    },

    _activateSaveButton() {
        const btn = document.getElementById('saveProcessBtn');
        if (!btn || btn.dataset.active === 'true') return;
        btn.dataset.active = 'true';
        btn.className = 'btn-save-active';
    },

    _collectProcessEdits() {
        const ratioMap = { progressive: 0.8, single: 1.0, shared: 0.5, progressive_shared: 0.4 };
        const tbody = document.getElementById('processTableBody');
        if (!tbody) return [];
        const rows = tbody.querySelectorAll('.process-row');
        return Array.from(rows).map((row) => {
            const processId = row.dataset.processId;
            const sel = row.querySelector('.die-type-select');
            const dieType = sel?.value ?? 'single';
            const costRatio = ratioMap[dieType] ?? 1.0;
            return { id: parseInt(processId, 10), cost_ratio: costRatio };
        });
    },

    async _saveProcessEdits(partId) {
        if (this.canUpdate === false) {
            showToast('无编辑权限', 'warning');
            return;
        }
        const btn = document.getElementById('saveProcessBtn');
        const processes = this._collectProcessEdits();
        if (processes.length === 0) return;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-2">${window.svgIcon('spinner', 'w-3.5 h-3.5 animate-spin')}保存中..</span>`;
        try {
            await HttpClient.put(`${PARTS_API}/${partId}/processes`, processes);
            showToast('工序参数已保存', 'success');
            const saveBtn = document.getElementById('saveProcessBtn');
            if (saveBtn) {
                saveBtn.dataset.active = 'false';
                saveBtn.className = 'btn-save-default';
            }
            this.loadParts(partsState.currentPage);
            this.showDetail(partId);
        } catch (error) {
            console.error('保存失败:', error);
            showToast(error.message || '保存失败', 'error');
            btn.disabled = false;
            btn.innerHTML = `<span class="tracking-[0.2em]">保存</span>`;
        }
    },

    async exportExcel() {
        if (this.canExport === false) {
            showToast('无导出权限', 'warning');
            return;
        }
        const scope = this.requireScope('导出');
        if (!scope) return;
        const params = {
            location: scope.location,
            stamping_supplier: scope.stamping_supplier,
            vehicle_model: scope.vehicle_model,
            version: scope.version,
        };

        const btn = document.getElementById('partsExportBtn');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
                导出中..
            `;
        }
        try {
            const { blob, filename } = await HttpClient.download(`${PARTS_API}/export-download`, {
                params,
                defaultFilename: '冲压工艺确认表.xlsx',
            });
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename || '冲压工艺确认表.xlsx';
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
            showToast(`导出成功: ${filename}`, 'success');
        } catch (error) {
            console.error('导出冲压工艺失败', error);
            showToast(error.message || '导出失败', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    },

    async deletePart(partId) {
        if (this.canDelete === false) {
            showToast('无删除权限', 'warning');
            return;
        }
        if (!confirm('确定要删除这个零件吗？')) return;
        try {
            await HttpClient.delete(`${PARTS_API}/${partId}`);
            showToast('删除成功', 'success');
            this.loadParts(partsState.currentPage);
        } catch (error) {
            console.error('删除失败:', error);
            showToast(error.message || '删除失败', 'error');
        }
    },

    bindDrawerEvents() {
        const closeDrawer = () => {
            const drawer = document.getElementById('partDrawer');
            const backdrop = document.getElementById('partDrawerBackdrop');
            if (!drawer) return;
            drawer.classList.add('translate-x-full');
            if (backdrop) backdrop.style.display = 'none';
            drawer.addEventListener('transitionend', () => {
                drawer.style.display = 'none';
            }, { once: true });
        };

        document.getElementById('closePartDrawer')?.addEventListener('click', closeDrawer);
        document.getElementById('partDrawerBackdrop')?.addEventListener('click', closeDrawer);

        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Escape') return;
            const drawer = document.getElementById('partDrawer');
            if (drawer && drawer.style.display !== 'none') closeDrawer();
        });
    },
};

export const pageConfig = {
    render: partsTemplate,
    init: () => PartsPage.init(),
};
