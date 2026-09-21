/**
 * 基地主数据页 — /api/masterdata/locations
 */

import {
    locationTemplate,
    renderLocationRows,
    renderAliasItems,
} from './template.js?v=23';

const API_BASE = '/api/masterdata/locations';
const DRAWER_ANIMATION_MS = 300;

const locationState = {
    records: [],
    isLoading: false,
    editLocation: '',
    toggleLocation: '',
    toggleNextEnabled: false,
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

function applyPermissionUi() {
    if (!canOp('op:location:create')) {
        document.getElementById('btnAddLocation')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    locationState.isLoading = isLoading;
    const loading = document.getElementById('locationLoading');
    const empty = document.getElementById('locationEmpty');
    const body = document.getElementById('locationTableBody');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        empty?.classList.add('hidden');
        if (body) body.innerHTML = '';
    }
}

function renderList() {
    const body = document.getElementById('locationTableBody');
    const empty = document.getElementById('locationEmpty');
    const hasRows = locationState.records.length > 0;
    if (body) body.innerHTML = renderLocationRows(locationState.records);
    empty?.classList.toggle('hidden', hasRows || locationState.isLoading);
}

async function loadData() {
    if (locationState.isLoading) return;
    setLoading(true);
    try {
        const res = await HttpClient.get(API_BASE);
        locationState.records = Array.isArray(res.data) ? res.data : [];
        renderList();
    } catch (_) {
        locationState.records = [];
        renderList();
    } finally {
        setLoading(false);
    }
}

function parseAliasLines(raw) {
    return String(raw || '')
        .split(/[\r\n，,]+/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function bindCreateDrawer() {
    const open = () => {
        const nameInput = document.getElementById('locationCreateName');
        const aliasInput = document.getElementById('locationCreateAliases');
        if (nameInput) nameInput.value = '';
        if (aliasInput) aliasInput.value = '';
        openDrawer('locationCreateDrawer', 'locationCreateBackdrop');
        nameInput?.focus();
    };
    const close = () => closeDrawer('locationCreateDrawer', 'locationCreateBackdrop');
    document.getElementById('btnAddLocation')?.addEventListener('click', open);
    document.getElementById('closeLocationCreateDrawer')?.addEventListener('click', close);
    document.getElementById('cancelLocationCreateBtn')?.addEventListener('click', close);
    document.getElementById('locationCreateBackdrop')?.addEventListener('click', close);
    document.getElementById('submitLocationCreateBtn')?.addEventListener('click', async () => {
        const name = document.getElementById('locationCreateName')?.value?.trim() || '';
        const aliases = parseAliasLines(document.getElementById('locationCreateAliases')?.value || '');
        if (!name) {
            showToast('请填写基地名', 'warning');
            return;
        }
        if (!aliases.length) {
            showToast('请至少填写一条别名', 'warning');
            return;
        }
        try {
            await HttpClient.post(API_BASE, { location: name, aliases });
            showToast('创建成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function findRecord(location) {
    return locationState.records.find((row) => row.location === location) || null;
}

function bindEditDrawer() {
    const close = () => {
        locationState.editLocation = '';
        closeDrawer('locationEditDrawer', 'locationEditBackdrop');
    };
    document.getElementById('closeLocationEditDrawer')?.addEventListener('click', close);
    document.getElementById('locationEditBackdrop')?.addEventListener('click', close);
    document.getElementById('locationEditAliasForm')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const location = locationState.editLocation;
        const alias = document.getElementById('locationEditAliasInput')?.value?.trim() || '';
        if (!location || !alias) {
            showToast('请填写别名', 'warning');
            return;
        }
        try {
            await HttpClient.post(`${API_BASE}/${encodeURIComponent(location)}/aliases`, { alias });
            showToast('别名已添加', 'success');
            const input = document.getElementById('locationEditAliasInput');
            if (input) input.value = '';
            await loadData();
            refreshEditDrawer(location);
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
    document.getElementById('locationEditAliasList')?.addEventListener('click', async (event) => {
        const btn = event.target.closest('[data-action="delete-alias"]');
        if (!btn) return;
        const location = locationState.editLocation;
        const alias = btn.getAttribute('data-alias') || '';
        if (!location || !alias) return;
        try {
            await HttpClient.delete(
                `${API_BASE}/${encodeURIComponent(location)}/aliases/${encodeURIComponent(alias)}`,
            );
            showToast('别名已删除', 'success');
            await loadData();
            refreshEditDrawer(location);
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function refreshEditDrawer(location) {
    const record = findRecord(location);
    const nameInput = document.getElementById('locationEditName');
    const list = document.getElementById('locationEditAliasList');
    const count = document.getElementById('locationEditAliasCount');
    const aliases = record?.aliases || [];
    if (nameInput) nameInput.value = location;
    if (count) count.textContent = String(aliases.length);
    if (list) {
        list.innerHTML = renderAliasItems(aliases, canOp('op:location:update'));
    }
    const addForm = document.getElementById('locationEditAliasForm');
    addForm?.classList.toggle('hidden', !canOp('op:location:create'));
}

function openEditDrawer(location) {
    locationState.editLocation = location;
    const input = document.getElementById('locationEditAliasInput');
    if (input) input.value = '';
    refreshEditDrawer(location);
    openDrawer('locationEditDrawer', 'locationEditBackdrop');
    input?.focus();
}

function bindDeleteDrawer() {
    const close = () => closeDrawer('locationDeleteDrawer', 'locationDeleteBackdrop');
    document.getElementById('closeLocationDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelLocationDeleteBtn')?.addEventListener('click', close);
    document.getElementById('locationDeleteBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmLocationDeleteBtn')?.addEventListener('click', async () => {
        const location = document.getElementById('locationDeleteName')?.textContent || '';
        if (!location) return;
        try {
            await HttpClient.delete(`${API_BASE}/${encodeURIComponent(location)}`);
            showToast('删除成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function openDeleteDrawer(location) {
    const nameEl = document.getElementById('locationDeleteName');
    if (nameEl) nameEl.textContent = location;
    openDrawer('locationDeleteDrawer', 'locationDeleteBackdrop');
}

function bindToggleDrawer() {
    const close = () => {
        locationState.toggleLocation = '';
        closeDrawer('locationToggleDrawer', 'locationToggleBackdrop');
    };
    document.getElementById('closeLocationToggleDrawer')?.addEventListener('click', close);
    document.getElementById('cancelLocationToggleBtn')?.addEventListener('click', close);
    document.getElementById('locationToggleBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmLocationToggleBtn')?.addEventListener('click', async () => {
        const location = locationState.toggleLocation;
        if (!location) return;
        const nextEnabled = locationState.toggleNextEnabled;
        try {
            await HttpClient.patch(`${API_BASE}/${encodeURIComponent(location)}`, {
                is_enabled: nextEnabled,
            });
            showToast(nextEnabled ? '已启用' : '已禁用', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function openToggleDrawer(location, currentlyEnabled) {
    const nextEnabled = !currentlyEnabled;
    locationState.toggleLocation = location;
    locationState.toggleNextEnabled = nextEnabled;

    const titleEl = document.getElementById('locationToggleTitle');
    const leadEl = document.getElementById('locationToggleLead');
    const nameEl = document.getElementById('locationToggleName');
    const hintEl = document.getElementById('locationToggleHint');
    const confirmBtn = document.getElementById('confirmLocationToggleBtn');
    if (titleEl) titleEl.textContent = nextEnabled ? '确认启用' : '确认禁用';
    if (leadEl) leadEl.textContent = nextEnabled ? '确认启用基地' : '确认禁用基地';
    if (nameEl) nameEl.textContent = location;
    if (hintEl) {
        hintEl.textContent = nextEnabled
            ? '启用后可作为采购基地写入，并出现在上传/计算下拉里。'
            : '禁用后不能再按此基地写入或开引擎；列表筛选仍可见。';
    }
    if (confirmBtn) confirmBtn.textContent = nextEnabled ? '确认启用' : '确认禁用';
    openDrawer('locationToggleDrawer', 'locationToggleBackdrop');
}

function bindTableActions() {
    document.getElementById('locationTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        const row = btn.closest('tr');
        const location = row?.getAttribute('data-location') || '';
        if (!location) return;
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            openEditDrawer(location);
            return;
        }
        if (action === 'toggle') {
            const enabled = btn.getAttribute('data-enabled') === '1';
            openToggleDrawer(location, enabled);
            return;
        }
        if (action === 'delete') {
            openDeleteDrawer(location);
        }
    });
}

function init() {
    applyPermissionUi();
    bindCreateDrawer();
    bindEditDrawer();
    bindDeleteDrawer();
    bindToggleDrawer();
    bindTableActions();
    loadData();
}

export const pageConfig = {
    render: locationTemplate,
    init,
};
