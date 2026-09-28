/**
 * 采购价格 — 只读价目表 + 协议导出
 */

import {
    procurementContractReportTemplate,
    renderPcrRows,
    renderPcrTableHead,
    bindPcrChipMenus,
    unbindPcrChipMenus,
    syncPcrChipFace,
    updatePcrHud,
    cancelPcrHudCountUp,
    updatePcrViewButtons,
    updateRingIndicators,
} from './template.js?v=56';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../ui/page-size.js?v=6';

const API_BASE = '/api/costing/procurement-contract-report';
const CASCADE_API = '/api/bom/filters/cascade';
const MAX_WINDOW_MONTHS = 12;
const SCOPE_REQUIRED_MESSAGE = '请选定基地、项目';
const EXPORT_ALL_VERSIONS_MESSAGE = '导出协议须选全部版本';
const PART_FILTER_DEBOUNCE_MS = 300;
const CASCADE_LOCK_IDS = ['pcrVehicleModelFilter', 'pcrBomVersionFilter', 'pcrSupplierFilter'];

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
};

let cascadeGeneration = 0;
let partFilterTimer = null;

function init() {
    applyPermissionUi();
    bindEvents();
    bindPcrChipMenus();
    bindPagination({
        selectId: 'pcrPageSize',
        buttonsId: 'pcrPagination',
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onPage: (page) => loadList(page),
    });
    fillYearMonthOptions();
    renderPcrTableHead([]);
    updatePcrViewButtons(listState.view);
    updateRingIndicators();
    openWithData();
}

function destroy() {
    clearPartFilterTimer();
    unbindPcrChipMenus();
    cancelPcrHudCountUp();
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    listState.canExport = canFn('op:procurement-contract-report:export');
    if (!listState.canExport) {
        document.getElementById('pcrExportBtn')?.classList.add('hidden');
    }
}

function bumpCascadeGeneration() {
    cascadeGeneration += 1;
    return cascadeGeneration;
}

function isCascadeCurrent(generation) {
    return generation === cascadeGeneration;
}

function setCascadeLocked(isLocked) {
    CASCADE_LOCK_IDS.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.disabled = isLocked;
        const trigger = document.querySelector(`[data-pcr-chip="${id}"]`);
        if (trigger) trigger.disabled = isLocked;
    });
}

function clearPartFilterTimer() {
    if (partFilterTimer) {
        clearTimeout(partFilterTimer);
        partFilterTimer = null;
    }
}

function schedulePartFilter() {
    clearPartFilterTimer();
    partFilterTimer = setTimeout(() => {
        partFilterTimer = null;
        loadList(1);
    }, PART_FILTER_DEBOUNCE_MS);
}

function flushPartFilterAndReload() {
    clearPartFilterTimer();
    loadList(1);
}

function bindEvents() {
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
        const generation = bumpCascadeGeneration();
        setCascadeLocked(true);
        loadCascade(generation).then((ok) => {
            if (!ok) return false;
            return refreshSuppliers(generation);
        }).then((ok) => {
            if (!ok) return;
            if (!isCascadeCurrent(generation)) return;
            setCascadeLocked(false);
            updateRingIndicators();
            loadList(1);
        });
    });
    document.getElementById('pcrVehicleModelFilter')?.addEventListener('change', () => {
        setSelectValue('pcrBomVersionFilter', '');
        const generation = bumpCascadeGeneration();
        setCascadeLocked(true);
        loadCascade(generation).then((ok) => {
            if (!ok) return false;
            return refreshSuppliers(generation);
        }).then((ok) => {
            if (!ok) return;
            if (!isCascadeCurrent(generation)) return;
            setCascadeLocked(false);
            updateRingIndicators();
            loadList(1);
        });
    });
    document.getElementById('pcrBomVersionFilter')?.addEventListener('change', () => {
        updateRingIndicators();
        const generation = bumpCascadeGeneration();
        refreshSuppliers(generation).then((ok) => {
            if (!ok) return;
            loadList(1);
        });
    });
    ['pcrStartYearFilter', 'pcrStartMonthFilter', 'pcrEndYearFilter', 'pcrEndMonthFilter']
        .forEach((id) => {
            document.getElementById(id)?.addEventListener('change', () => {
                updateRingIndicators();
                const generation = bumpCascadeGeneration();
                refreshSuppliers(generation).then((ok) => {
                    if (!ok) return;
                    loadList(1);
                });
            });
        });
    document.getElementById('pcrSupplierFilter')?.addEventListener('change', () => {
        updateRingIndicators();
        loadList(1);
    });
    const partEl = document.getElementById('pcrPartFilter');
    partEl?.addEventListener('input', () => {
        schedulePartFilter();
    });
    partEl?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            flushPartFilterAndReload();
        }
    });
    partEl?.addEventListener('blur', () => {
        flushPartFilterAndReload();
    });
    document.getElementById('pcrTableBody')?.addEventListener('click', (event) => {
        const restoreBtn = event.target.closest('.btn-open-restore');
        if (!restoreBtn) return;
        const year = restoreBtn.dataset.year;
        const month = restoreBtn.dataset.month;
        const partNumber = restoreBtn.dataset.partNumber;
        if (!year || !month || !partNumber) return;
        const view = listState.view === 'procurement' ? 'procurement' : 'finance';
        const query = new URLSearchParams({
            year,
            month,
            part_number: partNumber,
            view,
        });
        const location = val('pcrLocationFilter');
        const vehicleModel = val('pcrVehicleModelFilter');
        const bomVersion = val('pcrBomVersionFilter');
        if (location) query.set('location', location);
        if (vehicleModel) query.set('vehicle_model', vehicleModel);
        if (bomVersion) query.set('bom_version', bomVersion);
        const opened = window.open(
            `/assembly-cost-restore?${query.toString()}`,
            '_blank',
            'noopener,noreferrer',
        );
        if (opened) opened.opener = null;
    });
}

function isAssemblyView() {
    return listState.view === 'assembly';
}

function shouldShowSupplierColumn() {
    return !isAssemblyView() && !val('pcrSupplierFilter');
}

function setView(view) {
    if (listState.view === view) return;
    listState.view = view;
    if (view === 'assembly') {
        setSelectValue('pcrSupplierFilter', '');
    }
    updatePcrViewButtons(view);
    updateRingIndicators();
    const generation = bumpCascadeGeneration();
    refreshSuppliers(generation).then((ok) => {
        if (!ok) return;
        loadList(1);
    });
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
    const generation = bumpCascadeGeneration();
    setCascadeLocked(true);
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/defaults`, { skipToast: true });
        if (!isCascadeCurrent(generation)) return;
        const data = res.data || {};
        if (data.location) {
            const stepOne = await loadCascade(generation);
            if (!stepOne) return;
            setSelectValue('pcrLocationFilter', data.location);
            const stepTwo = await loadCascade(generation);
            if (!stepTwo) return;
            setSelectValue('pcrVehicleModelFilter', data.vehicle_model);
            const stepThree = await loadCascade(generation);
            if (!stepThree) return;
            // 版本默认全部版本（不填）
            setSelectValue('pcrBomVersionFilter', '');
            applyCostWindow(data.start_year, data.start_month);
        } else {
            const ok = await loadCascade(generation);
            if (!ok) return;
        }
        if (!isCascadeCurrent(generation)) return;
        const suppliersOk = await refreshSuppliers(generation);
        if (!suppliersOk) return;
        updateRingIndicators();
        await loadList(1);
    } catch (error) {
        console.error('加载默认范围失败', error);
        if (!isCascadeCurrent(generation)) return;
        const ok = await loadCascade(generation);
        if (!ok) return;
        await refreshSuppliers(generation);
        updateRingIndicators();
        await loadList(1);
    } finally {
        if (isCascadeCurrent(generation)) setCascadeLocked(false);
    }
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
    syncPcrChipFace(id);
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select) return;
    const text = value == null ? '' : String(value);
    if (text && ![...select.options].some((opt) => opt.value === text)) {
        select.insertAdjacentHTML('beforeend', `<option value="${esc(text)}">${esc(text)}</option>`);
    }
    select.value = text;
    syncPcrChipFace(id);
}

async function loadCascade(generation) {
    const token = generation == null ? bumpCascadeGeneration() : generation;
    const locationAtRequest = val('pcrLocationFilter');
    const vehicleAtRequest = val('pcrVehicleModelFilter');
    try {
        const params = {};
        if (locationAtRequest) params.location = locationAtRequest;
        if (vehicleAtRequest) params.vehicle_model = vehicleAtRequest;
        const res = await HttpClient.get(CASCADE_API, { params });
        if (!isCascadeCurrent(token)) return false;
        if (val('pcrLocationFilter') !== locationAtRequest) return false;
        if (val('pcrVehicleModelFilter') !== vehicleAtRequest) return false;
        const data = res.data || {};
        fillSelect('pcrLocationFilter', data.locations || []);
        fillSelect('pcrVehicleModelFilter', data.vehicle_models || []);
        fillSelect('pcrBomVersionFilter', data.bom_versions || [], true, null, '全部版本');
        return true;
    } catch (error) {
        console.error('加载级联筛选失败', error);
        return isCascadeCurrent(token);
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
    if (!location || !vehicleModel) {
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
    const scope = {
        location,
        vehicle_model: vehicleModel,
        start_year: startYear,
        start_month: startMonth,
        end_year: endYear,
        end_month: endMonth,
        supplier_name: isAssemblyView() ? undefined : (val('pcrSupplierFilter') || undefined),
        view: listState.view,
    };
    if (bomVersion) scope.bom_version = bomVersion;
    return scope;
}

function queryParams(scope, page, { includeKeyword = true } = {}) {
    const params = { ...scope };
    if (includeKeyword && val('pcrPartFilter')) params.keyword = val('pcrPartFilter');
    if (page != null) {
        params.page = page;
        params.size = listState.pageSize;
    }
    return params;
}

async function refreshSuppliers(generation) {
    const token = generation == null ? cascadeGeneration : generation;
    if (isAssemblyView()) {
        if (!isCascadeCurrent(token)) return false;
        fillSelect('pcrSupplierFilter', [], true, null, '全部');
        return true;
    }
    const scope = readScope();
    const selected = val('pcrSupplierFilter');
    if (!scope) {
        if (!isCascadeCurrent(token)) return false;
        fillSelect('pcrSupplierFilter', [], true, null, '全部');
        return true;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/prep`, {
            params: queryParams(scope, null, { includeKeyword: false }),
            skipToast: true,
        });
        if (!isCascadeCurrent(token)) return false;
        const names = res.data?.supplier_names || [];
        fillSelect('pcrSupplierFilter', names, true, null, '全部');
        if (selected && names.includes(selected)) {
            setSelectValue('pcrSupplierFilter', selected);
        }
        return true;
    } catch (_error) {
        if (!isCascadeCurrent(token)) return false;
        fillSelect('pcrSupplierFilter', selected ? [selected] : [], true, null, '全部');
        if (selected) setSelectValue('pcrSupplierFilter', selected);
        return true;
    }
}

function setListLoading(isLoading) {
    listState.isLoading = isLoading;
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
        banner.textContent = `采购对象列表检测未通过${detail}`;
        banner.classList.remove('hidden');
        return;
    }
    banner.textContent = '';
    banner.classList.add('hidden');
}

function missingListMessage() {
    return '请先生成采购对象列表。<a href="#/bom-procurement-object" class="text-brand-hud hover:underline">去生成</a>';
}

async function loadList(page = 1) {
    const body = document.getElementById('pcrTableBody');
    if (!body) return;
    if (listState.isLoading) return;
    updateRingIndicators();
    if (!val('pcrLocationFilter') || !val('pcrVehicleModelFilter')) {
        listState.items = [];
        listState.months = [];
        body.innerHTML = '';
        renderPcrTableHead([], shouldShowSupplierColumn());
        updatePcrHud(null);
        setQaBanner(null);
        setListLoading(false);
        setListEmpty(true, '请选择基地、项目后查询');
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
        const showSupplier = shouldShowSupplierColumn();
        renderPcrTableHead(listState.months, showSupplier);
        body.innerHTML = renderPcrRows(listState.items, listState.months, showSupplier);
        updatePcrHud(filters);
        setQaBanner(filters);
        const emptyHint = filters.empty_hint
            ? (isAssemblyView()
                ? esc(filters.empty_hint)
                : `${esc(filters.empty_hint)} <a href="#/bom-procurement-object-list" class="text-brand-hud hover:underline">去采购对象列表</a>`)
            : '当前范围没有可展示的价目行';
        setListEmpty(listState.items.length === 0, emptyHint);
        const pageInfo = document.getElementById('pcrPageInfo');
        if (pageInfo) {
            pageInfo.textContent =
                `第 ${listState.page} / ${Math.max(listState.totalPages, 1)} 页 · ${listState.total} 条`;
        }
        paintPagination('pcrPagination', listState.page, listState.totalPages);
    } catch (error) {
        listState.items = [];
        body.innerHTML = '';
        updatePcrHud(null);
        setQaBanner(null);
        const message = String(error?.message || '');
        let emptyText;
        if (!isAssemblyView() && message.includes('采购对象列表')) {
            emptyText = missingListMessage();
        } else if (isAssemblyView() && message.includes('材料清单')) {
            emptyText = '未找到对应材料清单。<a href="#/bom-upload" class="text-brand-hud hover:underline">去上传材料清单</a>';
        } else {
            emptyText = esc(message || '查询失败');
        }
        setListEmpty(true, emptyText);
    } finally {
        setListLoading(false);
    }
}

async function resetFilters() {
    clearPartFilterTimer();
    setSelectValue('pcrLocationFilter', '');
    setSelectValue('pcrVehicleModelFilter', '');
    setSelectValue('pcrBomVersionFilter', '');
    setSelectValue('pcrSupplierFilter', '');
    const partEl = document.getElementById('pcrPartFilter');
    if (partEl) partEl.value = '';
    await openWithData();
}

async function exportExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    clearPartFilterTimer();
    const scope = readScope(true);
    if (!scope) return;
    if (scope.bom_version) {
        return showToast(EXPORT_ALL_VERSIONS_MESSAGE, 'warning');
    }
    if (!isAssemblyView() && !scope.supplier_name) {
        return showToast('请先选定供应商再导出协议', 'warning');
    }
    const btn = document.getElementById('pcrExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            `<div class="w-3 h-3 border border-brand-hud border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: queryParams(scope, null),
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
