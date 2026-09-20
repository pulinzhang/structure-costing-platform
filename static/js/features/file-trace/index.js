/**
 * 文件溯源 — /api/file-trace
 */

import {
    fileTraceTemplate,
    renderDrawerDetail,
    renderTableRows,
} from './template.js?v=10';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../page-size.js?v=3';
import { setSearchBusy } from '../../search-busy.js?v=1';

const ftState = {
    items: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    filters: null,
    detailItem: null,
    drawerOpen: false,
    isLoading: false,
};

const API_BASE = '/api/file-trace';

function collectFilters() {
    return {
        file_category: document.getElementById('ftFilterCategory')?.value || '',
        location: document.getElementById('ftFilterLocation')?.value || '',
        year: document.getElementById('ftFilterYear')?.value || '',
        month: document.getElementById('ftFilterMonth')?.value || '',
        vehicle_model: document.getElementById('ftFilterVehicle')?.value || '',
        created_by: document.getElementById('ftFilterCreator')?.value || '',
        filename: (document.getElementById('ftFilterFilename')?.value || '').trim(),
        uploaded_from: document.getElementById('ftFilterFrom')?.value || '',
        uploaded_to: document.getElementById('ftFilterTo')?.value || '',
    };
}

function buildQueryParams(page) {
    const filters = collectFilters();
    const params = {
        page,
        size: ftState.pageSize,
    };
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value != null) params[key] = value;
    });
    return params;
}

function fillSelect(selectId, values, labelMap, placeholder) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const options = [`<option value="">${esc(placeholder)}</option>`];
    (values || []).forEach((value) => {
        const label = labelMap && labelMap[value] ? labelMap[value] : value;
        options.push(`<option value="${esc(String(value))}">${esc(String(label))}</option>`);
    });
    select.innerHTML = options.join('');
}

function applyFilterOptions(data) {
    if (!data) return;
    const labels = data.category_labels || {};
    fillSelect('ftFilterCategory', data.allowed_categories || [], labels, '全部分类');
    fillSelect('ftFilterLocation', data.locations || [], null, '全部基地');
    fillSelect('ftFilterYear', data.years || [], Object.fromEntries((data.years || []).map((y) => [y, fmtYear(y)])), '全部年度');
    fillSelect('ftFilterMonth', data.months || [], Object.fromEntries((data.months || []).map((m) => [m, fmtMonth(m)])), '全部月份');
    fillSelect('ftFilterVehicle', data.vehicle_models || [], null, '全部项目');
    fillSelect('ftFilterCreator', data.creators || [], null, '全部上传人');

    const noCategory = !(data.allowed_categories || []).length;
    document.getElementById('ftNoCategoryHint')?.classList.toggle('hidden', !noCategory);
    document.getElementById('ftTableWrap')?.classList.toggle('hidden', noCategory);
    document.getElementById('ftPagination')?.classList.toggle('hidden', noCategory);
}

async function loadFilters() {
    const res = await HttpClient.get(`${API_BASE}/filters`);
    ftState.filters = res.data;
    applyFilterOptions(res.data);
}

async function loadData(page = 1) {
    if (ftState.filters && !(ftState.filters.allowed_categories || []).length) {
        ftState.items = [];
        ftState.total = 0;
        renderList();
        return;
    }
    if (ftState.isLoading) return;

    ftState.page = page;
    ftState.isLoading = true;
    setSearchBusy('ftBtnSearch', true);
    try {
        const res = await HttpClient.get(`${API_BASE}/list`, { params: buildQueryParams(page) });
        const payload = res.data || {};
        ftState.items = payload.items || [];
        ftState.total = payload.total || 0;
        renderList();
    } catch (error) {
        console.error('加载文件溯源失败', error);
        ftState.items = [];
        ftState.total = 0;
        renderList();
    } finally {
        ftState.isLoading = false;
        setSearchBusy('ftBtnSearch', false);
    }
}

function renderList() {
    const tbody = document.getElementById('ftTableBody');
    if (tbody) tbody.innerHTML = renderTableRows(ftState.items);
    const info = document.getElementById('ftPageInfo');
    if (info) info.textContent = `共 ${ftState.total} 条`;
    const totalPages = Math.max(1, Math.ceil((ftState.total || 0) / ftState.pageSize));
    paintPagination('ftPageButtons', ftState.page, totalPages);
}

function openDrawer(item) {
    ftState.detailItem = item;
    ftState.drawerOpen = true;
    const body = document.getElementById('ftDrawerBody');
    if (body) body.innerHTML = renderDrawerDetail(item);
    document.getElementById('ftDrawerBackdrop')?.classList.remove('hidden');
    document.getElementById('ftDrawer')?.classList.remove('translate-x-full');
}

function closeDrawer() {
    ftState.drawerOpen = false;
    ftState.detailItem = null;
    document.getElementById('ftDrawerBackdrop')?.classList.add('hidden');
    document.getElementById('ftDrawer')?.classList.add('translate-x-full');
}

async function openDetail(fileId) {
    const res = await HttpClient.get(`${API_BASE}/${fileId}`);
    openDrawer(res.data);
}

async function downloadFile(fileId) {
    const { blob, filename } = await HttpClient.download(`${API_BASE}/${fileId}/download`, {
        defaultFilename: 'download.xlsx',
    });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    window.URL.revokeObjectURL(url);
    showToast(`下载成功: ${filename}`, 'success');
}

function resetFilters() {
    ['ftFilterCategory', 'ftFilterLocation', 'ftFilterYear', 'ftFilterMonth', 'ftFilterVehicle', 'ftFilterCreator'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    ['ftFilterFilename', 'ftFilterFrom', 'ftFilterTo'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    loadData(1);
}

function bindEvents() {
    bindPagination({
        selectId: 'ftPageSize',
        buttonsId: 'ftPageButtons',
        getSize: () => ftState.pageSize,
        setSize: (size) => {
            ftState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    document.getElementById('ftBtnSearch')?.addEventListener('click', () => loadData(1));
    document.getElementById('ftBtnReset')?.addEventListener('click', resetFilters);
    [
        'ftFilterCategory',
        'ftFilterLocation',
        'ftFilterYear',
        'ftFilterMonth',
        'ftFilterVehicle',
        'ftFilterCreator',
        'ftFilterFrom',
        'ftFilterTo',
    ].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => loadData(1));
    });
    document.getElementById('ftFilterFilename')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            loadData(1);
        }
    });
    document.getElementById('ftDrawerClose')?.addEventListener('click', closeDrawer);
    document.getElementById('ftDrawerBackdrop')?.addEventListener('click', closeDrawer);

    document.getElementById('ftTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        const fileId = btn.getAttribute('data-id');
        if (!fileId) return;
        if (btn.dataset.action === 'detail') {
            openDetail(fileId);
            return;
        }
        if (btn.dataset.action === 'download') {
            downloadFile(fileId);
        }
    });

    document.getElementById('ftDrawerBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('#ftDrawerDownload');
        if (!btn) return;
        downloadFile(btn.dataset.id);
    });

    document.addEventListener('keydown', onKeyDown);
}

function onKeyDown(event) {
    if (event.key === 'Escape' && ftState.drawerOpen) closeDrawer();
}

function destroy() {
    document.removeEventListener('keydown', onKeyDown);
    closeDrawer();
}

const FileTracePage = {
    init() {
        bindEvents();
        loadFilters().then(() => loadData(1));
    },
    destroy,
};

export const pageConfig = {
    render: fileTraceTemplate,
    init: () => FileTracePage.init(),
    destroy: () => FileTracePage.destroy(),
};
