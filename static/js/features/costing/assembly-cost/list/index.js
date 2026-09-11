import {
    assemblyCostListTemplate,
    renderLacPagination,
    renderLacRows,
    updateLacHud,
    updateLacFilterCapsules,
    updateLacTableHead,
} from './template.js?v=25';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';
import { setSearchBusy } from '../../../../search-busy.js?v=1';

const API_BASE = '/api/costing/assembly-costs';
const CASCADE_API = '/api/bom/filters/cascade';
const YEARS_API = `${API_BASE}/filters/years`;
const DRAWER_ANIMATION_MS = 300;

const FILTER_IDS = [
    'lacYearFilter',
    'lacMonthFilter',
    'lacLocationFilter',
    'lacVehicleModelFilter',
    'lacBomVersionFilter',
    'lacAuditFilter',
    'lacCalcFilter',
];

const listState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    items: [],
    canDelete: true,
    canApprove: true,
    canReverse: true,
    canExport: true,
    view: 'finance',
    advancedOpen: false,
    pendingFilters: null,
    batchAuditSubmitting: false,
    isLoading: false,
};

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

function init() {
    applyPermissionUi();
    bindEvents();
    syncViewButtons();
    bindPageSizeSelect('lacPageSize', {
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onChange: () => loadList(1),
    });
    fillMonthOptions();
    fillAuditOptions();
    fillCalcOptions();
    listState.pendingFilters = readHashFilters();
    if (listState.pendingFilters) setAdvancedOpen(true);
    updateLacFilterCapsules();
    loadYearOptions().then(async () => {
        await loadCascadeFilters();
        applyPendingFiltersToSelects();
        updateLacFilterCapsules();
        loadList(1);
    });
}

function destroy() {
    closeDetailDrawer();
}

function syncViewButtons() {
    const financeBtn = document.getElementById('lacViewFinanceBtn');
    const procurementBtn = document.getElementById('lacViewProcurementBtn');
    const active = 'bg-[#1A080A] border border-[#FF1E27]/50 text-[#FF1E27]';
    const idle = 'bg-transparent border border-[#2A2A35] text-[#6E6E73] hover:text-white';
    if (financeBtn) {
        financeBtn.className = `px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${listState.view === 'finance' ? active : idle}`;
    }
    if (procurementBtn) {
        procurementBtn.className = `px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${listState.view === 'procurement' ? active : idle}`;
    }
    const exportBtn = document.getElementById('lacExportBtn');
    const exportLabel = document.getElementById('lacExportBtnLabel');
    const bundleBtn = document.getElementById('lacExportBundleBtn');
    const isProcurement = listState.view === 'procurement';
    if (exportLabel) {
        exportLabel.textContent = isProcurement ? '导出零件成本' : '导出总成核价';
    }
    if (exportBtn) {
        exportBtn.title = isProcurement
            ? '导出零件成本（成本一览 + 材料明细 + 焊接费）'
            : '导出成品核价（一览 + 材料明细 + 焊接费 + 间接费用；金额为系统快照）';
    }
    if (bundleBtn && listState.canExport) {
        bundleBtn.classList.toggle('hidden', isProcurement);
    }
    updateLacTableHead(listState.view);
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    listState.canDelete = canFn('op:assembly-cost:delete') || canFn('op:l0-assembly-cost:delete');
    listState.canApprove = canFn('op:assembly-cost:approve') || canFn('op:l0-assembly-cost:approve');
    listState.canReverse = canFn('op:assembly-cost:reverse') || canFn('op:l0-assembly-cost:reverse');
    listState.canExport = canFn('op:assembly-cost:export') || canFn('op:l0-assembly-cost:export');
    if (!listState.canApprove) {
        document.getElementById('lacBatchApproveBtn')?.classList.add('hidden');
    }
    if (!listState.canReverse) {
        document.getElementById('lacBatchReverseBtn')?.classList.add('hidden');
    }
    if (!listState.canDelete) {
        document.getElementById('lacBatchDeleteBtn')?.classList.add('hidden');
    }
    if (!listState.canExport) {
        document.getElementById('lacExportBtn')?.classList.add('hidden');
        document.getElementById('lacExportBundleBtn')?.classList.add('hidden');
    }
}

function setAdvancedOpen(isOpen) {
    listState.advancedOpen = isOpen;
    document.getElementById('lacAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('lacAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function readHashFilters() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return null;
    const params = new URLSearchParams(hash.slice(qIndex + 1));
    const year = params.get('year') || '';
    const month = params.get('month') || '';
    const location = params.get('location') || '';
    const vehicle_model = params.get('vehicle_model') || '';
    const bom_version = params.get('bom_version') || '';
    if (!year && !month && !location && !vehicle_model && !bom_version) return null;
    return { year, month, location, vehicle_model, bom_version };
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select || value == null || value === '') return;
    const text = String(value);
    if (![...select.options].some((opt) => opt.value === text)) {
        select.insertAdjacentHTML(
            'beforeend',
            `<option value="${esc(text)}">${esc(text)}</option>`,
        );
    }
    select.value = text;
}

function applyPendingFiltersToSelects() {
    const pending = listState.pendingFilters;
    if (!pending) return;
    setSelectValue('lacYearFilter', pending.year);
    setSelectValue('lacMonthFilter', pending.month);
    setSelectValue('lacLocationFilter', pending.location);
    setSelectValue('lacVehicleModelFilter', pending.vehicle_model);
    setSelectValue('lacBomVersionFilter', pending.bom_version);
    listState.pendingFilters = null;
}

function setListLoading(isLoading) {
    listState.isLoading = isLoading;
    setSearchBusy('lacSearchBtn', isLoading);
    const loading = document.getElementById('lacLoading');
    const empty = document.getElementById('lacEmpty');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading && empty) empty.classList.add('hidden');
}

function setListEmpty(isEmpty) {
    const empty = document.getElementById('lacEmpty');
    if (empty) empty.classList.toggle('hidden', !isEmpty);
}

function bindEvents() {
    document.getElementById('lacViewFinanceBtn')?.addEventListener('click', () => {
        if (listState.view === 'finance') return;
        listState.view = 'finance';
        syncViewButtons();
        loadList(1);
    });
    document.getElementById('lacViewProcurementBtn')?.addEventListener('click', () => {
        if (listState.view === 'procurement') return;
        listState.view = 'procurement';
        syncViewButtons();
        loadList(1);
    });
    document.getElementById('lacSearchBtn')?.addEventListener('click', () => {
        updateLacFilterCapsules();
        loadList(1);
    });
    document.getElementById('lacToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!listState.advancedOpen);
    });
    document.getElementById('lacResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('lacPartNumberFilter')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            updateLacFilterCapsules();
            loadList(1);
        }
    });
    document.getElementById('lacPartNumberFilter')?.addEventListener('input', () => {
        updateLacFilterCapsules();
    });

    document.getElementById('lacYearFilter')?.addEventListener('change', () => {
        updateLacFilterCapsules();
        loadList(1);
    });
    document.getElementById('lacMonthFilter')?.addEventListener('change', () => {
        updateLacFilterCapsules();
        loadList(1);
    });
    document.getElementById('lacLocationFilter')?.addEventListener('change', () => {
        setSelectValue('lacVehicleModelFilter', '');
        setSelectValue('lacBomVersionFilter', '');
        updateLacFilterCapsules();
        loadCascadeFilters().then(() => {
            updateLacFilterCapsules();
            loadList(1);
        });
    });
    document.getElementById('lacVehicleModelFilter')?.addEventListener('change', () => {
        setSelectValue('lacBomVersionFilter', '');
        updateLacFilterCapsules();
        loadCascadeFilters().then(() => {
            updateLacFilterCapsules();
            loadList(1);
        });
    });
    document.getElementById('lacBomVersionFilter')?.addEventListener('change', () => {
        updateLacFilterCapsules();
        loadList(1);
    });
    document.getElementById('lacAuditFilter')?.addEventListener('change', () => {
        updateLacFilterCapsules();
        loadList(1);
    });
    document.getElementById('lacCalcFilter')?.addEventListener('change', () => {
        updateLacFilterCapsules();
        loadList(1);
    });

    document.getElementById('lacBatchApproveBtn')?.addEventListener('click', () => openBatchAuditDrawer('approve'));
    document.getElementById('lacBatchReverseBtn')?.addEventListener('click', () => openBatchAuditDrawer('reverse'));
    document.getElementById('lacBatchDeleteBtn')?.addEventListener('click', () => batchDelete());
    bindBatchAuditDrawerEvents();
    document.getElementById('lacExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('lacExportBundleBtn')?.addEventListener('click', () => exportBundleExcel());

    document.getElementById('lacPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.lac-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadList(page);
        }
    });

    document.getElementById('lacTableBody')?.addEventListener('click', (event) => {
        const restoreBtn = event.target.closest('.btn-open-restore');
        if (restoreBtn) {
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
            const location = restoreBtn.dataset.location;
            const vehicleModel = restoreBtn.dataset.vehicleModel;
            const bomVersion = restoreBtn.dataset.bomVersion;
            if (location) query.set('location', location);
            if (vehicleModel) query.set('vehicle_model', vehicleModel);
            if (bomVersion) query.set('bom_version', bomVersion);
            const opened = window.open(
                `/assembly-cost-restore?${query.toString()}`,
                '_blank',
                'noopener,noreferrer',
            );
            if (opened) opened.opener = null;
            return;
        }
        const detailBtn = event.target.closest('.btn-open-detail');
        if (detailBtn) {
            openDetail(Number(detailBtn.dataset.id));
        }
    });
}

function fillMonthOptions() {
    const select = document.getElementById('lacMonthFilter');
    if (!select) return;
    select.innerHTML =
        `<option value="">全部</option>` +
        Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${esc(fmtMonth(i + 1))}</option>`).join('');
}

function fillAuditOptions() {
    const select = document.getElementById('lacAuditFilter');
    if (!select) return;
    select.innerHTML = `
        <option value="">全部</option>
        <option value="pending">待审</option>
        <option value="approved">已通过</option>
    `;
}

function fillCalcOptions() {
    const select = document.getElementById('lacCalcFilter');
    if (!select) return;
    select.innerHTML = `
        <option value="">全部</option>
        <option value="ok">ok</option>
        <option value="partial">partial</option>
    `;
}

function fillSelect(id, values = [], preferredValue = null, formatLabel = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        `<option value="">全部</option>` +
        values
            .map((value) => {
                const text = String(value);
                const label = formatLabel ? formatLabel(value) : text;
                return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(String(label))}</option>`;
            })
            .join('');
    if (preferredValue != null) select.value = String(preferredValue);
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(YEARS_API);
        fillSelect(
            'lacYearFilter',
            Array.isArray(res.data) ? res.data : [],
            listState.pendingFilters?.year || null,
            fmtYear,
        );
    } catch (error) {
        console.error(error);
    }
}

async function loadCascadeFilters() {
    try {
        const pending = listState.pendingFilters;
        const params = {
            location:
                document.getElementById('lacLocationFilter')?.value
                || pending?.location
                || '',
            vehicle_model:
                document.getElementById('lacVehicleModelFilter')?.value
                || pending?.vehicle_model
                || '',
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect(
            'lacLocationFilter',
            filters.locations || [],
            pending?.location || null,
        );
        fillSelect(
            'lacVehicleModelFilter',
            filters.vehicle_models || [],
            pending?.vehicle_model || null,
        );
        fillSelect(
            'lacBomVersionFilter',
            filters.bom_versions || [],
            pending?.bom_version || null,
        );
    } catch (error) {
        console.error(error);
    }
}

function resetFilters() {
    FILTER_IDS.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const partEl = document.getElementById('lacPartNumberFilter');
    if (partEl) partEl.value = '';
    updateLacFilterCapsules();
    loadCascadeFilters().then(() => {
        updateLacFilterCapsules();
        loadList(1);
    });
}

function getFilters() {
    const pending = listState.pendingFilters;
    const yearRaw = document.getElementById('lacYearFilter')?.value || pending?.year || '';
    const monthRaw = document.getElementById('lacMonthFilter')?.value || pending?.month || '';
    return {
        year: yearRaw ? Number(yearRaw) : undefined,
        month: monthRaw ? Number(monthRaw) : undefined,
        location:
            document.getElementById('lacLocationFilter')?.value
            || pending?.location
            || undefined,
        vehicle_model:
            document.getElementById('lacVehicleModelFilter')?.value
            || pending?.vehicle_model
            || undefined,
        bom_version:
            document.getElementById('lacBomVersionFilter')?.value
            || pending?.bom_version
            || undefined,
        audit_status: document.getElementById('lacAuditFilter')?.value || undefined,
        calc_status: document.getElementById('lacCalcFilter')?.value || undefined,
        part_number: document.getElementById('lacPartNumberFilter')?.value?.trim() || undefined,
        view: listState.view,
    };
}

function requireScope(actionLabel = '批量操作') {
    const f = getFilters();
    if (!f.year || !f.month || !f.location || !f.vehicle_model || !f.bom_version) {
        showToast(`${actionLabel}须选定年度、月份、基地、项目、版本`, 'warning');
        setAdvancedOpen(true);
        return null;
    }
    return {
        year: f.year,
        month: f.month,
        location: f.location,
        vehicle_model: f.vehicle_model,
        bom_version: f.bom_version,
        view: listState.view,
    };
}

async function loadList(page = 1) {
    const body = document.getElementById('lacTableBody');
    if (!body) return;
    if (listState.isLoading) return;
    setListLoading(true);
    body.innerHTML = '';
    updateLacFilterCapsules();
    try {
        const filters = getFilters();
        const res = await HttpClient.get(API_BASE, {
            params: {
                ...filters,
                page,
                size: listState.pageSize,
            },
        });
        const pageData = res.data || {};
        listState.page = pageData.page || page;
        listState.total = pageData.total || 0;
        listState.totalPages = pageData.total_pages || 1;
        listState.items = Array.isArray(pageData.items) ? pageData.items : [];
        body.innerHTML = renderLacRows(listState.items, listState.view);
        updateLacTableHead(listState.view);
        setListEmpty(listState.items.length === 0);
        updateLacHud(listState.total, pageData.filters?.summary || null);
        const pageInfo = document.getElementById('lacPageInfo');
        if (pageInfo) {
            pageInfo.textContent =
                `第 ${listState.page} / ${Math.max(listState.totalPages, 1)} 页 · ${listState.total} 条`;
        }
        const pagination = document.getElementById('lacPagination');
        if (pagination) {
            pagination.innerHTML = renderLacPagination(listState.page, listState.totalPages);
        }
    } catch (error) {
        body.innerHTML = '';
        setListEmpty(true);
    } finally {
        setListLoading(false);
    }
}

function bindBatchAuditDrawerEvents() {
    document.getElementById('closeLacBatchAuditDrawer')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('cancelLacBatchAuditBtn')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('lacBatchAuditDrawerBackdrop')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('confirmLacBatchAuditBtn')?.addEventListener('click', () => submitBatchAudit());
}

function getSessionDisplayName() {
    try {
        const raw = localStorage.getItem('brabus_user');
        if (!raw) return '';
        const session = JSON.parse(raw);
        return (session.real_name || session.name || session.username || '').trim();
    } catch (_) {
        return '';
    }
}

function openBatchAuditDrawer(mode) {
    const isApprove = mode === 'approve';
    if (isApprove && !listState.canApprove) return showToast('无审核权限', 'warning');
    if (!isApprove && !listState.canReverse) return showToast('无反审核权限', 'warning');
    const scope = requireScope(isApprove ? '批量审核' : '批量反审核');
    if (!scope) return;

    const modeEl = document.getElementById('lacBatchAuditMode');
    const titleEl = document.getElementById('lacBatchAuditDrawerTitle');
    const hintEl = document.getElementById('lacBatchAuditHint');
    const operatorLabel = document.getElementById('lacBatchAuditOperatorLabel');
    const remarkLabel = document.getElementById('lacBatchAuditRemarkLabel');
    const operatorDisplay = document.getElementById('lacBatchAuditOperatorDisplay');
    const remarkEl = document.getElementById('lacBatchAuditRemark');
    const summaryEl = document.getElementById('lacBatchAuditFilterSummary');
    const confirmBtn = document.getElementById('confirmLacBatchAuditBtn');

    if (modeEl) modeEl.value = isApprove ? 'approve' : 'reverse';
    if (titleEl) titleEl.textContent = isApprove ? '批量审核' : '批量反审核';
    if (hintEl) {
        hintEl.textContent = isApprove
            ? '仅按年度、月份、基地、项目、版本处理待审记录；已通过记录会跳过。'
            : '仅按年度、月份、基地、项目、版本处理已通过记录；其余状态会跳过。反审核意见必填。';
    }
    if (operatorLabel) operatorLabel.textContent = isApprove ? '审核人' : '反审核人';
    if (operatorDisplay) {
        operatorDisplay.textContent = getSessionDisplayName() || '（当前登录用户）';
    }
    if (remarkLabel) {
        remarkLabel.innerHTML = isApprove
            ? '审核意见<span class="text-[#d32f2f]">*</span>'
            : '反审核意见<span class="text-[#d32f2f]">*</span>';
    }
    if (remarkEl) {
        remarkEl.value = '';
        remarkEl.placeholder = isApprove ? '请填写审核意见（必填）' : '请填写反审核原因（必填）';
    }
    if (summaryEl) {
        summaryEl.textContent =
            `${fmtPeriod(scope.year, scope.month)} · 基地 ${scope.location} · 项目 ${scope.vehicle_model} · 版本 ${scope.bom_version}`;
    }
    if (confirmBtn) {
        confirmBtn.textContent = isApprove ? '确认审核通过' : '确认反审核';
        confirmBtn.className =
            'inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all';
    }

    openDrawer('lacBatchAuditDrawer', 'lacBatchAuditDrawerBackdrop');
}

function closeBatchAuditDrawer() {
    if (listState.batchAuditSubmitting) return;
    closeDrawer('lacBatchAuditDrawer', 'lacBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (listState.batchAuditSubmitting) return;
    const mode = document.getElementById('lacBatchAuditMode')?.value || 'approve';
    const isApprove = mode === 'approve';
    const scope = requireScope(isApprove ? '批量审核' : '批量反审核');
    if (!scope) return;

    const remark = document.getElementById('lacBatchAuditRemark')?.value.trim() || '';
    if (!remark) {
        showToast(isApprove ? '审核意见必填' : '反审核意见必填', 'warning');
        return;
    }

    const confirmBtn = document.getElementById('confirmLacBatchAuditBtn');
    const originalText = confirmBtn ? confirmBtn.textContent : '';
    listState.batchAuditSubmitting = true;
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = '提交中…';
    }

    try {
        const body = { ...scope };
        let response;
        if (isApprove) {
            body.audit_remark = remark;
            response = await HttpClient.post(`${API_BASE}/batch-approve`, body);
        } else {
            body.reverse_audit_remark = remark;
            response = await HttpClient.post(`${API_BASE}/batch-reverse`, body);
        }
        const result = response.data || {};
        const updated = result.updated_count ?? result.affected_count ?? 0;
        const skipped = result.skipped_count ?? 0;
        showToast(
            response.message ||
                `${isApprove ? '已审核通过' : '已反审核'} ${updated} 条` +
                    (skipped ? `，跳过 ${skipped} 条` : ''),
            updated > 0 ? 'success' : 'warning',
        );
        listState.batchAuditSubmitting = false;
        closeBatchAuditDrawer();
        loadList(listState.page);
    } catch (error) {
        /* HttpClient 已 toast */
    } finally {
        listState.batchAuditSubmitting = false;
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = originalText;
        }
    }
}

async function batchDelete() {
    if (!listState.canDelete) return showToast('无删除权限', 'warning');
    const scope = requireScope();
    if (!scope) return;
    if (!window.confirm('确认删除当前范围未审核记录？已审核将跳过。')) return;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        showToast(res.message || '删除完成', 'success');
        loadList(1);
    } catch (error) {
        /* HttpClient 已 toast */
    }
}

async function exportExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const filters = getFilters();
    if (listState.view === 'procurement') {
        const scope = requireScope('导出零件成本');
        if (!scope) return;
    } else if (!filters.year && !filters.month && !filters.location
        && !filters.vehicle_model && !filters.bom_version
        && !filters.part_number && !filters.audit_status && !filters.calc_status) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        return;
    }
    const btn = document.getElementById('lacExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params: {
                year: filters.year || undefined,
                month: filters.month || undefined,
                location: filters.location || undefined,
                vehicle_model: filters.vehicle_model || undefined,
                bom_version: filters.bom_version || undefined,
                part_number: filters.part_number || undefined,
                audit_status: filters.audit_status || undefined,
                calc_status: filters.calc_status || undefined,
                view: listState.view,
            },
            defaultFilename: listState.view === 'procurement' ? '零件成本.xlsx' : '成品核价.xlsx',
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
        if (!error.status) {
            showToast(error.message || '导出失败', 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function exportBundleExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const scope = requireScope('导出核对合册');
    if (!scope) return;
    const btn = document.getElementById('lacExportBundleBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>合册导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(
            '/api/costing/monthly-bundle/export-download',
            {
                params: {
                    year: scope.year,
                    month: scope.month,
                    location: scope.location,
                    vehicle_model: scope.vehicle_model,
                    bom_version: scope.bom_version,
                },
                defaultFilename: '核对合册.xlsx',
                timeout: 300000,
            },
        );
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
        showToast(`核对合册已导出: ${filename}`, 'success');
    } catch (error) {
        if (!error.status) {
            showToast(error.message || '核对合册导出失败', 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function openDetail(costId) {
    try {
        const res = await HttpClient.get(`${API_BASE}/${costId}`);
        const row = res.data;
        if (!row) return;
        closeDetailDrawer();
        const overlay = document.createElement('div');
        overlay.id = 'lacDetailOverlay';
        overlay.className = 'fixed inset-0 z-[80] bg-black/60';
        overlay.addEventListener('click', closeDetailDrawer);
        const panel = document.createElement('div');
        panel.id = 'lacDetailPanel';
        panel.className =
            'fixed top-0 right-0 h-full w-full max-w-xl z-[85] bg-[#0A0A0C] border-l border-[#1A1A22] overflow-y-auto';
        panel.innerHTML = renderDetailHtml(row);
        panel.querySelector('[data-action="close-detail"]')
            ?.addEventListener('click', closeDetailDrawer);
        document.body.appendChild(overlay);
        document.body.appendChild(panel);
    } catch (error) {
        /* toast */
    }
}

function renderDetailHtml(row) {
    const items = Array.isArray(row.items) ? row.items : [];
    const indirects = Array.isArray(row.indirects) ? row.indirects : [];
    return `
        <div class="p-4 border-b border-[#14141A] flex items-center justify-between sticky top-0 bg-[#0A0A0C] z-10">
            <div>
                <div class="text-sm font-bold text-[#F0F0F2] font-mono">${esc(row.part_number)}</div>
                <div class="text-[10px] text-[#555555]">${esc(row.part_name || '')}</div>
            </div>
            <button data-action="close-detail" class="text-[#6E6E73] hover:text-white text-xs">关闭</button>
        </div>
        <div class="p-4 space-y-4 text-[11px]">
            <div class="grid grid-cols-2 gap-2 font-mono">
                <div class="text-[#555555]">月总账 <span class="text-[#C8C8D0]">${esc(fmtNum(row.total_amount, 4))}</span></div>
                <div class="text-[#555555]">间接 <span class="text-[#C8C8D0]">${esc(fmtNum(row.indirect_amount, 4))}</span></div>
                <div class="col-span-2 text-[#555555]">总费用 <span class="text-[#FF1E27] font-bold">${esc(fmtNum(row.grand_total, 4))}</span></div>
            </div>
            <div>
                <div class="text-[10px] text-[#555555] mb-1 tracking-wider">材料明细</div>
                <div class="border border-[#1E1E26] divide-y divide-[#141418]">
                    ${items.map((it) => `
                        <div class="px-2 py-1.5 flex justify-between gap-2">
                            <div class="min-w-0">
                                <div class="font-mono text-[#F0F0F2] truncate">${esc(it.part_number)}</div>
                                <div class="text-[9px] text-[#555555]">${esc(it.level_label)} · ${esc(it.cost_source)}${it.match_hint ? ` · ${esc(it.match_hint)}` : ''}</div>
                            </div>
                            <div class="text-right font-mono text-[#8E8E93] shrink-0">${esc(fmtNum(it.line_amount, 4))}</div>
                        </div>
                    `).join('') || '<div class="px-2 py-3 text-[#555555]">无明细</div>'}
                </div>
            </div>
            <div>
                <div class="text-[10px] text-[#555555] mb-1 tracking-wider">间接费用</div>
                <div class="border border-[#1E1E26] divide-y divide-[#141418]">
                    ${indirects.map((ind) => `
                        <div class="px-2 py-1.5 flex justify-between gap-2">
                            <div class="text-[#C8C8D0]">${esc(ind.label)}</div>
                            <div class="font-mono text-[#8E8E93]">${esc(fmtNum(ind.amount, 4))}</div>
                        </div>
                    `).join('') || '<div class="px-2 py-3 text-[#555555]">无间接项</div>'}
                </div>
            </div>
        </div>
    `;
}

function closeDetailDrawer() {
    document.getElementById('lacDetailOverlay')?.remove();
    document.getElementById('lacDetailPanel')?.remove();
}

export const pageConfig = {
    render: assemblyCostListTemplate,
    init,
    destroy,
};
