/**
 * 钢厂档案页 — /api/masterdata/steel-mills
 */

import {
    bindPagination,
    paintPagination,
    DEFAULT_PAGE_SIZE,
    normalizePageSize,
} from '../../../ui/page-size.js?v=8';
import { renderSteelMillRows, steelMillTemplate } from './template.js?v=1';

const API_BASE = '/api/masterdata/steel-mills';
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
    editId: null,
    deleteId: null,
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
    if (!canOp('op:steel-mill:create')) {
        document.getElementById('steelMillBtnCreate')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    listState.isLoading = isLoading;
    document.getElementById('steelMillLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('steelMillEmpty')?.classList.add('hidden');
        const body = document.getElementById('steelMillTableBody');
        if (body) body.innerHTML = '';
    }
}

function renderStatusCapsules() {
    document.querySelectorAll('.steel-mill-status-capsule').forEach((btn) => {
        const value = btn.getAttribute('data-enabled-filter') ?? '';
        const selected = value === listState.isEnabled;
        btn.className = selected
            ? 'steel-mill-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-brand-hud/50 bg-brand-hud/10 text-ink'
            : 'steel-mill-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink';
    });
}

function renderList() {
    const body = document.getElementById('steelMillTableBody');
    const empty = document.getElementById('steelMillEmpty');
    const totalEl = document.getElementById('steelMillPageInfo');
    const hasRows = listState.records.length > 0;
    if (body) body.innerHTML = renderSteelMillRows(listState.records);
    empty?.classList.toggle('hidden', hasRows || listState.isLoading);
    if (totalEl) totalEl.textContent = `共 ${listState.total} 条`;
    paintPagination('steelMillPagination', listState.page, listState.totalPages);
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
    if (!canOp('op:steel-mill:view')) {
        listState.records = [];
        renderList();
        return;
    }
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

function findRecord(recordId) {
    return listState.records.find((row) => row.id === recordId) || null;
}

function fillForm(record) {
    const title = document.getElementById('steelMillFormTitle');
    const abbreviation = document.getElementById('steelMillAbbreviation');
    const fullName = document.getElementById('steelMillFullName');
    const aliases = document.getElementById('steelMillAliases');
    const enabled = document.getElementById('steelMillEnabled');
    const enabledWrap = document.getElementById('steelMillEnabledWrap');
    if (title) title.textContent = record ? '编辑钢厂' : '新增钢厂';
    if (abbreviation) abbreviation.value = record?.abbreviation || '';
    if (fullName) fullName.value = record?.full_name || '';
    if (aliases) aliases.value = Array.isArray(record?.aliases) ? record.aliases.join('\n') : '';
    if (enabled) enabled.checked = record ? record.is_enabled !== false : true;
    enabledWrap?.classList.toggle('hidden', !record);
}

function bindFormDrawer() {
    const close = () => {
        listState.editId = null;
        closeDrawer('steelMillFormDrawer', 'steelMillFormBackdrop');
    };
    document.getElementById('steelMillBtnCreate')?.addEventListener('click', () => {
        listState.editId = null;
        fillForm(null);
        openDrawer('steelMillFormDrawer', 'steelMillFormBackdrop');
        document.getElementById('steelMillAbbreviation')?.focus();
    });
    document.getElementById('closeSteelMillFormDrawer')?.addEventListener('click', close);
    document.getElementById('cancelSteelMillFormBtn')?.addEventListener('click', close);
    document.getElementById('steelMillFormBackdrop')?.addEventListener('click', close);
    document.getElementById('submitSteelMillFormBtn')?.addEventListener('click', async () => {
        const abbreviation = document.getElementById('steelMillAbbreviation')?.value?.trim() || '';
        const fullName = document.getElementById('steelMillFullName')?.value?.trim() || '';
        const aliases = parseAliasLines(document.getElementById('steelMillAliases')?.value || '');
        if (!abbreviation || !fullName) {
            showToast('请填写缩写和全称', 'warning');
            return;
        }
        const editing = listState.editId != null;
        if (editing && !canOp('op:steel-mill:update')) {
            showToast('无编辑权限', 'warning');
            return;
        }
        if (!editing && !canOp('op:steel-mill:create')) {
            showToast('无新增权限', 'warning');
            return;
        }
        try {
            if (editing) {
                await HttpClient.put(`${API_BASE}/${listState.editId}`, {
                    abbreviation,
                    full_name: fullName,
                    is_enabled: document.getElementById('steelMillEnabled')?.checked !== false,
                    aliases,
                });
                showToast('更新成功', 'success');
            } else {
                await HttpClient.post(API_BASE, {
                    abbreviation,
                    full_name: fullName,
                    aliases,
                });
                showToast('创建成功', 'success');
            }
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

function bindDeleteDrawer() {
    const close = () => {
        listState.deleteId = null;
        closeDrawer('steelMillDeleteDrawer', 'steelMillDeleteBackdrop');
    };
    document.getElementById('closeSteelMillDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelSteelMillDeleteBtn')?.addEventListener('click', close);
    document.getElementById('steelMillDeleteBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmSteelMillDeleteBtn')?.addEventListener('click', async () => {
        if (listState.deleteId == null) return;
        try {
            await HttpClient.delete(`${API_BASE}/${listState.deleteId}`);
            showToast('删除成功', 'success');
            close();
            await loadData();
        } catch (_) {
            /* HttpClient 已 Toast */
        }
    });
}

async function toggleRecord(record) {
    if (!canOp('op:steel-mill:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    try {
        await HttpClient.put(`${API_BASE}/${record.id}`, {
            abbreviation: record.abbreviation,
            full_name: record.full_name,
            is_enabled: record.is_enabled === false,
            aliases: Array.isArray(record.aliases) ? record.aliases : [],
            remark: record.remark || null,
        });
        showToast(record.is_enabled === false ? '已启用' : '已禁用', 'success');
        await loadData();
    } catch (_) {
        /* HttpClient 已 Toast */
    }
}

function bindTableActions() {
    document.getElementById('steelMillTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        const row = btn.closest('[data-id]');
        const recordId = Number(row?.getAttribute('data-id'));
        const record = findRecord(recordId);
        if (!record) return;
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            listState.editId = record.id;
            fillForm(record);
            openDrawer('steelMillFormDrawer', 'steelMillFormBackdrop');
            return;
        }
        if (action === 'toggle') {
            toggleRecord(record);
            return;
        }
        if (action === 'delete') {
            listState.deleteId = record.id;
            const nameEl = document.getElementById('steelMillDeleteName');
            if (nameEl) nameEl.textContent = record.abbreviation;
            openDrawer('steelMillDeleteDrawer', 'steelMillDeleteBackdrop');
        }
    });
}

function bindFilters() {
    const search = () => {
        listState.keyword = document.getElementById('steelMillFilterKeyword')?.value?.trim() || '';
        listState.page = 1;
        loadData();
    };
    const keywordInput = document.getElementById('steelMillFilterKeyword');
    let searchTimer = 0;
    keywordInput?.addEventListener('input', () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(search, 280);
    });
    keywordInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            window.clearTimeout(searchTimer);
            search();
        }
    });
    document.querySelectorAll('.steel-mill-status-capsule').forEach((btn) => {
        btn.addEventListener('click', () => {
            listState.isEnabled = btn.getAttribute('data-enabled-filter') ?? '';
            listState.page = 1;
            loadData();
        });
    });
    bindPagination({
        selectId: 'steelMillPageSize',
        buttonsId: 'steelMillPagination',
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = normalizePageSize(size);
        },
        onPage: (page) => {
            listState.page = page;
            loadData();
        },
    });
}

function init() {
    applyPermissionUi();
    bindFormDrawer();
    bindDeleteDrawer();
    bindTableActions();
    bindFilters();
    loadData();
}

export const pageConfig = {
    render: steelMillTemplate,
    init,
};
