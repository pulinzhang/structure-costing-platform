/**
 * 项目一览 — HUD 分卡筛选 + 抽屉 CRUD，不分页
 */

import {
    fillYearMonthSelects,
    renderHudCards,
    renderTableBody,
    vehicleModelListTemplate,
} from './template.js?v=25';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=6';

const API_BASE = '/api/masterdata/vehicle-models';
const DRAWER_ANIMATION_MS = 300;

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;

const listState = {
    locations: [],
    items: [],
    asOfYear: null,
    asOfMonth: null,
    filterLocation: '',
    isLoading: false,
    editLocation: '',
    editCode: '',
    deleteLocation: '',
    deleteCode: '',
};

function canOp(code) {
    return typeof can === 'function' ? can(code) : true;
}

function readHashLocation() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return '';
    return new URLSearchParams(hash.slice(queryIndex + 1)).get('location') || '';
}

function writeHashLocation(location) {
    const next = location
        ? `/vehicle-model-list?location=${encodeURIComponent(location)}`
        : '/vehicle-model-list';
    if (window.location.hash === `#${next}` || window.location.hash === next) {
        renderAll();
        return;
    }
    window.location.hash = next;
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

function applyPermissionUi() {
    if (!canOp('op:vehicle-model-list:create')) {
        document.getElementById('vmBtnCreate')?.classList.add('hidden');
    }
    if (!canOp('op:vehicle-model-list:export')) {
        document.getElementById('vmMoreWrap')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    listState.isLoading = isLoading;
    document.getElementById('vmLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('vmEmpty')?.classList.add('hidden');
        const body = document.getElementById('vmTableBody');
        if (body) body.innerHTML = '';
    }
}

function visibleItems() {
    if (!listState.filterLocation) return listState.items;
    return listState.items.filter((row) => row.location === listState.filterLocation);
}

function renderAll() {
    const cards = document.getElementById('vmHudCards');
    if (cards) {
        cards.innerHTML = renderHudCards(
            listState.locations,
            listState.filterLocation,
            listState.asOfYear,
            listState.asOfMonth,
        );
    }
    const capsule = document.getElementById('vmFilterCapsule');
    if (capsule) {
        capsule.textContent = listState.filterLocation || '全部基地';
    }
    const body = document.getElementById('vmTableBody');
    const html = renderTableBody(
        listState.locations,
        listState.items,
        listState.filterLocation,
        canOp('op:vehicle-model-list:update'),
        canOp('op:vehicle-model-list:delete'),
    );
    if (body) body.innerHTML = html;
    const empty = document.getElementById('vmEmpty');
    const hasRows = visibleItems().length > 0;
    empty?.classList.toggle('hidden', hasRows || listState.isLoading);
}

async function loadData() {
    if (listState.isLoading) return;
    setLoading(true);
    try {
        const res = await HttpClient.get(API_BASE);
        const data = res.data || {};
        listState.locations = Array.isArray(data.locations) ? data.locations : [];
        listState.items = Array.isArray(data.items) ? data.items : [];
        listState.asOfYear = data.as_of_year;
        listState.asOfMonth = data.as_of_month;
        listState.filterLocation = readHashLocation();
        if (
            listState.filterLocation
            && !listState.locations.some((card) => card.location === listState.filterLocation)
        ) {
            listState.filterLocation = '';
        }
    } finally {
        setLoading(false);
        renderAll();
    }
}

function fillCreateLocationSelect() {
    const select = document.getElementById('vmCreateLocation');
    if (!select) return;
    const enabled = listState.locations.filter((card) => card.is_enabled);
    select.innerHTML = '<option value="">请选择基地</option>'
        + enabled.map((card) => `<option value="${esc(card.location)}">${esc(card.location)}</option>`).join('');
}

function readPeriod(prefix) {
    const effectiveYear = Number(document.getElementById(`${prefix}EffectiveYear`)?.value || 0);
    const effectiveMonth = Number(document.getElementById(`${prefix}EffectiveMonth`)?.value || 0);
    const expiryYearRaw = document.getElementById(`${prefix}ExpiryYear`)?.value || '';
    const expiryMonthRaw = document.getElementById(`${prefix}ExpiryMonth`)?.value || '';
    const expiryYear = expiryYearRaw ? Number(expiryYearRaw) : null;
    const expiryMonth = expiryMonthRaw ? Number(expiryMonthRaw) : null;
    if (!effectiveYear || !effectiveMonth) {
        showToast('请填写生效年、月', 'warning');
        return null;
    }
    if ((expiryYear && !expiryMonth) || (!expiryYear && expiryMonth)) {
        showToast('失效年与失效月必须同空或同有', 'warning');
        return null;
    }
    return {
        effective_year: effectiveYear,
        effective_month: effectiveMonth,
        expiry_year: expiryYear,
        expiry_month: expiryMonth,
    };
}

function readSuppliedUnits(prefix) {
    const raw = document.getElementById(`${prefix}SuppliedUnits`)?.value ?? '';
    if (raw === '') {
        showToast('请填写当前供货台数', 'warning');
        return null;
    }
    const value = Number(raw);
    if (!Number.isInteger(value) || value < 0) {
        showToast('当前供货台数必须为 ≥0 的整数（台）', 'warning');
        return null;
    }
    return value;
}

function bindHud() {
    document.getElementById('vmHudCards')?.addEventListener('click', (event) => {
        const allBtn = event.target.closest('[data-action="filter-all"]');
        if (allBtn) {
            writeHashLocation('');
            return;
        }
        const locBtn = event.target.closest('[data-action="filter-location"]');
        if (!locBtn) return;
        const location = locBtn.getAttribute('data-location') || '';
        if (listState.filterLocation === location) {
            writeHashLocation('');
            return;
        }
        writeHashLocation(location);
    });
}

function bindCreateDrawer() {
    const close = () => closeDrawer('vmCreateDrawer', 'vmCreateBackdrop');
    document.getElementById('vmBtnCreate')?.addEventListener('click', () => {
        fillCreateLocationSelect();
        const clock = new Date();
        fillYearMonthSelects('vmCreate', clock.getFullYear(), clock.getMonth() + 1, null, null);
        const code = document.getElementById('vmCreateCode');
        if (code) code.value = '';
        const supplied = document.getElementById('vmCreateSuppliedUnits');
        if (supplied) supplied.value = '0';
        openDrawer('vmCreateDrawer', 'vmCreateBackdrop');
    });
    document.getElementById('vmCloseCreate')?.addEventListener('click', close);
    document.getElementById('vmCancelCreate')?.addEventListener('click', close);
    document.getElementById('vmCreateBackdrop')?.addEventListener('click', close);
    document.getElementById('vmSubmitCreate')?.addEventListener('click', async () => {
        const location = document.getElementById('vmCreateLocation')?.value?.trim() || '';
        const vehicleModel = document.getElementById('vmCreateCode')?.value?.trim() || '';
        if (!location) {
            showToast('请选择基地', 'warning');
            return;
        }
        if (!vehicleModel) {
            showToast('请填写项目代号', 'warning');
            return;
        }
        const period = readPeriod('vmCreate');
        if (!period) return;
        const suppliedUnits = readSuppliedUnits('vmCreate');
        if (suppliedUnits === null) return;
        try {
            await HttpClient.post(API_BASE, {
                location,
                vehicle_model: vehicleModel,
                current_supplied_units: suppliedUnits,
                ...period,
            });
            showToast('创建成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function bindEditDrawer() {
    const close = () => closeDrawer('vmEditDrawer', 'vmEditBackdrop');
    document.getElementById('vmCloseEdit')?.addEventListener('click', close);
    document.getElementById('vmCancelEdit')?.addEventListener('click', close);
    document.getElementById('vmEditBackdrop')?.addEventListener('click', close);
    document.getElementById('vmSubmitEdit')?.addEventListener('click', async () => {
        const location = listState.editLocation;
        const code = listState.editCode;
        if (!location || !code) return;
        const period = readPeriod('vmEdit');
        if (!period) return;
        const suppliedUnits = readSuppliedUnits('vmEdit');
        if (suppliedUnits === null) return;
        try {
            await HttpClient.patch(
                `${API_BASE}/${encodeURIComponent(location)}/${encodeURIComponent(code)}`,
                {
                    ...period,
                    current_supplied_units: suppliedUnits,
                },
            );
            showToast('更新成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function openEditDrawer(location, vehicleModel) {
    const row = listState.items.find(
        (item) => item.location === location && item.vehicle_model === vehicleModel,
    );
    if (!row) return;
    listState.editLocation = location;
    listState.editCode = vehicleModel;
    const locInput = document.getElementById('vmEditLocation');
    const codeInput = document.getElementById('vmEditCode');
    if (locInput) locInput.value = location;
    if (codeInput) codeInput.value = vehicleModel;
    fillYearMonthSelects(
        'vmEdit',
        row.effective_year,
        row.effective_month,
        row.expiry_year,
        row.expiry_month,
    );
    const supplied = document.getElementById('vmEditSuppliedUnits');
    if (supplied) supplied.value = String(row.current_supplied_units ?? 0);
    openDrawer('vmEditDrawer', 'vmEditBackdrop');
}

function bindDeleteDrawer() {
    const close = () => closeDrawer('vmDeleteDrawer', 'vmDeleteBackdrop');
    document.getElementById('vmCloseDelete')?.addEventListener('click', close);
    document.getElementById('vmCancelDelete')?.addEventListener('click', close);
    document.getElementById('vmDeleteBackdrop')?.addEventListener('click', close);
    document.getElementById('vmConfirmDelete')?.addEventListener('click', async () => {
        const location = listState.deleteLocation;
        const code = listState.deleteCode;
        if (!location || !code) return;
        try {
            await HttpClient.delete(
                `${API_BASE}/${encodeURIComponent(location)}/${encodeURIComponent(code)}`,
            );
            showToast('删除成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function openDeleteDrawer(location, vehicleModel) {
    listState.deleteLocation = location;
    listState.deleteCode = vehicleModel;
    const lead = document.getElementById('vmDeleteLead');
    if (lead) lead.textContent = `${location} / ${vehicleModel}`;
    openDrawer('vmDeleteDrawer', 'vmDeleteBackdrop');
}

function bindTableActions() {
    document.getElementById('vmTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        const row = btn.closest('tr');
        const location = row?.getAttribute('data-location') || '';
        const vehicleModel = row?.getAttribute('data-vehicle-model') || '';
        if (!location || !vehicleModel) return;
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            openEditDrawer(location, vehicleModel);
            return;
        }
        if (action === 'delete') {
            openDeleteDrawer(location, vehicleModel);
        }
    });
}

async function exportExcel() {
    if (!canOp('op:vehicle-model-list:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const btn = document.getElementById('vmBtnExport');
    try {
        if (btn) btn.disabled = true;
        const params = {};
        if (listState.filterLocation) params.location = listState.filterLocation;
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '项目一览.xlsx',
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
        if (btn) btn.disabled = false;
    }
}

function init() {
    applyPermissionUi();
    bindHud();
    bindCreateDrawer();
    bindEditDrawer();
    bindDeleteDrawer();
    bindTableActions();
    moreMenu = bindMoreMenu({
        wrapId: 'vmMoreWrap',
        btnId: 'vmMoreBtn',
        menuId: 'vmMoreMenu',
    });
    document.getElementById('vmBtnExport')?.addEventListener('click', () => {
        moreMenu?.close();
        exportExcel();
    });
    loadData();
}

export const pageConfig = {
    render: vehicleModelListTemplate,
    init,
    destroy() {
        moreMenu?.unbind();
        moreMenu = null;
    },
};
