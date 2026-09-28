/**
 * Parts Page
 * 零件列表 —进入即加载、筛选均可选、级联（基地 → 项目 → 版本 → 冲压工厂）、批量删除须基地+项目+版本
 * 明细抽屉逻辑保持不变
 */

import {
    partsTemplate,
    renderDetailContent,
    updatePartsHudScope,
    updatePartsHud,
} from './template.js?v=63';
import { can } from '../../../../core/permissions.js?v=8';
import { hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=6';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=4';
import { fmtPeriodRange } from '../../../common/period-ui.js?v=4';
import {
    BTN_SOLID,
    SKETCH_PLACEHOLDER,
    SKETCH_THUMBNAIL,
    ZOOM_OVERLAY,
} from '../../../../ui/classes.js?v=13';
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    bindPagination,
    paintPagination,
    normalizePageSize,
} from '../../../../ui/page-size.js?v=6';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;
/** @type {{ paint: () => void, setOpen: (isOpen: boolean) => void, unbind: () => void } | null} */
let filterBar = null;

const PARTS_FILTER_FIELD_IDS = [
    'locationFilter',
    'vehicleModelFilter',
    'versionFilter',
    'supplierFilter',
    'searchInput',
];

function offalCell(part) {
    if (!part.is_offal_nested) {
        return '<span class="text-ink-faint">—</span>';
    }
    const source = part.offal_source ? esc(part.offal_source) : '';
    const label = source || '利废';
    return `<span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-warn bg-app-hud border border-warn/40/30" title="是否利废">${label}</span>`;
}

function scrapByproductCell(part) {
    if (!part.is_scrap_byproduct) {
        return '<span class="text-ink-faint">—</span>';
    }
    return '<span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-ink-muted bg-app-rowhover border border-line-hud" title="废料副产品，不算冲压费">是</span>';
}

function materialChangeCell(part) {
    if (!part.has_material_change) {
        return '<span class="text-ink-faint">—</span>';
    }
    return '<span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-ink-muted bg-app-hud border border-line-hud" title="该零件有材料变更">是</span>';
}

function swingShearCell(part) {
    if (!part.has_swing_shear) {
        return '<span class="text-ink-faint">—</span>';
    }
    return '<span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-ink-muted bg-app-deep border border-ink-muted/30" title="含摆剪工序">是</span>';
}


const CASCADE_API = '/api/stamping/filters/cascade';
const PARTS_API = '/api/stamping/parts';

const PARTS_CONFIG = {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    STORAGE_KEY: 'parts_page_size',
};

function readHashFilters() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return null;
    const params = new URLSearchParams(hash.slice(qIndex + 1));
    const location = params.get('location') || '';
    const stamping_supplier = params.get('stamping_supplier') || '';
    const vehicle_model = params.get('vehicle_model') || '';
    const version = params.get('version') || '';
    const part_number = params.get('part_number') || '';
    if (!location && !stamping_supplier && !vehicle_model && !version && !part_number) {
        return null;
    }
    return { location, stamping_supplier, vehicle_model, version, part_number };
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select || value == null || value === '') return;
    const text = String(value);
    if (![...select.options].some((opt) => opt.value === text)) {
        select.insertAdjacentHTML(
            'beforeend',
            `<option value="${esc(text)}">${esc(text)}</option>`,
        );
    }
    select.value = text;
}

function applyPendingFiltersToSelects() {
    const pending = partsState.pendingFilters;
    if (!pending) return;
    setSelectValue('locationFilter', pending.location);
    setSelectValue('supplierFilter', pending.stamping_supplier);
    setSelectValue('vehicleModelFilter', pending.vehicle_model);
    setSelectValue('versionFilter', pending.version);
    const searchEl = document.getElementById('searchInput');
    if (searchEl && pending.part_number) searchEl.value = pending.part_number;
    partsState.pendingFilters = null;
    filterBar?.paint();
    updatePartsHudScope();
}

const partsState = {
    currentPage: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    isLoading: false,
    advancedOpen: false,
    pendingFilters: null,
    total: 0,
    items: [],
};

function specText(value) {
    const text = String(value ?? '').trim();
    return text || '—';
}

function partDeleteSpecs(part) {
    const project = [part?.vehicle_model, part?.version].map((item) => String(item ?? '').trim()).filter(Boolean).join(' / ');
    return [
        { label: '零件名称', value: specText(part?.part_name) },
        { label: '零件号', value: specText(part?.part_number) },
        { label: '项目', value: specText(project) },
        { label: '冲压工厂', value: specText(part?.stamping_supplier) },
    ];
}

export const PartsPage = {
    init() {
        this.initState();
        this.bindEvents();
        this.bindDrawerEvents();
        this.applyPermissionUi();
        partsState.pendingFilters = readHashFilters();
        this.loadCascadeFilters().then(() => {
            applyPendingFiltersToSelects();
            this.loadParts(1);
        });
    },

    applyPermissionUi() {
        this.canUpdate = typeof can === 'function' ? can('op:stamping-parts:update') : true;
        this.canDelete = typeof can === 'function' ? can('op:stamping-parts:delete') : true;
        this.canExport = typeof can === 'function' ? can('op:stamping-parts:export') : true;
        if (!this.canDelete) {
            document.getElementById('partsBatchDeleteBtn')?.classList.add('hidden');
            document.getElementById('partsMoreWrap')?.classList.add('hidden');
        }
        if (!this.canExport) {
            document.getElementById('partsExportBtn')?.classList.add('hidden');
            document.getElementById('partsSteelPurchaseExportBtn')?.classList.add('hidden');
        }
    },

    initState() {
        const savedSize = localStorage.getItem(PARTS_CONFIG.STORAGE_KEY);
        partsState.pageSize = normalizePageSize(savedSize);

        bindPagination({
            selectId: 'partsPageSize',
            buttonsId: 'partsPagination',
            getSize: () => partsState.pageSize,
            setSize: (size) => {
                partsState.pageSize = size;
                localStorage.setItem(PARTS_CONFIG.STORAGE_KEY, String(size));
            },
            onPage: (page) => this.loadParts(page),
        });
    },

    bindEvents() {
        const pageContent = document.getElementById('pageContent');
        filterBar = bindFilterBar({
            prefix: 'parts',
            capsules: [
                { capsuleId: 'partsCapsuleLocation', fieldId: 'locationFilter', idleLabel: '全部基地' },
                { capsuleId: 'partsCapsuleVehicle', fieldId: 'vehicleModelFilter', idleLabel: '全部项目' },
                { capsuleId: 'partsCapsuleVersion', fieldId: 'versionFilter', idleLabel: '全部版本' },
                { capsuleId: 'partsCapsuleSupplier', fieldId: 'supplierFilter', idleLabel: '全部工厂' },
            ],
            countFieldIds: PARTS_FILTER_FIELD_IDS,
            resetId: 'partsResetBtn',
            enterFieldIds: ['searchInput'],
            onSearch: () => this.loadParts(1),
            onReset: () => this.resetFilters(),
        });
        document.getElementById('partsBatchDeleteBtn')?.addEventListener('click', () => {
            moreMenu?.close();
            this.batchDelete();
        });
        moreMenu = bindMoreMenu({
            wrapId: 'partsMoreWrap',
            btnId: 'partsMoreBtn',
            menuId: 'partsMoreMenu',
        });
        document.getElementById('partsExportBtn')?.addEventListener('click', () => this.exportExcel());
        document.getElementById('partsSteelPurchaseExportBtn')?.addEventListener('click', () => this.exportSteelPurchase());

        pageContent?.addEventListener('change', (e) => {
            const cascadeResets = {
                locationFilter: ['vehicleModelFilter', 'versionFilter', 'supplierFilter'],
                vehicleModelFilter: ['versionFilter', 'supplierFilter'],
                versionFilter: ['supplierFilter'],
            };
            if (cascadeResets[e.target.id]) {
                this.resetDependentFilters(cascadeResets[e.target.id]);
                this.loadCascadeFilters().then(() => this.loadParts(1));
                return;
            }
            if (e.target.id === 'supplierFilter') {
                filterBar?.paint();
                updatePartsHudScope();
                this.loadParts(1);
                return;
            }
        });

        pageContent?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn || !btn.hasAttribute('data-id')) return;
            e.stopPropagation();
            const id = Number(btn.getAttribute('data-id'));
            const action = btn.getAttribute('data-action');
            if (action === 'detail') this.showDetail(id);
            else if (action === 'delete') this.deletePart(id);
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
                vehicle_model: document.getElementById('vehicleModelFilter')?.value || '',
                version: document.getElementById('versionFilter')?.value || '',
                stamping_supplier: document.getElementById('supplierFilter')?.value || '',
            };
            const res = await HttpClient.get(CASCADE_API, { params });
            const filters = res.data || {};
            this.fillSelect('locationFilter', filters.locations || []);
            this.fillSelect('supplierFilter', filters.stamping_suppliers || []);
            this.fillSelect('vehicleModelFilter', filters.vehicle_models || []);
            this.fillSelect('versionFilter', filters.versions || []);
            filterBar?.paint();
            updatePartsHudScope();
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
        if (!filters.location || !filters.vehicle_model || !filters.version) {
            filterBar?.setOpen(true);
            showToast(`${actionLabel}须同时选择基地、项目和版本；冲压工厂可选`, 'warning');
            return null;
        }
        return filters;
    },

    requireScopeForBatchDelete() {
        return this.requireScope('批量删除');
    },

    requireLocationForExport() {
        const filters = this.collectScopeFilters();
        if (!filters.location) {
            filterBar?.setOpen(true);
            showToast('导出须选择基地', 'warning');
            return null;
        }
        return filters;
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
        setSearchBusy('partsSearchBtn', true);
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
        params.include_expired = true;

        try {
            const resp = await HttpClient.get(`${PARTS_API}/list`, { params });
            const pageInfo = resp.data ?? {};
            const items = pageInfo.items || [];
            const total = pageInfo.total ?? 0;
            partsState.items = items;
            partsState.total = total;
            const totalPages = pageInfo.total_pages ?? 1;

            updatePartsHud(pageInfo.filters?.summary || null);

            const totalLabel = document.getElementById('partsPageInfo');
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

            paintPagination('partsPagination', page, totalPages);
        } catch (error) {
            console.error('加载零件列表失败:', error);
            showToast(error.message || '加载失败', 'error');
            partsState.items = [];
            partsState.total = 0;
            this.showEmptyHint('加载失败', esc(error.message) || '请稍后重试');
            updatePartsHud(null);
        } finally {
            loading?.classList.add('hidden');
            partsState.isLoading = false;
            setSearchBusy('partsSearchBtn', false);
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
        const cell = 'px-3 py-3 border-b border-line-subtle font-mono text-[11px]';
        const muted = 'text-ink-muted';

        const thumbnailCell = sketchUrl
            ? `<div class="${SKETCH_THUMBNAIL}" title="图纸预览">
                    <img class="w-full h-full object-cover" src="/uploads/${esc(sketchUrl)}" alt="零件图纸" onerror="this.style.display='none';this.nextElementSibling&&(this.nextElementSibling.style.display='flex')">
                    <div class="${ZOOM_OVERLAY}">${window.svgIcon('search')}</div>
               </div>`
            : `<div class="${SKETCH_PLACEHOLDER}" title="无图纸">
                    ${window.svgIcon('file-earmark')}
               </div>`;

        const detailBtn = opsIconButtonHtml({
            action: 'detail',
            title: '查看详情',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
            attrs: `data-id="${part.id}"`,
        });
        const deleteBtn = this.canDelete !== false
            ? opsIconButtonHtml({
                action: 'delete',
                danger: true,
                title: '删除',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                attrs: `data-id="${part.id}"`,
            })
            : '';
        return hudRowHtml({
            attrs: `data-id="${esc(part.id)}"`,
            cellsHtml: `
                <td class="${cell}">
                    <div class="flex items-center justify-center">${thumbnailCell}</div>
                </td>
                <td class="${cell} font-sans whitespace-nowrap">
                    ${partShortCodeCellHtml(part.part_number)}
                </td>
                <td class="${cell} font-sans overflow-hidden">
                    ${partNumberNameCellHtml(part.part_number, part.part_name)}
                </td>
                <td class="${cell} ${muted}">${esc(part.location) || '—'}</td>
                <td class="${cell} ${muted}">${esc(part.vehicle_model) || '—'}</td>
                <td class="${cell} ${muted}">${esc(part.version) || '—'}</td>
                <td class="${cell} ${muted} font-sans border-r border-line-hud">${esc(part.stamping_supplier) || '—'}</td>
                <td class="${cell} ${muted} font-sans">${esc(part.material) || '—'}</td>
                <td class="${cell}">${materialChangeCell(part)}</td>
                <td class="${cell}">${offalCell(part)}</td>
                <td class="${cell}">${scrapByproductCell(part)}</td>
                <td class="${cell}">${swingShearCell(part)}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${thickness}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${partWeight}</td>
                <td class="${cell} text-right tabular-nums ${muted}">${processCount}</td>
                <td class="${cell} ${muted} whitespace-nowrap">${esc(fmtPeriodRange(part.effective_year, part.effective_month, part.expiry_year, part.expiry_month))}</td>
                <td class="${cell} text-[10px] text-ink-faint max-w-[160px] truncate" title="${esc(part.excel_filename || '')}">${esc(part.excel_filename) || '—'}</td>`,
            opsHtml: `${detailBtn}${deleteBtn}`,
        });
    },

    async batchDelete() {
        if (this.canDelete === false) {
            showToast('无删除权限', 'warning');
            return;
        }
        const filters = this.requireScopeForBatchDelete();
        if (!filters) return;

        if (!await window.confirmAction(
            '即将删除该范围内的零件，并同时删除关联工序。此操作不可恢复。',
            {
                title: '确认批量删除零件',
                confirmLabel: '确认彻底删除',
                specs: [
                    { label: '基地', value: specText(filters.location) },
                    { label: '项目', value: specText(filters.vehicle_model) },
                    { label: '版本', value: specText(filters.version) },
                    { label: '工厂', value: specText(filters.stamping_supplier || '全部工厂') },
                ],
            },
        )) {
            return;
        }

        const btn = document.getElementById('partsBatchDeleteBtn');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>
                删除中..
            `;
        }

        try {
            const body = {
                location: filters.location,
                vehicle_model: filters.vehicle_model,
                version: filters.version,
            };
            if (filters.stamping_supplier) body.stamping_supplier = filters.stamping_supplier;

            const res = await HttpClient.post(`${PARTS_API}/batch-delete`, body);
            const result = res.data || {};
            const deleted = result.deleted_count ?? 0;
            showToast(res.message || `已删除${deleted} 个零件`, deleted > 0 ? 'success' : 'warning');
            await this.loadCascadeFilters();
            if (deleted > 0) {
                await this.loadParts(1);
            }
        } catch (error) {
            console.error('批量删除失败:', error);
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
                <div class="w-7 h-7 border-2 border-line border-brand rounded-full animate-spin"></div>
            </div>
        `;

        drawer.style.display = 'flex';
        backdrop && (backdrop.style.display = 'block');
        requestAnimationFrame(() => drawer.classList.remove('translate-x-full'));

        try {
            const result = await HttpClient.get(`${PARTS_API}/${partId}`);
            const part = result.data?.data ?? result.data ?? result;
            contentEl.innerHTML = renderDetailContent(part, {
                canUpdate: this.canUpdate !== false,
                periodLabel: fmtPeriodRange(
                    part.effective_year,
                    part.effective_month,
                    part.expiry_year,
                    part.expiry_month,
                ),
            });

            const btn = document.getElementById('saveProcessBtn');
            if (btn) {
                btn.dataset.active = 'false';
                btn.className = BTN_SOLID;
            }

            this._bindProcessEditEvents(part.id);
            this._bindOffalEditEvents(part.id);
            this._bindSketchModal(part);
        } catch (error) {
            contentEl.innerHTML = `
                <div class="p-4 m-4 bg-app-deep border border-line">
                    <div class="flex items-center gap-2 text-brand">
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
                <div class="absolute inset-0 bg-overlay/70 backdrop-blur-sm" id="sketchModalBackdrop"></div>
                <div class="relative z-10 max-w-4xl w-full mx-8 max-h-[85vh] flex flex-col">
                    <button type="button" id="closeSketchModal" class="absolute -top-10 right-0 flex items-center gap-1.5 text-[10px] text-ink-faint hover:text-ink transition-colors tracking-wider group">
                        <span class="group-hover:text-brand transition-colors">关闭</span>
                        ${window.svgIcon('x-lg', 'w-3.5 h-3.5 group-hover:text-brand transition-colors')}
                    </button>
                    <div class="flex-1 overflow-auto bg-app-deep border border-line-subtle rounded-sm shadow-2xl">
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

    _syncOffalToggleUi() {
        const toggle = document.getElementById('offalNestedToggle');
        const knob = document.getElementById('offalNestedKnob');
        const label = document.getElementById('offalNestedLabel');
        const sourceRow = document.getElementById('offalSourceRow');
        if (!toggle) return;
        const isOn = toggle.dataset.on === '1';
        toggle.setAttribute('aria-checked', isOn ? 'true' : 'false');
        toggle.style.background = isOn ? 'rgb(var(--brabus-red))' : 'rgb(var(--bg-hud))';
        toggle.style.borderColor = isOn ? 'rgb(var(--brabus-red))' : 'rgb(var(--border-color))';
        if (knob) knob.style.transform = `translateX(${isOn ? '16px' : '2px'})`;
        if (label) label.textContent = isOn ? '是' : '否';
        if (sourceRow) sourceRow.classList.toggle('hidden', !isOn);
    },

    _bindOffalEditEvents(partId) {
        const toggle = document.getElementById('offalNestedToggle');
        if (!toggle || this.canUpdate === false) return;

        toggle.addEventListener('click', () => {
            toggle.dataset.on = toggle.dataset.on === '1' ? '0' : '1';
            this._syncOffalToggleUi();
            this._activateOffalSaveButton();
        });
        document.getElementById('offalSourceInput')?.addEventListener('input', () => {
            this._activateOffalSaveButton();
        });
        document.getElementById('saveOffalBtn')?.addEventListener('click', async () => {
            await this._saveOffalEdits(partId);
        });
    },

    _activateOffalSaveButton() {
        const btn = document.getElementById('saveOffalBtn');
        if (!btn || btn.dataset.active === 'true') return;
        btn.dataset.active = 'true';
        btn.className = BTN_SOLID;
    },

    _activateSaveButton() {
        const btn = document.getElementById('saveProcessBtn');
        if (!btn || btn.dataset.active === 'true') return;
        btn.dataset.active = 'true';
        btn.className = BTN_SOLID;
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
                saveBtn.className = BTN_SOLID;
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

    async _saveOffalEdits(partId) {
        if (this.canUpdate === false) {
            showToast('无编辑权限', 'warning');
            return;
        }
        const toggle = document.getElementById('offalNestedToggle');
        const btn = document.getElementById('saveOffalBtn');
        if (!toggle || !btn) return;
        const isOn = toggle.dataset.on === '1';
        const sourceRaw = document.getElementById('offalSourceInput')?.value ?? '';
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '保存中..';
        try {
            await HttpClient.patch(`${PARTS_API}/${partId}/offal`, {
                is_offal_nested: isOn,
                offal_source: isOn ? sourceRaw.trim() || null : null,
            });
            showToast('利废设置已保存。零件价格需重算后才会按新规则计价。', 'success');
            this.loadParts(partsState.currentPage);
            this.showDetail(partId);
        } catch (error) {
            showToast(error.message || '保存失败', 'error');
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    },

    async exportExcel() {
        await this._downloadExport({
            path: 'export-download',
            defaultFilename: '冲压工艺确认表.xlsx',
            buttonId: 'partsExportBtn',
            failLog: '导出冲压工艺失败',
        });
    },

    async exportSteelPurchase() {
        await this._downloadExport({
            path: 'steel-purchase-export-download',
            defaultFilename: '钢材采购测算.xlsx',
            buttonId: 'partsSteelPurchaseExportBtn',
            failLog: '导出钢材测算失败',
        });
    },

    async _downloadExport({ path, defaultFilename, buttonId, failLog }) {
        if (this.canExport === false) {
            showToast('无导出权限', 'warning');
            return;
        }
        const scope = this.requireLocationForExport();
        if (!scope) return;
        if (!partsState.total) {
            showToast('当前筛选下没有零件，无法导出', 'warning');
            return;
        }
        const params = { location: scope.location };
        if (scope.stamping_supplier) params.stamping_supplier = scope.stamping_supplier;
        if (scope.vehicle_model) params.vehicle_model = scope.vehicle_model;
        if (scope.version) params.version = scope.version;
        const partNumber = document.getElementById('searchInput')?.value.trim() || '';
        if (partNumber) params.part_number = partNumber;
        if (path === 'export-download') {
            params.include_expired = true;
        }

        const btn = document.getElementById(buttonId);
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>
                导出中..
            `;
        }
        try {
            const { blob, filename } = await HttpClient.download(`${PARTS_API}/${path}`, {
                params,
                defaultFilename,
            });
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename || defaultFilename;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
            showToast(`导出成功: ${filename}`, 'success');
        } catch (error) {
            console.error(failLog, error);
            if (!error.status) showToast(error.message || '导出失败', 'error');
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
        const part = partsState.items.find((row) => Number(row.id) === Number(partId));
        const confirmed = await window.confirmAction(
            part
                ? '即将永久移除以下零件，并同时删除其关联工序。此操作不可恢复。'
                : '即将永久移除该零件，并同时删除其关联工序。此操作不可恢复。',
            {
                title: '确认删除零件',
                confirmLabel: '确认彻底删除',
                specs: part ? partDeleteSpecs(part) : [],
            },
        );
        if (!confirmed) return;
        try {
            await HttpClient.delete(`${PARTS_API}/${partId}`);
            showToast('删除成功', 'success');
            this.loadParts(partsState.currentPage);
        } catch (error) {
            console.error('删除失败:', error);
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
    destroy() {
        moreMenu?.unbind();
        moreMenu = null;
        filterBar?.unbind();
        filterBar = null;
    },
};
