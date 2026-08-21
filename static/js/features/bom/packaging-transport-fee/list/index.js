/**
 * 包装运输费列表：HUD + 批量审核/反审核/删除（范围=基地+年度+项目）
 */

import {
    pkgTransportFeeTemplate,
    renderTableRows,
    renderPagination,
    feeInputValue,
    parseFeeInput,
    updatePkgHud,
    updatePkgFilterCapsules,
    renderDetailBody,
} from './template.js?v=2';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const pkgState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    selectedLocation: null,
    selectedYear: null,
    selectedVehicleModel: null,
    selectedAuditStatus: null,
    selectedKeyword: null,
    locations: [],
    years: [],
    vehicleModels: [],
    isLoading: false,
    isBatchDeleting: false,
    batchAuditSubmitting: false,
    advancedOpen: false,
};

const API_BASE = '/api/bom/packaging-transport-fee';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '批量操作须同时选择基地、年度和项目';

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
    loadFilterOptions().then(() => loadData());
    bindEvents();
    bindPageSizeSelect('pkgTransportFeePageSize', {
        getSize: () => pkgState.pageSize,
        setSize: (size) => {
            pkgState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
    updatePkgFilterCapsules(pkgState);
}

function applyPermissionUi() {
    const canExport = typeof can === 'function' ? can('op:bom-packaging-transport-fee:export') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-packaging-transport-fee:delete') : true;
    const canApprove = typeof can === 'function' ? can('op:bom-packaging-transport-fee:approve') : true;
    const canReverse = typeof can === 'function' ? can('op:bom-packaging-transport-fee:reverse') : true;
    if (!canExport) document.getElementById('btnExportPkg')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnBatchDeletePkg')?.classList.add('hidden');
    if (!canApprove) document.getElementById('btnBatchApprovePkg')?.classList.add('hidden');
    if (!canReverse) document.getElementById('btnBatchReversePkg')?.classList.add('hidden');
}

function setAdvancedOpen(open) {
    pkgState.advancedOpen = open;
    document.getElementById('pkgAdvancedFilterPanel')?.classList.toggle('hidden', !open);
    const label = document.getElementById('pkgAdvancedFilterLabel');
    if (label) label.textContent = open ? '收起高级筛选' : '展开高级筛选';
}

async function loadFilterOptions() {
    try {
        const [locRes, yearRes, vehicleRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/filters/locations`),
            HttpClient.get(`${API_BASE}/filters/years`),
            HttpClient.get(`${API_BASE}/filters/vehicle-models`),
        ]);
        pkgState.locations = Array.isArray(locRes.data) ? locRes.data : [];
        pkgState.years = Array.isArray(yearRes.data) ? yearRes.data : [];
        pkgState.vehicleModels = Array.isArray(vehicleRes.data) ? vehicleRes.data : [];

        const locationFilter = document.getElementById('pkgLocationFilter');
        if (locationFilter) {
            const known = ['大连', '芜湖', '鄂尔多斯', '青岛'];
            const merged = [...new Set([...known, ...pkgState.locations])];
            locationFilter.innerHTML = `<option value="">全部</option>${merged.map((loc) => `<option value="${esc(loc)}">${esc(loc)}</option>`).join('')}`;
            if (pkgState.selectedLocation) locationFilter.value = pkgState.selectedLocation;
        }

        const yearFilter = document.getElementById('pkgYearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = '<option value="">全部</option>';
            pkgState.years.forEach((year) => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            if (!pkgState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
            if (pkgState.selectedYear) yearFilter.value = pkgState.selectedYear;
        }

        const vehicleFilter = document.getElementById('pkgVehicleFilter');
        if (vehicleFilter) {
            vehicleFilter.innerHTML = `<option value="">全部</option>${pkgState.vehicleModels.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join('')}`;
            if (pkgState.selectedVehicleModel) vehicleFilter.value = pkgState.selectedVehicleModel;
        }

        const auditFilter = document.getElementById('pkgAuditStatusFilter');
        if (auditFilter) {
            auditFilter.innerHTML = `
                <option value="">全部</option>
                <option value="pending">待审</option>
                <option value="approved">已通过</option>`;
            if (pkgState.selectedAuditStatus) auditFilter.value = pkgState.selectedAuditStatus;
        }
    } catch (error) {
        console.error('加载筛选项失败:', error);
    }
}

function readFiltersFromDom() {
    pkgState.selectedLocation = document.getElementById('pkgLocationFilter')?.value || null;
    pkgState.selectedYear = document.getElementById('pkgYearFilter')?.value || null;
    pkgState.selectedVehicleModel = document.getElementById('pkgVehicleFilter')?.value || null;
    pkgState.selectedAuditStatus = document.getElementById('pkgAuditStatusFilter')?.value || null;
    pkgState.selectedKeyword = document.getElementById('pkgKeywordFilter')?.value?.trim() || null;
    updatePkgFilterCapsules(pkgState);
}

function collectScopeFilters() {
    return {
        location: (document.getElementById('pkgLocationFilter')?.value || '').trim(),
        year: (document.getElementById('pkgYearFilter')?.value || '').trim(),
        vehicle_model: (document.getElementById('pkgVehicleFilter')?.value || '').trim(),
    };
}

function hasFullScope(filters) {
    return !!(filters.location && filters.year && filters.vehicle_model);
}

async function loadData(page = 1) {
    if (pkgState.isLoading) return;
    pkgState.isLoading = true;

    const tableBody = document.getElementById('pkgTransportFeeTableBody');
    const emptyState = document.getElementById('pkgEmptyState');
    const loadingState = document.getElementById('pkgLoadingState');
    if (tableBody) tableBody.innerHTML = '';
    emptyState?.classList.add('hidden');
    loadingState?.classList.remove('hidden');

    try {
        const params = { page, size: pkgState.pageSize };
        if (pkgState.selectedLocation) params.location = pkgState.selectedLocation;
        if (pkgState.selectedYear) params.year = pkgState.selectedYear;
        if (pkgState.selectedVehicleModel) params.vehicle_model = pkgState.selectedVehicleModel;
        if (pkgState.selectedAuditStatus) params.audit_status = pkgState.selectedAuditStatus;
        if (pkgState.selectedKeyword) params.keyword = pkgState.selectedKeyword;

        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};
        pkgState.records = pageResult.items || [];
        pkgState.total = pageResult.total || 0;
        pkgState.page = pageResult.page || page;
        pkgState.totalPages = pageResult.total_pages || 1;

        updatePkgHud((pageResult.filters || {}).summary || {});

        if (tableBody) {
            if (pkgState.records.length === 0) {
                emptyState?.classList.remove('hidden');
            } else {
                emptyState?.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(pkgState.records);
            }
        }

        const totalCountPagination = document.getElementById('pkgTotalCountPagination');
        if (totalCountPagination) totalCountPagination.textContent = `共 ${pkgState.total} 条`;
        const paginationBtns = document.getElementById('pkgPaginationBtns');
        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(pkgState.page, pkgState.totalPages);
        }

        // refresh vehicle options from filters if present
        const filters = pageResult.filters || {};
        if (Array.isArray(filters.vehicle_models) && filters.vehicle_models.length) {
            pkgState.vehicleModels = filters.vehicle_models;
            const vehicleFilter = document.getElementById('pkgVehicleFilter');
            if (vehicleFilter) {
                const current = vehicleFilter.value;
                vehicleFilter.innerHTML = `<option value="">全部</option>${pkgState.vehicleModels.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join('')}`;
                vehicleFilter.value = current;
            }
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="15" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">加载数据失败，请重试</td></tr>`;
        }
    } finally {
        pkgState.isLoading = false;
        loadingState?.classList.add('hidden');
    }
}

function bindEvents() {
    document.getElementById('pkgToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!pkgState.advancedOpen);
    });
    document.getElementById('btnFilterPkg')?.addEventListener('click', () => {
        readFiltersFromDom();
        loadData(1);
    });
    document.getElementById('pkgResetFilterBtn')?.addEventListener('click', () => {
        ['pkgLocationFilter', 'pkgYearFilter', 'pkgVehicleFilter', 'pkgAuditStatusFilter', 'pkgKeywordFilter'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        readFiltersFromDom();
        loadData(1);
    });

    document.getElementById('pkgPaginationBtns')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.pkg-page-btn');
        if (!btn) return;
        const page = Number(btn.dataset.page);
        if (page) loadData(page);
    });

    document.getElementById('pkgTransportFeeTableBody')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        const id = Number(btn.dataset.id);
        const record = pkgState.records.find((r) => r.id === id);
        if (!record) return;
        if (btn.dataset.action === 'detail') openDetail(record);
        if (btn.dataset.action === 'edit') openEdit(record);
        if (btn.dataset.action === 'delete') openDelete(record);
    });

    document.getElementById('btnExportPkg')?.addEventListener('click', exportExcel);
    document.getElementById('btnBatchDeletePkg')?.addEventListener('click', batchDelete);
    document.getElementById('btnBatchApprovePkg')?.addEventListener('click', () => openBatchAudit('approve'));
    document.getElementById('btnBatchReversePkg')?.addEventListener('click', () => openBatchAudit('reverse'));

    document.getElementById('closePkgBatchAuditDrawer')?.addEventListener('click', () => closeDrawer('pkgBatchAuditDrawer', 'pkgBatchAuditDrawerBackdrop'));
    document.getElementById('cancelPkgBatchAuditBtn')?.addEventListener('click', () => closeDrawer('pkgBatchAuditDrawer', 'pkgBatchAuditDrawerBackdrop'));
    document.getElementById('confirmPkgBatchAuditBtn')?.addEventListener('click', submitBatchAudit);
    document.getElementById('pkgBatchAuditDrawerBackdrop')?.addEventListener('click', () => closeDrawer('pkgBatchAuditDrawer', 'pkgBatchAuditDrawerBackdrop'));

    document.getElementById('closePkgDetailDrawer')?.addEventListener('click', () => closeDrawer('pkgDetailDrawer', 'pkgDetailDrawerBackdrop'));
    document.getElementById('pkgDetailDrawerBackdrop')?.addEventListener('click', () => closeDrawer('pkgDetailDrawer', 'pkgDetailDrawerBackdrop'));

    document.getElementById('closePkgEditDrawer')?.addEventListener('click', () => closeDrawer('pkgEditDrawer', 'pkgEditDrawerBackdrop'));
    document.getElementById('cancelPkgEditBtn')?.addEventListener('click', () => closeDrawer('pkgEditDrawer', 'pkgEditDrawerBackdrop'));
    document.getElementById('confirmPkgEditBtn')?.addEventListener('click', submitEdit);
    document.getElementById('pkgEditDrawerBackdrop')?.addEventListener('click', () => closeDrawer('pkgEditDrawer', 'pkgEditDrawerBackdrop'));

    document.getElementById('closePkgDeleteDrawer')?.addEventListener('click', () => closeDrawer('pkgDeleteDrawer', 'pkgDeleteDrawerBackdrop'));
    document.getElementById('cancelPkgDeleteBtn')?.addEventListener('click', () => closeDrawer('pkgDeleteDrawer', 'pkgDeleteDrawerBackdrop'));
    document.getElementById('confirmPkgDeleteBtn')?.addEventListener('click', submitDelete);
    document.getElementById('pkgDeleteDrawerBackdrop')?.addEventListener('click', () => closeDrawer('pkgDeleteDrawer', 'pkgDeleteDrawerBackdrop'));
}

function openDetail(record) {
    const body = document.getElementById('pkgDetailDrawerBody');
    if (body) body.innerHTML = renderDetailBody(record);
    openDrawer('pkgDetailDrawer', 'pkgDetailDrawerBackdrop');
}

function openEdit(record) {
    if (record.audit_status === 'approved') {
        showToast('已审核通过，请先反审核后再修改', 'warning');
        return;
    }
    document.getElementById('pkgEditId').value = String(record.id);
    document.getElementById('pkgEditScopeHint').textContent =
        `${record.location} · ${record.year} · ${record.vehicle_model} · ${record.part_number}`;
    document.getElementById('pkgEditPartName').value = record.part_name || '';
    document.getElementById('pkgEditPackagingType').value = record.packaging_type || '';
    document.getElementById('pkgEditPackagingFee').value = feeInputValue(record.unit_packaging_fee);
    document.getElementById('pkgEditTransportFee').value = feeInputValue(record.unit_transport_fee);
    document.getElementById('pkgEditMaintFee').value = feeInputValue(record.fixture_maint_fee);
    document.getElementById('pkgEditOtherFee').value = feeInputValue(record.other_fee);
    document.getElementById('pkgEditTotal').value = feeInputValue(record.packaging_transport_total);
    document.getElementById('pkgEditRemark').value = record.remark || '';
    openDrawer('pkgEditDrawer', 'pkgEditDrawerBackdrop');
}

function openDelete(record) {
    if (record.audit_status === 'approved') {
        showToast('已审核通过，请先反审核后再删除', 'warning');
        return;
    }
    document.getElementById('pkgDeleteId').value = String(record.id);
    document.getElementById('pkgDeleteHint').textContent =
        `确定删除「${record.part_number}」的包装运输费吗？此操作不可恢复。`;
    openDrawer('pkgDeleteDrawer', 'pkgDeleteDrawerBackdrop');
}

async function submitEdit() {
    const id = document.getElementById('pkgEditId')?.value;
    const packagingFee = parseFeeInput(document.getElementById('pkgEditPackagingFee')?.value);
    const transportFee = parseFeeInput(document.getElementById('pkgEditTransportFee')?.value);
    const maintFee = parseFeeInput(document.getElementById('pkgEditMaintFee')?.value);
    const otherFee = parseFeeInput(document.getElementById('pkgEditOtherFee')?.value);
    const total = parseFeeInput(document.getElementById('pkgEditTotal')?.value);
    if (packagingFee == null || transportFee == null || maintFee == null || otherFee == null || total == null) {
        showToast('请填写有效费用（≥0，最多4位小数）', 'warning');
        return;
    }
    try {
        await HttpClient.put(`${API_BASE}/${id}`, {
            part_name: document.getElementById('pkgEditPartName')?.value?.trim() || null,
            packaging_type: document.getElementById('pkgEditPackagingType')?.value?.trim() || null,
            unit_packaging_fee: packagingFee,
            unit_transport_fee: transportFee,
            fixture_maint_fee: maintFee,
            other_fee: otherFee,
            packaging_transport_total: total,
            remark: document.getElementById('pkgEditRemark')?.value?.trim() || null,
        });
        showToast('更新成功', 'success');
        closeDrawer('pkgEditDrawer', 'pkgEditDrawerBackdrop');
        loadData(pkgState.page);
    } catch (err) {
        showToast(err.message || '更新失败', 'error');
    }
}

async function submitDelete() {
    const id = document.getElementById('pkgDeleteId')?.value;
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('pkgDeleteDrawer', 'pkgDeleteDrawerBackdrop');
        loadData(pkgState.page);
    } catch (err) {
        showToast(err.message || '删除失败', 'error');
    }
}

async function exportExcel() {
    try {
        const params = {};
        if (pkgState.selectedLocation) params.location = pkgState.selectedLocation;
        if (pkgState.selectedYear) params.year = pkgState.selectedYear;
        if (pkgState.selectedVehicleModel) params.vehicle_model = pkgState.selectedVehicleModel;
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '包装运输费导出.xlsx',
        });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
        showToast('导出成功', 'success');
    } catch (err) {
        if (!err.status) showToast(err.message || '导出失败', 'error');
    }
}

async function batchDelete() {
    if (typeof can === 'function' && !can('op:bom-packaging-transport-fee:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const filters = collectScopeFilters();
    if (!hasFullScope(filters)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        setAdvancedOpen(true);
        return;
    }
    const year = Number(filters.year);
    const ok = window.confirm(
        `确定批量删除未审核包装运输费吗？\n\n基地: ${filters.location} | 年度: ${year} | 项目: ${filters.vehicle_model}\n\n仅删除待审记录；已审核通过会跳过。此操作不可恢复！`,
    );
    if (!ok) return;
    if (pkgState.isBatchDeleting) return;
    pkgState.isBatchDeleting = true;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, {
            location: filters.location,
            year,
            vehicle_model: filters.vehicle_model,
        });
        showToast(res.message || '批量删除完成', 'success');
        await loadFilterOptions();
        loadData(1);
    } catch (err) {
        showToast(err.message || '批量删除失败', 'error');
    } finally {
        pkgState.isBatchDeleting = false;
    }
}

function openBatchAudit(mode) {
    const filters = collectScopeFilters();
    if (!hasFullScope(filters)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        setAdvancedOpen(true);
        return;
    }
    document.getElementById('pkgBatchAuditMode').value = mode;
    document.getElementById('pkgBatchAuditDrawerTitle').textContent =
        mode === 'approve' ? '批量审核' : '批量反审核';
    document.getElementById('pkgBatchAuditFilterSummary').textContent =
        `基地：${filters.location} ｜ 年度：${filters.year} ｜ 项目：${filters.vehicle_model}`;
    document.getElementById('pkgBatchAuditHint').textContent =
        mode === 'approve'
            ? '将范围内待审记录批量审核通过。'
            : '将范围内已审核记录批量反审核为待审。';
    document.getElementById('pkgBatchAuditRemarkLabel').textContent =
        mode === 'approve' ? '审核意见' : '反审核原因 *';
    document.getElementById('pkgBatchAuditRemark').value = '';
    document.getElementById('pkgBatchAuditRemark').placeholder =
        mode === 'approve' ? '可选填写审核意见' : '必填反审核原因';

    const session = typeof getUserSession === 'function' ? getUserSession() : null;
    const operator = session?.display_name || session?.username || '—';
    document.getElementById('pkgBatchAuditOperatorDisplay').textContent = operator;

    openDrawer('pkgBatchAuditDrawer', 'pkgBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (pkgState.batchAuditSubmitting) return;
    const mode = document.getElementById('pkgBatchAuditMode')?.value;
    const filters = collectScopeFilters();
    if (!hasFullScope(filters)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const remark = document.getElementById('pkgBatchAuditRemark')?.value?.trim() || '';
    if (mode === 'reverse' && !remark) {
        showToast('反审核原因必填', 'warning');
        return;
    }
    const year = Number(filters.year);
    const body = {
        location: filters.location,
        year,
        vehicle_model: filters.vehicle_model,
    };
    if (mode === 'approve') body.audit_remark = remark || null;
    else body.reverse_audit_remark = remark;

    pkgState.batchAuditSubmitting = true;
    try {
        const path = mode === 'approve' ? `${API_BASE}/batch-approve` : `${API_BASE}/batch-reverse-audit`;
        const res = await HttpClient.post(path, body);
        showToast(res.message || '操作成功', 'success');
        closeDrawer('pkgBatchAuditDrawer', 'pkgBatchAuditDrawerBackdrop');
        loadData(pkgState.page);
    } catch (err) {
        showToast(err.message || '操作失败', 'error');
    } finally {
        pkgState.batchAuditSubmitting = false;
    }
}

export const pageConfig = {
    render: pkgTransportFeeTemplate,
    init: () => init(),
};
