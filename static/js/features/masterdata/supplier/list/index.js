/**
 * 供应商一览 — 面板 + 表 + 抽屉；搜索 / 分页 / 导出 / 删除
 */

import {
    bindPageSizeSelect,
    DEFAULT_PAGE_SIZE,
    normalizePageSize,
} from '../../../../page-size.js?v=2';
import { setSearchBusy } from '../../../../search-busy.js?v=1';
import {
    renderAliasItems,
    renderPagination,
    renderSupplierRows,
    supplierListTemplate,
} from './template.js?v=3';

const API_BASE = '/api/masterdata/suppliers';
const DRAWER_ANIMATION_MS = 300;

const listState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 0,
    keyword: '',
    isEnabled: '',
    isLoading: false,
    editFullName: '',
    toggleFullName: '',
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
    if (!canOp('op:supplier-list:create')) {
        document.getElementById('supplierBtnCreate')?.classList.add('hidden');
    }
    if (!canOp('op:supplier-list:export')) {
        document.getElementById('supplierBtnExport')?.classList.add('hidden');
    }
    if (!canOp('op:supplier-list:update')) {
        document.getElementById('submitSupplierEditBtn')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    listState.isLoading = isLoading;
    setSearchBusy('supplierBtnSearch', isLoading);
    document.getElementById('supplierLoadingState')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('supplierEmptyState')?.classList.add('hidden');
        const body = document.getElementById('supplierTableBody');
        if (body) body.innerHTML = '';
    }
}

function renderStatusCapsules() {
    document.querySelectorAll('.supplier-status-capsule').forEach((btn) => {
        const value = btn.getAttribute('data-enabled-filter') ?? '';
        const selected = value === listState.isEnabled;
        btn.className = selected
            ? 'supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#d32f2f]/50 bg-[#1a080a] text-[#d32f2f]'
            : 'supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2c2c2c] text-[#616161] hover:text-[#9e9e9e]';
    });
}

function renderList() {
    const body = document.getElementById('supplierTableBody');
    const empty = document.getElementById('supplierEmptyState');
    const hint = document.getElementById('supplierEmptyHint');
    const totalEl = document.getElementById('supplierTotalCount');
    const btns = document.getElementById('supplierPaginationBtns');
    const hasRows = listState.records.length > 0;
    if (body) body.innerHTML = renderSupplierRows(listState.records);
    empty?.classList.toggle('hidden', hasRows || listState.isLoading);
    if (hint) {
        const filtered = Boolean(listState.keyword) || listState.isEnabled !== '';
        hint.textContent = filtered
            ? '请调整关键字或状态筛选'
            : '点右上角新增，或到上传页导入 Excel';
    }
    if (totalEl) totalEl.textContent = `共 ${listState.total} 条`;
    if (btns) btns.innerHTML = renderPagination(listState.page, listState.totalPages);
    renderStatusCapsules();
}

function buildQueryParams() {
    const params = {
        page: listState.page,
        size: listState.pageSize,
    };
    if (listState.keyword) params.q = listState.keyword;
    if (listState.isEnabled === 'true') params.is_enabled = true;
    if (listState.isEnabled === 'false') params.is_enabled = false;
    return params;
}

async function loadData() {
    if (listState.isLoading) return;
    setLoading(true);
    try {
        const res = await HttpClient.get(API_BASE, { params: buildQueryParams() });
        const data = res.data || {};
        listState.records = Array.isArray(data.items) ? data.items : [];
        listState.total = data.total || 0;
        listState.page = data.page || listState.page;
        listState.pageSize = data.page_size || listState.pageSize;
        listState.totalPages = data.total_pages || 0;
        renderList();
    } catch (_) {
        listState.records = [];
        listState.total = 0;
        listState.totalPages = 0;
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
        ['supplierCreateAbbreviation', 'supplierCreateFullName', 'supplierCreateErpCode'].forEach((id) => {
            const input = document.getElementById(id);
            if (input) input.value = '';
        });
        const aliasInput = document.getElementById('supplierCreateAliases');
        if (aliasInput) aliasInput.value = '';
        openDrawer('supplierCreateDrawer', 'supplierCreateBackdrop');
        document.getElementById('supplierCreateAbbreviation')?.focus();
    };
    const close = () => closeDrawer('supplierCreateDrawer', 'supplierCreateBackdrop');
    document.getElementById('supplierBtnCreate')?.addEventListener('click', open);
    document.getElementById('closeSupplierCreateDrawer')?.addEventListener('click', close);
    document.getElementById('cancelSupplierCreateBtn')?.addEventListener('click', close);
    document.getElementById('supplierCreateBackdrop')?.addEventListener('click', close);
    document.getElementById('submitSupplierCreateBtn')?.addEventListener('click', async () => {
        const abbreviation = document.getElementById('supplierCreateAbbreviation')?.value?.trim() || '';
        const fullName = document.getElementById('supplierCreateFullName')?.value?.trim() || '';
        const erpCode = document.getElementById('supplierCreateErpCode')?.value?.trim() || '';
        const aliases = parseAliasLines(document.getElementById('supplierCreateAliases')?.value || '');
        if (!abbreviation) {
            showToast('请填写缩写', 'warning');
            return;
        }
        if (!fullName) {
            showToast('请填写工商名称', 'warning');
            return;
        }
        if (!erpCode) {
            showToast('请填写 ERP 代码', 'warning');
            return;
        }
        try {
            await HttpClient.post(API_BASE, {
                abbreviation,
                full_name: fullName,
                erp_code: erpCode,
                aliases,
            });
            showToast('创建成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function findRecord(fullName) {
    return listState.records.find((row) => row.full_name === fullName) || null;
}

function bindEditDrawer() {
    const close = () => {
        listState.editFullName = '';
        closeDrawer('supplierEditDrawer', 'supplierEditBackdrop');
    };
    document.getElementById('closeSupplierEditDrawer')?.addEventListener('click', close);
    document.getElementById('supplierEditBackdrop')?.addEventListener('click', close);
    document.getElementById('supplierEditAliasForm')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const fullName = listState.editFullName;
        const alias = document.getElementById('supplierEditAliasInput')?.value?.trim() || '';
        if (!fullName || !alias) {
            showToast('请填写别名', 'warning');
            return;
        }
        try {
            await HttpClient.post(`${API_BASE}/${encodeURIComponent(fullName)}/aliases`, { alias });
            showToast('别名已添加', 'success');
            const input = document.getElementById('supplierEditAliasInput');
            if (input) input.value = '';
            await loadData();
            refreshEditDrawer(fullName);
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
    document.getElementById('supplierEditAliasList')?.addEventListener('click', async (event) => {
        const btn = event.target.closest('[data-action="delete-alias"]');
        if (!btn) return;
        const fullName = listState.editFullName;
        const alias = btn.getAttribute('data-alias') || '';
        if (!fullName || !alias) return;
        try {
            await HttpClient.delete(
                `${API_BASE}/${encodeURIComponent(fullName)}/aliases/${encodeURIComponent(alias)}`,
            );
            showToast('别名已删除', 'success');
            await loadData();
            refreshEditDrawer(fullName);
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
    document.getElementById('submitSupplierEditBtn')?.addEventListener('click', async () => {
        const oldName = listState.editFullName;
        if (!oldName) return;
        const abbreviation = document.getElementById('supplierEditAbbreviation')?.value?.trim() || '';
        const fullName = document.getElementById('supplierEditFullName')?.value?.trim() || '';
        const erpCode = document.getElementById('supplierEditErpCode')?.value?.trim() || '';
        if (!abbreviation || !fullName || !erpCode) {
            showToast('请填写缩写、工商名称和 ERP 代码', 'warning');
            return;
        }
        try {
            await HttpClient.patch(`${API_BASE}/${encodeURIComponent(oldName)}`, {
                abbreviation,
                full_name: fullName,
                erp_code: erpCode,
            });
            showToast('更新成功', 'success');
            listState.editFullName = fullName;
            await loadData();
            refreshEditDrawer(fullName);
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function refreshEditDrawer(fullName) {
    const record = findRecord(fullName);
    const aliases = record?.aliases || [];
    const abbr = document.getElementById('supplierEditAbbreviation');
    const nameInput = document.getElementById('supplierEditFullName');
    const erp = document.getElementById('supplierEditErpCode');
    const list = document.getElementById('supplierEditAliasList');
    const count = document.getElementById('supplierEditAliasCount');
    if (abbr) abbr.value = record?.abbreviation || '';
    if (nameInput) nameInput.value = fullName;
    if (erp) erp.value = record?.erp_code || '';
    if (count) count.textContent = String(aliases.length);
    if (list) {
        list.innerHTML = renderAliasItems(aliases, canOp('op:supplier-list:update'));
    }
    const addForm = document.getElementById('supplierEditAliasForm');
    addForm?.classList.toggle('hidden', !canOp('op:supplier-list:create'));
}

function openEditDrawer(fullName) {
    listState.editFullName = fullName;
    const input = document.getElementById('supplierEditAliasInput');
    if (input) input.value = '';
    refreshEditDrawer(fullName);
    openDrawer('supplierEditDrawer', 'supplierEditBackdrop');
    input?.focus();
}

function bindToggleDrawer() {
    const close = () => {
        listState.toggleFullName = '';
        closeDrawer('supplierToggleDrawer', 'supplierToggleBackdrop');
    };
    document.getElementById('closeSupplierToggleDrawer')?.addEventListener('click', close);
    document.getElementById('cancelSupplierToggleBtn')?.addEventListener('click', close);
    document.getElementById('supplierToggleBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmSupplierToggleBtn')?.addEventListener('click', async () => {
        const fullName = listState.toggleFullName;
        if (!fullName) return;
        const nextEnabled = listState.toggleNextEnabled;
        try {
            await HttpClient.patch(`${API_BASE}/${encodeURIComponent(fullName)}`, {
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

function openToggleDrawer(fullName, currentlyEnabled) {
    const nextEnabled = !currentlyEnabled;
    listState.toggleFullName = fullName;
    listState.toggleNextEnabled = nextEnabled;
    const titleEl = document.getElementById('supplierToggleTitle');
    const leadEl = document.getElementById('supplierToggleLead');
    const nameEl = document.getElementById('supplierToggleName');
    const hintEl = document.getElementById('supplierToggleHint');
    const confirmBtn = document.getElementById('confirmSupplierToggleBtn');
    if (titleEl) titleEl.textContent = nextEnabled ? '确认启用' : '确认禁用';
    if (leadEl) leadEl.textContent = nextEnabled ? '确认启用供应商' : '确认禁用供应商';
    if (nameEl) nameEl.textContent = fullName;
    if (hintEl) {
        hintEl.textContent = nextEnabled
            ? '启用后可作为冲压工厂写入，并出现在上传下拉里。'
            : '禁用后不能再按此供应商新引入；列表筛选仍可见。';
    }
    if (confirmBtn) confirmBtn.textContent = nextEnabled ? '确认启用' : '确认禁用';
    openDrawer('supplierToggleDrawer', 'supplierToggleBackdrop');
}

function bindDeleteDrawer() {
    const close = () => closeDrawer('supplierDeleteDrawer', 'supplierDeleteBackdrop');
    document.getElementById('closeSupplierDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelSupplierDeleteBtn')?.addEventListener('click', close);
    document.getElementById('supplierDeleteBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmSupplierDeleteBtn')?.addEventListener('click', async () => {
        const fullName = document.getElementById('supplierDeleteName')?.textContent || '';
        if (!fullName) return;
        try {
            await HttpClient.delete(`${API_BASE}/${encodeURIComponent(fullName)}`);
            showToast('删除成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function openDeleteDrawer(fullName) {
    const nameEl = document.getElementById('supplierDeleteName');
    if (nameEl) nameEl.textContent = fullName;
    openDrawer('supplierDeleteDrawer', 'supplierDeleteBackdrop');
}

function bindTableActions() {
    document.getElementById('supplierTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        const row = btn.closest('tr');
        const fullName = row?.getAttribute('data-full-name') || '';
        if (!fullName) return;
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            openEditDrawer(fullName);
            return;
        }
        if (action === 'toggle') {
            const enabled = btn.getAttribute('data-enabled') === '1';
            openToggleDrawer(fullName, enabled);
            return;
        }
        if (action === 'delete') {
            openDeleteDrawer(fullName);
        }
    });
}

function bindFilters() {
    const search = () => {
        listState.keyword = document.getElementById('supplierFilterKeyword')?.value?.trim() || '';
        listState.page = 1;
        loadData();
    };
    document.getElementById('supplierBtnSearch')?.addEventListener('click', search);
    document.getElementById('supplierFilterKeyword')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            search();
        }
    });
    document.querySelectorAll('.supplier-status-capsule').forEach((btn) => {
        btn.addEventListener('click', () => {
            listState.isEnabled = btn.getAttribute('data-enabled-filter') ?? '';
            listState.page = 1;
            loadData();
        });
    });
    document.getElementById('supplierPaginationBtns')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.page-btn');
        if (!btn || btn.disabled) return;
        const next = Number.parseInt(btn.getAttribute('data-page') || '0', 10);
        if (!next || next === listState.page) return;
        listState.page = next;
        loadData();
    });
    bindPageSizeSelect('supplierPageSize', {
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = normalizePageSize(size);
            listState.page = 1;
        },
        onChange: () => loadData(),
    });
}

async function exportExcel() {
    if (!canOp('op:supplier-list:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const btn = document.getElementById('supplierBtnExport');
    const original = btn ? btn.innerHTML : '';
    try {
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<div class="w-3 h-3 border border-[#d32f2f] border-t-transparent rounded-full animate-spin"></div>导出中`;
        }
        const params = {};
        if (listState.keyword) params.q = listState.keyword;
        if (listState.isEnabled === 'true') params.is_enabled = true;
        if (listState.isEnabled === 'false') params.is_enabled = false;
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '供应商一览.xlsx',
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
            btn.innerHTML = original;
        }
    }
}

function init() {
    applyPermissionUi();
    bindCreateDrawer();
    bindEditDrawer();
    bindToggleDrawer();
    bindDeleteDrawer();
    bindTableActions();
    bindFilters();
    document.getElementById('supplierBtnExport')?.addEventListener('click', () => exportExcel());
    loadData();
}

export const pageConfig = {
    render: supplierListTemplate,
    init,
};
