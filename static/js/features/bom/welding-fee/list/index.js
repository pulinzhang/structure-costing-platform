/**
 * BOM 焊接费列表：HUD + 筛选 + 明细抽屉 + 编辑其它费用 + 批量审核/反审核/删除
 */

import {
    l0WeldingFeeListTemplate,
    renderL0WeldingFeeRows,
    updateL0WeldingFeeHud,
    updateL0WeldingFeeFilterCapsules,
    renderFeeDetailItems,
} from './template.js?v=24';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../page-size.js?v=3';
import { setSearchBusy } from '../../../../search-busy.js?v=1';
import { shortPartNumber } from '../../../../part-identity.js?v=3';

const API_BASE = '/api/bom/welding-fees';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目、版本';
const FEE_DIGITS = 4;

const feeState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    summary: {},
    onlyPartial: false,
    advancedOpen: false,
    batchAuditMode: null,
    batchAuditSubmitting: false,
    isLoading: false,
    canUpdate: false,
    editingSystemFee: null,
    viewingFee: null,
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
        selectId: 'l0wfPageSize',
        buttonsId: 'l0wfPagination',
        getSize: () => feeState.pageSize,
        setSize: (size) => {
            feeState.pageSize = size;
        },
        onPage: (page) => loadData(page),
    });
    applyPermissionUi();
    fillAuditStatusOptions();
    fillLevelOptions();
    applyHashFilters();
    loadFilterOptions().then(() => {
        updateCapsules();
        loadData(1);
    });
}

function destroy() {
    closeDrawer('l0wfViewDrawer', 'l0wfViewBackdrop');
    closeDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
    closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    feeState.canUpdate = canFn('op:bom-welding-fee-list:update');
    if (!canFn('op:bom-welding-fee-list:export')) {
        document.getElementById('l0wfExportBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-welding-fee-list:approve')) {
        document.getElementById('l0wfBatchApproveBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-welding-fee-list:reverse')) {
        document.getElementById('l0wfBatchReverseBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-welding-fee-list:delete')) {
        document.getElementById('l0wfBatchDeleteBtn')?.classList.add('hidden');
    }
}

function fillLevelOptions() {
    const el = document.getElementById('l0wfLevelFilter');
    if (!el) return;
    el.innerHTML = `
        <option value="">全部</option>
        <option value="0,1">L0 + L1</option>
        <option value="0">L0</option>
        <option value="1">L1</option>
        <option value="2">L2</option>
    `;
    el.value = '0,1';
}

function fillAuditStatusOptions() {
    const el = document.getElementById('l0wfAuditStatusFilter');
    if (!el) return;
    el.innerHTML = `
        <option value="">全部</option>
        <option value="pending">待审</option>
        <option value="approved">已通过</option>
    `;
}

function applyHashFilters() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return;
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    ['year', 'location', 'vehicle_model', 'bom_version', 'level', 'levels'].forEach((key) => {
        const value = qs.get(key);
        if (!value) return;
        const idMap = {
            year: 'l0wfYearFilter',
            location: 'l0wfLocationFilter',
            vehicle_model: 'l0wfVehicleModelFilter',
            bom_version: 'l0wfBomVersionFilter',
            level: 'l0wfLevelFilter',
            levels: 'l0wfLevelFilter',
        };
        const el = document.getElementById(idMap[key]);
        if (!el) return;
        if (key === 'level' || key === 'levels') {
            el.value = value;
            return;
        }
        el.dataset.pending = value;
    });
    if (qs.get('year') || qs.get('location')) setAdvancedOpen(true);
}

function setAdvancedOpen(isOpen) {
    feeState.advancedOpen = isOpen;
    document.getElementById('l0wfAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('l0wfAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选' : '展开高级筛选';
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function parseLevelFilter(raw) {
    const text = String(raw || '').trim();
    if (!text) return { level: null, levels: null };
    if (text.includes(',')) {
        const levels = text.split(',').map(Number).filter((n) => Number.isInteger(n) && n >= 0);
        return { level: null, levels: levels.length ? levels : null };
    }
    const level = Number(text);
    if (!Number.isInteger(level) || level < 0) return { level: null, levels: null };
    return { level, levels: null };
}

function applyLevelQuery(target, f) {
    if (Array.isArray(f.levels) && f.levels.length) {
        target.levels = f.levels.join(',');
        return;
    }
    if (f.level === 0 || f.level) target.level = f.level;
}

function applyLevelBody(target, f) {
    if (Array.isArray(f.levels) && f.levels.length) {
        target.levels = f.levels;
        return;
    }
    if (f.level === 0 || f.level) target.level = f.level;
}

function getFilters() {
    const yearRaw = val('l0wfYearFilter');
    const levelParsed = parseLevelFilter(val('l0wfLevelFilter'));
    return {
        year: yearRaw ? Number(yearRaw) : null,
        location: val('l0wfLocationFilter') || null,
        vehicle_model: val('l0wfVehicleModelFilter') || null,
        bom_version: val('l0wfBomVersionFilter') || null,
        level: levelParsed.level,
        levels: levelParsed.levels,
        audit_status: val('l0wfAuditStatusFilter') || null,
        part_number: val('l0wfPartNumberFilter') || null,
        onlyPartial: feeState.onlyPartial,
    };
}

function updateCapsules() {
    updateL0WeldingFeeFilterCapsules(getFilters());
}

function fillSelect(id, values = [], preferred = null, formatLabel = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const pending = select.dataset.pending || null;
    const current = preferred ?? pending ?? select.value;
    delete select.dataset.pending;
    select.innerHTML =
        `<option value="">全部</option>` +
        values.map((v) => {
            const text = String(v);
            const label = formatLabel ? formatLabel(v) : text;
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(String(label))}</option>`;
        }).join('');
}

async function loadFilterOptions() {
    try {
        const yearRes = await HttpClient.get(`${API_BASE}/filters/years`);
        fillSelect('l0wfYearFilter', yearRes.data || [], null, fmtYear);
        await loadLocationOptions();
        await loadVehicleModelOptions();
        await loadBomVersionOptions();
    } catch (error) {
        console.error('加载筛选失败:', error);
    }
}

async function loadLocationOptions() {
    const year = val('l0wfYearFilter');
    const params = {};
    if (year) params.year = Number(year);
    const res = await HttpClient.get(`${API_BASE}/filters/locations`, { params });
    fillSelect('l0wfLocationFilter', res.data || []);
}

async function loadVehicleModelOptions() {
    const year = val('l0wfYearFilter');
    const location = val('l0wfLocationFilter');
    const params = {};
    if (year) params.year = Number(year);
    if (location) params.location = location;
    const res = await HttpClient.get(`${API_BASE}/filters/vehicle-models`, { params });
    fillSelect('l0wfVehicleModelFilter', res.data || []);
}

async function loadBomVersionOptions() {
    const year = val('l0wfYearFilter');
    const location = val('l0wfLocationFilter');
    const vehicleModel = val('l0wfVehicleModelFilter');
    const params = {};
    if (year) params.year = Number(year);
    if (location) params.location = location;
    if (vehicleModel) params.vehicle_model = vehicleModel;
    const res = await HttpClient.get(`${API_BASE}/filters/bom-versions`, { params });
    fillSelect('l0wfBomVersionFilter', res.data || []);
}

function bindEvents() {
    document.getElementById('l0wfSearchBtn')?.addEventListener('click', () => loadData(1));
    document.getElementById('l0wfResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('l0wfToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!feeState.advancedOpen);
    });
    document.getElementById('l0wfHudPartialCard')?.addEventListener('click', () => {
        if (feeState.onlyPartial) {
            feeState.onlyPartial = false;
            loadData(1);
            return;
        }
        const partial = Number(feeState.summary?.partial_count) || 0;
        if (partial <= 0) {
            showToast('当前无缺单价待办', 'success');
            return;
        }
        feeState.onlyPartial = true;
        loadData(1);
    });

    document.getElementById('l0wfYearFilter')?.addEventListener('change', async () => {
        updateCapsules();
        await loadLocationOptions();
        await loadVehicleModelOptions();
        await loadBomVersionOptions();
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfLocationFilter')?.addEventListener('change', async () => {
        updateCapsules();
        await loadVehicleModelOptions();
        await loadBomVersionOptions();
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfVehicleModelFilter')?.addEventListener('change', async () => {
        updateCapsules();
        await loadBomVersionOptions();
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfBomVersionFilter')?.addEventListener('change', () => {
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfLevelFilter')?.addEventListener('change', () => {
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfAuditStatusFilter')?.addEventListener('change', () => {
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfPartNumberFilter')?.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfPartNumberFilter')?.addEventListener('input', updateCapsules);


    document.getElementById('l0wfTableBody')?.addEventListener('click', (event) => {
        const editBtn = event.target.closest('[data-action="edit"]');
        if (editBtn) {
            event.preventDefault();
            event.stopPropagation();
            const record = feeState.records.find((row) => Number(row.id) === Number(editBtn.dataset.id));
            if (record) openEditDrawer(record);
            return;
        }
        const detailBtn = event.target.closest('[data-action="detail"]');
        if (!detailBtn) return;
        event.preventDefault();
        event.stopPropagation();
        openDetailDrawer(Number(detailBtn.dataset.id));
    });

    document.getElementById('l0wfBatchApproveBtn')?.addEventListener('click', () => openBatchAudit('approve'));
    document.getElementById('l0wfBatchReverseBtn')?.addEventListener('click', () => openBatchAudit('reverse'));
    document.getElementById('l0wfBatchDeleteBtn')?.addEventListener('click', batchDelete);
    document.getElementById('l0wfExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('l0wfBatchAuditClose')?.addEventListener('click', () => {
        closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
    });
    document.getElementById('l0wfBatchAuditCancel')?.addEventListener('click', () => {
        closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
    });
    document.getElementById('l0wfBatchAuditBackdrop')?.addEventListener('click', () => {
        closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
    });
    document.getElementById('l0wfBatchAuditSubmit')?.addEventListener('click', submitBatchAudit);

    document.getElementById('l0wfEditClose')?.addEventListener('click', () => {
        closeDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
    });
    document.getElementById('l0wfEditCancel')?.addEventListener('click', () => {
        closeDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
    });
    document.getElementById('l0wfEditBackdrop')?.addEventListener('click', () => {
        closeDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
    });
    document.getElementById('l0wfEditSubmit')?.addEventListener('click', () => saveEdit());
    document.getElementById('l0wfEditOtherFee')?.addEventListener('input', updateFinalFeePreview);

    const closeView = () => closeDrawer('l0wfViewDrawer', 'l0wfViewBackdrop');
    document.getElementById('l0wfViewClose')?.addEventListener('click', closeView);
    document.getElementById('l0wfViewBackdrop')?.addEventListener('click', closeView);
    document.getElementById('l0wfViewEditBtn')?.addEventListener('click', () => {
        const fee = feeState.viewingFee;
        closeDrawer('l0wfViewDrawer', 'l0wfViewBackdrop');
        if (fee) openEditDrawer(fee);
    });
}

function resetFilters() {
    feeState.onlyPartial = false;
    ['l0wfYearFilter', 'l0wfLocationFilter', 'l0wfVehicleModelFilter', 'l0wfBomVersionFilter', 'l0wfAuditStatusFilter', 'l0wfPartNumberFilter']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    fillLevelOptions();
    loadFilterOptions().then(() => {
        updateCapsules();
        loadData(1);
    });
}

function requireScope() {
    const f = getFilters();
    if (!f.year || !f.location || !f.vehicle_model || !f.bom_version) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        setAdvancedOpen(true);
        return null;
    }
    const body = {
        year: f.year,
        location: f.location,
        vehicle_model: f.vehicle_model,
        bom_version: f.bom_version,
    };
    applyLevelBody(body, f);
    return body;
}

async function loadData(page = feeState.page) {
    if (feeState.isLoading) return;
    feeState.isLoading = true;
    setSearchBusy('l0wfSearchBtn', true);
    const body = document.getElementById('l0wfTableBody');
    const empty = document.getElementById('l0wfEmpty');
    if (body) {
        body.innerHTML = `<tr><td colspan="16" class="py-10 text-center text-[#555]">
            <div class="inline-block w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
        </td></tr>`;
    }
    empty?.classList.add('hidden');

    const f = getFilters();
    const params = {
        page,
        size: feeState.pageSize,
    };
    if (f.year) params.year = f.year;
    if (f.location) params.location = f.location;
    if (f.vehicle_model) params.vehicle_model = f.vehicle_model;
    if (f.bom_version) params.bom_version = f.bom_version;
    applyLevelQuery(params, f);
    if (f.audit_status) params.audit_status = f.audit_status;
    if (f.part_number) params.part_number = f.part_number;
    if (f.onlyPartial) params.calc_status = 'partial';

    try {
        const res = await HttpClient.get(API_BASE, { params });
        const data = res.data || {};
        const items = Array.isArray(data.items) ? data.items : [];
        feeState.records = items;
        feeState.total = data.total || 0;
        feeState.page = data.page || page;
        feeState.totalPages = data.total_pages || 1;
        feeState.summary = data.filters?.summary || {};
        // HUD 用筛选全量 summary，不用本页 items
        updateL0WeldingFeeHud(
            feeState.summary,
            f.bom_version || (f.vehicle_model ? f.vehicle_model : '—'),
        );
        updateCapsules();

        const totalLabel = document.getElementById('l0wfTotalLabel');
        if (totalLabel) totalLabel.textContent = `共 ${feeState.total} 条`;

        paintPagination('l0wfPagination', feeState.page, feeState.totalPages);

        if (!items.length) {
            if (body) body.innerHTML = '';
            empty?.classList.remove('hidden');
            return;
        }
        empty?.classList.add('hidden');
        if (body) body.innerHTML = renderL0WeldingFeeRows(items);
    } catch (error) {
        console.error('加载焊接费失败:', error);
        if (body) {
            body.innerHTML = `<tr><td colspan="16" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
        }
    } finally {
        feeState.isLoading = false;
        setSearchBusy('l0wfSearchBtn', false);
    }
}

async function openDetailDrawer(feeId) {
    if (!feeId) return;
    try {
        const res = await HttpClient.get(`${API_BASE}/${feeId}`);
        const fee = res.data || {};
        openViewDrawer(fee);
    } catch (error) {
        showToast(error.message || '加载明细失败', 'error');
    }
}

function fillViewField(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null || value === '' ? '—' : String(value);
}

function fillPartNumberFields(prefix, partNumber) {
    const shortEl = document.getElementById(`${prefix}-part-short`);
    const fullEl = document.getElementById(`${prefix}-part-number`);
    const full = String(partNumber || '').trim();
    const shortNo = shortPartNumber(full) || full || '—';
    if (shortEl) shortEl.textContent = shortNo;
    if (fullEl) {
        const showFull = Boolean(full) && shortNo !== full && shortNo !== '—';
        fullEl.textContent = showFull ? full : '';
        fullEl.classList.toggle('hidden', !showFull);
    }
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value).replace('T', ' ');
    return text.length >= 19 ? text.slice(0, 19) : text;
}

function auditStatusLabel(status) {
    return { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '—';
}

function calcStatusLabel(status) {
    return { ok: '正常', partial: '缺单价', failed: '失败' }[status] || status || '—';
}

function openViewDrawer(fee) {
    feeState.viewingFee = fee;
    fillViewFieldsFromRecord(fee);

    const itemsEl = document.getElementById('l0wfViewProcessItems');
    if (itemsEl) itemsEl.innerHTML = renderFeeDetailItems(fee.items || []);

    const approved = fee.audit_status === 'approved';
    const editBtn = document.getElementById('l0wfViewEditBtn');
    if (editBtn) {
        editBtn.classList.toggle('hidden', !(feeState.canUpdate && !approved));
    }
    openDrawer('l0wfViewDrawer', 'l0wfViewBackdrop');
}

function fillViewFieldsFromRecord(fee) {
    fillViewField('l0wf-view-year', fmtYear(fee.year));
    fillViewField('l0wf-view-location', fee.location);
    fillViewField('l0wf-view-vehicle', fee.vehicle_model);
    fillViewField('l0wf-view-version', fee.bom_version);
    fillPartNumberFields('l0wf-view', fee.part_number);
    fillViewField('l0wf-view-part-name', fee.part_name);
    fillViewField('l0wf-view-customer', fee.customer_name);

    fillViewField('l0wf-view-system-fee', formatDecimal(fee.total_welding_fee, FEE_DIGITS));
    fillViewField('l0wf-view-other-fee', formatDecimal(fee.other_fee, FEE_DIGITS));
    fillViewField(
        'l0wf-view-final-fee',
        formatDecimal(
            fee.final_welding_fee != null ? fee.final_welding_fee : fee.total_welding_fee,
            FEE_DIGITS,
        ),
    );
    fillViewField('l0wf-view-process-count', fee.process_line_count ?? 0);
    fillViewField(
        'l0wf-view-match-stats',
        `${fee.matched_line_count ?? 0} / ${fee.missing_price_count ?? 0}`,
    );
    fillViewField('l0wf-view-calc-status', calcStatusLabel(fee.calc_status));
    fillViewField('l0wf-view-remark', fee.remark);
    fillViewField('l0wf-view-calc-message', fee.calc_message);

    const weldEl = document.getElementById('l0wf-view-weld-info');
    if (weldEl) {
        weldEl.textContent = (fee.weld_info_raw || '').trim() || '—';
    }

    fillViewField('l0wf-view-audit-status', auditStatusLabel(fee.audit_status));
    fillViewField('l0wf-view-audited-by', fee.audited_by);
    fillViewField('l0wf-view-audited-at', formatDateTime(fee.audited_at));
    fillViewField('l0wf-view-audit-remark', fee.audit_remark);
    fillViewField('l0wf-view-reverse-by', fee.reverse_audited_by);
    fillViewField('l0wf-view-reverse-at', formatDateTime(fee.reverse_audited_at));
    fillViewField('l0wf-view-reverse-remark', fee.reverse_audit_remark);
    fillViewField('l0wf-view-created-by', fee.created_by);
    fillViewField('l0wf-view-created-at', formatDateTime(fee.created_at));
    fillViewField('l0wf-view-updated-by', fee.updated_by);
    fillViewField('l0wf-view-updated-at', formatDateTime(fee.updated_at));
}

function formatDecimal(value, digits = FEE_DIGITS) {
    if (typeof formatDecimalFixed === 'function') {
        const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
        return fixed == null ? '—' : fixed;
    }
    if (value == null || value === '') return '—';
    const num = Number(value);
    return Number.isFinite(num) ? num.toFixed(digits) : '—';
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

    feeState.editingSystemFee = record.total_welding_fee;
    fillViewField('l0wf-edit-year', fmtYear(record.year));
    fillViewField('l0wf-edit-location', record.location);
    fillViewField('l0wf-edit-vehicle', record.vehicle_model);
    fillViewField('l0wf-edit-version', record.bom_version);
    fillPartNumberFields('l0wf-edit', record.part_number);
    fillViewField('l0wf-edit-part-name', record.part_name);
    fillViewField('l0wf-edit-system-fee', formatDecimal(record.total_welding_fee, FEE_DIGITS));

    const idEl = document.getElementById('l0wfEditRecordId');
    if (idEl) idEl.value = String(record.id);
    const otherEl = document.getElementById('l0wfEditOtherFee');
    if (otherEl) {
        otherEl.value = record.other_fee == null ? '' : String(record.other_fee);
    }
    const remarkEl = document.getElementById('l0wfEditRemark');
    if (remarkEl) remarkEl.value = record.remark || '';

    updateFinalFeePreview();
    openDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
}

function updateFinalFeePreview() {
    const finalEl = document.getElementById('l0wf-edit-final-fee');
    const otherEl = document.getElementById('l0wfEditOtherFee');
    if (!finalEl) return;

    const baseText = feeState.editingSystemFee == null || feeState.editingSystemFee === ''
        ? null
        : formatDecimal(feeState.editingSystemFee, FEE_DIGITS);
    const otherRaw = String(otherEl?.value || '').trim();
    let otherText = null;
    if (otherRaw !== '') {
        otherText = parseDecimalInput(otherRaw, FEE_DIGITS, { allowNegative: true });
        if (otherText == null) {
            finalEl.textContent = '—';
            return;
        }
    }

    if (baseText == null || baseText === '—') {
        finalEl.textContent = otherText == null ? '—' : otherText;
        return;
    }
    finalEl.textContent = addFixedDecimalStrings(baseText, otherText || `0.${'0'.repeat(FEE_DIGITS)}`, FEE_DIGITS) || '—';
}

/** 固定小数位字符串相加（不经 Number，避免金额精度漂移）。 */
function addFixedDecimalStrings(left, right, digits = FEE_DIGITS) {
    const leftText = formatDecimal(left, digits);
    const rightText = formatDecimal(right, digits);
    if (leftText == null || leftText === '—' || rightText == null || rightText === '—') return null;
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
    const feeId = Number(document.getElementById('l0wfEditRecordId')?.value);
    if (!Number.isFinite(feeId)) return;

    const otherRaw = String(document.getElementById('l0wfEditOtherFee')?.value || '').trim();
    let otherFee = null;
    if (otherRaw !== '') {
        const parsed = parseDecimalInput(otherRaw, FEE_DIGITS, { allowNegative: true });
        if (parsed == null) {
            showToast('其它费用须为有效数字（可正可负）', 'warning');
            return;
        }
        otherFee = parsed;
    }

    const remark = String(document.getElementById('l0wfEditRemark')?.value || '').trim() || null;

    try {
        const res = await HttpClient.patch(`${API_BASE}/${feeId}`, {
            other_fee: otherFee,
            remark,
        });
        showToast(res.message || '保存成功', 'success');
        closeDrawer('l0wfEditDrawer', 'l0wfEditBackdrop');
        await loadData(feeState.page);
    } catch (error) {
        showToast(error.message || '保存失败', 'error');
    }
}

function openBatchAudit(mode) {
    const scope = requireScope();
    if (!scope) return;
    feeState.batchAuditMode = mode;
    const isReverse = mode === 'reverse';
    const title = document.getElementById('l0wfBatchAuditTitle');
    const label = document.getElementById('l0wfBatchAuditRemarkLabel');
    const remark = document.getElementById('l0wfBatchAuditRemark');
    const scopeEl = document.getElementById('l0wfBatchAuditScope');
    if (title) title.textContent = isReverse ? '批量反审核' : '批量审核';
    if (label) label.textContent = isReverse ? '反审核原因（必填）' : '审核意见（必填）';
    if (remark) {
        remark.value = '';
        remark.placeholder = isReverse ? '请填写反审核原因' : '请填写审核意见';
    }
    if (scopeEl) {
        scopeEl.textContent = `${fmtYear(scope.year)} · ${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}`;
    }
    openDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
}

async function submitBatchAudit() {
    if (feeState.batchAuditSubmitting) return;
    const scope = requireScope();
    if (!scope) return;
    const mode = feeState.batchAuditMode;
    const remark = (document.getElementById('l0wfBatchAuditRemark')?.value || '').trim();
    if (!remark) {
        showToast(mode === 'approve' ? '审核意见必填' : '反审核原因必填', 'warning');
        return;
    }

    const body = { ...scope };
    const url = mode === 'approve' ? `${API_BASE}/batch-approve` : `${API_BASE}/batch-reverse-audit`;
    if (mode === 'approve') body.audit_remark = remark;
    else body.reverse_audit_remark = remark;

    feeState.batchAuditSubmitting = true;
    try {
        const res = await HttpClient.post(url, body);
        const data = res.data || {};
        showToast(
            `${mode === 'approve' ? '审核' : '反审核'}完成：更新 ${data.updated_count ?? 0}，跳过 ${data.skipped_count ?? 0}`,
            'success',
        );
        closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
        loadData(feeState.page);
    } catch (error) {
        showToast(error.message || '操作失败', 'error');
    } finally {
        feeState.batchAuditSubmitting = false;
    }
}

async function batchDelete() {
    const scope = requireScope();
    if (!scope) return;
    if (!window.confirm(`确定删除未审核的焊接费？\n${fmtYear(scope.year)} · ${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}\n已审核记录将跳过。`)) {
        return;
    }
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        const data = res.data || {};
        showToast(`删除完成：删除 ${data.deleted_count ?? 0}，跳过 ${data.skipped_approved_count ?? 0}`, 'success');
        loadData(1);
    } catch (error) {
        showToast(error.message || '删除失败', 'error');
    }
}

async function exportExcel() {
    if (typeof can === 'function' && !can('op:bom-welding-fee-list:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const f = getFilters();
    const params = {};
    if (f.year) params.year = f.year;
    if (f.location) params.location = f.location;
    if (f.vehicle_model) params.vehicle_model = f.vehicle_model;
    if (f.bom_version) params.bom_version = f.bom_version;
    applyLevelQuery(params, f);
    if (f.audit_status) params.audit_status = f.audit_status;
    if (f.part_number) params.part_number = f.part_number;
    if (f.onlyPartial) params.calc_status = 'partial';

    if (!Object.keys(params).length) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        setAdvancedOpen(true);
        return;
    }

    const btn = document.getElementById('l0wfExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params,
            defaultFilename: '焊接费导出.xlsx',
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

export const pageConfig = {
    render: l0WeldingFeeListTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
