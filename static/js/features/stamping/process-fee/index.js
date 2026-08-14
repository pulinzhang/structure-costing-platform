/**
 * 冲压加工费列表页
 * 对齐钢材价格列表：HUD + 胶囊筛选 + 查看/编辑抽屉 + 批量审核/反审核/删除 + Excel 导出
 */

import {
    processFeeListTemplate,
    renderFeeRows,
    renderFeePagination,
    updateFeeHud,
    updateFeeFilterCapsules,
    shortPartNumber,
} from './template.js?v=19';

const API_BASE = '/api/stamping/process-fees';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、冲压工厂';

const TONNAGE_SOURCE_LABEL = {
    self: '自有',
    inherited: '继承',
    swing_shear: '摆剪',
};

const feeState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    canUpdate: true,
    advancedOpen: false,
    batchAuditSubmitting: false,
    editingId: null,
    viewingId: null,
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
    bindEvents();
    applyPermissionUi();
    applyHashFilters();
    fillAuditStatusOptions();
    loadFilterOptions().then(() => {
        updateFeeFilterCapsules();
        loadData(1);
    });
}

function applyPermissionUi() {
    feeState.canUpdate = typeof can === 'function' ? can('op:stamping-process-fee:update') : true;
    const canDelete = typeof can === 'function' ? can('op:stamping-process-fee:delete') : true;
    const canApprove = typeof can === 'function' ? can('op:stamping-process-fee:approve') : true;
    const canReverse = typeof can === 'function' ? can('op:stamping-process-fee:reverse') : true;
    const canExport = typeof can === 'function' ? can('op:stamping-process-fee:export') : true;
    if (!canDelete) document.getElementById('feeBatchDeleteBtn')?.classList.add('hidden');
    if (!canApprove) document.getElementById('feeBatchApproveBtn')?.classList.add('hidden');
    if (!canReverse) document.getElementById('feeBatchReverseBtn')?.classList.add('hidden');
    if (!canExport) document.getElementById('feeExportBtn')?.classList.add('hidden');
}

function applyHashFilters() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return;
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    const year = qs.get('year') || '';
    const location = qs.get('location') || '';
    const supplier = qs.get('stamping_supplier') || '';
    if (year) {
        const yearEl = document.getElementById('feeYearFilter');
        if (yearEl) yearEl.dataset.pending = year;
    }
    if (location) {
        const locEl = document.getElementById('feeLocationFilter');
        if (locEl) locEl.dataset.pending = location;
    }
    if (supplier) {
        const supplierEl = document.getElementById('feeSupplierFilter');
        if (supplierEl) supplierEl.dataset.pending = supplier;
    }
    if (year || location || supplier) {
        setAdvancedOpen(true);
    }
}

function fillAuditStatusOptions() {
    const el = document.getElementById('feeAuditStatusFilter');
    if (!el) return;
    el.innerHTML = `
        <option value="">全部</option>
        <option value="pending">待审</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
    `;
}

function setAdvancedOpen(isOpen) {
    feeState.advancedOpen = isOpen;
    document.getElementById('feeAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('feeAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function bindEvents() {
    document.getElementById('feeSearchBtn')?.addEventListener('click', () => loadData(1));
    document.getElementById('feeResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('feeToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!feeState.advancedOpen);
    });
    document.getElementById('feeExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('feeBatchDeleteBtn')?.addEventListener('click', batchDelete);
    document.getElementById('feeBatchApproveBtn')?.addEventListener('click', () => openBatchAuditDrawer('approve'));
    document.getElementById('feeBatchReverseBtn')?.addEventListener('click', () => openBatchAuditDrawer('reverse'));

    document.getElementById('feeYearFilter')?.addEventListener('change', () => {
        updateFeeFilterCapsules();
        loadLocationOptions().then(() => loadSupplierOptions().then(() => {
            updateFeeFilterCapsules();
            loadData(1);
        }));
    });
    document.getElementById('feeLocationFilter')?.addEventListener('change', () => {
        updateFeeFilterCapsules();
        loadSupplierOptions().then(() => {
            updateFeeFilterCapsules();
            loadData(1);
        });
    });
    document.getElementById('feeSupplierFilter')?.addEventListener('change', () => {
        updateFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('feeAuditStatusFilter')?.addEventListener('change', () => {
        updateFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('feePartNumberFilter')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') loadData(1);
    });
    document.getElementById('feePartNumberFilter')?.addEventListener('input', () => {
        updateFeeFilterCapsules();
    });

    document.getElementById('feePagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-fee-page]');
        if (!btn) return;
        const page = Number(btn.getAttribute('data-fee-page'));
        if (!Number.isFinite(page) || page < 1) return;
        loadData(page);
    });

    bindEditDrawerEvents();
    bindViewDrawerEvents();
    bindBatchAuditDrawerEvents();
}

function bindRowEvents() {
    document.querySelectorAll('#feeTableBody .view-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const row = btn.closest('tr');
            const id = Number(row?.dataset.id);
            const record = feeState.records.find((item) => item.id === id);
            if (record) openViewDrawer(record);
        });
    });
    document.querySelectorAll('#feeTableBody .edit-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const row = btn.closest('tr');
            const id = Number(row?.dataset.id);
            const record = feeState.records.find((item) => item.id === id);
            if (record) openEditDrawer(record);
        });
    });
    document.querySelectorAll('#feeTableBody tr[data-id]').forEach((tr) => {
        tr.addEventListener('click', (event) => {
            if (event.target.closest('button')) return;
            const id = Number(tr.dataset.id);
            const record = feeState.records.find((item) => item.id === id);
            if (record) openViewDrawer(record);
        });
    });
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('feeEditDrawer', 'feeEditDrawerBackdrop');
    document.getElementById('closeFeeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelFeeEditBtn')?.addEventListener('click', close);
    document.getElementById('feeEditDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitFeeEditBtn')?.addEventListener('click', () => saveEdit());
}

function bindViewDrawerEvents() {
    const close = () => closeDrawer('feeViewDrawer', 'feeViewDrawerBackdrop');
    document.getElementById('closeFeeViewDrawer')?.addEventListener('click', close);
    document.getElementById('feeViewDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('feeViewDrawerEditBtn')?.addEventListener('click', () => {
        const record = feeState.records.find((item) => item.id === feeState.viewingId);
        if (!record) return;
        closeDrawer('feeViewDrawer', 'feeViewDrawerBackdrop');
        openEditDrawer(record);
    });
}

function bindBatchAuditDrawerEvents() {
    document.getElementById('closeFeeBatchAuditDrawer')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('cancelFeeBatchAuditBtn')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('feeBatchAuditDrawerBackdrop')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('confirmFeeBatchAuditBtn')?.addEventListener('click', submitBatchAudit);
}

async function loadFilterOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        const years = Array.isArray(res.data) ? res.data : [];
        const yearEl = document.getElementById('feeYearFilter');
        if (yearEl) {
            const pending = yearEl.dataset.pending || '';
            let html = '<option value="">全部</option>';
            years.forEach((year) => {
                const selected = String(year) === String(pending) ? ' selected' : '';
                html += `<option value="${esc(year)}"${selected}>${esc(year)}</option>`;
            });
            yearEl.innerHTML = html;
            delete yearEl.dataset.pending;
        }
        await loadLocationOptions();
        await loadSupplierOptions();
    } catch (error) {
        showToast(error.message || '加载筛选失败', 'error');
    }
}

async function loadLocationOptions() {
    const year = document.getElementById('feeYearFilter')?.value || undefined;
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/locations`, {
            params: { year },
        });
        const locations = Array.isArray(res.data) ? res.data : [];
        const locEl = document.getElementById('feeLocationFilter');
        if (!locEl) return;
        const pending = locEl.dataset.pending || locEl.value || '';
        let html = '<option value="">全部</option>';
        locations.forEach((location) => {
            const selected = String(location) === String(pending) ? ' selected' : '';
            html += `<option value="${esc(location)}"${selected}>${esc(location)}</option>`;
        });
        locEl.innerHTML = html;
        delete locEl.dataset.pending;
    } catch (error) {
        showToast(error.message || '加载基地失败', 'error');
    }
}

async function loadSupplierOptions() {
    const year = document.getElementById('feeYearFilter')?.value || undefined;
    const location = document.getElementById('feeLocationFilter')?.value || undefined;
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/suppliers`, {
            params: { year, location },
        });
        const suppliers = Array.isArray(res.data) ? res.data : [];
        const supplierEl = document.getElementById('feeSupplierFilter');
        if (!supplierEl) return;
        const pending = supplierEl.dataset.pending || supplierEl.value || '';
        let html = '<option value="">全部</option>';
        suppliers.forEach((supplier) => {
            const selected = String(supplier) === String(pending) ? ' selected' : '';
            html += `<option value="${esc(supplier)}"${selected}>${esc(supplier)}</option>`;
        });
        supplierEl.innerHTML = html;
        delete supplierEl.dataset.pending;
    } catch (error) {
        showToast(error.message || '加载工厂失败', 'error');
    }
}

function resetFilters() {
    ['feeYearFilter', 'feeLocationFilter', 'feeSupplierFilter', 'feeAuditStatusFilter'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const partEl = document.getElementById('feePartNumberFilter');
    if (partEl) partEl.value = '';
    loadLocationOptions().then(() => loadSupplierOptions().then(() => {
        updateFeeFilterCapsules();
        loadData(1);
    }));
}

function collectScopeFilters() {
    return {
        year: document.getElementById('feeYearFilter')?.value || '',
        location: document.getElementById('feeLocationFilter')?.value || '',
        stamping_supplier: document.getElementById('feeSupplierFilter')?.value || '',
    };
}

function collectListFilters() {
    return {
        ...collectScopeFilters(),
        audit_status: document.getElementById('feeAuditStatusFilter')?.value || '',
        part_number: (document.getElementById('feePartNumberFilter')?.value || '').trim(),
    };
}

async function loadData(page = 1) {
    const loading = document.getElementById('feeLoading');
    const empty = document.getElementById('feeEmpty');
    const body = document.getElementById('feeTableBody');
    if (body) body.innerHTML = '';
    empty?.classList.add('hidden');
    loading?.classList.remove('hidden');
    updateFeeFilterCapsules();

    try {
        const filters = collectListFilters();
        const params = {
            page,
            size: feeState.pageSize,
            year: filters.year || undefined,
            location: filters.location || undefined,
            stamping_supplier: filters.stamping_supplier || undefined,
            part_number: filters.part_number || undefined,
            audit_status: filters.audit_status || undefined,
        };
        const res = await HttpClient.get(API_BASE, { params });
        const data = res.data || {};
        feeState.records = Array.isArray(data.items) ? data.items : [];
        feeState.total = data.total || 0;
        feeState.page = data.page || page;
        feeState.pageSize = data.page_size || feeState.pageSize;
        feeState.totalPages = data.total_pages || Math.ceil(feeState.total / feeState.pageSize) || 1;

        const totalLabel = document.getElementById('feeTotalLabel');
        if (totalLabel) totalLabel.textContent = `共 ${feeState.total} 条`;
        updateFeeHud(feeState.total, feeState.records);

        if (!feeState.records.length) {
            empty?.classList.remove('hidden');
        } else if (body) {
            body.innerHTML = renderFeeRows(feeState.records);
            bindRowEvents();
        }

        const pagination = document.getElementById('feePagination');
        if (pagination) {
            pagination.innerHTML = renderFeePagination(feeState.page, feeState.totalPages);
        }
    } catch (error) {
        showToast(error.message || '加载失败', 'error');
        empty?.classList.remove('hidden');
    } finally {
        loading?.classList.add('hidden');
    }
}

function fillPartNumberFields(prefix, partNumber) {
    const shortEl = document.getElementById(`${prefix}-part-short`);
    const fullEl = document.getElementById(`${prefix}-part-number`);
    const full = partNumber || '';
    const shortNo = shortPartNumber(full);
    if (shortEl) {
        shortEl.textContent = shortNo || (full || '—');
        shortEl.classList.toggle('text-xl', Boolean(shortNo));
        shortEl.classList.toggle('text-xs', !shortNo);
        shortEl.classList.toggle('text-[#cccccc]', !shortNo);
        shortEl.classList.toggle('text-white', Boolean(shortNo));
    }
    if (fullEl) {
        fullEl.textContent = shortNo ? full : '';
        fullEl.classList.toggle('hidden', !shortNo);
    }
}

function fillViewField(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null || value === '' ? '—' : String(value);
}

function formatDecimal(value, digits = 3) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '—';
    return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value).replace('T', ' ');
    return text.length >= 19 ? text.slice(0, 19) : text;
}

function auditStatusLabel(status) {
    return { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '—';
}

function openViewDrawer(record) {
    feeState.viewingId = record.id;
    fillViewFieldsFromRecord(record);
    renderProcessItems(record.process_items || []);

    const approved = record.audit_status === 'approved';
    const editBtn = document.getElementById('feeViewDrawerEditBtn');
    if (editBtn) {
        editBtn.classList.toggle('hidden', !(feeState.canUpdate && !approved));
    }
    openDrawer('feeViewDrawer', 'feeViewDrawerBackdrop');
    loadFeeDetail(record.id);
}

function fillViewFieldsFromRecord(record) {
    fillViewField('fee-view-year', record.year);
    fillViewField('fee-view-location', record.location);
    fillViewField('fee-view-supplier', record.stamping_supplier);
    fillViewField('fee-view-vehicle', record.vehicle_model);
    fillViewField('fee-view-version', record.version);
    fillPartNumberFields('fee-view', record.part_number);
    fillViewField('fee-view-part-name', record.part_name);
    fillViewField('fee-view-seq-no', record.seq_no);
    fillViewField('fee-view-material', record.material);
    fillViewField('fee-view-thickness', formatDecimal(record.thickness, 4));
    fillViewField('fee-view-part-weight', formatDecimal(record.part_weight, 4));
    fillViewField('fee-view-sheet-length', formatDecimal(record.sheet_length, 2));
    fillViewField('fee-view-sheet-width', formatDecimal(record.sheet_width, 2));
    fillViewField('fee-view-parts-per-sheet', record.parts_per_sheet);
    fillViewField('fee-view-sheet-type', record.sheet_type);
    fillViewField('fee-view-die-type', record.die_type);
    fillViewField('fee-view-process-method', record.process_method);
    fillViewField('fee-view-automation', record.automation);
    fillViewField('fee-view-excel-filename', record.excel_filename);
    fillViewField('fee-view-part-remark', record.part_remark);
    fillViewField('fee-view-process-count', record.process_count);
    fillViewField('fee-view-processing-fee', formatDecimal(record.processing_fee, 3));
    fillViewField('fee-view-manual-price', formatDecimal(record.manual_unit_price, 3));
    fillViewField('fee-view-final-fee', formatDecimal(record.final_processing_fee, 3));
    fillViewField('fee-view-fail-reason', record.calc_fail_reason);
    fillViewField('fee-view-remark', record.remark);
    fillViewField('fee-view-audit-status', auditStatusLabel(record.audit_status));
    fillViewField('fee-view-audited-by', record.audited_by);
    fillViewField('fee-view-audited-at', formatDateTime(record.audited_at));
    fillViewField('fee-view-audit-remark', record.audit_remark);
    fillViewField('fee-view-reverse-by', record.reverse_audited_by);
    fillViewField('fee-view-reverse-at', formatDateTime(record.reverse_audited_at));
    fillViewField('fee-view-reverse-remark', record.reverse_audit_remark);
    fillViewField('fee-view-created-by', record.created_by);
    fillViewField('fee-view-created-at', formatDateTime(record.created_at));
    fillViewField('fee-view-updated-by', record.updated_by);
    fillViewField('fee-view-updated-at', formatDateTime(record.updated_at));
}

async function loadFeeDetail(feeId) {
    const container = document.getElementById('feeViewProcessItems');
    if (container) {
        container.innerHTML = '<div class="px-4 py-6 text-[11px] text-[#616161]">加载中...</div>';
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/${feeId}`);
        const detail = res?.data || res;
        if (!detail || feeState.viewingId !== feeId) return;
        fillViewFieldsFromRecord(detail);
        renderProcessItems(detail.process_items || []);
    } catch (error) {
        if (container && feeState.viewingId === feeId) {
            container.innerHTML = `<div class="px-4 py-6 text-[11px] text-[#ef5350]">${esc(error.message || '加载溯源失败')}</div>`;
        }
    }
}

function renderProcessItems(items) {
    const container = document.getElementById('feeViewProcessItems');
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = '<div class="px-4 py-6 text-[11px] text-[#616161]">暂无工序溯源（请重新计算后生成）</div>';
        return;
    }
    const rows = items.map((item) => {
        const sourceLabel = TONNAGE_SOURCE_LABEL[item.tonnage_source] || item.tonnage_source || '—';
        const inheritHint = item.tonnage_source === 'inherited'
            ? `${esc(item.inherited_from_part_number || '')} / ${esc(item.inherited_from_process_seq || '')}`
            : '—';
        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors">
                <td class="px-3 py-2 text-[11px] font-mono text-[#9e9e9e] whitespace-nowrap">${esc(item.process_seq || '—')}</td>
                <td class="px-3 py-2 text-[11px] text-[#cccccc] whitespace-nowrap">${esc(item.process_code || '—')}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${esc(item.resolved_tonnage != null ? `${item.resolved_tonnage}T` : '—')}</td>
                <td class="px-3 py-2 text-[11px] text-[#9e9e9e] whitespace-nowrap">${esc(sourceLabel)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${formatDecimal(item.cost_ratio, 2)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${formatDecimal(item.price_per_stroke, 3)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#ffffff]">${formatDecimal(item.line_fee, 3)}</td>
                <td class="px-3 py-2 text-[11px] text-[#888888] min-w-[180px]">${esc(item.basis_text || inheritHint)}</td>
            </tr>`;
    }).join('');
    container.innerHTML = `
        <table class="w-full">
            <thead>
                <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">工序</th>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">代码</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">吨位</th>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">来源</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">比例</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">冲次单价</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">本序费</th>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">计算依据</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-[#222222]">${rows}</tbody>
        </table>`;
}

function openEditDrawer(record) {
    if (!feeState.canUpdate) {
        showToast('无编辑权限', 'warning');
        return;
    }
    if (record.audit_status === 'approved') {
        showToast('已审核通过，请先反审核后再调整', 'warning');
        return;
    }
    feeState.editingId = record.id;
    fillViewField('fee-edit-year', record.year);
    fillViewField('fee-edit-location', record.location);
    fillViewField('fee-edit-supplier', record.stamping_supplier);
    fillPartNumberFields('fee-edit', record.part_number);
    fillViewField('fee-edit-vehicle', record.vehicle_model);
    fillViewField('fee-edit-version', record.version);
    fillViewField('fee-edit-processing-fee', formatDecimal(record.processing_fee, 3));
    fillViewField('fee-edit-final-fee', formatDecimal(record.final_processing_fee, 3));

    const idEl = document.getElementById('feeEditRecordId');
    if (idEl) idEl.value = String(record.id);
    const manualEl = document.getElementById('feeEditManualPrice');
    if (manualEl) {
        manualEl.value = record.manual_unit_price == null ? '' : String(record.manual_unit_price);
    }
    const remarkEl = document.getElementById('feeEditRemark');
    if (remarkEl) remarkEl.value = record.remark || '';

    openDrawer('feeEditDrawer', 'feeEditDrawerBackdrop');
}

async function saveEdit() {
    const feeId = Number(document.getElementById('feeEditRecordId')?.value);
    if (!Number.isFinite(feeId)) return;

    const raw = String(document.getElementById('feeEditManualPrice')?.value || '').trim();
    let manualUnitPrice = null;
    if (raw !== '') {
        const parsed = Number(raw);
        if (!Number.isFinite(parsed) || parsed < 0) {
            showToast('手工调整单价须为非负数字', 'warning');
            return;
        }
        manualUnitPrice = parsed;
    }
    const remark = String(document.getElementById('feeEditRemark')?.value || '').trim() || null;

    try {
        const res = await HttpClient.patch(`${API_BASE}/${feeId}`, {
            manual_unit_price: manualUnitPrice,
            remark,
        });
        showToast(res.message || '保存成功', 'success');
        closeDrawer('feeEditDrawer', 'feeEditDrawerBackdrop');
        await loadData(feeState.page);
    } catch (error) {
        showToast(error.message || '保存失败', 'error');
    }
}

async function exportExcel() {
    const filters = collectListFilters();
    if (
        !filters.year
        && !filters.location
        && !filters.stamping_supplier
        && !filters.audit_status
        && !filters.part_number
    ) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        return;
    }

    const btn = document.getElementById('feeExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            导出中...
        `;
    }

    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params: {
                year: filters.year || undefined,
                location: filters.location || undefined,
                stamping_supplier: filters.stamping_supplier || undefined,
                audit_status: filters.audit_status || undefined,
                part_number: filters.part_number || undefined,
            },
            defaultFilename: '冲压加工费导出.xlsx',
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
        console.error('导出冲压加工费失败:', error);
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

async function batchDelete() {
    const filters = collectScopeFilters();
    if (!filters.year || !filters.location || !filters.stamping_supplier) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (!window.confirm(
        `确定批量删除未审核记录吗？\n\n年度: ${filters.year} | 基地: ${filters.location} | 工厂: ${filters.stamping_supplier}\n\n仅删除待审/已驳回；已审核通过会跳过。此操作不可恢复！`,
    )) {
        return;
    }

    const btn = document.getElementById('feeBatchDeleteBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中...
        `;
    }

    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, {
            year: Number(filters.year),
            location: filters.location,
            stamping_supplier: filters.stamping_supplier,
        });
        const result = res.data || {};
        const deleted = result.deleted_count ?? 0;
        const skipped = result.skipped_approved_count ?? 0;
        showToast(
            res.message || `已删除 ${deleted} 条` + (skipped ? `，跳过已审核 ${skipped} 条` : ''),
            deleted > 0 ? 'success' : 'warning',
        );
        await loadFilterOptions();
        await loadData(1);
    } catch (error) {
        showToast(error.message || '批量删除失败', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
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
    if (!filters.year || !filters.location || !filters.stamping_supplier) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }

    const isApprove = mode === 'approve';
    const modeEl = document.getElementById('feeBatchAuditMode');
    const titleEl = document.getElementById('feeBatchAuditDrawerTitle');
    const hintEl = document.getElementById('feeBatchAuditHint');
    const operatorLabel = document.getElementById('feeBatchAuditOperatorLabel');
    const remarkLabel = document.getElementById('feeBatchAuditRemarkLabel');
    const operatorDisplay = document.getElementById('feeBatchAuditOperatorDisplay');
    const remarkEl = document.getElementById('feeBatchAuditRemark');
    const summaryEl = document.getElementById('feeBatchAuditFilterSummary');

    if (modeEl) modeEl.value = isApprove ? 'approve' : 'reverse';
    if (titleEl) titleEl.textContent = isApprove ? '批量审核' : '批量反审核';
    if (hintEl) {
        hintEl.textContent = isApprove
            ? '仅处理待审/已驳回；已通过记录会跳过。'
            : '仅处理已通过记录；其余状态会跳过。反审核意见必填。';
    }
    if (operatorLabel) operatorLabel.textContent = isApprove ? '审核人' : '反审核人';
    if (operatorDisplay) {
        operatorDisplay.textContent = getSessionDisplayName() || '（当前登录用户）';
    }
    if (remarkLabel) {
        remarkLabel.innerHTML = isApprove
            ? '审核意见'
            : '反审核意见 <span class="text-[#d32f2f]">*</span>';
    }
    if (remarkEl) {
        remarkEl.value = '';
        remarkEl.placeholder = isApprove ? '可选填写审核意见' : '必填反审核原因';
    }
    if (summaryEl) {
        summaryEl.textContent = `年度 ${filters.year} · 基地 ${filters.location} · 工厂 ${filters.stamping_supplier}`;
    }
    openDrawer('feeBatchAuditDrawer', 'feeBatchAuditDrawerBackdrop');
}

function closeBatchAuditDrawer() {
    if (feeState.batchAuditSubmitting) return;
    closeDrawer('feeBatchAuditDrawer', 'feeBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (feeState.batchAuditSubmitting) return;
    const mode = document.getElementById('feeBatchAuditMode')?.value || 'approve';
    const filters = collectScopeFilters();
    const remark = document.getElementById('feeBatchAuditRemark')?.value.trim() || '';
    if (mode === 'reverse' && !remark) {
        showToast('反审核意见必填', 'warning');
        return;
    }

    const body = {
        year: Number(filters.year),
        location: filters.location,
        stamping_supplier: filters.stamping_supplier,
    };
    const url = mode === 'approve'
        ? `${API_BASE}/batch-approve`
        : `${API_BASE}/batch-reverse-audit`;
    if (mode === 'approve') {
        body.audit_remark = remark || null;
    } else {
        body.reverse_audit_remark = remark;
    }

    const btn = document.getElementById('confirmFeeBatchAuditBtn');
    feeState.batchAuditSubmitting = true;
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
        closeDrawer('feeBatchAuditDrawer', 'feeBatchAuditDrawerBackdrop');
        await loadData(feeState.page);
    } catch (error) {
        showToast(error.message || '操作失败', 'error');
    } finally {
        feeState.batchAuditSubmitting = false;
        if (btn) {
            btn.disabled = false;
            btn.textContent = '确认提交';
        }
    }
}

export const pageConfig = {
    render: processFeeListTemplate,
    init: () => init(),
};
