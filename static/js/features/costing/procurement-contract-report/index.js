/**
 * 采购价格 — 只读价目表 + 协议导出
 */

import {
    procurementContractReportTemplate,
    renderPcrPagination,
    renderPcrRows,
    renderPcrTableHead,
    updatePcrFilterCapsules,
    updatePcrHud,
    updatePcrViewButtons,
} from './template.js?v=15';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../page-size.js?v=2';
import { setSearchBusy } from '../../../search-busy.js?v=1';

const API_BASE = '/api/costing/procurement-contract-report';
const CASCADE_API = '/api/bom/filters/cascade';
const MAX_WINDOW_MONTHS = 12;
const SCOPE_REQUIRED_MESSAGE = '请选定基地、项目、BOM 版本';

const listState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    items: [],
    months: [],
    view: 'procurement',
    canExport: true,
    isLoading: false,
    advancedOpen: false,
};

function init() {
    applyPermissionUi();
    bindEvents();
    bindPageSizeSelect('pcrPageSize', {
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onChange: () => loadList(1),
    });
    fillYearMonthOptions();
    renderPcrTableHead([]);
    updatePcrViewButtons(listState.view);
    updatePcrFilterCapsules();
    openWithData();
}

function destroy() {}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    listState.canExport = canFn('op:procurement-contract-report:export');
    if (!listState.canExport) {
        document.getElementById('pcrExportBtn')?.classList.add('hidden');
    }
}

function setAdvancedOpen(isOpen) {
    listState.advancedOpen = isOpen;
    document.getElementById('pcrAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('pcrAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function bindEvents() {
    document.getElementById('pcrSearchBtn')?.addEventListener('click', () => {
        updatePcrFilterCapsules();
        refreshSuppliers().then(() => loadList(1));
    });
    document.getElementById('pcrToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!listState.advancedOpen);
    });
    document.getElementById('pcrResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('pcrExportBtn')?.addEventListener('click', exportExcel);
    document.getElementById('pcrViewProcurementBtn')?.addEventListener('click', () => {
        setView('procurement');
    });
    document.getElementById('pcrViewAssemblyBtn')?.addEventListener('click', () => {
        setView('assembly');
    });
    document.getElementById('pcrLocationFilter')?.addEventListener('change', () => {
        setSelectValue('pcrVehicleModelFilter', '');
        setSelectValue('pcrBomVersionFilter', '');
        loadCascade().then(() => {
            updatePcrFilterCapsules();
            refreshSuppliers().then(() => loadList(1));
        });
    });
    document.getElementById('pcrVehicleModelFilter')?.addEventListener('change', () => {
        setSelectValue('pcrBomVersionFilter', '');
        loadCascade().then(() => {
            updatePcrFilterCapsules();
            refreshSuppliers().then(() => loadList(1));
        });
    });
    document.getElementById('pcrBomVersionFilter')?.addEventListener('change', () => {
        updatePcrFilterCapsules();
        refreshSuppliers().then(() => loadList(1));
    });
    ['pcrStartYearFilter', 'pcrStartMonthFilter', 'pcrEndYearFilter', 'pcrEndMonthFilter']
        .forEach((id) => {
            document.getElementById(id)?.addEventListener('change', () => {
                updatePcrFilterCapsules();
                refreshSuppliers().then(() => loadList(1));
            });
        });
    document.getElementById('pcrSupplierFilter')?.addEventListener('change', () => {
        updatePcrFilterCapsules();
        loadList(1);
    });
    ['pcrPartNumberFilter', 'pcrPartNameFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                updatePcrFilterCapsules();
                loadList(1);
            }
        });
    });
    document.getElementById('pcrPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.pcr-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadList(page);
        }
    });
}

function isAssemblyView() {
    return listState.view === 'assembly';
}

function setView(view) {
    if (listState.view === view) return;
    listState.view = view;
    if (view === 'assembly') {
        setSelectValue('pcrSupplierFilter', '');
    }
    updatePcrViewButtons(view);
    updatePcrFilterCapsules();
    refreshSuppliers().then(() => loadList(1));
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function fillYearMonthOptions(extraYears = []) {
    const now = new Date();
    const thisYear = now.getFullYear();
    let minYear = 2020;
    let maxYear = thisYear + 1;
    extraYears.forEach((raw) => {
        const year = Number(raw);
        if (Number.isFinite(year)) {
            minYear = Math.min(minYear, year);
            maxYear = Math.max(maxYear, year);
        }
    });
    const years = [];
    for (let year = minYear; year <= maxYear; year += 1) years.push(String(year));
    ['pcrStartYearFilter', 'pcrEndYearFilter'].forEach((id) => fillSelect(id, years, false));
    const months = [];
    for (let month = 1; month <= 12; month += 1) months.push(String(month));
    ['pcrStartMonthFilter', 'pcrEndMonthFilter'].forEach((id) => {
        fillSelect(id, months, false, (month) => fmtMonth(month) || month);
    });
}

function applyCostWindow(year, month) {
    const yearNum = Number(year);
    const monthNum = Number(month);
    if (!Number.isFinite(yearNum) || !Number.isFinite(monthNum)) return false;
    if (monthNum < 1 || monthNum > 12) return false;
    fillYearMonthOptions([yearNum]);
    setSelectValue('pcrStartYearFilter', String(yearNum));
    setSelectValue('pcrStartMonthFilter', String(monthNum));
    setSelectValue('pcrEndYearFilter', String(yearNum));
    setSelectValue('pcrEndMonthFilter', String(monthNum));
    return true;
}

async function openWithData() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/defaults`, { skipToast: true });
        const data = res.data || {};
        if (data.location) {
            await loadCascade();
            setSelectValue('pcrLocationFilter', data.location);
            await loadCascade();
            setSelectValue('pcrVehicleModelFilter', data.vehicle_model);
            await loadCascade();
            setSelectValue('pcrBomVersionFilter', data.bom_version);
            applyCostWindow(data.start_year, data.start_month);
        } else {
            await loadCascade();
        }
    } catch (error) {
        console.error('加载默认范围失败', error);
        await loadCascade();
    }
    updatePcrFilterCapsules();
    await refreshSuppliers();
    await loadList(1);
}

function fillSelect(id, values, includeEmpty = true, labelFn = null, emptyLabel = '请选择') {
    const el = document.getElementById(id);
    if (!el) return;
    const selected = el.value;
    let html = includeEmpty ? `<option value="">${esc(emptyLabel)}</option>` : '';
    (values || []).forEach((item) => {
        const value = String(item);
        const label = labelFn ? labelFn(value) : value;
        html += `<option value="${esc(value)}">${esc(label)}</option>`;
    });
    el.innerHTML = html;
    if (selected && (values || []).map(String).includes(selected)) el.value = selected;
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select) return;
    const text = value == null ? '' : String(value);
    if (text && ![...select.options].some((opt) => opt.value === text)) {
        select.insertAdjacentHTML('beforeend', `<option value="${esc(text)}">${esc(text)}</option>`);
    }
    select.value = text;
}

async function loadCascade() {
    try {
        const params = {};
        if (val('pcrLocationFilter')) params.location = val('pcrLocationFilter');
        if (val('pcrVehicleModelFilter')) params.vehicle_model = val('pcrVehicleModelFilter');
        const res = await HttpClient.get(CASCADE_API, { params });
        const data = res.data || {};
        fillSelect('pcrLocationFilter', data.locations || []);
        fillSelect('pcrVehicleModelFilter', data.vehicle_models || []);
        fillSelect('pcrBomVersionFilter', data.bom_versions || []);
    } catch (error) {
        console.error('加载级联筛选失败', error);
    }
}

function readScope(showWarning = false) {
    const location = val('pcrLocationFilter');
    const vehicleModel = val('pcrVehicleModelFilter');
    const bomVersion = val('pcrBomVersionFilter');
    const startYear = Number.parseInt(val('pcrStartYearFilter'), 10);
    const startMonth = Number.parseInt(val('pcrStartMonthFilter'), 10);
    const endYear = Number.parseInt(val('pcrEndYearFilter'), 10);
    const endMonth = Number.parseInt(val('pcrEndMonthFilter'), 10);
    if (!location || !vehicleModel || !bomVersion) {
        if (showWarning) showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return null;
    }
    if (![startYear, startMonth, endYear, endMonth].every(Number.isFinite)) {
        if (showWarning) showToast('请选定开始、结束年月', 'warning');
        return null;
    }
    const startIndex = startYear * 12 + startMonth;
    const endIndex = endYear * 12 + endMonth;
    if (startIndex > endIndex) {
        if (showWarning) showToast('开始年月不得晚于结束年月', 'warning');
        return null;
    }
    const count = endIndex - startIndex + 1;
    if (count > MAX_WINDOW_MONTHS) {
        if (showWarning) showToast(`查询窗口最多 ${MAX_WINDOW_MONTHS} 个月，当前 ${count} 个月`, 'warning');
        return null;
    }
    return {
        location,
        vehicle_model: vehicleModel,
        bom_version: bomVersion,
        start_year: startYear,
        start_month: startMonth,
        end_year: endYear,
        end_month: endMonth,
        supplier_name: isAssemblyView() ? undefined : (val('pcrSupplierFilter') || undefined),
        view: listState.view,
    };
}

function queryParams(scope, page, { forExport = false } = {}) {
    const params = { ...scope };
    if (!forExport) {
        if (val('pcrPartNumberFilter')) params.part_number = val('pcrPartNumberFilter');
        if (val('pcrPartNameFilter')) params.part_name = val('pcrPartNameFilter');
    }
    if (page != null) {
        params.page = page;
        params.size = listState.pageSize;
    }
    return params;
}

async function refreshSuppliers() {
    if (isAssemblyView()) {
        fillSelect('pcrSupplierFilter', [], true, null, '全部');
        return;
    }
    const scope = readScope();
    const selected = val('pcrSupplierFilter');
    if (!scope) {
        fillSelect('pcrSupplierFilter', [], true, null, '全部');
        return;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/prep`, {
            params: queryParams(scope, null, { forExport: true }),
            skipToast: true,
        });
        const names = res.data?.supplier_names || [];
        fillSelect('pcrSupplierFilter', names, true, null, '全部');
        if (selected && names.includes(selected)) {
            setSelectValue('pcrSupplierFilter', selected);
        }
    } catch (_error) {
        fillSelect('pcrSupplierFilter', selected ? [selected] : [], true, null, '全部');
        if (selected) setSelectValue('pcrSupplierFilter', selected);
    }
}

function setListLoading(isLoading) {
    listState.isLoading = isLoading;
    setSearchBusy('pcrSearchBtn', isLoading);
    document.getElementById('pcrLoading')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        document.getElementById('pcrEmpty')?.classList.add('hidden');
        document.getElementById('pcrTable')?.parentElement?.classList.remove('hidden');
    }
}

function setListEmpty(isEmpty, message) {
    const empty = document.getElementById('pcrEmpty');
    const text = document.getElementById('pcrEmptyText');
    if (text && message) text.innerHTML = message;
    empty?.classList.toggle('hidden', !isEmpty);
    document.getElementById('pcrTable')?.parentElement?.classList.toggle('hidden', Boolean(isEmpty));
}

function setQaBanner(filters) {
    const banner = document.getElementById('pcrQaBanner');
    if (!banner) return;
    if (filters && filters.qa_passed === false) {
        const detail = filters.qa_error_text ? `：${esc(filters.qa_error_text)}` : '';
        banner.textContent = `采购对象清单检测未通过${detail}`;
        banner.classList.remove('hidden');
        return;
    }
    banner.textContent = '';
    banner.classList.add('hidden');
}

function missingListMessage() {
    return '请先生成采购对象清单。<a href="#/bom-procurement-object" class="text-[#FF1E27] hover:underline">去生成</a>';
}

async function loadList(page = 1) {
    const body = document.getElementById('pcrTableBody');
    if (!body) return;
    if (listState.isLoading) return;
    updatePcrFilterCapsules();
    if (!val('pcrLocationFilter') || !val('pcrVehicleModelFilter') || !val('pcrBomVersionFilter')) {
        listState.items = [];
        listState.months = [];
        body.innerHTML = '';
        renderPcrTableHead([]);
        updatePcrHud(null);
        setQaBanner(null);
        setListLoading(false);
        setListEmpty(true, '请选择基地、项目、BOM 版本后查询');
        const pageInfo = document.getElementById('pcrPageInfo');
        if (pageInfo) pageInfo.textContent = '—';
        const pagination = document.getElementById('pcrPagination');
        if (pagination) pagination.innerHTML = '';
        return;
    }
    const scope = readScope(true);
    if (!scope) return;
    setListLoading(true);
    body.innerHTML = '';
    try {
        const res = await HttpClient.get(API_BASE, { params: queryParams(scope, page) });
        const pageData = res.data || {};
        const filters = pageData.filters || {};
        listState.page = pageData.page || page;
        listState.total = pageData.total || 0;
        listState.totalPages = pageData.total_pages || 1;
        listState.items = Array.isArray(pageData.items) ? pageData.items : [];
        listState.months = Array.isArray(filters.months) ? filters.months : [];
        renderPcrTableHead(listState.months);
        body.innerHTML = renderPcrRows(listState.items, listState.months);
        updatePcrHud(filters);
        setQaBanner(filters);
        const emptyHint = filters.empty_hint
            ? (isAssemblyView()
                ? esc(filters.empty_hint)
                : `${esc(filters.empty_hint)} <a href="#/bom-procurement-object-list" class="text-[#FF1E27] hover:underline">去采购对象清单</a>`)
            : '当前范围没有可展示的价目行';
        setListEmpty(listState.items.length === 0, emptyHint);
        const pageInfo = document.getElementById('pcrPageInfo');
        if (pageInfo) {
            pageInfo.textContent =
                `第 ${listState.page} / ${Math.max(listState.totalPages, 1)} 页 · ${listState.total} 条`;
        }
        const pagination = document.getElementById('pcrPagination');
        if (pagination) {
            pagination.innerHTML = renderPcrPagination(listState.page, listState.totalPages);
        }
    } catch (error) {
        listState.items = [];
        body.innerHTML = '';
        updatePcrHud(null);
        setQaBanner(null);
        const message = String(error?.message || '');
        let emptyText;
        if (!isAssemblyView() && message.includes('采购对象清单')) {
            emptyText = missingListMessage();
        } else if (isAssemblyView() && message.includes('材料清单')) {
            emptyText = '未找到对应材料清单。<a href="#/bom-upload" class="text-[#FF1E27] hover:underline">去上传材料清单</a>';
        } else {
            emptyText = esc(message || '查询失败');
        }
        setListEmpty(true, emptyText);
    } finally {
        setListLoading(false);
    }
}

async function resetFilters() {
    setSelectValue('pcrLocationFilter', '');
    setSelectValue('pcrVehicleModelFilter', '');
    setSelectValue('pcrBomVersionFilter', '');
    setSelectValue('pcrSupplierFilter', '');
    const partNumberEl = document.getElementById('pcrPartNumberFilter');
    const partNameEl = document.getElementById('pcrPartNameFilter');
    if (partNumberEl) partNumberEl.value = '';
    if (partNameEl) partNameEl.value = '';
    await openWithData();
}

async function exportExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const scope = readScope(true);
    if (!scope) return;
    if (!isAssemblyView() && !scope.supplier_name) {
        setAdvancedOpen(true);
        return showToast('请先选定供应商再导出协议', 'warning');
    }
    const btn = document.getElementById('pcrExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: queryParams(scope, null, { forExport: true }),
            defaultFilename: '批量零部件价格协议.xlsx',
            timeout: 120000,
        });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
        showToast(`导出成功: ${filename}`, 'success');
    } catch (error) {
        if (!error.status) showToast(error.message || '导出失败', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

export const pageConfig = {
    render: procurementContractReportTemplate,
    init,
    destroy,
};
