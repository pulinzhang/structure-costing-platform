/**
 * BOM 材料清单列表 — 筛选查看 + 单行删除
 */

import {
    bomMaterialListTemplate,
    renderBomMatTableRows,
    renderBomMatPagination,
    updateBomMatHud,
    updateBomMatCapsules,
} from './template.js?v=3';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';
import { setSearchBusy } from '../../../../search-busy.js?v=1';

const API_BASE = '/api/bom';

const bomMatState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    location: null,
    vehicleModel: null,
    bomVersion: null,
    status: null,
    summary: null,
    isLoading: false,
    deleting: false,
    advancedOpen: false,
    canDelete: false,
    canViewStructure: false,
};

function init() {
    applyHashQuery();
    bindEvents();
    bindPageSizeSelect('bomMatPageSize', {
        getSize: () => bomMatState.pageSize,
        setSize: (size) => {
            bomMatState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
    if (bomMatState.advancedOpen) {
        document.getElementById('bomMatAdvancedFilterPanel')?.classList.remove('hidden');
        const label = document.getElementById('bomMatAdvancedFilterLabel');
        if (label) label.textContent = '收起高级筛选';
    }
    loadData(1);
    updateBomMatCapsules(bomMatState);
}

function applyHashQuery() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return;
    const params = new URLSearchParams(hash.slice(queryIndex + 1));
    bomMatState.location = params.get('location') || null;
    bomMatState.vehicleModel = params.get('vehicle_model') || null;
    bomMatState.bomVersion = params.get('bom_version') || null;
    bomMatState.status = params.get('status') || null;
    if (bomMatState.location || bomMatState.vehicleModel || bomMatState.bomVersion || bomMatState.status) {
        bomMatState.advancedOpen = true;
    }
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    bomMatState.canDelete = canFn('op:bom-material:delete');
    bomMatState.canViewStructure = canFn('op:bom-structure:view');
}

function bindEvents() {
    document.getElementById('btnBomMatFilter')?.addEventListener('click', () => {
        readFiltersFromDom();
        loadData(1);
    });
    ['bomMatLocationFilter', 'bomMatModelFilter', 'bomMatVersionFilter', 'bomMatStatusFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            readFiltersFromDom();
            loadData(1);
        });
    });
    document.getElementById('bomMatResetFilterBtn')?.addEventListener('click', resetFilters);
    document.getElementById('bomMatToggleAdvancedFilter')?.addEventListener('click', () => {
        bomMatState.advancedOpen = !bomMatState.advancedOpen;
        document.getElementById('bomMatAdvancedFilterPanel')?.classList.toggle('hidden', !bomMatState.advancedOpen);
        const label = document.getElementById('bomMatAdvancedFilterLabel');
        if (label) label.textContent = bomMatState.advancedOpen ? '收起高级筛选' : '展开高级筛选';
    });

    document.getElementById('bomMatTableBody')?.addEventListener('click', (event) => {
        const structureBtn = event.target.closest('[data-action="open-structure"]');
        if (structureBtn) {
            const id = Number(structureBtn.getAttribute('data-snapshot-id'));
            if (id) {
                window.location.hash = `/bom-structure?snapshot_id=${encodeURIComponent(id)}`;
            }
            return;
        }
        const deleteBtn = event.target.closest('[data-action="delete-one"]');
        if (deleteBtn) {
            deleteOne(deleteBtn);
        }
    });

    document.getElementById('bomMatPaginationBtns')?.addEventListener('click', (event) => {
        const btn = event.target.closest('button[data-page]');
        if (!btn || btn.disabled) return;
        const page = Number(btn.getAttribute('data-page'));
        if (page) loadData(page);
    });
}

function readFiltersFromDom() {
    bomMatState.location = val('bomMatLocationFilter') || null;
    bomMatState.vehicleModel = val('bomMatModelFilter') || null;
    bomMatState.bomVersion = val('bomMatVersionFilter') || null;
    bomMatState.status = val('bomMatStatusFilter') || null;
    updateBomMatCapsules(bomMatState);
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function resetFilters() {
    ['bomMatLocationFilter', 'bomMatModelFilter', 'bomMatVersionFilter', 'bomMatStatusFilter']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    readFiltersFromDom();
    loadData(1);
}

function fillSelect(id, values, emptyLabel = '全部') {
    const el = document.getElementById(id);
    if (!el) return;
    const current = el.value;
    let html = `<option value="">${emptyLabel}</option>`;
    (values || []).forEach((v) => {
        const label = id === 'bomMatStatusFilter' ? statusOptionLabel(v) : v;
        html += `<option value="${esc(v)}">${esc(label)}</option>`;
    });
    el.innerHTML = html;
    if (current) el.value = current;
}

function statusOptionLabel(value) {
    const map = { draft: '草稿', active: '生效', archived: '归档' };
    return map[value] || value;
}

function syncFilterSelects() {
    const loc = document.getElementById('bomMatLocationFilter');
    const model = document.getElementById('bomMatModelFilter');
    const version = document.getElementById('bomMatVersionFilter');
    const status = document.getElementById('bomMatStatusFilter');
    if (loc && bomMatState.location) loc.value = bomMatState.location;
    if (model && bomMatState.vehicleModel) model.value = bomMatState.vehicleModel;
    if (version && bomMatState.bomVersion) version.value = bomMatState.bomVersion;
    if (status && bomMatState.status) status.value = bomMatState.status;
}

async function loadData(page = 1) {
    if (bomMatState.isLoading) return;
    bomMatState.isLoading = true;
    setSearchBusy('btnBomMatFilter', true);
    const tbody = document.getElementById('bomMatTableBody');
    const empty = document.getElementById('bomMatEmptyState');
    const loading = document.getElementById('bomMatLoadingState');
    if (tbody) tbody.innerHTML = '';
    empty?.classList.add('hidden');
    loading?.classList.remove('hidden');

    try {
        const params = {
            page,
            size: bomMatState.pageSize,
        };
        if (bomMatState.location) params.location = bomMatState.location;
        if (bomMatState.vehicleModel) params.vehicle_model = bomMatState.vehicleModel;
        if (bomMatState.bomVersion) params.bom_version = bomMatState.bomVersion;
        if (bomMatState.status) params.status = bomMatState.status;

        const res = await HttpClient.get(`${API_BASE}/snapshots`, { params });
        const pageResult = res.data || {};
        bomMatState.records = pageResult.items || [];
        bomMatState.total = pageResult.total || 0;
        bomMatState.page = pageResult.page || page;
        bomMatState.totalPages = pageResult.total_pages || 1;
        const filters = pageResult.filters || {};
        bomMatState.summary = filters.summary || null;

        fillSelect('bomMatLocationFilter', filters.locations);
        fillSelect('bomMatModelFilter', filters.vehicle_models);
        fillSelect('bomMatVersionFilter', filters.bom_versions);
        fillSelect('bomMatStatusFilter', filters.statuses);
        syncFilterSelects();

        updateBomMatHud(bomMatState.summary);
        updateBomMatCapsules(bomMatState);

        if (tbody) {
            tbody.innerHTML = renderBomMatTableRows(bomMatState.records, {
                canViewStructure: bomMatState.canViewStructure,
                canDelete: bomMatState.canDelete,
            });
        }
        const totalEl = document.getElementById('bomMatTotalCount');
        if (totalEl) totalEl.textContent = `共 ${bomMatState.total} 条`;
        const pager = document.getElementById('bomMatPaginationBtns');
        if (pager) pager.innerHTML = renderBomMatPagination(bomMatState.page, bomMatState.totalPages);

        if (!bomMatState.records.length) empty?.classList.remove('hidden');
    } catch (error) {
        console.error(error);
        empty?.classList.remove('hidden');
    } finally {
        loading?.classList.add('hidden');
        bomMatState.isLoading = false;
        setSearchBusy('btnBomMatFilter', false);
    }
}

async function deleteOne(deleteBtn) {
    if (!bomMatState.canDelete || bomMatState.deleting) return;
    const snapshotId = Number(deleteBtn.getAttribute('data-snapshot-id'));
    const location = deleteBtn.getAttribute('data-location') || '';
    const vehicleModel = deleteBtn.getAttribute('data-vehicle-model') || '';
    const bomVersion = deleteBtn.getAttribute('data-bom-version') || '';
    if (!snapshotId || !location || !vehicleModel || !bomVersion) {
        showToast('删除须具备基地、项目、版本', 'warning');
        return;
    }
    const ok = window.confirm(
        `确认删除材料清单？\n${location} / ${vehicleModel} / ${bomVersion}\n树节点将一并清除，不可恢复。`,
    );
    if (!ok) return;

    bomMatState.deleting = true;
    try {
        const res = await HttpClient.delete(`${API_BASE}/snapshots/${snapshotId}`);
        showToast(res.message || '删除成功', 'success');
        await loadData(bomMatState.page);
    } catch (error) {
        console.error(error);
    } finally {
        bomMatState.deleting = false;
    }
}

export const pageConfig = {
    render: bomMaterialListTemplate,
    init: () => init(),
};
