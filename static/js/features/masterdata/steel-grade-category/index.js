/**
 * 牌号分类档案 — 列表 + 抽屉 CRUD
 */

import {
    steelGradeCategoryTemplate,
    renderTableRows,
    syncTabStyles,
} from './template.js?v=6';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../page-size.js?v=3';

const API_BASE = '/api/masterdata/steel-grade-category';
const DRAWER_ANIMATION_MS = 300;

const pageState = {
    tab: 'all',
    grade: '',
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

function applyPermissionUi() {
    if (!canOp('op:steel-grade-category:create')) {
        document.getElementById('sgcAddBtn')?.classList.add('hidden');
    }
    if (!canOp('op:steel-grade-category:export')) {
        document.getElementById('sgcExportBtn')?.classList.add('hidden');
    }
}

function buildFilterParams() {
    const params = {
        grade: pageState.grade.trim(),
    };
    if (pageState.tab !== 'all') {
        params.category_name = pageState.tab;
    }
    return params;
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    const loading = document.getElementById('sgcLoadingState');
    const empty = document.getElementById('sgcEmptyState');
    const body = document.getElementById('sgcTableBody');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        empty?.classList.add('hidden');
        if (body) body.innerHTML = '';
    }
}

function buildQueryParams() {
    return {
        page: pageState.page,
        size: pageState.pageSize,
        ...buildFilterParams(),
    };
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
    const body = document.getElementById('sgcTableBody');
    const empty = document.getElementById('sgcEmptyState');
    const totalEl = document.getElementById('sgcTotalCount');
    if (body) body.innerHTML = renderTableRows(pageState.records);
    empty?.classList.toggle('hidden', pageState.records.length > 0 || pageState.isLoading);
    if (totalEl) totalEl.textContent = `共 ${pageState.total} 条`;
    paintPagination('sgcPaginationBtns', pageState.page, pageState.totalPages);
    syncTabStyles(pageState.tab);
}

function openCreateDrawer() {
    if (!canOp('op:steel-grade-category:create')) {
        showToast('无新增权限');
        return;
    }
    document.getElementById('sgcEditTitle').textContent = '新增牌号';
    document.getElementById('sgcEditId').value = '';
    document.getElementById('sgcEditGrade').value = '';
    document.getElementById('sgcEditGrade').disabled = false;
    document.getElementById('sgcEditCategory').value = pageState.tab !== 'all'
        ? pageState.tab
        : '';
    document.getElementById('sgcEditRemark').value = '';
    openDrawer('sgcEditDrawer', 'sgcEditBackdrop');
}

function openEditDrawer(record) {
    if (!canOp('op:steel-grade-category:update')) {
        showToast('无编辑权限', 'warning');
        return;
    }
    document.getElementById('sgcEditTitle').textContent = '编辑牌号';
    document.getElementById('sgcEditId').value = String(record.id);
    document.getElementById('sgcEditGrade').value = record.grade || '';
    document.getElementById('sgcEditGrade').disabled = false;
    document.getElementById('sgcEditCategory').value = record.category_name || '';
    document.getElementById('sgcEditRemark').value = record.remark || '';
    openDrawer('sgcEditDrawer', 'sgcEditBackdrop');
}

function openDeleteDrawer(recordId, grade) {
    if (!canOp('op:steel-grade-category:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    document.getElementById('sgcDeleteId').value = String(recordId);
    const gradeEl = document.getElementById('sgcDeleteGrade');
    if (gradeEl) gradeEl.textContent = grade || '';
    openDrawer('sgcDeleteDrawer', 'sgcDeleteBackdrop');
}

async function submitEdit() {
    if (pageState.isSaving) return;
    const recordId = document.getElementById('sgcEditId')?.value;
    const grade = (document.getElementById('sgcEditGrade')?.value || '').trim().toUpperCase();
    const categoryName = document.getElementById('sgcEditCategory')?.value || '';
    const remark = document.getElementById('sgcEditRemark')?.value?.trim() || null;
    if (!grade) {
        showToast('请填写牌号', 'warning');
        return;
    }
    if (!categoryName) {
        showToast('请选择大类', 'warning');
        return;
    }

    pageState.isSaving = true;
    const btn = document.getElementById('sgcSubmitEdit');
    if (btn) btn.disabled = true;
    try {
        if (recordId) {
            await HttpClient.put(`${API_BASE}/${recordId}`, {
                grade,
                category_name: categoryName,
                remark,
            });
            showToast('更新成功', 'success');
        } else {
            await HttpClient.post(API_BASE, {
                grade,
                category_name: categoryName,
                remark,
            });
            showToast('创建成功', 'success');
        }
        closeDrawer('sgcEditDrawer', 'sgcEditBackdrop');
        await loadData(recordId ? pageState.page : 1);
    } catch (_) {
        // toast 已由 HttpClient 处理
    } finally {
        pageState.isSaving = false;
        if (btn) btn.disabled = false;
    }
}

async function confirmDelete() {
    const recordId = document.getElementById('sgcDeleteId')?.value;
    if (!recordId) return;
    try {
        await HttpClient.delete(`${API_BASE}/${recordId}`);
        showToast('删除成功', 'success');
        closeDrawer('sgcDeleteDrawer', 'sgcDeleteBackdrop');
        const nextPage = pageState.records.length <= 1 && pageState.page > 1
            ? pageState.page - 1
            : pageState.page;
        await loadData(nextPage);
    } catch (_) {
        // toast 已由 HttpClient 处理
    }
}

async function exportExcel() {
    if (!canOp('op:steel-grade-category:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: buildFilterParams(),
            defaultFilename: '牌号分类.xlsx',
        });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        showToast('导出成功', 'success');
    } catch (_) {
        // toast 已由 HttpClient 处理
    }
}

function bindEvents() {
    document.getElementById('sgcAddBtn')?.addEventListener('click', () => openCreateDrawer());
    document.getElementById('sgcExportBtn')?.addEventListener('click', () => exportExcel());

    document.getElementById('sgcTabBar')?.addEventListener('click', (event) => {
        const tabBtn = event.target.closest('[data-action=tab]');
        if (!tabBtn) return;
        const tab = tabBtn.getAttribute('data-tab');
        if (!tab || tab === pageState.tab) return;
        pageState.tab = tab;
        loadData(1);
    });

    const gradeInput = document.getElementById('sgcGradeFilter');
    let searchTimer = 0;
    gradeInput?.addEventListener('input', () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(() => {
            pageState.grade = gradeInput.value || '';
            loadData(1);
        }, 250);
    });
    gradeInput?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        window.clearTimeout(searchTimer);
        pageState.grade = gradeInput.value || '';
        loadData(1);
    });

    document.getElementById('sgcTableBody')?.addEventListener('click', (event) => {
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
            openDeleteDrawer(recordId, actionEl.getAttribute('data-grade') || '');
        }
    });


    document.getElementById('sgcCloseEdit')?.addEventListener('click', () => {
        closeDrawer('sgcEditDrawer', 'sgcEditBackdrop');
    });
    document.getElementById('sgcEditBackdrop')?.addEventListener('click', () => {
        closeDrawer('sgcEditDrawer', 'sgcEditBackdrop');
    });
    document.getElementById('sgcCancelEdit')?.addEventListener('click', () => {
        closeDrawer('sgcEditDrawer', 'sgcEditBackdrop');
    });
    document.getElementById('sgcSubmitEdit')?.addEventListener('click', () => submitEdit());
    document.getElementById('sgcEditForm')?.addEventListener('submit', (event) => {
        event.preventDefault();
        submitEdit();
    });

    document.getElementById('sgcCloseDelete')?.addEventListener('click', () => {
        closeDrawer('sgcDeleteDrawer', 'sgcDeleteBackdrop');
    });
    document.getElementById('sgcDeleteBackdrop')?.addEventListener('click', () => {
        closeDrawer('sgcDeleteDrawer', 'sgcDeleteBackdrop');
    });
    document.getElementById('sgcCancelDelete')?.addEventListener('click', () => {
        closeDrawer('sgcDeleteDrawer', 'sgcDeleteBackdrop');
    });
    document.getElementById('sgcConfirmDelete')?.addEventListener('click', () => confirmDelete());
}

function init() {
    applyPermissionUi();
    bindEvents();
    bindPagination({
        selectId: 'sgcPageSize',
        buttonsId: 'sgcPaginationBtns',
        getSize: () => pageState.pageSize,
        setSize: (size) => {
            pageState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    syncTabStyles(pageState.tab);
    loadData(1);
}

export const pageConfig = {
    render: steelGradeCategoryTemplate,
    init,
};
