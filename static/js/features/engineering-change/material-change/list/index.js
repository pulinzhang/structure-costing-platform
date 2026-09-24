/**
 * 材料变更列表 — 按变更单行展示；删除即整本回滚并物理删除
 */

import {
    materialChangeListTemplate,
    renderEcmDetailBody,
    renderEcmListRows,
} from './template.js?v=6';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import { can } from '../../../../core/permissions.js?v=8';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=4';
import { monthOptionsHtml, yearOptionsHtml } from '../../../common/period-ui.js?v=4';
import { downloadMaterialChangeFile } from '../download.js?v=1';

const API = '/api/engineering-change/material';
const CASCADE_API = '/api/bom/filters/cascade';
const FILTER_IDS = [
    'ecmListYearFilter',
    'ecmListMonthFilter',
    'ecmListLocationFilter',
    'ecmListVehicleFilter',
    'ecmListStatusFilter',
];

let filterBar = null;

const state = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    canDelete: false,
    isLoading: false,
};

function init() {
    state.canDelete = typeof can === 'function'
        ? can('op:engineering-change-material-list:delete')
        : false;
    fillPeriodFilters();
    bindEvents();
    bindPagination({
        selectId: 'ecmPageSize',
        buttonsId: 'ecmPagination',
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
    const yearEl = document.getElementById('ecmListYearFilter');
    const monthEl = document.getElementById('ecmListMonthFilter');
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
    const location = document.getElementById('ecmListLocationFilter')?.value || '';
    const year = document.getElementById('ecmListYearFilter')?.value || '';
    const month = document.getElementById('ecmListMonthFilter')?.value || '';
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
        fillSelect('ecmListLocationFilter', locations);
        fillSelect('ecmListVehicleFilter', vehicles);
    } catch (_error) {
        fillSelect('ecmListLocationFilter', []);
        fillSelect('ecmListVehicleFilter', []);
    }
    filterBar?.paint();
}

function bindEvents() {
    filterBar = bindFilterBar({
        prefix: 'ecm',
        searchId: 'ecmListSearchBtn',
        resetId: 'ecmListResetBtn',
        capsules: [
            {
                capsuleId: 'ecmCapsulePeriod',
                fieldIds: ['ecmListYearFilter', 'ecmListMonthFilter'],
                idleLabel: '全部期间',
                display: () => {
                    const year = document.getElementById('ecmListYearFilter')?.value || '';
                    const month = document.getElementById('ecmListMonthFilter')?.value || '';
                    if (year && month && typeof fmtPeriod === 'function') return fmtPeriod(year, month);
                    if (year && typeof fmtYear === 'function') return fmtYear(year);
                    return year;
                },
            },
            { capsuleId: 'ecmCapsuleLocation', fieldId: 'ecmListLocationFilter', idleLabel: '全部基地' },
            { capsuleId: 'ecmCapsuleVehicle', fieldId: 'ecmListVehicleFilter', idleLabel: '全部项目' },
            { capsuleId: 'ecmCapsuleStatus', fieldId: 'ecmListStatusFilter', idleLabel: '全部状态' },
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
    ['ecmListYearFilter', 'ecmListMonthFilter', 'ecmListLocationFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            loadScopeOptions().then(() => loadData(1));
        });
    });
    ['ecmListVehicleFilter', 'ecmListStatusFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            loadData(1);
        });
    });
    document.getElementById('ecmTableBody')?.addEventListener('click', (event) => {
        handleActionClick(event);
    });
    document.getElementById('ecmDetailCloseBtn')?.addEventListener('click', closeDrawer);
    document.getElementById('ecmDetailDrawerBackdrop')?.addEventListener('click', closeDrawer);
    document.getElementById('ecmDetailBody')?.addEventListener('click', (event) => {
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
    if (!await window.confirmAction('确定删除？会撤销这一整本材料变更，同一文件里的零件一起去掉。')) return;
    HttpClient.delete(`${API}/uploads/${uploadLogId}`)
        .then(() => {
            showToast('已撤销这一整本', 'success');
            closeDrawer();
            loadData(state.page);
        })
        .catch(() => {
            /* HttpClient 已弹出删除失败提示框 */
        });
}

function collectFilters() {
    const location = document.getElementById('ecmListLocationFilter')?.value || '';
    const vehicle = document.getElementById('ecmListVehicleFilter')?.value || '';
    const year = document.getElementById('ecmListYearFilter')?.value || '';
    const month = document.getElementById('ecmListMonthFilter')?.value || '';
    const status = document.getElementById('ecmListStatusFilter')?.value || '';
    return { location, vehicle, year, month, status };
}

function updateHud(filters) {
    const parts = [
        filters.location,
        filters.vehicle,
        filters.year && filters.month
            ? (typeof fmtPeriod === 'function' ? fmtPeriod(filters.year, filters.month) : `${filters.year}年${String(filters.month).padStart(2, '0')}月`)
            : (filters.year ? (typeof fmtYear === 'function' ? fmtYear(filters.year) : `${filters.year}年`) : ''),
        ({ pending: '进行中', success: '成功', failed: '失败' }[filters.status] || filters.status),
    ].filter(Boolean);
    const scopeEl = document.getElementById('ecmListHudScope');
    if (scopeEl) scopeEl.textContent = parts.length ? parts.join(' · ') : '全部范围';
    const totalEl = document.getElementById('ecmListHudTotal');
    if (totalEl) totalEl.textContent = String(state.total);
}

function renderEmpty(title, hint) {
    const empty = document.getElementById('ecmEmpty');
    const body = document.getElementById('ecmTableBody');
    if (body) body.innerHTML = '';
    empty?.classList.remove('hidden');
    const titleEl = document.getElementById('ecmEmptyTitle');
    const hintEl = document.getElementById('ecmEmptyHint');
    if (titleEl) titleEl.textContent = title;
    if (hintEl) hintEl.textContent = hint;
    const info = document.getElementById('ecmPageInfo');
    if (info) info.textContent = '';
    const pager = document.getElementById('ecmPagination');
    if (pager) pager.innerHTML = '';
}

async function loadData(page) {
    if (state.isLoading) return;
    state.page = page;
    state.isLoading = true;
    setSearchBusy('ecmListSearchBtn', true);
    const empty = document.getElementById('ecmEmpty');
    const loading = document.getElementById('ecmLoading');
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
    try {
        const res = await HttpClient.get(`${API}/uploads`, { params });
        const data = res?.data || {};
        state.records = Array.isArray(data.items) ? data.items : [];
        state.total = Number(data.total || 0);
        updateHud(filters);
        const body = document.getElementById('ecmTableBody');
        if (body) {
            body.innerHTML = renderEcmListRows(state.records, { canDelete: state.canDelete });
        }
        const info = document.getElementById('ecmPageInfo');
        if (info) info.textContent = `共 ${state.total} 条`;
        paintPagination(
            'ecmPagination',
            state.page,
            state.total > 0 ? Math.ceil(state.total / state.pageSize) : 0,
        );
        if (!state.records.length) {
            renderEmpty('暂无记录', '请先上传材料变更，或调整筛选条件');
            const totalEl = document.getElementById('ecmListHudTotal');
            if (totalEl) totalEl.textContent = '0';
        }
    } catch (error) {
        showToast(error?.message || '加载列表失败', 'error');
        renderEmpty('加载失败', error?.message || '请稍后重试');
        const totalEl = document.getElementById('ecmListHudTotal');
        if (totalEl) totalEl.textContent = '—';
    } finally {
        state.isLoading = false;
        setSearchBusy('ecmListSearchBtn', false);
        loading?.classList.add('hidden');
    }
}

function openDrawer() {
    document.getElementById('ecmDetailDrawer')?.classList.remove('hidden');
    document.getElementById('ecmDetailDrawerBackdrop')?.classList.remove('hidden');
}

function closeDrawer() {
    document.getElementById('ecmDetailDrawer')?.classList.add('hidden');
    document.getElementById('ecmDetailDrawerBackdrop')?.classList.add('hidden');
}

function openView(uploadLogId) {
    const row = state.records.find((item) => Number(item.upload_log_id) === uploadLogId);
    const body = document.getElementById('ecmDetailBody');
    if (!row || !body) {
        showToast('记录不存在', 'error');
        return;
    }
    body.innerHTML = renderEcmDetailBody(row);
    openDrawer();
}

async function downloadOriginal(uploadLogId, fallbackName) {
    try {
        await downloadMaterialChangeFile(uploadLogId, fallbackName);
    } catch (error) {
        showToast(error?.message || '下载失败', 'error');
    }
}

export const pageConfig = {
    render: () => materialChangeListTemplate(),
    init,
    destroy,
};
