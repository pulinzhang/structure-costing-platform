/**
 * 计费管理 — 左分类、右费用勾选，一次保存
 */

import {
    categoryBillingTemplate,
    renderCategoryList,
    renderFeeRows,
    paintFeeHeading,
} from './template.js?v=4';

const API_BASE = '/api/masterdata/category-billings';
const PAGE_LIMIT = 20;

const pageState = {
    categories: [],
    fees: [],
    billings: [],
    categoryId: '',
    isLoading: false,
    isSaving: false,
};

function canOp(code) {
    return typeof can === 'function' ? can(code) : true;
}

function sameIds(left, right) {
    if (left.length !== right.length) return false;
    for (let index = 0; index < left.length; index += 1) {
        if (left[index] !== right[index]) return false;
    }
    return true;
}

function savedIds(categoryId) {
    return pageState.billings
        .filter((row) => String(row.assembly_category_id) === String(categoryId))
        .map((row) => String(row.fee_archive_id))
        .sort();
}

function checkedIdsFromDom() {
    const body = document.getElementById('cbTableBody');
    if (!body || !pageState.fees.length) return null;
    return [...body.querySelectorAll('.cb-fee:checked')]
        .map((box) => box.getAttribute('data-fee-id') || '')
        .filter(Boolean)
        .sort();
}

function activeCategory() {
    return pageState.categories.find((row) => String(row.id) === String(pageState.categoryId)) || null;
}

function readOnly() {
    const category = activeCategory();
    if (!category || !category.is_enabled) return true;
    return !canOp('op:category-billing:update');
}

function isDirty() {
    if (!pageState.categoryId || readOnly()) return false;
    const current = checkedIdsFromDom();
    if (!current) return false;
    return !sameIds(current, savedIds(pageState.categoryId));
}

function selectionCounts() {
    const counts = new Map();
    pageState.categories.forEach((row) => {
        const saved = savedIds(row.id);
        const current = String(row.id) === String(pageState.categoryId) ? checkedIdsFromDom() : null;
        const ids = current || saved;
        counts.set(String(row.id), ids.length);
        if (current && !sameIds(current, saved)) counts.set(`dirty:${row.id}`, 1);
    });
    return counts;
}

function setLoading(isLoading) {
    pageState.isLoading = isLoading;
    document.getElementById('cbLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('cbEmpty')?.classList.add('hidden');
        const body = document.getElementById('cbTableBody');
        if (body) body.innerHTML = '';
    }
}

function syncCheckAll() {
    const all = document.getElementById('cbCheckAll');
    if (!all) return;
    const boxes = [...document.querySelectorAll('#cbTableBody .cb-fee:not(:disabled)')];
    const checked = boxes.filter((box) => box.checked).length;
    all.disabled = readOnly() || boxes.length === 0;
    all.checked = boxes.length > 0 && checked === boxes.length;
    all.indeterminate = checked > 0 && checked < boxes.length;
}

function syncSaveButton() {
    const button = document.getElementById('cbSaveBtn');
    if (!button) return;
    const enabled = !readOnly() && !pageState.isSaving && isDirty();
    button.disabled = !enabled;
    button.textContent = pageState.isSaving ? '保存中…' : '保存';
}

function renderBoard() {
    const category = activeCategory();
    const locked = readOnly();
    paintFeeHeading(category, locked);
    const body = document.getElementById('cbTableBody');
    const empty = document.getElementById('cbEmpty');
    const wrap = document.getElementById('cbTableWrap');
    const hasFees = pageState.fees.length > 0 && Boolean(category);
    if (body) {
        body.innerHTML = hasFees
            ? renderFeeRows(pageState.fees, new Set(savedIds(pageState.categoryId)), locked)
            : '';
    }
    empty?.classList.toggle('hidden', hasFees || pageState.isLoading);
    wrap?.classList.toggle('hidden', !hasFees);
    const emptyTitle = document.getElementById('cbEmptyTitle');
    const emptyHint = document.getElementById('cbEmptyHint');
    if (!hasFees && emptyTitle && emptyHint) {
        if (!pageState.categories.length) {
            emptyTitle.textContent = '暂无总成分类';
            emptyHint.textContent = '先到总成分类维护';
        } else if (!category) {
            emptyTitle.textContent = '选择分类';
            emptyHint.textContent = '在左侧点一个总成分类';
        } else {
            emptyTitle.textContent = '暂无费用';
            emptyHint.textContent = '先到费用档案维护';
        }
    }
    renderCategoryList(pageState.categories, pageState.categoryId, selectionCounts());
    syncCheckAll();
    syncSaveButton();
}

async function loadPage(url, params) {
    const items = [];
    let page = 1;
    let totalPages = 1;
    while (page <= totalPages && page <= PAGE_LIMIT) {
        const res = await HttpClient.get(url, { params: { ...params, page, size: 100 } });
        const data = res.data || {};
        if (Array.isArray(data.items)) items.push(...data.items);
        totalPages = Number(data.total_pages) || 1;
        page += 1;
    }
    return items;
}

async function loadCatalogs() {
    const [categories, fees, billings] = await Promise.all([
        loadPage('/api/masterdata/assembly-categories', {}),
        loadPage('/api/masterdata/fee-archives', {}),
        loadPage(API_BASE, {}),
    ]);
    pageState.categories = categories;
    pageState.fees = fees;
    pageState.billings = billings;
    if (!pageState.categoryId && categories.length) {
        pageState.categoryId = String(categories[0].id);
    }
    if (pageState.categoryId && !categories.some((row) => String(row.id) === String(pageState.categoryId))) {
        pageState.categoryId = categories.length ? String(categories[0].id) : '';
    }
}

async function loadData() {
    if (pageState.isLoading) return;
    if (!canOp('op:category-billing:view')) {
        pageState.categories = [];
        pageState.fees = [];
        pageState.billings = [];
        renderBoard();
        return;
    }
    setLoading(true);
    try {
        await loadCatalogs();
    } catch (_) {
        pageState.categories = [];
        pageState.fees = [];
        pageState.billings = [];
    } finally {
        setLoading(false);
    }
    renderBoard();
}

async function selectCategory(categoryId) {
    if (String(categoryId) === String(pageState.categoryId)) return;
    if (isDirty()) {
        const confirmed = await window.confirmAction('当前分类的勾选还没保存，要切换吗？', {
            title: '未保存',
            confirmLabel: '切换',
        });
        if (!confirmed) return;
    }
    pageState.categoryId = String(categoryId);
    renderBoard();
}

function markRows() {
    document.querySelectorAll('#cbTableBody .cb-fee').forEach((box) => {
        const row = box.closest('tr');
        if (!row) return;
        if (box.checked) row.setAttribute('data-current', '1');
        else row.removeAttribute('data-current');
    });
}

function onFeeToggle() {
    markRows();
    renderCategoryList(pageState.categories, pageState.categoryId, selectionCounts());
    syncCheckAll();
    syncSaveButton();
}

function onCheckAll(event) {
    const turnOn = event.target.checked;
    document.querySelectorAll('#cbTableBody .cb-fee:not(:disabled)').forEach((box) => {
        box.checked = turnOn;
    });
    onFeeToggle();
}

async function saveSelection() {
    const category = activeCategory();
    if (!category || readOnly() || pageState.isSaving || !isDirty()) return;
    const feeIds = (checkedIdsFromDom() || []).map((value) => Number.parseInt(value, 10));
    pageState.isSaving = true;
    syncSaveButton();
    try {
        const res = await HttpClient.put(`${API_BASE}/categories/${category.id}`, {
            fee_archive_ids: feeIds,
        });
        const items = Array.isArray(res.data?.items) ? res.data.items : [];
        pageState.billings = pageState.billings.filter(
            (row) => String(row.assembly_category_id) !== String(category.id),
        );
        pageState.billings.push(...items);
        showToast('已保存', 'success');
        renderBoard();
    } catch (_) {
        // HttpClient 已提示
    } finally {
        pageState.isSaving = false;
        syncSaveButton();
    }
}

function bindEvents() {
    document.getElementById('cbCategoryList')?.addEventListener('click', (event) => {
        const button = event.target.closest('.cb-category');
        if (!button) return;
        selectCategory(button.getAttribute('data-category') || '');
    });
    document.getElementById('cbTableBody')?.addEventListener('change', (event) => {
        if (!event.target.classList.contains('cb-fee')) return;
        onFeeToggle();
    });
    document.getElementById('cbCheckAll')?.addEventListener('change', onCheckAll);
    document.getElementById('cbSaveBtn')?.addEventListener('click', () => saveSelection());
}

async function init() {
    bindEvents();
    await loadData();
}

export const pageConfig = {
    render: categoryBillingTemplate,
    init,
};
