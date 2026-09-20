/**
 * 工程变更单列表 — 按变更单行展示；删除即整本回滚并物理删除
 */

import {
    engineeringChangeListTemplate,
    renderEcDetailBody,
    renderEcListRows,
    updateEcFilterCapsules,
} from './template.js?v=20';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../page-size.js?v=3';
import { can } from '../../../permissions.js?v=6';
import { setSearchBusy } from '../../../search-busy.js?v=1';
import { monthOptionsHtml, yearOptionsHtml } from '../../common/period-ui.js?v=2';

const API = '/api/engineering-change';
const CASCADE_API = '/api/bom/filters/cascade';
const FILTER_IDS = [
    'ecListYearFilter',
    'ecListMonthFilter',
    'ecListLocationFilter',
    'ecListVehicleFilter',
    'ecListStatusFilter',
    'ecListChangeTypeFilter',
];

const state = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    canDelete: false,
    isLoading: false,
    advancedOpen: false,
};

function init() {
    state.canDelete = typeof can === 'function'
        ? can('op:engineering-change-order-list:delete')
        : false;
    fillPeriodFilters();
    bindEvents();
    bindPagination({
        selectId: 'ecListPageSize',
        buttonsId: 'ecListPagination',
        getSize: () => state.pageSize,
        setSize: (size) => {
            state.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    updateEcFilterCapsules();
    loadScopeOptions().then(() => loadData(1));
}

function destroy() {
    closeDrawer();
}

function fillPeriodFilters() {
    const yearEl = document.getElementById('ecListYearFilter');
    const monthEl = document.getElementById('ecListMonthFilter');
    if (yearEl) {
        yearEl.innerHTML = `<option value="">全部</option>${yearOptionsHtml(null)}`;
        yearEl.value = '';
    }
    if (monthEl) {
        monthEl.innerHTML = `<option value="">全部</option>${monthOptionsHtml(null)}`;
        monthEl.value = '';
    }
}

function setAdvancedOpen(isOpen) {
    state.advancedOpen = isOpen;
    document.getElementById('ecAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('ecAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function fillSelect(id, values) {
    const select = document.getElementById(id);
    if (!select) return;
    const kept = select.value || '';
    const options = ['<option value="">全部</option>'];
    (values || []).forEach((value) => {
        const text = String(value);
        options.push(`<option value="${esc(text)}">${esc(text)}</option>`);
    });
    select.innerHTML = options.join('');
    if (kept && [...select.options].some((opt) => opt.value === kept)) {
        select.value = kept;
    } else {
        select.value = '';
    }
}

async function loadScopeOptions() {
    const location = document.getElementById('ecListLocationFilter')?.value || '';
    const year = document.getElementById('ecListYearFilter')?.value || '';
    const month = document.getElementById('ecListMonthFilter')?.value || '';
    const params = {};
    if (location) params.location = location;
    if (year) params.year = Number(year);
    if (month) params.month = Number(month);
    try {
        const res = await HttpClient.get(CASCADE_API, { skipToast: true, params });
        const data = res && res.data;
        const locations = Array.isArray(data)
            ? data
            : (data && Array.isArray(data.locations) ? data.locations : []);
        const vehicles = location && data && Array.isArray(data.vehicle_models)
            ? data.vehicle_models
            : [];
        fillSelect('ecListLocationFilter', locations);
        fillSelect('ecListVehicleFilter', vehicles);
    } catch (_error) {
        fillSelect('ecListLocationFilter', []);
        fillSelect('ecListVehicleFilter', []);
    }
    updateEcFilterCapsules();
}

function bindEvents() {
    document.getElementById('ecListSearchBtn')?.addEventListener('click', () => {
        updateEcFilterCapsules();
        loadData(1);
    });
    document.getElementById('ecToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!state.advancedOpen);
    });
    document.getElementById('ecListResetBtn')?.addEventListener('click', () => {
        FILTER_IDS.forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        updateEcFilterCapsules();
        loadScopeOptions().then(() => loadData(1));
    });
    ['ecListYearFilter', 'ecListMonthFilter', 'ecListLocationFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            loadScopeOptions().then(() => loadData(1));
        });
    });
    ['ecListVehicleFilter', 'ecListStatusFilter', 'ecListChangeTypeFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            updateEcFilterCapsules();
            loadData(1);
        });
    });
    document.getElementById('ecListTableBody')?.addEventListener('click', (event) => {
        handleActionClick(event);
    });
    document.getElementById('ecDetailCloseBtn')?.addEventListener('click', closeDrawer);
    document.getElementById('ecDetailDrawerBackdrop')?.addEventListener('click', closeDrawer);
    document.getElementById('ecDetailBody')?.addEventListener('click', (event) => {
        handleActionClick(event);
    });
}

function handleActionClick(event) {
    const btn = event.target.closest('[data-action]');
    if (!btn) return;
    const uploadLogId = Number(btn.getAttribute('data-upload-log-id'));
    if (!uploadLogId) return;
    const action = btn.getAttribute('data-action');
    if (action === 'view') {
        openView(uploadLogId);
        return;
    }
    if (action === 'download') {
        downloadOriginal(uploadLogId, btn.getAttribute('data-filename'));
        return;
    }
    if (action !== 'delete') return;
    if (!confirm('删除即回滚。将撤销本次上传的全部变更并删除本记录，同一文件的全部变更单行都会去掉。')) return;
    HttpClient.delete(`${API}/change-orders/${uploadLogId}`)
        .then(() => {
            showToast('已删除并回滚', 'success');
            loadData(state.page);
        })
        .catch((error) => {
            showToast(error?.message || '删除失败', 'error');
        });
}

function collectFilters() {
    const location = document.getElementById('ecListLocationFilter')?.value || '';
    const vehicle = document.getElementById('ecListVehicleFilter')?.value || '';
    const year = document.getElementById('ecListYearFilter')?.value || '';
    const month = document.getElementById('ecListMonthFilter')?.value || '';
    const status = document.getElementById('ecListStatusFilter')?.value || '';
    const changeType = document.getElementById('ecListChangeTypeFilter')?.value || '';
    return { location, vehicle, year, month, status, changeType };
}

function updateHud(filters) {
    const parts = [
        filters.location,
        filters.vehicle,
        filters.year && filters.month
            ? (typeof fmtPeriod === 'function' ? fmtPeriod(filters.year, filters.month) : `${filters.year}年${String(filters.month).padStart(2, '0')}月`)
            : (filters.year ? (typeof fmtYear === 'function' ? fmtYear(filters.year) : `${filters.year}年`) : ''),
        ({ pending: '进行中', success: '成功', failed: '失败' }[filters.status] || filters.status),
        filters.changeType,
    ].filter(Boolean);
    const scopeEl = document.getElementById('ecListHudScope');
    if (scopeEl) scopeEl.textContent = parts.length ? parts.join(' · ') : '全部范围';
    const totalEl = document.getElementById('ecListHudTotal');
    if (totalEl) totalEl.textContent = String(state.total);
}

function renderEmpty(title, hint) {
    const empty = document.getElementById('ecListEmpty');
    const body = document.getElementById('ecListTableBody');
    if (body) body.innerHTML = '';
    empty?.classList.remove('hidden');
    const titleEl = document.getElementById('ecListEmptyTitle');
    const hintEl = document.getElementById('ecListEmptyHint');
    if (titleEl) titleEl.textContent = title;
    if (hintEl) hintEl.textContent = hint;
    const info = document.getElementById('ecListTotalLabel');
    if (info) info.textContent = '';
    const pager = document.getElementById('ecListPagination');
    if (pager) pager.innerHTML = '';
}

async function loadData(page) {
    if (state.isLoading) return;
    state.page = page;
    state.isLoading = true;
    setSearchBusy('ecListSearchBtn', true);
    const empty = document.getElementById('ecListEmpty');
    const loading = document.getElementById('ecListLoading');
    empty?.classList.add('hidden');
    loading?.classList.remove('hidden');
    const filters = collectFilters();
    updateEcFilterCapsules();
    const params = {
        page: state.page,
        size: state.pageSize,
    };
    if (filters.location) params.location = filters.location;
    if (filters.vehicle) params.vehicle_model = filters.vehicle;
    if (filters.year) params.effective_year = Number(filters.year);
    if (filters.month) params.effective_month = Number(filters.month);
    if (filters.status) params.status = filters.status;
    if (filters.changeType) params.change_type = filters.changeType;
    try {
        const res = await HttpClient.get(`${API}/change-orders`, { params });
        const data = res?.data || {};
        state.records = Array.isArray(data.items) ? data.items : [];
        state.total = Number(data.total || 0);
        updateHud(filters);
        const body = document.getElementById('ecListTableBody');
        if (body) {
            body.innerHTML = renderEcListRows(state.records, { canDelete: state.canDelete });
        }
        const info = document.getElementById('ecListTotalLabel');
        if (info) info.textContent = `共 ${state.total} 条`;
        paintPagination(
            'ecListPagination',
            state.page,
            state.total > 0 ? Math.ceil(state.total / state.pageSize) : 0,
        );
        if (!state.records.length) {
            renderEmpty('暂无记录', '请先上传工程变更，或调整筛选条件');
            const totalEl = document.getElementById('ecListHudTotal');
            if (totalEl) totalEl.textContent = '0';
        }
    } catch (error) {
        showToast(error?.message || '加载列表失败', 'error');
        renderEmpty('加载失败', error?.message || '请稍后重试');
        const totalEl = document.getElementById('ecListHudTotal');
        if (totalEl) totalEl.textContent = '—';
    } finally {
        state.isLoading = false;
        setSearchBusy('ecListSearchBtn', false);
        loading?.classList.add('hidden');
    }
}

function openDrawer() {
    document.getElementById('ecDetailDrawer')?.classList.remove('hidden');
    document.getElementById('ecDetailDrawerBackdrop')?.classList.remove('hidden');
}

function closeDrawer() {
    document.getElementById('ecDetailDrawer')?.classList.add('hidden');
    document.getElementById('ecDetailDrawerBackdrop')?.classList.add('hidden');
}

function openView(uploadLogId) {
    const row = state.records.find((item) => Number(item.upload_log_id) === uploadLogId);
    const body = document.getElementById('ecDetailBody');
    if (!row || !body) {
        showToast('记录不存在', 'error');
        return;
    }
    body.innerHTML = renderEcDetailBody(row);
    openDrawer();
}

async function downloadOriginal(uploadLogId, fallbackName) {
    try {
        const { blob, filename } = await HttpClient.download(
            `${API}/change-orders/${uploadLogId}/original-file`,
            { defaultFilename: fallbackName || 'engineering-change.xlsx' },
        );
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
        showToast(`下载成功: ${filename}`, 'success');
    } catch (error) {
        showToast(error?.message || '下载失败', 'error');
    }
}

export const pageConfig = {
    render: () => engineeringChangeListTemplate(),
    init,
    destroy,
};
