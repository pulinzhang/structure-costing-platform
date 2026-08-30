/**
 * 冲压模具单价档案 — 列表 + 抽屉 CRUD
 */

import {
    dieUnitPriceTemplate,
    renderTableRows,
    renderPagination,
} from './template.js?v=5';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
    normalizePageSize,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/stamping/die-unit-prices';
const STORAGE_KEY = 'dieUnitPricePageSize';
const DRAWER_ANIMATION_MS = 300;

const pageState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    records: [],
    total: 0,
    totalPages: 1,
    isLoading: false,
    isSaving: false,
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
    }, DRAWER_ANIMATION_MS);
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
    const location = document.getElementById('dupListLocation')?.value || '';
    if (resetVehicle) {
        const vehicle = document.getElementById('dupListVehicle');
        if (vehicle) vehicle.value = '';
    }
    const data = await fetchFilters(location);
    fillSelect('dupListLocation', data.locations || [], '全部');
    if (location) {
        const locEl = document.getElementById('dupListLocation');
        if (locEl) locEl.value = location;
    }
    fillSelect(
        'dupListVehicle',
        data.vehicle_models || [],
        location ? '全部' : '全部'
    );
}

async function loadEditFilters(location, selectedVehicle) {
    const data = await fetchFilters(location || '');
    fillSelect('dupEditLocation', data.locations || [], '请选择');
    if (location) {
        const locEl = document.getElementById('dupEditLocation');
        if (locEl) locEl.value = location;
    }
    const vehicles = [...(data.vehicle_models || [])];
    if (selectedVehicle && !vehicles.includes(selectedVehicle)) {
        vehicles.unshift(selectedVehicle);
    }
    fillSelect(
        'dupEditVehicle',
        vehicles,
        location ? '请选择项目' : '请先选择基地'
    );
    if (selectedVehicle) {
        const vehicleEl = document.getElementById('dupEditVehicle');
        if (vehicleEl) vehicleEl.value = selectedVehicle;
    }
}

function applyPermissionUi() {
    if (!canOp('op:stamping-die-unit-price:create')) {
        document.getElementById('dupAddBtn')?.classList.add('hidden');
    }
}

function buildQueryParams() {
    const params = {
        page: pageState.page,
        size: pageState.pageSize,
    };
    const location = document.getElementById('dupListLocation')?.value?.trim();
    const vehicle = document.getElementById('dupListVehicle')?.value?.trim();
    const status = document.getElementById('dupListStatus')?.value?.trim();
    if (location) params.location = location;
    if (vehicle) params.vehicle_model = vehicle;
    if (status) params.status = status;
    return params;
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    const loading = document.getElementById('dupLoadingState');
    const empty = document.getElementById('dupEmptyState');
    const body = document.getElementById('dupTableBody');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        empty?.classList.add('hidden');
        if (body) body.innerHTML = '';
    }
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
        renderList();
    } catch (_) {
        pageState.records = [];
        pageState.total = 0;
        pageState.totalPages = 0;
        renderList();
    } finally {
        setLoading(false);
    }
}

function renderList() {
    const body = document.getElementById('dupTableBody');
    const empty = document.getElementById('dupEmptyState');
    const totalEl = document.getElementById('dupTotalCount');
    const pager = document.getElementById('dupPaginationBtns');
    if (body) body.innerHTML = renderTableRows(pageState.records);
    empty?.classList.toggle('hidden', pageState.records.length > 0 || pageState.isLoading);
    if (totalEl) totalEl.textContent = `共 ${pageState.total} 条`;
    if (pager) pager.innerHTML = renderPagination(pageState.page, pageState.totalPages);
}

async function openCreateDrawer() {
    if (!canOp('op:stamping-die-unit-price:create')) {
        showToast('无新增权限', 'warning');
        return;
    }
    document.getElementById('dupEditTitle').textContent = '新增模具单价';
    document.getElementById('dupEditId').value = '';
    document.getElementById('dupEditPlatePrice').value = '';
    document.getElementById('dupEditProgressivePrice').value = '';
    document.getElementById('dupEditAllocQty').value = '10';
    document.getElementById('dupEditStatus').value = 'effective';
    await loadEditFilters('', '');
    openDrawer('dupEditDrawer', 'dupEditBackdrop');
}

async function openEditDrawer(record) {
    if (!canOp('op:stamping-die-unit-price:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    document.getElementById('dupEditTitle').textContent = '编辑模具单价';
    document.getElementById('dupEditId').value = String(record.id);
    document.getElementById('dupEditPlatePrice').value = record.steel_plate_unit_price || '';
    document.getElementById('dupEditProgressivePrice').value = record.progressive_die_unit_price || '';
    document.getElementById('dupEditAllocQty').value = String(record.allocation_qty ?? 10);
    document.getElementById('dupEditStatus').value = record.status || 'effective';
    await loadEditFilters(record.location, record.vehicle_model);
    openDrawer('dupEditDrawer', 'dupEditBackdrop');
}

function openDeleteDrawer(recordId, scope) {
    if (!canOp('op:stamping-die-unit-price:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    document.getElementById('dupDeleteId').value = String(recordId);
    const scopeEl = document.getElementById('dupDeleteScope');
    if (scopeEl) scopeEl.textContent = scope || '';
    openDrawer('dupDeleteDrawer', 'dupDeleteBackdrop');
}

async function submitEdit() {
    if (pageState.isSaving) return;
    const recordId = document.getElementById('dupEditId')?.value;
    const location = document.getElementById('dupEditLocation')?.value?.trim() || '';
    const vehicleModel = document.getElementById('dupEditVehicle')?.value?.trim() || '';
    const plate = document.getElementById('dupEditPlatePrice')?.value?.trim() || '';
    const progressive = document.getElementById('dupEditProgressivePrice')?.value?.trim() || '';
    const allocationQty = document.getElementById('dupEditAllocQty')?.value?.trim() || '';
    const status = document.getElementById('dupEditStatus')?.value || 'effective';

    if (!location || !vehicleModel) {
        showToast('请选择基地和项目', 'warning');
        return;
    }
    if (!plate || !progressive) {
        showToast('请填写两档单价', 'warning');
        return;
    }
    const allocationNumber = Number(allocationQty);
    if (!allocationQty || !Number.isInteger(allocationNumber) || allocationNumber <= 0) {
        showToast('分摊万台须为正整数', 'warning');
        return;
    }

    pageState.isSaving = true;
    const btn = document.getElementById('dupSubmitEdit');
    if (btn) btn.disabled = true;
    try {
        if (recordId) {
            await HttpClient.put(`${API_BASE}/${recordId}`, {
                location,
                vehicle_model: vehicleModel,
                steel_plate_unit_price: plate,
                progressive_die_unit_price: progressive,
                allocation_qty: allocationQty,
                status,
            });
            showToast('更新成功', 'success');
        } else {
            await HttpClient.post(API_BASE, {
                location,
                vehicle_model: vehicleModel,
                steel_plate_unit_price: plate,
                progressive_die_unit_price: progressive,
                allocation_qty: allocationQty,
                status,
            });
            showToast('创建成功', 'success');
        }
        closeDrawer('dupEditDrawer', 'dupEditBackdrop');
        await loadData(recordId ? pageState.page : 1);
    } catch (_) {
        // toast 已由 HttpClient 处理
    } finally {
        pageState.isSaving = false;
        if (btn) btn.disabled = false;
    }
}

async function confirmDelete() {
    const recordId = document.getElementById('dupDeleteId')?.value;
    if (!recordId) return;
    try {
        await HttpClient.delete(`${API_BASE}/${recordId}`);
        showToast('删除成功', 'success');
        closeDrawer('dupDeleteDrawer', 'dupDeleteBackdrop');
        const nextPage = pageState.records.length <= 1 && pageState.page > 1
            ? pageState.page - 1
            : pageState.page;
        await loadData(nextPage);
    } catch (_) {
        // toast 已由 HttpClient 处理
    }
}

function bindEvents() {
    document.getElementById('dupAddBtn')?.addEventListener('click', () => openCreateDrawer());
    document.getElementById('dupListSearchBtn')?.addEventListener('click', () => loadData(1));
    document.getElementById('dupListLocation')?.addEventListener('change', () => {
        loadListFilters(true).catch(() => {});
    });
    document.getElementById('dupEditLocation')?.addEventListener('change', () => {
        const location = document.getElementById('dupEditLocation')?.value || '';
        loadEditFilters(location, '').catch(() => {});
    });

    document.getElementById('dupTableBody')?.addEventListener('click', (event) => {
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
            openDeleteDrawer(recordId, actionEl.getAttribute('data-scope') || '');
        }
    });

    document.getElementById('dupPaginationBtns')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.page-btn');
        if (!btn || btn.disabled) return;
        const nextPage = Number(btn.getAttribute('data-page'));
        if (!nextPage || nextPage === pageState.page) return;
        loadData(nextPage);
    });

    document.getElementById('dupCloseEdit')?.addEventListener('click', () => {
        closeDrawer('dupEditDrawer', 'dupEditBackdrop');
    });
    document.getElementById('dupEditBackdrop')?.addEventListener('click', () => {
        closeDrawer('dupEditDrawer', 'dupEditBackdrop');
    });
    document.getElementById('dupCancelEdit')?.addEventListener('click', () => {
        closeDrawer('dupEditDrawer', 'dupEditBackdrop');
    });
    document.getElementById('dupSubmitEdit')?.addEventListener('click', () => submitEdit());
    document.getElementById('dupEditForm')?.addEventListener('submit', (event) => {
        event.preventDefault();
        submitEdit();
    });

    document.getElementById('dupCloseDelete')?.addEventListener('click', () => {
        closeDrawer('dupDeleteDrawer', 'dupDeleteBackdrop');
    });
    document.getElementById('dupDeleteBackdrop')?.addEventListener('click', () => {
        closeDrawer('dupDeleteDrawer', 'dupDeleteBackdrop');
    });
    document.getElementById('dupCancelDelete')?.addEventListener('click', () => {
        closeDrawer('dupDeleteDrawer', 'dupDeleteBackdrop');
    });
    document.getElementById('dupConfirmDelete')?.addEventListener('click', () => confirmDelete());
}

function init() {
    pageState.pageSize = normalizePageSize(localStorage.getItem(STORAGE_KEY));
    applyPermissionUi();
    bindEvents();
    bindPageSizeSelect('dupPageSize', {
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
    render: dieUnitPriceTemplate,
    init,
};
