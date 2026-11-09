/**
 * 费用档案 — /api/masterdata/fee-archives
 */

import {
    bindPagination,
    paintPagination,
    DEFAULT_PAGE_SIZE,
} from '../../../ui/page-size.js?v=11';
import {
    feeArchiveTemplate,
    renderFeeArchiveRows,
    syncFeeArchiveStatus,
    percentToRate,
    rateToPercentInput,
} from './template.js?v=1';

const API_BASE = '/api/masterdata/fee-archives';
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
    if (!canOp('op:fee-archive:create')) {
        document.getElementById('faAddBtn')?.classList.add('hidden');
    }
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    document.getElementById('faLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('faEmpty')?.classList.add('hidden');
        const body = document.getElementById('faTableBody');
        if (body) body.innerHTML = '';
    }
}

function renderList() {
    const body = document.getElementById('faTableBody');
    const empty = document.getElementById('faEmpty');
    const totalEl = document.getElementById('faPageInfo');
    const hasRows = pageState.records.length > 0;
    if (body) body.innerHTML = renderFeeArchiveRows(pageState.records);
    empty?.classList.toggle('hidden', hasRows || pageState.isLoading);
    if (totalEl) totalEl.textContent = `共 ${pageState.total} 条`;
    paintPagination('faPagination', pageState.page, pageState.totalPages);
    syncFeeArchiveStatus(pageState.isEnabled);
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
    if (!canOp('op:fee-archive:view')) {
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
    const title = document.getElementById('faFormTitle');
    const code = document.getElementById('faCode');
    if (title) title.textContent = record ? '编辑费用' : '新增费用';
    if (code) {
        code.value = record?.code || '';
        code.disabled = Boolean(record);
    }
    document.getElementById('faCodeWrap')?.classList.toggle('hidden', Boolean(record));
    const name = document.getElementById('faName');
    const basis = document.getElementById('faBasis');
    const rate = document.getElementById('faRate');
    const sort = document.getElementById('faSort');
    const remark = document.getElementById('faRemark');
    const enabled = document.getElementById('faEnabled');
    if (name) name.value = record?.name || '';
    if (basis) basis.value = record?.charge_basis || 'rate';
    if (rate) rate.value = record ? rateToPercentInput(record.charge_rate) : '';
    if (sort) sort.value = record ? String(record.sort_order) : '';
    if (remark) remark.value = record?.remark || '';
    if (enabled) enabled.checked = record ? record.is_enabled !== false : true;
    document.getElementById('faEnabledWrap')?.classList.toggle('hidden', !record);
}

function closeForm() {
    pageState.editId = null;
    closeDrawer('faFormDrawer', 'faFormBackdrop');
}

async function submitForm() {
    const editing = pageState.editId != null;
    if (editing && !canOp('op:fee-archive:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    if (!editing && !canOp('op:fee-archive:create')) {
        showToast('无新增权限', 'warning');
        return;
    }
    const name = document.getElementById('faName')?.value?.trim() || '';
    const sortRaw = document.getElementById('faSort')?.value?.trim() || '';
    const sortOrder = Number.parseInt(sortRaw, 10);
    const chargeRate = percentToRate(document.getElementById('faRate')?.value);
    if (!name || !Number.isInteger(sortOrder) || !chargeRate) {
        showToast('请填写名称、顺序，以及 0 到 100 的计费率', 'warning');
        return;
    }
    const payload = {
        name,
        charge_basis: document.getElementById('faBasis')?.value || 'rate',
        charge_rate: chargeRate,
        sort_order: sortOrder,
        remark: document.getElementById('faRemark')?.value?.trim() || null,
    };
    try {
        if (editing) {
            await HttpClient.put(`${API_BASE}/${pageState.editId}`, {
                ...payload,
                is_enabled: document.getElementById('faEnabled')?.checked !== false,
            });
            showToast('更新成功', 'success');
        } else {
            const code = document.getElementById('faCode')?.value?.trim() || '';
            if (!code) {
                showToast('请填写编码', 'warning');
                return;
            }
            await HttpClient.post(API_BASE, { ...payload, code });
            showToast('创建成功', 'success');
        }
        closeForm();
        await loadData(editing ? pageState.page : 1);
    } catch (_) {
        // HttpClient 已提示
    }
}

async function removeRecord(recordId, name) {
    if (!canOp('op:fee-archive:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const confirmed = await confirmAction(`删除费用「${name}」？`, { title: '删除费用' });
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
    document.getElementById('faAddBtn')?.addEventListener('click', () => {
        pageState.editId = null;
        fillForm(null);
        openDrawer('faFormDrawer', 'faFormBackdrop');
        document.getElementById('faCode')?.focus();
    });
    document.getElementById('faCloseForm')?.addEventListener('click', closeForm);
    document.getElementById('faCancelForm')?.addEventListener('click', closeForm);
    document.getElementById('faFormBackdrop')?.addEventListener('click', closeForm);
    document.getElementById('faSubmitForm')?.addEventListener('click', () => submitForm());
    document.getElementById('faStatusBar')?.addEventListener('click', (event) => {
        const button = event.target.closest('.fa-status');
        if (!button) return;
        pageState.isEnabled = button.getAttribute('data-enabled') ?? '';
        loadData(1);
    });
    const keyword = document.getElementById('faKeyword');
    let searchTimer = 0;
    keyword?.addEventListener('input', () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(() => {
            pageState.keyword = keyword.value || '';
            loadData(1);
        }, 250);
    });
    document.getElementById('faTableBody')?.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const recordId = button.getAttribute('data-id');
        if (button.getAttribute('data-action') === 'edit') {
            pageState.editId = recordId;
            fillForm(findRecord(recordId));
            openDrawer('faFormDrawer', 'faFormBackdrop');
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
        selectId: 'faPageSize',
        buttonsId: 'faPagination',
        getSize: () => pageState.pageSize,
        setSize: (size) => {
            pageState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    syncFeeArchiveStatus('');
    loadData(1);
}

export const pageConfig = {
    render: feeArchiveTemplate,
    init,
};
