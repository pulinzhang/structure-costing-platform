/**
 * Welding Unit Price Page
 * 焊接单价列表：HUD + 批量审核/反审核/删除（范围=基地+年度，与上传对等）
 */

import {
    weldingUnitPriceTemplate,
    renderTableRows,
    renderPagination,
    unitPriceInputValue,
    parseUnitPriceInput,
    updateWeldingHud,
    updateWeldingFilterCapsules,
} from './template.js?v=12';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const weldingUnitPriceState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    selectedLocation: null,
    selectedYear: null,
    selectedAuditStatus: null,
    locations: [],
    years: [],
    isLoading: false,
    isBatchDeleting: false,
    batchAuditSubmitting: false,
    advancedOpen: false,
};

const API_BASE = '/api/bom/welding-unit-price';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '批量操作须同时选择基地和年度';

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
    bindPageSizeSelect('weldingUnitPricePageSize', {
        getSize: () => weldingUnitPriceState.pageSize,
        setSize: (size) => {
            weldingUnitPriceState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
    updateWeldingFilterCapsules();
}

function applyPermissionUi() {
    const canExport = typeof can === 'function' ? can('op:bom-welding-unit-price:export') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-welding-unit-price:delete') : true;
    const canApprove = typeof can === 'function' ? can('op:bom-welding-unit-price:approve') : true;
    const canReverse = typeof can === 'function' ? can('op:bom-welding-unit-price:reverse') : true;
    if (!canExport) document.getElementById('btnExportWeldingUnitPrice')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnBatchDeleteWeldingUnitPrice')?.classList.add('hidden');
    if (!canApprove) document.getElementById('btnBatchApproveWelding')?.classList.add('hidden');
    if (!canReverse) document.getElementById('btnBatchReverseWelding')?.classList.add('hidden');
}

function setAdvancedOpen(open) {
    weldingUnitPriceState.advancedOpen = open;
    const panel = document.getElementById('weldingAdvancedFilterPanel');
    const label = document.getElementById('weldingAdvancedFilterLabel');
    if (panel) panel.classList.toggle('hidden', !open);
    if (label) label.textContent = open ? '收起高级筛选' : '展开高级筛选';
}

async function loadFilterOptions() {
    try {
        const [locRes, yearRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/filters/locations`),
            HttpClient.get(`${API_BASE}/filters/years`),
        ]);
        weldingUnitPriceState.locations = Array.isArray(locRes.data) ? locRes.data : [];
        weldingUnitPriceState.years = Array.isArray(yearRes.data) ? yearRes.data : [];

        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter) {
            const known = ['大连', '芜湖', '鄂尔多斯', '青岛'];
            const merged = [...new Set([...known, ...weldingUnitPriceState.locations])];
            let options = `<option value="">全部</option>`;
            merged.forEach((loc) => {
                options += `<option value="${esc(loc)}">${esc(loc)}</option>`;
            });
            locationFilter.innerHTML = options;
            if (weldingUnitPriceState.selectedLocation) {
                locationFilter.value = weldingUnitPriceState.selectedLocation;
            }
        }

        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">全部</option>`;
            weldingUnitPriceState.years.forEach((year) => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            if (!weldingUnitPriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
            if (weldingUnitPriceState.selectedYear) {
                yearFilter.value = weldingUnitPriceState.selectedYear;
            }
        }

        const auditFilter = document.getElementById('auditStatusFilter');
        if (auditFilter) {
            auditFilter.innerHTML = `
                <option value="">全部</option>
                <option value="pending">待审</option>
                <option value="approved">已通过</option>
            `;
            if (weldingUnitPriceState.selectedAuditStatus) {
                auditFilter.value = weldingUnitPriceState.selectedAuditStatus;
            }
        }
    } catch (error) {
        console.error('加载筛选项失败:', error);
    }
}

function readFiltersFromDom() {
    const locationFilter = document.getElementById('locationFilter');
    const yearFilter = document.getElementById('yearFilter');
    const auditFilter = document.getElementById('auditStatusFilter');
    weldingUnitPriceState.selectedLocation = locationFilter ? (locationFilter.value || null) : null;
    weldingUnitPriceState.selectedYear = yearFilter ? (yearFilter.value || null) : null;
    weldingUnitPriceState.selectedAuditStatus = auditFilter ? (auditFilter.value || null) : null;
    updateWeldingFilterCapsules();
}

function collectScopeFilters() {
    return {
        location: (document.getElementById('locationFilter')?.value || '').trim(),
        year: (document.getElementById('yearFilter')?.value || '').trim(),
    };
}

async function loadData(page = 1) {
    if (weldingUnitPriceState.isLoading) return;
    weldingUnitPriceState.isLoading = true;

    const tableBody = document.getElementById('weldingUnitPriceTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCountPagination = document.getElementById('totalCountPagination');
    const paginationBtns = document.getElementById('paginationBtns');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page,
            size: weldingUnitPriceState.pageSize,
        };
        if (weldingUnitPriceState.selectedLocation) params.location = weldingUnitPriceState.selectedLocation;
        if (weldingUnitPriceState.selectedYear) params.year = weldingUnitPriceState.selectedYear;
        if (weldingUnitPriceState.selectedAuditStatus) {
            params.audit_status = weldingUnitPriceState.selectedAuditStatus;
        }

        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};

        weldingUnitPriceState.records = pageResult.items || [];
        weldingUnitPriceState.total = pageResult.total || 0;
        weldingUnitPriceState.page = pageResult.page || page;
        weldingUnitPriceState.totalPages = pageResult.total_pages || 1;

        const filters = pageResult.filters || {};
        updateWeldingHud(filters.summary || {});

        if (tableBody) {
            if (weldingUnitPriceState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(weldingUnitPriceState.records);
                bindTableRowEvents();
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${weldingUnitPriceState.total} 条`;
        }
        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(
                weldingUnitPriceState.page,
                weldingUnitPriceState.totalPages
            );
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">加载数据失败，请重试</td>
                </tr>`;
        }
    } finally {
        weldingUnitPriceState.isLoading = false;
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function bindTableRowEvents() {
    document.querySelectorAll('.edit-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = weldingUnitPriceState.records.find((r) => r.id === id);
            if (record) {
                if (record.audit_status === 'approved') {
                    showToast('已审核通过，请先反审核后再修改', 'warning');
                    return;
                }
                openEditDrawer(record);
            }
        });
    });
    document.querySelectorAll('.delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = weldingUnitPriceState.records.find((r) => r.id === id);
            if (record?.audit_status === 'approved') {
                showToast('已审核通过，请先反审核后再删除', 'warning');
                return;
            }
            openDeleteDrawer(id);
        });
    });
}

function bindEvents() {
    document.getElementById('btnExportWeldingUnitPrice')?.addEventListener('click', () => exportExcel());
    document.getElementById('btnBatchDeleteWeldingUnitPrice')?.addEventListener('click', () => batchDeleteByFilters());
    document.getElementById('btnBatchApproveWelding')?.addEventListener('click', () => openBatchAuditDrawer('approve'));
    document.getElementById('btnBatchReverseWelding')?.addEventListener('click', () => openBatchAuditDrawer('reverse'));
    document.getElementById('btnFilter')?.addEventListener('click', () => {
        readFiltersFromDom();
        loadData(1);
    });
    document.getElementById('weldingToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!weldingUnitPriceState.advancedOpen);
    });
    document.getElementById('weldingResetFilterBtn')?.addEventListener('click', () => {
        ['locationFilter', 'yearFilter', 'auditStatusFilter'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        readFiltersFromDom();
        loadData(1);
    });

    bindEditDrawerEvents();
    bindDeleteDrawerEvents();
    bindBatchAuditDrawerEvents();
    bindPaginationEvents();
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');
    document.getElementById('closeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelEditBtn')?.addEventListener('click', close);
    document.getElementById('editDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitEditBtn')?.addEventListener('click', async (e) => {
        e.preventDefault();
        await saveRecord();
    });
}

function bindDeleteDrawerEvents() {
    const close = () => closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
    document.getElementById('closeDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelDeleteBtn')?.addEventListener('click', close);
    document.getElementById('deleteDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', async () => {
        const id = parseInt(document.getElementById('deleteRecordId')?.value, 10);
        if (id) await deleteRecord(id);
    });
}

function bindBatchAuditDrawerEvents() {
    const close = () => {
        if (weldingUnitPriceState.batchAuditSubmitting) return;
        closeDrawer('weldingBatchAuditDrawer', 'weldingBatchAuditDrawerBackdrop');
    };
    document.getElementById('closeWeldingBatchAuditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelWeldingBatchAuditBtn')?.addEventListener('click', close);
    document.getElementById('weldingBatchAuditDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmWeldingBatchAuditBtn')?.addEventListener('click', submitBatchAudit);
}

function bindPaginationEvents() {
    document.getElementById('paginationBtns')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadData(page);
        }
    });
}

function openEditDrawer(record) {
    document.getElementById('editDrawerTitle').textContent = '编辑费用';
    document.getElementById('editRecordId').value = record.id;
    document.getElementById('editLocation').value = record.location;
    document.getElementById('editYear').value = record.year;
    document.getElementById('editItemName').value = record.item_name;
    document.getElementById('editUnit').value = record.unit || '';
    document.getElementById('editUnitPrice').value = unitPriceInputValue(record.unit_price);
    document.getElementById('editRemark').value = record.remark || '';
    openDrawer('editDrawer', 'editDrawerBackdrop');
}

function openDeleteDrawer(id) {
    document.getElementById('deleteRecordId').value = id;
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
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
    const filters = collectScopeFilters();
    if (!filters.year || !filters.location) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const isApprove = mode === 'approve';
    document.getElementById('weldingBatchAuditMode').value = isApprove ? 'approve' : 'reverse';
    document.getElementById('weldingBatchAuditDrawerTitle').textContent = isApprove ? '批量审核' : '批量反审核';
    document.getElementById('weldingBatchAuditHint').textContent = isApprove
        ? '仅处理待审记录；已通过会跳过。'
        : '仅处理已通过记录；其余状态会跳过。反审核意见必填。';
    document.getElementById('weldingBatchAuditOperatorLabel').textContent = isApprove ? '审核人' : '反审核人';
    document.getElementById('weldingBatchAuditOperatorDisplay').textContent =
        getSessionDisplayName() || '（当前登录用户）';
    const remarkLabel = document.getElementById('weldingBatchAuditRemarkLabel');
    remarkLabel.innerHTML = isApprove
        ? '审核意见<span class="text-[#d32f2f]">*</span>'
        : '反审核意见<span class="text-[#d32f2f]">*</span>';
    const remarkEl = document.getElementById('weldingBatchAuditRemark');
    remarkEl.value = '';
    remarkEl.placeholder = isApprove ? '请填写审核意见（必填）' : '必填反审核原因';
    document.getElementById('weldingBatchAuditFilterSummary').textContent =
        `基地 ${filters.location} · 年度 ${filters.year}`;
    openDrawer('weldingBatchAuditDrawer', 'weldingBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (weldingUnitPriceState.batchAuditSubmitting) return;
    const mode = document.getElementById('weldingBatchAuditMode')?.value || 'approve';
    const filters = collectScopeFilters();
    const remark = document.getElementById('weldingBatchAuditRemark')?.value.trim() || '';
    if (!remark) {
        showToast(mode === 'approve' ? '审核意见必填' : '反审核意见必填', 'warning');
        return;
    }
    const body = {
        location: filters.location,
        year: Number(filters.year),
    };
    const url = mode === 'approve'
        ? `${API_BASE}/batch-approve`
        : `${API_BASE}/batch-reverse-audit`;
    if (mode === 'approve') body.audit_remark = remark;
    else body.reverse_audit_remark = remark;

    const btn = document.getElementById('confirmWeldingBatchAuditBtn');
    weldingUnitPriceState.batchAuditSubmitting = true;
    if (btn) {
        btn.disabled = true;
        btn.textContent = '提交中…';
    }
    try {
        const res = await HttpClient.post(url, body);
        const result = res.data || {};
        showToast(
            res.message
                || (mode === 'approve'
                    ? `已审核通过 ${result.updated_count || 0} 条`
                    : `已反审核 ${result.updated_count || 0} 条`),
            (result.updated_count || 0) > 0 ? 'success' : 'warning',
        );
        closeDrawer('weldingBatchAuditDrawer', 'weldingBatchAuditDrawerBackdrop');
        await loadData(weldingUnitPriceState.page);
    } catch (error) {
        if (!error.status) showToast(error.message || '操作失败', 'error');
    } finally {
        weldingUnitPriceState.batchAuditSubmitting = false;
        if (btn) {
            btn.disabled = false;
            btn.textContent = '确认提交';
        }
    }
}

async function exportExcel() {
    const btn = document.getElementById('btnExportWeldingUnitPrice');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: {
                location: weldingUnitPriceState.selectedLocation || undefined,
                year: weldingUnitPriceState.selectedYear || undefined,
            },
            defaultFilename: '焊接单价导出.xlsx',
        });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
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

async function batchDeleteByFilters() {
    if (typeof can === 'function' && !can('op:bom-welding-unit-price:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (weldingUnitPriceState.isBatchDeleting) return;
    const filters = collectScopeFilters();
    if (!filters.location || !filters.year) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const year = parseInt(filters.year, 10);
    if (!year || year < 2000 || year > 2100) {
        showToast('请选择正确的年度', 'warning');
        return;
    }
    if (!window.confirm(
        `确定批量删除未审核焊接单价吗？\n\n基地: ${filters.location} | 年度: ${year}\n\n仅删除待审记录；已审核通过会跳过。此操作不可恢复！`,
    )) return;

    const btn = document.getElementById('btnBatchDeleteWeldingUnitPrice');
    const originalHtml = btn ? btn.innerHTML : '';
    weldingUnitPriceState.isBatchDeleting = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>删除中..`;
    }
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, {
            location: filters.location,
            year,
        });
        const data = res.data || {};
        const deleted = data.deleted_count ?? 0;
        const skipped = data.skipped_approved_count ?? 0;
        showToast(
            res.message || `已删除 ${deleted} 条` + (skipped ? `，跳过已审核 ${skipped} 条` : ''),
            deleted > 0 ? 'success' : 'warning',
        );
        weldingUnitPriceState.selectedLocation = filters.location;
        weldingUnitPriceState.selectedYear = String(year);
        await loadData(1);
        await loadFilterOptions();
    } catch (error) {
        if (!error.status) showToast(error.message || '批量删除失败', 'error');
    } finally {
        weldingUnitPriceState.isBatchDeleting = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function saveRecord() {
    const recordId = document.getElementById('editRecordId')?.value;
    const unit = document.getElementById('editUnit')?.value?.trim();
    const unitPrice = parseUnitPriceInput(document.getElementById('editUnitPrice')?.value);
    const remark = document.getElementById('editRemark')?.value?.trim() || null;
    if (!recordId || !unit || !unitPrice) {
        showToast('请填写单位和费用（费用须为最多4位小数的数字）', 'warning');
        return;
    }
    try {
        await HttpClient.put(`${API_BASE}/${recordId}`, {
            unit,
            unit_price: unitPrice,
            remark,
        });
        showToast('更新成功', 'success');
        closeDrawer('editDrawer', 'editDrawerBackdrop');
        loadData(weldingUnitPriceState.page);
    } catch (error) {
        console.error('保存失败:', error);
    }
}

async function deleteRecord(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
        loadData(weldingUnitPriceState.page);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

export const pageConfig = {
    render: weldingUnitPriceTemplate,
    init: () => init(),
};
