/**
 * Annual Part Price Page
 * 年度零件价列表：HUD + 批量审核/反审核/删除（范围=基地+年度，与上传对等）
 */

import {
    annualPartPriceTemplate,
    renderTableRows,
    unitPriceInputValue,
    parseUnitPriceInput,
    conversionFactorInputValue,
    parseConversionFactorInput,
    updateAnnualHud,
} from './template.js?v=33';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=6';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=4';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;
/** @type {{ paint: () => void, setOpen: (isOpen: boolean) => void, unbind: () => void } | null} */
let filterBar = null;

const annualPartPriceState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    selectedLocation: null,
    selectedYear: null,
    selectedAuditStatus: null,
    selectedKeyword: null,
    locations: [],
    years: [],
    isLoading: false,
    isBatchDeleting: false,
    batchAuditSubmitting: false,
    advancedOpen: false,
    suppliers: [],
};

const API_BASE = '/api/bom/annual-part-price';
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
    bindPagination({
        selectId: 'annualPageSize',
        buttonsId: 'annualPagination',
        getSize: () => annualPartPriceState.pageSize,
        setSize: (size) => {
            annualPartPriceState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    applyPermissionUi();
}

function applyPermissionUi() {
    const canExport = typeof can === 'function' ? can('op:bom-annual-part-price:export') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-annual-part-price:delete') : true;
    const canApprove = typeof can === 'function' ? can('op:bom-annual-part-price:approve') : true;
    const canReverse = typeof can === 'function' ? can('op:bom-annual-part-price:reverse') : true;
    if (!canExport) document.getElementById('btnExportAnnualPartPrice')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnBatchDeleteAnnualPartPrice')?.classList.add('hidden');
    if (!canApprove) document.getElementById('btnBatchApproveAnnual')?.classList.add('hidden');
    if (!canReverse) document.getElementById('btnBatchReverseAnnual')?.classList.add('hidden');
    const moreItems = ['btnBatchApproveAnnual', 'btnBatchReverseAnnual', 'btnBatchDeleteAnnualPartPrice']
        .map((id) => document.getElementById(id))
        .filter((el) => el && !el.classList.contains('hidden'));
    if (!moreItems.length) {
        document.getElementById('annualMoreWrap')?.classList.add('hidden');
    }
}

async function loadFilterOptions() {
    try {
        const [locRes, yearRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/filters/locations`),
            HttpClient.get(`${API_BASE}/filters/years`),
        ]);
        annualPartPriceState.locations = Array.isArray(locRes.data) ? locRes.data : [];
        annualPartPriceState.years = Array.isArray(yearRes.data) ? yearRes.data : [];

        const locationFilter = document.getElementById('annualLocationFilter');
        if (locationFilter) {
            let options = `<option value="">全部</option>`;
            annualPartPriceState.locations.forEach((loc) => {
                options += `<option value="${esc(loc)}">${esc(loc)}</option>`;
            });
            locationFilter.innerHTML = options;
            if (annualPartPriceState.selectedLocation) {
                locationFilter.value = annualPartPriceState.selectedLocation;
            }
        }

        const yearFilter = document.getElementById('annualYearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">全部</option>`;
            annualPartPriceState.years.forEach((year) => {
                options += `<option value="${year}">${esc(fmtYear(year))}</option>`;
            });
            if (!annualPartPriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${esc(fmtYear(currentYear))}</option>`;
            }
            yearFilter.innerHTML = options;
            if (annualPartPriceState.selectedYear) {
                yearFilter.value = annualPartPriceState.selectedYear;
            }
        }

        const auditFilter = document.getElementById('annualAuditStatusFilter');
        if (auditFilter) {
            auditFilter.innerHTML = `
                <option value="">全部</option>
                <option value="pending">待审</option>
                <option value="approved">已通过</option>
            `;
            if (annualPartPriceState.selectedAuditStatus) {
                auditFilter.value = annualPartPriceState.selectedAuditStatus;
            }
        }
        filterBar?.paint();
    } catch (error) {
        console.error('加载筛选项失败:', error);
    }
}

function readFiltersFromDom() {
    const locationFilter = document.getElementById('annualLocationFilter');
    const yearFilter = document.getElementById('annualYearFilter');
    const auditFilter = document.getElementById('annualAuditStatusFilter');
    const keywordFilter = document.getElementById('annualKeywordFilter');
    annualPartPriceState.selectedLocation = locationFilter ? (locationFilter.value || null) : null;
    annualPartPriceState.selectedYear = yearFilter ? (yearFilter.value || null) : null;
    annualPartPriceState.selectedAuditStatus = auditFilter ? (auditFilter.value || null) : null;
    annualPartPriceState.selectedKeyword = keywordFilter
        ? (keywordFilter.value.trim() || null)
        : null;
}

function collectScopeFilters() {
    return {
        location: (document.getElementById('annualLocationFilter')?.value || '').trim(),
        year: (document.getElementById('annualYearFilter')?.value || '').trim(),
    };
}

async function loadData(page = 1) {
    if (annualPartPriceState.isLoading) return;
    annualPartPriceState.isLoading = true;
    setSearchBusy('btnFilter', true);

    const tableBody = document.getElementById('annualPartPriceTableBody');
    const emptyState = document.getElementById('annualEmpty');
    const loadingState = document.getElementById('annualLoading');
    const totalCountPagination = document.getElementById('annualPageInfo');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page,
            size: annualPartPriceState.pageSize,
        };
        if (annualPartPriceState.selectedLocation) params.location = annualPartPriceState.selectedLocation;
        if (annualPartPriceState.selectedYear) params.year = annualPartPriceState.selectedYear;
        if (annualPartPriceState.selectedAuditStatus) {
            params.audit_status = annualPartPriceState.selectedAuditStatus;
        }
        if (annualPartPriceState.selectedKeyword) {
            params.keyword = annualPartPriceState.selectedKeyword;
        }

        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};

        annualPartPriceState.records = pageResult.items || [];
        annualPartPriceState.total = pageResult.total || 0;
        annualPartPriceState.page = pageResult.page || page;
        annualPartPriceState.totalPages = pageResult.total_pages || 1;

        const filters = pageResult.filters || {};
        annualPartPriceState.suppliers = filters.suppliers || [];
        updateAnnualHud(filters.summary || {});

        if (tableBody) {
            if (annualPartPriceState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(annualPartPriceState.records);
                bindTableRowEvents();
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${annualPartPriceState.total} 条`;
        }
        paintPagination('annualPagination', annualPartPriceState.page, annualPartPriceState.totalPages);
    } catch (error) {
        console.error('加载数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="15" class="px-4 py-8 text-center text-ink-muted text-xs">加载数据失败，请重试</td>
                </tr>`;
        }
    } finally {
        annualPartPriceState.isLoading = false;
        setSearchBusy('btnFilter', false);
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function bindTableRowEvents() {
    document.querySelectorAll('.annual-edit-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = annualPartPriceState.records.find((r) => r.id === id);
            if (record) {
                if (record.audit_status === 'approved') {
                    showToast('已审核通过，请先反审核后再修改', 'warning');
                    return;
                }
                openEditDrawer(record);
            }
        });
    });
    document.querySelectorAll('.annual-delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = annualPartPriceState.records.find((r) => r.id === id);
            if (record?.audit_status === 'approved') {
                showToast('已审核通过，请先反审核后再删除', 'warning');
                return;
            }
            openDeleteDrawer(id);
        });
    });
}

function bindEvents() {
    document.getElementById('btnExportAnnualPartPrice')?.addEventListener('click', () => exportExcel());
    moreMenu = bindMoreMenu({
        wrapId: 'annualMoreWrap',
        btnId: 'annualMoreBtn',
        menuId: 'annualMoreMenu',
    });
    document.getElementById('btnBatchDeleteAnnualPartPrice')?.addEventListener('click', () => {
        moreMenu?.close();
        batchDeleteByFilters();
    });
    document.getElementById('btnBatchApproveAnnual')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('approve');
    });
    document.getElementById('btnBatchReverseAnnual')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('reverse');
    });
    filterBar = bindFilterBar({
        prefix: 'annual',
        searchId: 'btnFilter',
        resetId: 'annualResetFilterBtn',
        capsules: [
            { capsuleId: 'annualCapsuleYear', fieldId: 'annualYearFilter', idleLabel: '全部年度' },
            { capsuleId: 'annualCapsuleLocation', fieldId: 'annualLocationFilter', idleLabel: '全部基地' },
            { capsuleId: 'annualCapsuleAudit', fieldId: 'annualAuditStatusFilter', idleLabel: '全部审核' },
            { capsuleId: 'annualCapsuleKeyword', fieldId: 'annualKeywordFilter', idleLabel: '零件号/名称' },
        ],
        enterFieldIds: ['annualKeywordFilter'],
        onSearch: () => {
            readFiltersFromDom();
            loadData(1);
        },
        onReset: () => {
            ['annualLocationFilter', 'annualYearFilter', 'annualAuditStatusFilter', 'annualKeywordFilter'].forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            readFiltersFromDom();
            loadData(1);
        },
    });
    ['annualLocationFilter', 'annualYearFilter', 'annualAuditStatusFilter'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            readFiltersFromDom();
            loadData(1);
        });
    });

    bindEditDrawerEvents();
    bindDeleteDrawerEvents();
    bindBatchAuditDrawerEvents();
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('annualEditDrawer', 'annualEditDrawerBackdrop');
    document.getElementById('closeAnnualEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelAnnualEditBtn')?.addEventListener('click', close);
    document.getElementById('annualEditDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitAnnualEditBtn')?.addEventListener('click', async (e) => {
        e.preventDefault();
        await saveRecord();
    });
}

function bindDeleteDrawerEvents() {
    const close = () => closeDrawer('annualDeleteDrawer', 'annualDeleteDrawerBackdrop');
    document.getElementById('closeAnnualDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelAnnualDeleteBtn')?.addEventListener('click', close);
    document.getElementById('annualDeleteDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmAnnualDeleteBtn')?.addEventListener('click', async () => {
        const id = parseInt(document.getElementById('annualDeleteRecordId')?.value, 10);
        if (id) await deleteRecord(id);
    });
}

function bindBatchAuditDrawerEvents() {
    const close = () => {
        if (annualPartPriceState.batchAuditSubmitting) return;
        closeDrawer('annualBatchAuditDrawer', 'annualBatchAuditDrawerBackdrop');
    };
    document.getElementById('closeAnnualBatchAuditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelAnnualBatchAuditBtn')?.addEventListener('click', close);
    document.getElementById('annualBatchAuditDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmAnnualBatchAuditBtn')?.addEventListener('click', submitBatchAudit);
}


function openEditDrawer(record) {
    document.getElementById('annualEditDrawerTitle').textContent = '编辑零件价';
    document.getElementById('annualEditRecordId').value = record.id;
    document.getElementById('annualEditLocation').value = record.location;
    document.getElementById('annualEditYear').value = record.year;
    document.getElementById('annualEditPartNumber').value = record.part_number || '';
    document.getElementById('annualEditPartName').value = record.part_name || '';
    document.getElementById('annualEditSpecification').value = record.specification || '';
    document.getElementById('annualEditPurchaseUnit').value = record.purchase_unit || '';
    document.getElementById('annualEditPurchaseUnitPrice').value =
        record.purchase_unit_price == null || record.purchase_unit_price === ''
            ? ''
            : unitPriceInputValue(record.purchase_unit_price);
    document.getElementById('annualEditConversionFactor').value =
        conversionFactorInputValue(record.conversion_factor);
    document.getElementById('annualEditUnit').value = record.unit || '';
    document.getElementById('annualEditUnitPrice').value = unitPriceInputValue(record.unit_price);
    document.getElementById('annualEditSupplyType').value = record.supply_type || '';
    fillAnnualSupplierSelect(record.supplier_name || '');
    document.getElementById('annualEditRemark').value = record.remark || '';
    openDrawer('annualEditDrawer', 'annualEditDrawerBackdrop');
}

function fillAnnualSupplierSelect(currentValue) {
    const el = document.getElementById('annualEditSupplierName');
    if (!el) return;
    const enabled = annualPartPriceState.suppliers || [];
    let html = '<option value="">（空）</option>';
    const seen = new Set();
    enabled.forEach((item) => {
        const name = item.full_name || '';
        seen.add(name);
        html += `<option value="${esc(name)}">${esc(item.abbreviation || '')}（${esc(name)}）</option>`;
    });
    if (currentValue && !seen.has(currentValue)) {
        html += `<option value="${esc(currentValue)}">${esc(currentValue)}</option>`;
    }
    el.innerHTML = html;
    el.value = currentValue || '';
}

function openDeleteDrawer(id) {
    document.getElementById('annualDeleteRecordId').value = id;
    openDrawer('annualDeleteDrawer', 'annualDeleteDrawerBackdrop');
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
        filterBar?.setOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const isApprove = mode === 'approve';
    document.getElementById('annualBatchAuditMode').value = isApprove ? 'approve' : 'reverse';
    document.getElementById('annualBatchAuditDrawerTitle').textContent = isApprove ? '批量审核' : '批量反审核';
    document.getElementById('annualBatchAuditHint').textContent = isApprove
        ? '仅处理待审记录；已通过会跳过。'
        : '仅处理已通过记录；其余状态会跳过。反审核意见必填。';
    document.getElementById('annualBatchAuditOperatorLabel').textContent = isApprove ? '审核人' : '反审核人';
    document.getElementById('annualBatchAuditOperatorDisplay').textContent =
        getSessionDisplayName() || '（当前登录用户）';
    const remarkLabel = document.getElementById('annualBatchAuditRemarkLabel');
    remarkLabel.innerHTML = isApprove
        ? '审核意见<span class="text-brand">*</span>'
        : '反审核意见<span class="text-brand">*</span>';
    const remarkEl = document.getElementById('annualBatchAuditRemark');
    remarkEl.value = '';
    remarkEl.placeholder = isApprove ? '请填写审核意见（必填）' : '必填反审核原因';
    document.getElementById('annualBatchAuditFilterSummary').textContent =
        `基地 ${filters.location} · ${fmtYear(filters.year)}`;
    openDrawer('annualBatchAuditDrawer', 'annualBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (annualPartPriceState.batchAuditSubmitting) return;
    const mode = document.getElementById('annualBatchAuditMode')?.value || 'approve';
    const filters = collectScopeFilters();
    const remark = document.getElementById('annualBatchAuditRemark')?.value.trim() || '';
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

    const btn = document.getElementById('confirmAnnualBatchAuditBtn');
    annualPartPriceState.batchAuditSubmitting = true;
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
        closeDrawer('annualBatchAuditDrawer', 'annualBatchAuditDrawerBackdrop');
        await loadData(annualPartPriceState.page);
    } catch (error) {
        if (!error.status) showToast(error.message || '操作失败', 'error');
    } finally {
        annualPartPriceState.batchAuditSubmitting = false;
        if (btn) {
            btn.disabled = false;
            btn.textContent = '确认提交';
        }
    }
}

async function exportExcel() {
    const btn = document.getElementById('btnExportAnnualPartPrice');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: {
                location: annualPartPriceState.selectedLocation || undefined,
                year: annualPartPriceState.selectedYear || undefined,
            },
            defaultFilename: '年度零件价导出.xlsx',
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
    if (typeof can === 'function' && !can('op:bom-annual-part-price:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (annualPartPriceState.isBatchDeleting) return;
    const filters = collectScopeFilters();
    if (!filters.location || !filters.year) {
        filterBar?.setOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const year = parseInt(filters.year, 10);
    if (!year || year < 2000 || year > 2100) {
        showToast('请选择正确的年度', 'warning');
        return;
    }
    if (!await window.confirmAction(
        `确定批量删除未审核年度零件价吗？\n\n基地: ${filters.location} · ${fmtYear(year)}\n\n仅删除待审记录；已审核通过会跳过。此操作不可恢复！`,
    )) return;

    const btn = document.getElementById('btnBatchDeleteAnnualPartPrice');
    const originalHtml = btn ? btn.innerHTML : '';
    annualPartPriceState.isBatchDeleting = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>删除中..`;
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
        annualPartPriceState.selectedLocation = filters.location;
        annualPartPriceState.selectedYear = String(year);
        await loadData(1);
        await loadFilterOptions();
    } catch (error) {
        console.error('批量删除失败:', error);
    } finally {
        annualPartPriceState.isBatchDeleting = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function saveRecord() {
    const recordId = document.getElementById('annualEditRecordId')?.value;
    const partName = document.getElementById('annualEditPartName')?.value?.trim() || null;
    const specification = document.getElementById('annualEditSpecification')?.value?.trim() || null;
    const purchaseUnit = document.getElementById('annualEditPurchaseUnit')?.value?.trim() || null;
    const purchaseRaw = document.getElementById('annualEditPurchaseUnitPrice')?.value?.trim() || '';
    const purchaseUnitPrice = purchaseRaw ? parseUnitPriceInput(purchaseRaw) : null;
    const conversionFactor = parseConversionFactorInput(
        document.getElementById('annualEditConversionFactor')?.value,
    );
    const unit = document.getElementById('annualEditUnit')?.value?.trim();
    const unitPrice = parseUnitPriceInput(document.getElementById('annualEditUnitPrice')?.value);
    const supplyType = document.getElementById('annualEditSupplyType')?.value?.trim() || null;
    const supplierName = document.getElementById('annualEditSupplierName')?.value?.trim() || null;
    const remark = document.getElementById('annualEditRemark')?.value?.trim() || null;
    if (purchaseRaw && purchaseUnitPrice == null) {
        showToast('采购单价须 ≥ 0，最多4位小数', 'warning');
        return;
    }
    if (!conversionFactor) {
        showToast('转换系数须大于 0（默认 1；1 采购单位=N 核价单位，可小数如 25.4，最多 6 位）', 'warning');
        return;
    }
    if (!recordId || !unit || unitPrice == null) {
        showToast('请填写单位和单价（单价须 ≥ 0，最多4位小数；填 0 表示成品核价不计入该件）', 'warning');
        return;
    }
    if (!supplyType) {
        showToast('请填写原供货类型', 'warning');
        return;
    }
    try {
        await HttpClient.put(`${API_BASE}/${recordId}`, {
            part_name: partName,
            specification,
            purchase_unit: purchaseUnit,
            purchase_unit_price: purchaseUnitPrice,
            conversion_factor: conversionFactor,
            unit,
            unit_price: unitPrice,
            supply_type: supplyType,
            supplier_name: supplierName,
            remark,
        });
        showToast('更新成功', 'success');
        closeDrawer('annualEditDrawer', 'annualEditDrawerBackdrop');
        loadData(annualPartPriceState.page);
    } catch (error) {
        console.error('保存失败:', error);
    }
}

async function deleteRecord(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('annualDeleteDrawer', 'annualDeleteDrawerBackdrop');
        loadData(annualPartPriceState.page);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

export const pageConfig = {
    render: annualPartPriceTemplate,
    init: () => init(),
    destroy() {
        moreMenu?.unbind();
        moreMenu = null;
        filterBar?.unbind();
        filterBar = null;
    },
};
