/**
 * 冲压检具费列表
 */

import {
    gaugeFeeListTemplate,
    renderTableRows,
    renderPagination,
    updateGaugeFeeHud,
    updateGaugeFeeFilterCapsules,
} from './template.js?v=9';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
    normalizePageSize,
} from '../../../../page-size.js?v=2';
import { setSearchBusy } from '../../../../search-busy.js?v=1';

const API_BASE = '/api/stamping/gauge-fees';
const STORAGE_KEY = 'gaugeFeePageSize';
const DRAWER_MS = 300;

const pageState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    records: [],
    total: 0,
    totalPages: 1,
    isLoading: false,
    isSaving: false,
    summary: null,
    advancedOpen: false,
};

function canOp(code) {
    return typeof can === 'function' ? can(code) : true;
}

function openDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.style.display = 'flex';
    if (backdrop) backdrop.style.display = 'block';
    void drawer.offsetWidth;
    drawer.classList.remove('translate-x-full');
    drawer.classList.add('translate-x-0');
}

function closeDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.classList.remove('translate-x-0');
    drawer.classList.add('translate-x-full');
    setTimeout(() => {
        drawer.style.display = 'none';
        if (backdrop) backdrop.style.display = 'none';
    }, DRAWER_MS);
}

function fillSelect(id, values, placeholder) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    const options = [`<option value="">${esc(placeholder)}</option>`];
    (values || []).forEach((value) => {
        const text = String(value);
        options.push(
            `<option value="${esc(text)}"${text === current ? ' selected' : ''}>${esc(text)}</option>`
        );
    });
    select.innerHTML = options.join('');
}

async function fetchFilters(location) {
    const res = await HttpClient.get(`${API_BASE}/filters`, {
        params: location ? { location } : {},
    });
    return res.data || {};
}

async function loadListFilters(resetVehicle = false) {
    const location = document.getElementById('gflLocation')?.value || '';
    if (resetVehicle) {
        const vehicle = document.getElementById('gflVehicle');
        if (vehicle) vehicle.value = '';
    }
    const data = await fetchFilters(location);
    fillSelect('gflLocation', data.locations || [], '全部');
    if (location) {
        const locEl = document.getElementById('gflLocation');
        if (locEl) locEl.value = location;
    }
    fillSelect('gflVehicle', data.vehicle_models || [], '全部');
}

function buildQueryParams() {
    const params = { page: pageState.page, size: pageState.pageSize };
    const location = document.getElementById('gflLocation')?.value?.trim();
    const vehicle = document.getElementById('gflVehicle')?.value?.trim();
    const partNumber = document.getElementById('gflPartNumber')?.value?.trim();
    const status = document.getElementById('gflStatus')?.value?.trim();
    if (location) params.location = location;
    if (vehicle) params.vehicle_model = vehicle;
    if (partNumber) params.part_number = partNumber;
    if (status) params.status = status;
    return params;
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    setSearchBusy('gflSearchBtn', isLoading);
    document.getElementById('gflLoadingState')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('gflEmptyState')?.classList.add('hidden');
        const body = document.getElementById('gflTableBody');
        if (body) body.innerHTML = '';
    }
}

function renderList() {
    const body = document.getElementById('gflTableBody');
    if (body) body.innerHTML = renderTableRows(pageState.records);
    document.getElementById('gflEmptyState')?.classList.toggle(
        'hidden',
        pageState.records.length > 0 || pageState.isLoading
    );
    const totalEl = document.getElementById('gflTotalCount');
    if (totalEl) totalEl.textContent = `共 ${pageState.total} 条`;
    const pager = document.getElementById('gflPaginationBtns');
    if (pager) pager.innerHTML = renderPagination(pageState.page, pageState.totalPages);
    updateGaugeFeeHud(pageState.summary);
    updateGaugeFeeFilterCapsules();
}

async function loadData(page = pageState.page) {
    if (pageState.isLoading) return;
    pageState.page = page;
    setLoading(true);
    try {
        const res = await HttpClient.get(API_BASE, { params: buildQueryParams() });
        const data = res.data || {};
        pageState.records = Array.isArray(data.items) ? data.items : [];
        pageState.total = data.total || 0;
        pageState.totalPages = data.total_pages || 0;
        pageState.summary = data.filters?.summary || null;
        renderList();
    } catch (_) {
        pageState.records = [];
        pageState.total = 0;
        pageState.totalPages = 0;
        pageState.summary = null;
        renderList();
    } finally {
        setLoading(false);
    }
}

function openEditDrawer(record) {
    if (!canOp('op:stamping-gauge-fee:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    document.getElementById('gflEditId').value = String(record.id);
    const scopeEl = document.getElementById('gflEditScope');
    if (scopeEl) {
        scopeEl.textContent = `${record.location} / ${record.vehicle_model} / ${record.part_number}`;
    }
    document.getElementById('gflEditGaugeFee').value = record.gauge_fee ?? '';
    document.getElementById('gflEditAllocQty').value = String(record.allocation_qty ?? 10);
    document.getElementById('gflEditStatus').value = record.status || 'effective';
    openDrawer('gflEditDrawer', 'gflEditBackdrop');
}

function openRowDeleteDrawer(recordId, scope) {
    if (!canOp('op:stamping-gauge-fee:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    document.getElementById('gflDeleteMode').value = 'row';
    document.getElementById('gflDeleteId').value = String(recordId);
    document.getElementById('gflDeleteTitle').textContent = '删除检具费';
    document.getElementById('gflDeleteHint').innerHTML =
        `确定删除 <span class="font-mono text-white">${esc(scope)}</span> 这一条？`;
    openDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
}

function openScopeDeleteDrawer() {
    if (!canOp('op:stamping-gauge-fee:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const location = document.getElementById('gflLocation')?.value?.trim();
    const vehicle = document.getElementById('gflVehicle')?.value?.trim();
    if (!location || !vehicle) {
        showToast('批量删除须同时选定基地和项目', 'warning');
        return;
    }
    document.getElementById('gflDeleteMode').value = 'scope';
    document.getElementById('gflDeleteId').value = '';
    document.getElementById('gflDeleteTitle').textContent = '批量删除';
    document.getElementById('gflDeleteHint').innerHTML =
        `将删除 <span class="font-mono text-white">${esc(`${location} / ${vehicle}`)}</span> 下全部检具费档案。`;
    openDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
}

async function submitEdit() {
    if (pageState.isSaving) return;
    const recordId = document.getElementById('gflEditId')?.value;
    const gaugeFee = document.getElementById('gflEditGaugeFee')?.value?.trim() || '';
    const allocationQty = document.getElementById('gflEditAllocQty')?.value?.trim() || '';
    const status = document.getElementById('gflEditStatus')?.value || 'effective';
    if (!recordId) return;
    if (!gaugeFee) {
        showToast('请填写检具费', 'warning');
        return;
    }
    const allocationNumber = Number(allocationQty);
    if (!allocationQty || !Number.isInteger(allocationNumber) || allocationNumber <= 0) {
        showToast('分摊万台须为正整数', 'warning');
        return;
    }
    pageState.isSaving = true;
    const btn = document.getElementById('gflSubmitEdit');
    if (btn) btn.disabled = true;
    try {
        await HttpClient.put(`${API_BASE}/${recordId}`, {
            gauge_fee: gaugeFee,
            allocation_qty: allocationQty,
            status,
        });
        showToast('更新成功', 'success');
        closeDrawer('gflEditDrawer', 'gflEditBackdrop');
        await loadData(pageState.page);
    } catch (_) {
        /* toast 已由 HttpClient 处理 */
    } finally {
        pageState.isSaving = false;
        if (btn) btn.disabled = false;
    }
}

async function confirmDelete() {
    const mode = document.getElementById('gflDeleteMode')?.value;
    try {
        if (mode === 'row') {
            const recordId = document.getElementById('gflDeleteId')?.value;
            if (!recordId) return;
            await HttpClient.delete(`${API_BASE}/${recordId}`);
            showToast('删除成功', 'success');
            closeDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
            const nextPage = pageState.records.length <= 1 && pageState.page > 1
                ? pageState.page - 1
                : pageState.page;
            await loadData(nextPage);
            return;
        }
        const location = document.getElementById('gflLocation')?.value?.trim();
        const vehicle = document.getElementById('gflVehicle')?.value?.trim();
        if (!location || !vehicle) return;
        await HttpClient.delete(`${API_BASE}/scope`, {
            params: { location, vehicle_model: vehicle },
        });
        showToast('删除成功', 'success');
        closeDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
        await loadData(1);
    } catch (_) {
        /* toast 已由 HttpClient 处理 */
    }
}

async function exportExcel() {
    if (!canOp('op:stamping-gauge-fee:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const btn = document.getElementById('gflExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中`;
    }
    try {
        const params = buildQueryParams();
        delete params.page;
        delete params.size;
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '冲压检具费.xlsx',
        });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
        showToast(`导出成功: ${filename}`, 'success');
    } catch (error) {
        if (!error.status) showToast(error.message || '导出失败', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

function setAdvancedOpen(isOpen) {
    pageState.advancedOpen = isOpen;
    document.getElementById('gflAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('gflAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

async function resetFilters() {
    const location = document.getElementById('gflLocation');
    const vehicle = document.getElementById('gflVehicle');
    const partNumber = document.getElementById('gflPartNumber');
    const status = document.getElementById('gflStatus');
    if (location) location.value = '';
    if (vehicle) vehicle.value = '';
    if (partNumber) partNumber.value = '';
    if (status) status.value = '';
    await loadListFilters(true);
    updateGaugeFeeFilterCapsules();
    await loadData(1);
}

function bindEvents() {
    document.getElementById('gflSearchBtn')?.addEventListener('click', () => loadData(1));
    document.getElementById('gflResetBtn')?.addEventListener('click', () => {
        resetFilters().catch(() => {});
    });
    document.getElementById('gflToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!pageState.advancedOpen);
    });
    document.getElementById('gflLocation')?.addEventListener('change', () => {
        loadListFilters(true)
            .then(() => {
                updateGaugeFeeFilterCapsules();
                return loadData(1);
            })
            .catch(() => {});
    });
    document.getElementById('gflVehicle')?.addEventListener('change', () => {
        updateGaugeFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('gflStatus')?.addEventListener('change', () => {
        updateGaugeFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('gflPartNumber')?.addEventListener('input', () => {
        updateGaugeFeeFilterCapsules();
    });
    document.getElementById('gflPartNumber')?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        loadData(1);
    });
    document.getElementById('gflPaginationBtns')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.page-btn');
        if (!btn || btn.disabled) return;
        const nextPage = Number(btn.getAttribute('data-page'));
        if (!nextPage || nextPage === pageState.page) return;
        loadData(nextPage);
    });
    document.getElementById('gflTableBody')?.addEventListener('click', (event) => {
        const actionEl = event.target.closest('[data-action]');
        if (!actionEl) return;
        event.preventDefault();
        const action = actionEl.getAttribute('data-action');
        const recordId = Number(actionEl.getAttribute('data-id'));
        if (action === 'edit') {
            const record = pageState.records.find((row) => row.id === recordId);
            if (record) openEditDrawer(record);
            return;
        }
        if (action === 'delete') {
            openRowDeleteDrawer(recordId, actionEl.getAttribute('data-scope') || '');
        }
    });
    document.getElementById('gflExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('gflDeleteScopeBtn')?.addEventListener('click', () => openScopeDeleteDrawer());
    document.getElementById('gflCloseEdit')?.addEventListener('click', () => {
        closeDrawer('gflEditDrawer', 'gflEditBackdrop');
    });
    document.getElementById('gflEditBackdrop')?.addEventListener('click', () => {
        closeDrawer('gflEditDrawer', 'gflEditBackdrop');
    });
    document.getElementById('gflCancelEdit')?.addEventListener('click', () => {
        closeDrawer('gflEditDrawer', 'gflEditBackdrop');
    });
    document.getElementById('gflSubmitEdit')?.addEventListener('click', () => submitEdit());
    document.getElementById('gflEditForm')?.addEventListener('submit', (event) => {
        event.preventDefault();
        submitEdit();
    });
    document.getElementById('gflCancelDelete')?.addEventListener('click', () => {
        closeDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
    });
    document.getElementById('gflDeleteBackdrop')?.addEventListener('click', () => {
        closeDrawer('gflDeleteDrawer', 'gflDeleteBackdrop');
    });
    document.getElementById('gflConfirmDelete')?.addEventListener('click', () => confirmDelete());
}

function init() {
    pageState.pageSize = normalizePageSize(localStorage.getItem(STORAGE_KEY));
    bindEvents();
    bindPageSizeSelect('gflPageSize', {
        getSize: () => pageState.pageSize,
        setSize: (size) => {
            pageState.pageSize = size;
            localStorage.setItem(STORAGE_KEY, String(size));
        },
        onChange: () => loadData(1),
    });
    loadListFilters().then(() => loadData(1)).catch(() => loadData(1));
}

export const pageConfig = {
    render: gaugeFeeListTemplate,
    init,
};
