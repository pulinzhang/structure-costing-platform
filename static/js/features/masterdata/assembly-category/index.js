/**
 * 总成分类 — /api/masterdata/assembly-categories
 */

import {
    bindPagination,
    paintPagination,
    DEFAULT_PAGE_SIZE,
} from '../../../ui/page-size.js?v=11';
import {
    assemblyCategoryTemplate,
    renderAssemblyCategoryRows,
    syncAssemblyCategoryStatus,
} from './template.js?v=1';

const API_BASE = '/api/masterdata/assembly-categories';
const DRAWER_ANIMATION_MS = 300;

const pageState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 0,
    keyword: '',
    isEnabled: '',
    isLoading: false,
    editId: null,
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
    if (!canOp('op:assembly-category:create')) {
        document.getElementById('acAddBtn')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    document.getElementById('acLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('acEmpty')?.classList.add('hidden');
        const body = document.getElementById('acTableBody');
        if (body) body.innerHTML = '';
    }
}

function renderList() {
    const body = document.getElementById('acTableBody');
    const empty = document.getElementById('acEmpty');
    const totalEl = document.getElementById('acPageInfo');
    const hasRows = pageState.records.length > 0;
    if (body) body.innerHTML = renderAssemblyCategoryRows(pageState.records);
    empty?.classList.toggle('hidden', hasRows || pageState.isLoading);
    if (totalEl) totalEl.textContent = `共 ${pageState.total} 条`;
    paintPagination('acPagination', pageState.page, pageState.totalPages);
    syncAssemblyCategoryStatus(pageState.isEnabled);
}

function buildQueryParams() {
    const params = { page: pageState.page, size: pageState.pageSize };
    if (pageState.keyword) params.q = pageState.keyword;
    if (pageState.isEnabled === 'true') params.is_enabled = true;
    if (pageState.isEnabled === 'false') params.is_enabled = false;
    return params;
}

async function loadData(page = pageState.page) {
    if (pageState.isLoading) return;
    pageState.page = page;
    if (!canOp('op:assembly-category:view')) {
        pageState.records = [];
        renderList();
        return;
    }
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

function findRecord(recordId) {
    return pageState.records.find((row) => String(row.id) === String(recordId)) || null;
}

function fillForm(record) {
    const title = document.getElementById('acFormTitle');
    const code = document.getElementById('acCode');
    const codeWrap = document.getElementById('acCodeWrap');
    if (title) title.textContent = record ? '编辑总成分类' : '新增总成分类';
    if (code) {
        code.value = record?.code || '';
        code.disabled = Boolean(record);
    }
    codeWrap?.classList.toggle('hidden', Boolean(record));
    const name = document.getElementById('acName');
    const sort = document.getElementById('acSort');
    const remark = document.getElementById('acRemark');
    const enabled = document.getElementById('acEnabled');
    if (name) name.value = record?.name || '';
    if (sort) sort.value = record ? String(record.sort_order) : '';
    if (remark) remark.value = record?.remark || '';
    if (enabled) enabled.checked = record ? record.is_enabled !== false : true;
    document.getElementById('acEnabledWrap')?.classList.toggle('hidden', !record);
}

function closeForm() {
    pageState.editId = null;
    closeDrawer('acFormDrawer', 'acFormBackdrop');
}

async function submitForm() {
    const editing = pageState.editId != null;
    if (editing && !canOp('op:assembly-category:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    if (!editing && !canOp('op:assembly-category:create')) {
        showToast('无新增权限', 'warning');
        return;
    }
    const name = document.getElementById('acName')?.value?.trim() || '';
    const sortRaw = document.getElementById('acSort')?.value?.trim() || '';
    const sortOrder = Number.parseInt(sortRaw, 10);
    if (!name || !Number.isInteger(sortOrder)) {
        showToast('请填写名称和顺序', 'warning');
        return;
    }
    const remark = document.getElementById('acRemark')?.value?.trim() || null;
    try {
        if (editing) {
            await HttpClient.put(`${API_BASE}/${pageState.editId}`, {
                name,
                sort_order: sortOrder,
                is_enabled: document.getElementById('acEnabled')?.checked !== false,
                remark,
            });
            showToast('更新成功', 'success');
        } else {
            const code = document.getElementById('acCode')?.value?.trim() || '';
            if (!code) {
                showToast('请填写编码', 'warning');
                return;
            }
            await HttpClient.post(API_BASE, { code, name, sort_order: sortOrder, remark });
            showToast('创建成功', 'success');
        }
        closeForm();
        await loadData(editing ? pageState.page : 1);
    } catch (_) {
        // HttpClient 已提示
    }
}

async function removeRecord(recordId, name) {
    if (!canOp('op:assembly-category:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const confirmed = await confirmAction(`删除总成分类「${name}」？`, { title: '删除总成分类' });
    if (!confirmed) return;
    try {
        await HttpClient.delete(`${API_BASE}/${recordId}`);
        showToast('已删除', 'success');
        await loadData(1);
    } catch (_) {
        // 删除失败走错误框
    }
}

function bindEvents() {
    document.getElementById('acAddBtn')?.addEventListener('click', () => {
        pageState.editId = null;
        fillForm(null);
        openDrawer('acFormDrawer', 'acFormBackdrop');
        document.getElementById('acCode')?.focus();
    });
    document.getElementById('acCloseForm')?.addEventListener('click', closeForm);
    document.getElementById('acCancelForm')?.addEventListener('click', closeForm);
    document.getElementById('acFormBackdrop')?.addEventListener('click', closeForm);
    document.getElementById('acSubmitForm')?.addEventListener('click', () => submitForm());
    document.getElementById('acStatusBar')?.addEventListener('click', (event) => {
        const button = event.target.closest('.ac-status');
        if (!button) return;
        pageState.isEnabled = button.getAttribute('data-enabled') ?? '';
        loadData(1);
    });
    const keyword = document.getElementById('acKeyword');
    let searchTimer = 0;
    keyword?.addEventListener('input', () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(() => {
            pageState.keyword = keyword.value || '';
            loadData(1);
        }, 250);
    });
    document.getElementById('acTableBody')?.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const recordId = button.getAttribute('data-id');
        if (button.getAttribute('data-action') === 'edit') {
            pageState.editId = recordId;
            fillForm(findRecord(recordId));
            openDrawer('acFormDrawer', 'acFormBackdrop');
            return;
        }
        if (button.getAttribute('data-action') === 'delete') {
            removeRecord(recordId, button.getAttribute('data-name') || '');
        }
    });
}

function init() {
    applyPermissionUi();
    bindEvents();
    bindPagination({
        selectId: 'acPageSize',
        buttonsId: 'acPagination',
        getSize: () => pageState.pageSize,
        setSize: (size) => {
            pageState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    syncAssemblyCategoryStatus('');
    loadData(1);
}

export const pageConfig = {
    render: assemblyCategoryTemplate,
    init,
};
