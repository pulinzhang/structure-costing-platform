/**
 * 冲压模具费列表页
 * 对齐冲压加工费列表：HUD + 胶囊筛选 + 查看/编辑抽屉 + 批量审核/反审核/删除 + Excel 导出
 */

import {
    dieFeeListTemplate,
    renderDieFeeRows,
    updateDieFeeHud,
    updateDieFeeFilterCapsules,
} from './template.js?v=17';
import { bindMoreMenu } from '../../../../more-menu.js?v=1';
import { shortPartNumber } from '../../../../part-identity.js?v=3';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../page-size.js?v=3';
import { setSearchBusy } from '../../../../search-busy.js?v=1';

const API_BASE = '/api/stamping/die-fees';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;

const feeState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    canUpdate: true,
    advancedOpen: false,
    onlyZero: false,
    zeroCount: 0,
    batchAuditSubmitting: false,
    isLoading: false,
    viewingId: null,
    editingDieFee: null,
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
    bindPagination({
        selectId: 'dieFeePageSize',
        buttonsId: 'dieFeePagination',
        getSize: () => feeState.pageSize,
        setSize: (size) => {
            feeState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    applyPermissionUi();
    applyHashFilters();
    fillAuditStatusOptions();
    loadFilterOptions().then(() => {
        updateDieFeeFilterCapsules();
        loadData(1);
    });
}

function applyPermissionUi() {
    feeState.canUpdate = typeof can === 'function' ? can('op:stamping-die-fee:update') : true;
    const canDelete = typeof can === 'function' ? can('op:stamping-die-fee:delete') : true;
    const canApprove = typeof can === 'function' ? can('op:stamping-die-fee:approve') : true;
    const canReverse = typeof can === 'function' ? can('op:stamping-die-fee:reverse') : true;
    const canExport = typeof can === 'function' ? can('op:stamping-die-fee:export') : true;
    if (!canDelete) document.getElementById('dieFeeBatchDeleteBtn')?.classList.add('hidden');
    if (!canApprove) document.getElementById('dieFeeBatchApproveBtn')?.classList.add('hidden');
    if (!canReverse) document.getElementById('dieFeeBatchReverseBtn')?.classList.add('hidden');
    if (!canExport) document.getElementById('dieFeeExportBtn')?.classList.add('hidden');
    const moreItems = ['dieFeeBatchApproveBtn', 'dieFeeBatchReverseBtn', 'dieFeeBatchDeleteBtn']
        .map((id) => document.getElementById(id))
        .filter((el) => el && !el.classList.contains('hidden'));
    if (!moreItems.length) {
        document.getElementById('dieFeeMoreWrap')?.classList.add('hidden');
    }
}

function applyHashFilters() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return;
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    const year = qs.get('year') || '';
    const location = qs.get('location') || '';
    const vehicle = qs.get('vehicle_model') || '';
    const supplier = qs.get('stamping_supplier') || '';
    const version = qs.get('version') || '';
    if (year) {
        const yearEl = document.getElementById('dieFeeYearFilter');
        if (yearEl) yearEl.dataset.pending = year;
    }
    if (location) {
        const locEl = document.getElementById('dieFeeLocationFilter');
        if (locEl) locEl.dataset.pending = location;
    }
    if (vehicle) {
        const vehicleEl = document.getElementById('dieFeeVehicleFilter');
        if (vehicleEl) vehicleEl.dataset.pending = vehicle;
    }
    if (supplier) {
        const supplierEl = document.getElementById('dieFeeSupplierFilter');
        if (supplierEl) supplierEl.dataset.pending = supplier;
    }
    if (version) {
        const versionEl = document.getElementById('dieFeeVersionFilter');
        if (versionEl) versionEl.dataset.pending = version;
    }
    if (year || location || vehicle || supplier || version) {
        setAdvancedOpen(true);
    }
}

function fillAuditStatusOptions() {
    const el = document.getElementById('dieFeeAuditStatusFilter');
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
    document.getElementById('dieFeeAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('dieFeeAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function bindEvents() {
    document.getElementById('dieFeeSearchBtn')?.addEventListener('click', () => loadData(1));
    document.getElementById('dieFeeResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('dieFeeToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!feeState.advancedOpen);
    });
    document.getElementById('dieFeeHudZeroCard')?.addEventListener('click', () => {
        if (feeState.onlyZero) {
            feeState.onlyZero = false;
            loadData(1);
            return;
        }
        if (feeState.zeroCount <= 0) {
            showToast('当前无最终为零的行', 'success');
            return;
        }
        feeState.onlyZero = true;
        loadData(1);
    });
    document.getElementById('dieFeeExportBtn')?.addEventListener('click', () => exportExcel());
    moreMenu = bindMoreMenu({
        wrapId: 'dieFeeMoreWrap',
        btnId: 'dieFeeMoreBtn',
        menuId: 'dieFeeMoreMenu',
    });
    document.getElementById('dieFeeBatchDeleteBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        batchDelete();
    });
    document.getElementById('dieFeeBatchApproveBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('approve');
    });
    document.getElementById('dieFeeBatchReverseBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('reverse');
    });

    document.getElementById('dieFeeYearFilter')?.addEventListener('change', () => {
        loadIdentityOptions().then(() => {
            updateDieFeeFilterCapsules();
            loadData(1);
        });
    });
    document.getElementById('dieFeeLocationFilter')?.addEventListener('change', () => {
        loadVehicleOptions().then(() => loadIdentityOptions().then(() => {
            updateDieFeeFilterCapsules();
            loadData(1);
        }));
    });
    document.getElementById('dieFeeVehicleFilter')?.addEventListener('change', () => {
        loadIdentityOptions().then(() => {
            updateDieFeeFilterCapsules();
            loadData(1);
        });
    });
    document.getElementById('dieFeeSupplierFilter')?.addEventListener('change', () => {
        loadVersionOptions().then(() => {
            updateDieFeeFilterCapsules();
            loadData(1);
        });
    });
    document.getElementById('dieFeeVersionFilter')?.addEventListener('change', () => {
        updateDieFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('dieFeeAuditStatusFilter')?.addEventListener('change', () => {
        updateDieFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('dieFeePartNumberFilter')?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        updateDieFeeFilterCapsules();
        loadData(1);
    });
    document.getElementById('dieFeePartNumberFilter')?.addEventListener('input', () => {
        updateDieFeeFilterCapsules();
    });


    bindEditDrawerEvents();
    bindViewDrawerEvents();
    bindBatchAuditDrawerEvents();
}

function bindRowEvents() {
    document.querySelectorAll('#dieFeeTableBody .view-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const row = btn.closest('tr');
            const id = Number(row?.dataset.id);
            const record = feeState.records.find((item) => item.id === id);
            if (record) openViewDrawer(record);
        });
    });
    document.querySelectorAll('#dieFeeTableBody .edit-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const row = btn.closest('tr');
            const id = Number(row?.dataset.id);
            const record = feeState.records.find((item) => item.id === id);
            if (record) openEditDrawer(record);
        });
    });
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('dieFeeEditDrawer', 'dieFeeEditDrawerBackdrop');
    document.getElementById('closeDieFeeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelDieFeeEditBtn')?.addEventListener('click', close);
    document.getElementById('dieFeeEditDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitDieFeeEditBtn')?.addEventListener('click', () => saveEdit());
    document.getElementById('dieFeeEditAdjustment')?.addEventListener('input', updateFinalFeePreview);
}

function bindViewDrawerEvents() {
    const close = () => closeDrawer('dieFeeViewDrawer', 'dieFeeViewDrawerBackdrop');
    document.getElementById('closeDieFeeViewDrawer')?.addEventListener('click', close);
    document.getElementById('dieFeeViewDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('dieFeeViewDrawerEditBtn')?.addEventListener('click', () => {
        const record = feeState.records.find((item) => item.id === feeState.viewingId);
        if (!record) return;
        closeDrawer('dieFeeViewDrawer', 'dieFeeViewDrawerBackdrop');
        openEditDrawer(record);
    });
}

function bindBatchAuditDrawerEvents() {
    document.getElementById('closeDieFeeBatchAuditDrawer')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('cancelDieFeeBatchAuditBtn')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('dieFeeBatchAuditDrawerBackdrop')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('confirmDieFeeBatchAuditBtn')?.addEventListener('click', submitBatchAudit);
}

async function loadFilterOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters`);
        const data = res.data || {};
        fillSelect('dieFeeYearFilter', data.years || [], fmtYear);
        fillSelect('dieFeeLocationFilter', data.locations || []);
        await loadVehicleOptions();
        await loadIdentityOptions();
    } catch (error) {
        showToast(error.message || '加载筛选失败', 'error');
    }
}

async function loadVehicleOptions() {
    const location = document.getElementById('dieFeeLocationFilter')?.value || '';
    try {
        const res = await HttpClient.get(`${API_BASE}/filters`, {
            params: location ? { location } : {},
        });
        const models = res.data?.vehicle_models || [];
        fillSelect('dieFeeVehicleFilter', models);
    } catch (error) {
        showToast(error.message || '加载项目失败', 'error');
    }
}

async function loadIdentityOptions() {
    const year = document.getElementById('dieFeeYearFilter')?.value || '';
    const location = document.getElementById('dieFeeLocationFilter')?.value || '';
    const vehicle = document.getElementById('dieFeeVehicleFilter')?.value || '';
    if (!year || !location || !vehicle) {
        fillSelect('dieFeeSupplierFilter', []);
        fillSelect('dieFeeVersionFilter', []);
        return;
    }
    try {
        const supplierEl = document.getElementById('dieFeeSupplierFilter');
        const supplier = supplierEl?.dataset.pending || supplierEl?.value || '';
        const res = await HttpClient.get(`${API_BASE}/filters`, {
            params: {
                year,
                location,
                vehicle_model: vehicle,
                stamping_supplier: supplier || undefined,
            },
        });
        fillSelect('dieFeeSupplierFilter', res.data?.stamping_suppliers || []);
        fillSelect('dieFeeVersionFilter', res.data?.versions || []);
    } catch (error) {
        showToast(error.message || '加载供应商/版本失败', 'error');
    }
}

async function loadVersionOptions() {
    const versionEl = document.getElementById('dieFeeVersionFilter');
    if (versionEl) {
        versionEl.value = '';
        delete versionEl.dataset.pending;
    }
    await loadIdentityOptions();
}

function fillSelect(id, values, formatLabel) {
    const select = document.getElementById(id);
    if (!select) return;
    const pending = select.dataset.pending || select.value || '';
    let html = '<option value="">全部</option>';
    (values || []).forEach((value) => {
        const text = String(value);
        const selected = text === String(pending) ? ' selected' : '';
        const label = formatLabel ? formatLabel(value) : text;
        html += `<option value="${esc(text)}"${selected}>${esc(String(label))}</option>`;
    });
    select.innerHTML = html;
    delete select.dataset.pending;
}

function resetFilters() {
    ['dieFeeYearFilter', 'dieFeeLocationFilter', 'dieFeeVehicleFilter', 'dieFeeSupplierFilter', 'dieFeeVersionFilter', 'dieFeeAuditStatusFilter'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const partEl = document.getElementById('dieFeePartNumberFilter');
    if (partEl) partEl.value = '';
    feeState.onlyZero = false;
    loadFilterOptions().then(() => {
        updateDieFeeFilterCapsules();
        loadData(1);
    });
}

function collectScopeFilters() {
    return {
        year: document.getElementById('dieFeeYearFilter')?.value || '',
        location: document.getElementById('dieFeeLocationFilter')?.value || '',
        vehicle_model: document.getElementById('dieFeeVehicleFilter')?.value || '',
    };
}

function collectListFilters() {
    return {
        ...collectScopeFilters(),
        stamping_supplier: document.getElementById('dieFeeSupplierFilter')?.value || '',
        version: document.getElementById('dieFeeVersionFilter')?.value || '',
        audit_status: document.getElementById('dieFeeAuditStatusFilter')?.value || '',
        part_number: (document.getElementById('dieFeePartNumberFilter')?.value || '').trim(),
        only_zero: feeState.onlyZero,
    };
}

function hasScope(scope) {
    const year = Number(scope.year);
    return year >= 2000 && Boolean(scope.location) && Boolean(scope.vehicle_model);
}

function scopeLabel(scope) {
    const bits = [];
    if (scope.year) bits.push(String(scope.year));
    if (scope.location) bits.push(scope.location);
    if (scope.vehicle_model) bits.push(scope.vehicle_model);
    if (scope.stamping_supplier) bits.push(scope.stamping_supplier);
    if (scope.version) bits.push(scope.version);
    return bits.length ? bits.join(' · ') : '全部';
}

function showEmpty(message) {
    const empty = document.getElementById('dieFeeEmpty');
    const hint = document.getElementById('dieFeeEmptyHint');
    if (hint && message) hint.textContent = message;
    empty?.classList.remove('hidden');
}

async function loadData(page = 1) {
    if (feeState.isLoading) return;
    const loading = document.getElementById('dieFeeLoading');
    const empty = document.getElementById('dieFeeEmpty');
    const body = document.getElementById('dieFeeTableBody');
    if (body) body.innerHTML = '';
    empty?.classList.add('hidden');
    updateDieFeeFilterCapsules();

    const filters = collectListFilters();

    feeState.isLoading = true;
    setSearchBusy('dieFeeSearchBtn', true);
    loading?.classList.remove('hidden');

    try {
        const params = {
            page,
            size: feeState.pageSize,
            year: filters.year ? Number(filters.year) : undefined,
            location: filters.location || undefined,
            vehicle_model: filters.vehicle_model || undefined,
            stamping_supplier: filters.stamping_supplier || undefined,
            version: filters.version || undefined,
            part_number: filters.part_number || undefined,
            audit_status: filters.audit_status || undefined,
            only_zero: filters.only_zero || undefined,
        };
        const res = await HttpClient.get(API_BASE, { params });
        const data = res.data || {};
        feeState.records = Array.isArray(data.items) ? data.items : [];
        feeState.total = data.total || 0;
        feeState.page = data.page || page;
        feeState.pageSize = data.page_size || feeState.pageSize;
        feeState.totalPages = data.total_pages || Math.ceil(feeState.total / feeState.pageSize) || 1;

        const totalLabel = document.getElementById('dieFeeTotalLabel');
        if (totalLabel) {
            totalLabel.textContent = feeState.onlyZero
                ? `零价 ${feeState.total} 条`
                : `共 ${feeState.total} 条`;
        }
        const summary = data.filters || null;
        updateDieFeeHud(feeState.total, summary, feeState.onlyZero, scopeLabel(filters));
        feeState.zeroCount = Number(summary?.zero_count ?? 0);

        if (!feeState.records.length) {
            showEmpty('当前筛选下暂无模具费数据；可到「冲压模具费计算」手算，或由自动核价引擎补算');
        } else if (body) {
            body.innerHTML = renderDieFeeRows(feeState.records);
            bindRowEvents();
        }

        paintPagination('dieFeePagination', feeState.page, feeState.totalPages);
    } catch (error) {
        showToast(error.message || '加载失败');
        showEmpty('加载失败，请稍后重试');
        updateDieFeeHud(0, null, feeState.onlyZero, scopeLabel(filters));
    } finally {
        feeState.isLoading = false;
        setSearchBusy('dieFeeSearchBtn', false);
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

function formatDecimal(value, digits = 4) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    return fixed == null ? '—' : withThousandsSep(fixed);
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value).replace('T', ' ');
    return text.length >= 19 ? text.slice(0, 19) : text;
}

function auditStatusLabel(status) {
    return { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '—';
}

function priceKindLabel(kind) {
    return kind === 'progressive' ? '级进模' : '钢板模';
}

function openViewDrawer(record) {
    feeState.viewingId = record.id;
    fillViewFieldsFromRecord(record);
    renderProcessItems(record.items || []);

    const approved = record.audit_status === 'approved';
    const editBtn = document.getElementById('dieFeeViewDrawerEditBtn');
    if (editBtn) {
        editBtn.classList.toggle('hidden', !(feeState.canUpdate && !approved));
    }
    openDrawer('dieFeeViewDrawer', 'dieFeeViewDrawerBackdrop');
    loadFeeDetail(record.id);
}

function fillViewFieldsFromRecord(record) {
    fillViewField('die-fee-view-year', fmtYear(record.year));
    fillViewField('die-fee-view-location', record.location);
    fillViewField('die-fee-view-vehicle', record.vehicle_model);
    fillViewField('die-fee-view-supplier', record.stamping_supplier);
    fillViewField('die-fee-view-version', record.version);
    fillPartNumberFields('die-fee-view', record.part_number);
    fillViewField('die-fee-view-part-name', record.part_name);
    fillViewField('die-fee-view-seq-no', record.seq_no);
    fillViewField('die-fee-view-production-mode', record.production_mode);
    fillViewField('die-fee-view-price-kind', priceKindLabel(record.price_kind));
    fillViewField('die-fee-view-material', record.material);
    fillViewField('die-fee-view-thickness', formatDecimal(record.thickness, 4));
    fillViewField('die-fee-view-part-weight', formatDecimal(record.part_weight, 4));
    fillViewField('die-fee-view-die-type', record.die_type);
    fillViewField('die-fee-view-die-method', record.die_method);
    fillViewField('die-fee-view-excel-filename', record.excel_filename);
    fillViewField('die-fee-view-die-fee', formatDecimal(record.die_fee, 4));
    fillViewField('die-fee-view-adjustment', formatDecimal(record.adjustment_amount, 4));
    fillViewField('die-fee-view-final-fee', formatDecimal(record.final_die_fee, 4));
    fillViewField('die-fee-view-unit-price', formatDecimal(record.unit_price, 4));
    fillViewField('die-fee-view-allocation-qty', formatDecimal(record.allocation_qty, 0));
    fillViewField('die-fee-view-remark', record.remark);
    fillViewField('die-fee-view-audit-status', auditStatusLabel(record.audit_status));
    fillViewField('die-fee-view-audited-by', record.audited_by);
    fillViewField('die-fee-view-audited-at', formatDateTime(record.audited_at));
    fillViewField('die-fee-view-audit-remark', record.audit_remark);
    fillViewField('die-fee-view-reverse-by', record.reverse_audited_by);
    fillViewField('die-fee-view-reverse-at', formatDateTime(record.reverse_audited_at));
    fillViewField('die-fee-view-reverse-remark', record.reverse_audit_remark);
    fillViewField('die-fee-view-created-by', record.created_by);
    fillViewField('die-fee-view-created-at', formatDateTime(record.created_at));
    fillViewField('die-fee-view-updated-by', record.updated_by);
    fillViewField('die-fee-view-updated-at', formatDateTime(record.updated_at));
}

async function loadFeeDetail(feeId) {
    const container = document.getElementById('dieFeeViewProcessItems');
    if (container) {
        container.innerHTML = '<div class="px-4 py-6 text-[11px] text-[#616161]">加载中..</div>';
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/${feeId}`);
        const detail = res?.data || res;
        if (!detail || feeState.viewingId !== feeId) return;
        fillViewFieldsFromRecord(detail);
        renderProcessItems(detail.items || []);
    } catch (error) {
        if (container && feeState.viewingId === feeId) {
            container.innerHTML = `<div class="px-4 py-6 text-[11px] text-[#ef5350]">${esc(error.message || '加载溯源失败')}</div>`;
        }
    }
}

function renderProcessItems(items) {
    const container = document.getElementById('dieFeeViewProcessItems');
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = '<div class="px-4 py-6 text-[11px] text-[#616161]">暂无各序溯源</div>';
        return;
    }
    const rows = items.map((item) => `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors">
                <td class="px-3 py-2 text-[11px] font-mono text-[#9e9e9e] whitespace-nowrap">${esc(item.process_seq || '—')}</td>
                <td class="px-3 py-2 text-[11px] text-[#cccccc] whitespace-nowrap">${esc(item.process_code || '—')}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${formatDecimal(item.estimated_weight_t, 4)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${formatDecimal(item.alloc_ratio, 2)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">${formatDecimal(item.unit_price, 4)}</td>
                <td class="px-3 py-2 text-[11px] text-right font-mono tabular-nums text-[#ffffff]">${formatDecimal(item.line_die_fee, 4)}</td>
                <td class="px-3 py-2 text-[11px] text-[#888888] min-w-[180px]">${esc(item.basis_text || '—')}</td>
            </tr>`).join('');
    container.innerHTML = `
        <table class="w-full">
            <thead>
                <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">工序</th>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">代码</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">预估重量(T)</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">分摊比例</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">单价</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161]">本序模具费</th>
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
    feeState.editingDieFee = record.die_fee;
    fillViewField('die-fee-edit-year', fmtYear(record.year));
    fillViewField('die-fee-edit-location', record.location);
    fillPartNumberFields('die-fee-edit', record.part_number);
    fillViewField('die-fee-edit-vehicle', record.vehicle_model);
    fillViewField('die-fee-edit-supplier', record.stamping_supplier);
    fillViewField('die-fee-edit-version', record.version);
    fillViewField('die-fee-edit-production-mode', record.production_mode);
    fillViewField('die-fee-edit-price-kind', priceKindLabel(record.price_kind));
    fillViewField('die-fee-edit-die-fee', formatDecimal(record.die_fee, 4));

    const idEl = document.getElementById('dieFeeEditRecordId');
    if (idEl) idEl.value = String(record.id);
    const adjEl = document.getElementById('dieFeeEditAdjustment');
    if (adjEl) {
        adjEl.value = record.adjustment_amount == null ? '' : String(record.adjustment_amount);
    }
    const remarkEl = document.getElementById('dieFeeEditRemark');
    if (remarkEl) remarkEl.value = record.remark || '';
    updateFinalFeePreview();

    openDrawer('dieFeeEditDrawer', 'dieFeeEditDrawerBackdrop');
}

function updateFinalFeePreview() {
    const finalEl = document.getElementById('die-fee-edit-final-fee');
    const adjEl = document.getElementById('dieFeeEditAdjustment');
    if (!finalEl) return;

    const baseText = feeState.editingDieFee == null || feeState.editingDieFee === ''
        ? null
        : formatDecimalFixed(feeState.editingDieFee, 4, { allowNegative: true });
    const adjRaw = String(adjEl?.value || '').trim();
    let adjText = null;
    if (adjRaw !== '') {
        adjText = parseDecimalInput(adjRaw, 4, { allowNegative: true });
        if (adjText == null) {
            finalEl.textContent = '—';
            return;
        }
    }

    if (baseText == null) {
        finalEl.textContent = adjText == null ? '—' : withThousandsSep(adjText);
        return;
    }
    const summed = addFixedDecimalStrings(baseText, adjText || '0.0000', 4);
    finalEl.textContent = summed ? withThousandsSep(summed) : '—';
}

function addFixedDecimalStrings(left, right, digits = 4) {
    const leftText = formatDecimalFixed(left, digits, { allowNegative: true });
    const rightText = formatDecimalFixed(right, digits, { allowNegative: true });
    if (leftText == null || rightText == null) return null;
    const toScaled = (text) => {
        const negative = text.startsWith('-');
        const body = negative ? text.slice(1) : text;
        const [intPart, frac = ''] = body.split('.');
        const padded = `${frac}${'0'.repeat(digits)}`.slice(0, digits);
        const scaled = BigInt(`${intPart || '0'}${padded}`);
        return negative ? -scaled : scaled;
    };
    const sum = toScaled(leftText) + toScaled(rightText);
    const negative = sum < 0n;
    const abs = negative ? -sum : sum;
    const raw = abs.toString().padStart(digits + 1, '0');
    const intPart = raw.slice(0, -digits) || '0';
    const frac = raw.slice(-digits);
    return `${negative ? '-' : ''}${intPart}.${frac}`;
}

async function saveEdit() {
    const feeId = Number(document.getElementById('dieFeeEditRecordId')?.value);
    if (!Number.isFinite(feeId)) return;

    const adjRaw = String(document.getElementById('dieFeeEditAdjustment')?.value || '').trim();
    let adjustmentAmount = null;
    if (adjRaw !== '') {
        const parsed = parseDecimalInput(adjRaw, 4, { allowNegative: true });
        if (parsed == null) {
            showToast('调整金额须为有效数字（可正可负）', 'warning');
            return;
        }
        adjustmentAmount = parsed;
    }

    const remark = String(document.getElementById('dieFeeEditRemark')?.value || '').trim() || null;

    try {
        const res = await HttpClient.put(`${API_BASE}/${feeId}`, {
            adjustment_amount: adjustmentAmount,
            remark,
        });
        showToast(res.message || '保存成功', 'success');
        closeDrawer('dieFeeEditDrawer', 'dieFeeEditDrawerBackdrop');
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
        && !filters.vehicle_model
        && !filters.stamping_supplier
        && !filters.version
        && !filters.audit_status
        && !filters.part_number
        && !filters.only_zero
    ) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        return;
    }

    const btn = document.getElementById('dieFeeExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            导出中..
        `;
    }

    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: {
                year: filters.year ? Number(filters.year) : undefined,
                location: filters.location || undefined,
                vehicle_model: filters.vehicle_model || undefined,
                stamping_supplier: filters.stamping_supplier || undefined,
                version: filters.version || undefined,
                audit_status: filters.audit_status || undefined,
                part_number: filters.part_number || undefined,
                only_zero: filters.only_zero || undefined,
            },
            defaultFilename: '冲压模具费导出.xlsx',
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
    if (!hasScope(filters)) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (!window.confirm(
        `确定批量删除未审核记录吗？\n\n${fmtYear(filters.year)} · 基地 ${filters.location} · 项目 ${filters.vehicle_model}\n\n仅删除待审/已驳回；已审核通过会跳过。此操作不可恢复！`,
    )) {
        return;
    }

    const btn = document.getElementById('dieFeeBatchDeleteBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中..
        `;
    }

    try {
        const res = await HttpClient.delete(`${API_BASE}/scope`, {
            params: {
                year: Number(filters.year),
                location: filters.location,
                vehicle_model: filters.vehicle_model,
            },
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
    if (!hasScope(filters)) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }

    const isApprove = mode === 'approve';
    const modeEl = document.getElementById('dieFeeBatchAuditMode');
    const titleEl = document.getElementById('dieFeeBatchAuditDrawerTitle');
    const hintEl = document.getElementById('dieFeeBatchAuditHint');
    const operatorLabel = document.getElementById('dieFeeBatchAuditOperatorLabel');
    const remarkLabel = document.getElementById('dieFeeBatchAuditRemarkLabel');
    const operatorDisplay = document.getElementById('dieFeeBatchAuditOperatorDisplay');
    const remarkEl = document.getElementById('dieFeeBatchAuditRemark');
    const summaryEl = document.getElementById('dieFeeBatchAuditFilterSummary');

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
            ? '审核意见<span class="text-[#d32f2f]">*</span>'
            : '反审核意见<span class="text-[#d32f2f]">*</span>';
    }
    if (remarkEl) {
        remarkEl.value = '';
        remarkEl.placeholder = isApprove ? '请填写审核意见（必填）' : '必填反审核原因';
    }
    if (summaryEl) {
        summaryEl.textContent = `${fmtYear(filters.year)} · 基地 ${filters.location} · 项目 ${filters.vehicle_model}`;
    }
    openDrawer('dieFeeBatchAuditDrawer', 'dieFeeBatchAuditDrawerBackdrop');
}

function closeBatchAuditDrawer() {
    if (feeState.batchAuditSubmitting) return;
    closeDrawer('dieFeeBatchAuditDrawer', 'dieFeeBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (feeState.batchAuditSubmitting) return;
    const mode = document.getElementById('dieFeeBatchAuditMode')?.value || 'approve';
    const filters = collectScopeFilters();
    const remark = document.getElementById('dieFeeBatchAuditRemark')?.value.trim() || '';
    if (!remark) {
        showToast(mode === 'approve' ? '审核意见必填' : '反审核意见必填', 'warning');
        return;
    }

    const body = {
        year: Number(filters.year),
        location: filters.location,
        vehicle_model: filters.vehicle_model,
    };
    const url = mode === 'approve'
        ? `${API_BASE}/batch-approve`
        : `${API_BASE}/batch-reverse-audit`;
    if (mode === 'approve') {
        body.audit_remark = remark;
    } else {
        body.reverse_audit_remark = remark;
    }

    const btn = document.getElementById('confirmDieFeeBatchAuditBtn');
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
        closeDrawer('dieFeeBatchAuditDrawer', 'dieFeeBatchAuditDrawerBackdrop');
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

function destroy() {
    moreMenu?.unbind();
    moreMenu = null;
    closeDrawer('dieFeeViewDrawer', 'dieFeeViewDrawerBackdrop');
    closeDrawer('dieFeeEditDrawer', 'dieFeeEditDrawerBackdrop');
    closeDrawer('dieFeeBatchAuditDrawer', 'dieFeeBatchAuditDrawerBackdrop');
}

export const pageConfig = {
    render: dieFeeListTemplate,
    init,
    destroy,
};
