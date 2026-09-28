/**
 * 工程变更单列表 — 按变更单行展示；删除即整本回滚并物理删除
 */

import {
    engineeringChangeListTemplate,
    renderEcDetailBody,
    renderEcListRows,
} from './template.js?v=41';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import { can } from '../../../../core/permissions.js?v=8';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=4';
import { monthOptionsHtml, yearOptionsHtml } from '../../../common/period-ui.js?v=4';

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

/** @type {{ paint: () => void, setOpen: (isOpen: boolean) => void, unbind: () => void } | null} */
let filterBar = null;

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
        selectId: 'ecPageSize',
        buttonsId: 'ecPagination',
        getSize: () => state.pageSize,
        setSize: (size) => {
            state.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    loadScopeOptions().then(() => loadData(1));
}

function destroy() {
    filterBar?.unbind();
    filterBar = null;
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
    filterBar?.paint();
}

function bindEvents() {
    filterBar = bindFilterBar({
        prefix: 'ec',
        searchId: 'ecListSearchBtn',
        resetId: 'ecListResetBtn',
        capsules: [
            {
                capsuleId: 'ecCapsulePeriod',
                fieldIds: ['ecListYearFilter', 'ecListMonthFilter'],
                idleLabel: '全部期间',
                display: () => {
                    const year = document.getElementById('ecListYearFilter')?.value || '';
                    const month = document.getElementById('ecListMonthFilter')?.value || '';
                    if (year && month && typeof fmtPeriod === 'function') return fmtPeriod(year, month);
                    if (year && typeof fmtYear === 'function') return fmtYear(year);
                    return year;
                },
            },
            { capsuleId: 'ecCapsuleLocation', fieldId: 'ecListLocationFilter', idleLabel: '全部基地' },
            { capsuleId: 'ecCapsuleVehicle', fieldId: 'ecListVehicleFilter', idleLabel: '全部项目' },
            { capsuleId: 'ecCapsuleStatus', fieldId: 'ecListStatusFilter', idleLabel: '全部状态' },
            { capsuleId: 'ecCapsuleChangeType', fieldId: 'ecListChangeTypeFilter', idleLabel: '全部变更类型' },
        ],
        onSearch: () => loadData(1),
        onReset: () => {
            FILTER_IDS.forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            loadScopeOptions().then(() => loadData(1));
        },
    });
    ['ecListYearFilter', 'ecListMonthFilter', 'ecListLocationFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            loadScopeOptions().then(() => loadData(1));
        });
    });
    ['ecListVehicleFilter', 'ecListStatusFilter', 'ecListChangeTypeFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            loadData(1);
        });
    });
    document.getElementById('ecTableBody')?.addEventListener('click', (event) => {
        handleActionClick(event);
    });
    document.getElementById('ecDetailCloseBtn')?.addEventListener('click', closeDrawer);
    document.getElementById('ecDetailDrawerBackdrop')?.addEventListener('click', closeDrawer);
    document.getElementById('ecDetailBody')?.addEventListener('click', (event) => {
        handleActionClick(event);
    });
}

async function handleActionClick(event) {
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
    if (!await window.confirmAction('确定删除？会撤销这一整本设计变更，同一文件里的变更一起去掉。')) return;
    HttpClient.delete(`${API}/change-orders/${uploadLogId}`)
        .then(() => {
            showToast('已撤销这一整本', 'success');
            loadData(state.page);
        })
        .catch(() => {
            /* HttpClient 已弹出删除失败提示框 */
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
    const empty = document.getElementById('ecEmpty');
    const body = document.getElementById('ecTableBody');
    if (body) body.innerHTML = '';
    empty?.classList.remove('hidden');
    const titleEl = document.getElementById('ecEmptyTitle');
    const hintEl = document.getElementById('ecEmptyHint');
    if (titleEl) titleEl.textContent = title;
    if (hintEl) hintEl.textContent = hint;
    const info = document.getElementById('ecPageInfo');
    if (info) info.textContent = '';
    const pager = document.getElementById('ecPagination');
    if (pager) pager.innerHTML = '';
}

async function loadData(page) {
    if (state.isLoading) return;
    state.page = page;
    state.isLoading = true;
    setSearchBusy('ecListSearchBtn', true);
    const empty = document.getElementById('ecEmpty');
    const loading = document.getElementById('ecLoading');
    empty?.classList.add('hidden');
    loading?.classList.remove('hidden');
    const filters = collectFilters();
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
        const body = document.getElementById('ecTableBody');
        if (body) {
            body.innerHTML = renderEcListRows(state.records, { canDelete: state.canDelete });
        }
        const info = document.getElementById('ecPageInfo');
        if (info) info.textContent = `共 ${state.total} 条`;
        paintPagination(
            'ecPagination',
            state.page,
            state.total > 0 ? Math.ceil(state.total / state.pageSize) : 0,
        );
        if (!state.records.length) {
            renderEmpty('暂无记录', '请先上传设计变更，或调整筛选条件');
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
