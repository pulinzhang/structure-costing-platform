/**
 * 采购对象清单列表
 */

import {
    procurementObjectListTemplate,
    renderPoPagination,
    renderProcurementObjectRows,
} from './template.js?v=12';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';
import { setSearchBusy } from '../../../../search-busy.js?v=1';
import { AUDIT_LABELS, CONFIRM_LABELS, KIND_LABELS, SECTION_LABELS } from '../labels.js?v=2';

const API_BASE = '/api/bom/procurement-objects';
const CASCADE_API = '/api/bom/filters/cascade';
const SCOPE_REQUIRED_MESSAGE = '批量操作须选定基地、项目、版本';

const listState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    items: [],
    section: '',
    canUpdate: true,
    canDelete: true,
    canApprove: true,
    canReverse: true,
    canExport: true,
    submitting: false,
    isLoading: false,
};

const supplierPicker = {
    selectedName: '',
    selectedLabel: '',
    highlightIndex: 0,
    items: [],
    requestSeq: 0,
    timer: 0,
    approved: false,
};

function init() {
    applyPermissionUi();
    bindEvents();
    bindPageSizeSelect('poPageSize', {
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onChange: () => loadList(1),
    });
    fillStaticSelects();
    loadCascade().then(() => loadList(1));
}

function applyPermissionUi() {
    const canFn = typeof window.can === 'function' ? window.can : () => true;
    listState.canUpdate = canFn('op:bom-procurement-object-list:update');
    listState.canDelete = canFn('op:bom-procurement-object-list:delete');
    listState.canApprove = canFn('op:bom-procurement-object-list:approve');
    listState.canReverse = canFn('op:bom-procurement-object-list:reverse');
    listState.canExport = canFn('op:bom-procurement-object-list:export');
    if (!listState.canApprove) document.getElementById('poBatchApproveBtn')?.classList.add('hidden');
    if (!listState.canReverse) document.getElementById('poBatchReverseBtn')?.classList.add('hidden');
    if (!listState.canDelete) document.getElementById('poBatchDeleteBtn')?.classList.add('hidden');
    if (!listState.canExport) document.getElementById('poExportBtn')?.classList.add('hidden');
}

function bindEvents() {
    document.getElementById('poSearchBtn')?.addEventListener('click', () => loadList(1));
    document.getElementById('poResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('poToggleAdvancedFilter')?.addEventListener('click', () => {
        document.getElementById('poAdvancedFilterPanel')?.classList.toggle('hidden');
    });
    document.getElementById('poLocationFilter')?.addEventListener('change', () => {
        loadCascade().then(() => loadList(1));
    });
    document.getElementById('poModelFilter')?.addEventListener('change', () => {
        loadCascade().then(() => loadList(1));
    });
    document.getElementById('poVersionFilter')?.addEventListener('change', () => loadList(1));
    document.getElementById('poKindFilter')?.addEventListener('change', () => loadList(1));
    document.getElementById('poConfirmFilter')?.addEventListener('change', () => loadList(1));
    document.getElementById('poAuditFilter')?.addEventListener('change', () => loadList(1));
    document.getElementById('poHasSupplierFilter')?.addEventListener('change', () => loadList(1));
    document.getElementById('poConfirmStatus')?.addEventListener('change', syncConfirmSupplierEnabled);
    document.getElementById('poConfirmSupplierSearch')?.addEventListener('input', onSupplierSearchInput);
    document.getElementById('poConfirmSupplierSearch')?.addEventListener('focus', onSupplierSearchFocus);
    document.getElementById('poConfirmSupplierSearch')?.addEventListener('keydown', onSupplierSearchKeydown);
    document.getElementById('poConfirmSupplierMenu')?.addEventListener('mousedown', onSupplierMenuMouseDown);
    document.addEventListener('click', onSupplierPickerDocumentClick);
    document.getElementById('poPartFilter')?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        loadList(1);
    });
    document.getElementById('poSupplierFilter')?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        loadList(1);
    });
    document.querySelectorAll('.po-section-tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            listState.section = btn.dataset.section || '';
            syncTabs();
            loadList(1);
        });
    });
    document.getElementById('poTableBody')?.addEventListener('click', onTableClick);
    document.getElementById('poPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.po-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadList(page);
        }
    });
    document.getElementById('poBatchApproveBtn')?.addEventListener('click', () => openAuditDrawer('approve'));
    document.getElementById('poBatchReverseBtn')?.addEventListener('click', () => openAuditDrawer('reverse'));
    document.getElementById('poBatchDeleteBtn')?.addEventListener('click', openDeleteDrawer);
    document.getElementById('poExportBtn')?.addEventListener('click', exportExcel);
    document.getElementById('poBatchAuditCloseBtn')?.addEventListener('click', closeAuditDrawer);
    document.getElementById('poBatchAuditCancelBtn')?.addEventListener('click', closeAuditDrawer);
    document.getElementById('poBatchAuditDrawerBackdrop')?.addEventListener('click', closeAuditDrawer);
    document.getElementById('poBatchAuditConfirmBtn')?.addEventListener('click', submitAudit);
    document.getElementById('poBatchDeleteCloseBtn')?.addEventListener('click', closeDeleteDrawer);
    document.getElementById('poBatchDeleteCancelBtn')?.addEventListener('click', closeDeleteDrawer);
    document.getElementById('poBatchDeleteDrawerBackdrop')?.addEventListener('click', closeDeleteDrawer);
    document.getElementById('poBatchDeleteConfirmBtn')?.addEventListener('click', submitDelete);
    document.getElementById('poConfirmCloseBtn')?.addEventListener('click', closeConfirmDrawer);
    document.getElementById('poConfirmCancelBtn')?.addEventListener('click', closeConfirmDrawer);
    document.getElementById('poConfirmDrawerBackdrop')?.addEventListener('click', closeConfirmDrawer);
    document.getElementById('poConfirmSaveBtn')?.addEventListener('click', saveConfirm);
    document.getElementById('poDetailCloseBtn')?.addEventListener('click', closeDetailDrawer);
    document.getElementById('poDetailDrawerBackdrop')?.addEventListener('click', closeDetailDrawer);
}

function fillStaticSelects() {
    fillOptions('poKindFilter', [
        ['l0_degenerate', KIND_LABELS.l0_degenerate],
        ['l1_subassembly', KIND_LABELS.l1_subassembly],
        ['l1_stamping', KIND_LABELS.l1_stamping],
    ]);
    fillOptions('poConfirmFilter', [
        ['pending', CONFIRM_LABELS.pending],
        ['outsourced', CONFIRM_LABELS.outsourced],
        ['in_house', CONFIRM_LABELS.in_house],
    ]);
    fillOptions('poAuditFilter', [
        ['pending', AUDIT_LABELS.pending],
        ['approved', AUDIT_LABELS.approved],
    ]);
    fillOptions('poHasSupplierFilter', [
        ['true', '已指定'],
        ['false', '未指定'],
    ]);
}

function fillOptions(id, pairs) {
    const el = document.getElementById(id);
    if (!el) return;
    let html = '<option value="">全部</option>';
    pairs.forEach(([value, label]) => {
        html += `<option value="${esc(value)}">${esc(label)}</option>`;
    });
    el.innerHTML = html;
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function queryParams() {
    const params = {
        page: listState.page,
        size: listState.pageSize,
    };
    if (listState.section) params.section = listState.section;
    if (val('poLocationFilter')) params.location = val('poLocationFilter');
    if (val('poModelFilter')) params.vehicle_model = val('poModelFilter');
    if (val('poVersionFilter')) params.bom_version = val('poVersionFilter');
    if (val('poKindFilter')) params.object_kind = val('poKindFilter');
    if (val('poConfirmFilter')) params.confirm_status = val('poConfirmFilter');
    if (val('poAuditFilter')) params.audit_status = val('poAuditFilter');
    if (val('poSupplierFilter')) params.supplier_name = val('poSupplierFilter');
    if (val('poHasSupplierFilter')) params.has_supplier = val('poHasSupplierFilter') === 'true';
    if (val('poPartFilter')) params.part_number = val('poPartFilter');
    return params;
}

function requireScope() {
    const location = val('poLocationFilter');
    const vehicleModel = val('poModelFilter');
    const bomVersion = val('poVersionFilter');
    if (!location || !vehicleModel || !bomVersion) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return null;
    }
    return { location, vehicle_model: vehicleModel, bom_version: bomVersion };
}

async function loadCascade() {
    try {
        const params = {};
        if (val('poLocationFilter')) params.location = val('poLocationFilter');
        if (val('poModelFilter')) params.vehicle_model = val('poModelFilter');
        const res = await HttpClient.get(CASCADE_API, { params });
        const data = res.data || {};
        fillSelectKeep('poLocationFilter', data.locations || []);
        fillSelectKeep('poModelFilter', data.vehicle_models || []);
        fillSelectKeep('poVersionFilter', data.bom_versions || []);
    } catch (error) {
        console.error('加载级联筛选失败', error);
    }
}

function fillSelectKeep(id, values) {
    const el = document.getElementById(id);
    if (!el) return;
    const selected = el.value;
    let html = '<option value="">全部</option>';
    (values || []).forEach((item) => {
        html += `<option value="${esc(item)}">${esc(item)}</option>`;
    });
    el.innerHTML = html;
    if (selected && (values || []).includes(selected)) el.value = selected;
}

function supplierChoiceLabel(item) {
    const name = item.full_name || '';
    const abbr = item.abbreviation || '';
    return abbr ? `${abbr}（${name}）` : name;
}

function setSupplierPickerValue(fullName, label) {
    supplierPicker.selectedName = fullName || '';
    supplierPicker.selectedLabel = label || '';
    const hidden = document.getElementById('poConfirmSupplier');
    const search = document.getElementById('poConfirmSupplierSearch');
    if (hidden) hidden.value = supplierPicker.selectedName;
    if (search) search.value = supplierPicker.selectedLabel;
}

function closeSupplierMenu() {
    document.getElementById('poConfirmSupplierMenu')?.classList.add('hidden');
}

function renderSupplierMenu() {
    const menu = document.getElementById('poConfirmSupplierMenu');
    if (!menu) return;
    const rows = [{ full_name: '', abbreviation: '', isClear: true }, ...supplierPicker.items];
    if (supplierPicker.highlightIndex < 0) supplierPicker.highlightIndex = 0;
    if (supplierPicker.highlightIndex >= rows.length) supplierPicker.highlightIndex = rows.length - 1;
    menu.innerHTML = rows.map((item, index) => {
        const active = index === supplierPicker.highlightIndex
            ? 'bg-[#FF1E27]/15 text-white'
            : 'text-[#C8C8D0] hover:bg-[#161620]';
        const text = item.isClear ? '未指定' : supplierChoiceLabel(item);
        return `<button type="button" data-supplier-index="${index}"
                class="block w-full text-left px-3 py-1.5 text-[11px] font-mono ${active}">${esc(text)}</button>`;
    }).join('');
    menu.classList.remove('hidden');
}

function pickSupplierByIndex(index) {
    if (index === 0) {
        setSupplierPickerValue('', '');
        closeSupplierMenu();
        return;
    }
    const item = supplierPicker.items[index - 1];
    if (!item) return;
    setSupplierPickerValue(item.full_name, supplierChoiceLabel(item));
    closeSupplierMenu();
}

async function fetchSupplierChoices(keyword) {
    const seq = ++supplierPicker.requestSeq;
    const params = { page: 1, size: 20 };
    if (keyword) params.q = keyword;
    const res = await HttpClient.get(`${API_BASE}/supplier-choices`, { params });
    if (seq !== supplierPicker.requestSeq) return null;
    const data = res.data || {};
    return Array.isArray(data.items) ? data.items : [];
}

async function loadSupplierChoices() {
    const search = document.getElementById('poConfirmSupplierSearch');
    if (!search || search.disabled) return;
    try {
        const items = await fetchSupplierChoices(search.value.trim());
        if (items == null) return;
        supplierPicker.items = items;
        supplierPicker.highlightIndex = 0;
        renderSupplierMenu();
    } catch (error) {
        console.error('检索供应商失败', error);
        closeSupplierMenu();
    }
}

function onSupplierSearchInput() {
    if (supplierPicker.timer) window.clearTimeout(supplierPicker.timer);
    supplierPicker.timer = window.setTimeout(() => {
        loadSupplierChoices();
    }, 250);
}

function onSupplierSearchFocus() {
    const search = document.getElementById('poConfirmSupplierSearch');
    if (!search || search.disabled) return;
    loadSupplierChoices();
}

function onSupplierSearchKeydown(event) {
    const menu = document.getElementById('poConfirmSupplierMenu');
    const menuOpen = menu && !menu.classList.contains('hidden');
    if (event.key === 'ArrowDown') {
        event.preventDefault();
        supplierPicker.highlightIndex += 1;
        renderSupplierMenu();
        return;
    }
    if (event.key === 'ArrowUp') {
        event.preventDefault();
        supplierPicker.highlightIndex -= 1;
        renderSupplierMenu();
        return;
    }
    if (event.key === 'Enter' && menuOpen) {
        event.preventDefault();
        pickSupplierByIndex(supplierPicker.highlightIndex);
        return;
    }
    if (event.key === 'Escape') {
        closeSupplierMenu();
        setSupplierPickerValue(supplierPicker.selectedName, supplierPicker.selectedLabel);
    }
}

function onSupplierMenuMouseDown(event) {
    const btn = event.target.closest('[data-supplier-index]');
    if (!btn) return;
    event.preventDefault();
    pickSupplierByIndex(parseInt(btn.dataset.supplierIndex, 10));
}

function onSupplierPickerDocumentClick(event) {
    const wrap = document.getElementById('poConfirmSupplierWrap');
    if (!wrap || wrap.contains(event.target)) return;
    closeSupplierMenu();
    const search = document.getElementById('poConfirmSupplierSearch');
    if (search && !search.disabled) {
        search.value = supplierPicker.selectedLabel;
    }
}

async function initConfirmSupplierPicker(currentValue, approved) {
    supplierPicker.approved = Boolean(approved);
    supplierPicker.items = [];
    closeSupplierMenu();
    if (!currentValue) {
        setSupplierPickerValue('', '');
        return;
    }
    setSupplierPickerValue(currentValue, currentValue);
    try {
        const items = await fetchSupplierChoices(currentValue);
        if (!items) return;
        const hit = items.find((item) => item.full_name === currentValue);
        if (hit) setSupplierPickerValue(hit.full_name, supplierChoiceLabel(hit));
    } catch (_) {
        setSupplierPickerValue(currentValue, currentValue);
    }
}

function syncConfirmSupplierEnabled() {
    const status = val('poConfirmStatus');
    const search = document.getElementById('poConfirmSupplierSearch');
    if (!search) return;
    const locked = supplierPicker.approved || status === 'in_house';
    if (status === 'in_house') {
        setSupplierPickerValue('', '');
        closeSupplierMenu();
    }
    search.disabled = locked;
}

function setListLoading(isLoading) {
    listState.isLoading = isLoading;
    setSearchBusy('poSearchBtn', isLoading);
    document.getElementById('poLoadingState')?.classList.toggle('hidden', !isLoading);
    if (isLoading) {
        const body = document.getElementById('poTableBody');
        if (body) body.innerHTML = '';
    }
}

async function loadList(page) {
    if (listState.isLoading) return;
    listState.page = page || 1;
    updateCapsules();
    syncTabs();
    setListLoading(true);
    try {
        const res = await HttpClient.get(API_BASE, { params: queryParams() });
        const data = res.data || {};
        listState.items = data.items || [];
        listState.total = data.total || 0;
        listState.totalPages = data.total_pages || 1;
        const summary = (data.filters && data.filters.summary) || {};
        setText('poHudObject', String(summary.object_count ?? 0));
        setText('poHudOther', String(summary.other_leaf_count ?? 0));
        setText('poHudPending', String(summary.pending_count ?? 0));
        setText('poHudApproved', String(summary.approved_count ?? 0));
        setText('poTotalLabel', `共 ${listState.total} 条`);
        const body = document.getElementById('poTableBody');
        if (body) body.innerHTML = renderProcurementObjectRows(listState.items);
        const pager = document.getElementById('poPagination');
        if (pager) pager.innerHTML = renderPoPagination(listState.page, listState.totalPages);
        loadSummaryBanner();
    } catch (error) {
        console.error('加载采购对象清单失败', error);
    } finally {
        setListLoading(false);
    }
}

async function loadSummaryBanner() {
    const scope = {
        location: val('poLocationFilter'),
        vehicle_model: val('poModelFilter'),
        bom_version: val('poVersionFilter'),
    };
    const banner = document.getElementById('poQaBanner');
    if (!banner) return;
    if (!scope.location || !scope.vehicle_model || !scope.bom_version) {
        banner.classList.add('hidden');
        return;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/summary`, { params: scope });
        const header = res.data || {};
        if (header.qa_passed === false) {
            banner.textContent = `检测未通过：${header.qa_error_text || '禁止确认与审核'}`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    } catch (_) {
        banner.classList.add('hidden');
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function updateCapsules() {
    const active = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idle = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';
    const loc = val('poLocationFilter');
    const model = val('poModelFilter');
    const ver = val('poVersionFilter');
    const locEl = document.getElementById('poCapsuleLocation');
    const modelEl = document.getElementById('poCapsuleModel');
    const verEl = document.getElementById('poCapsuleVersion');
    if (locEl) {
        locEl.textContent = loc || '全部基地';
        locEl.className = loc ? active : idle;
    }
    if (modelEl) {
        modelEl.textContent = model || '全部项目';
        modelEl.className = model ? active : idle;
    }
    if (verEl) {
        verEl.textContent = ver || '全部版本';
        verEl.className = ver ? active : idle;
    }
}

function syncTabs() {
    document.querySelectorAll('.po-section-tab').forEach((btn) => {
        const on = btn.dataset.section === listState.section;
        btn.className = on
            ? 'po-section-tab h-7 px-3 text-[11px] font-semibold rounded-md border border-[#FF1E27] text-[#FF1E27] bg-[#FF1E27]/10'
            : 'po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-[#2A2A35] text-[#8E8E93]';
    });
}

function resetFilters() {
    ['poLocationFilter', 'poModelFilter', 'poVersionFilter', 'poKindFilter', 'poConfirmFilter', 'poAuditFilter', 'poSupplierFilter', 'poHasSupplierFilter', 'poPartFilter']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    loadCascade().then(() => loadList(1));
}

function onTableClick(event) {
    const btn = event.target.closest('[data-action]');
    if (!btn) return;
    const id = parseInt(btn.dataset.id, 10);
    if (!id) return;
    if (btn.dataset.action === 'confirm') openConfirmDrawer(id);
    if (btn.dataset.action === 'detail') openDetailDrawer(id);
}

function openDrawer(id) {
    document.getElementById(id)?.classList.remove('hidden');
    document.getElementById(`${id}Backdrop`)?.classList.remove('hidden');
}

function closeDrawer(id) {
    document.getElementById(id)?.classList.add('hidden');
    document.getElementById(`${id}Backdrop`)?.classList.add('hidden');
}

function sessionName() {
    try {
        const raw = localStorage.getItem('brabus_user');
        if (!raw) return '';
        const session = JSON.parse(raw);
        return (session.real_name || session.username || '').trim();
    } catch (_) {
        return '';
    }
}

function openAuditDrawer(mode) {
    if (mode === 'approve' && !listState.canApprove) return showToast('无审核权限', 'warning');
    if (mode !== 'approve' && !listState.canReverse) return showToast('无反审核权限', 'warning');
    const scope = requireScope();
    if (!scope) return;
    document.getElementById('poBatchAuditMode').value = mode;
    document.getElementById('poBatchAuditDrawerTitle').textContent = mode === 'approve' ? '批量审核' : '批量反审核';
    document.getElementById('poBatchAuditHint').textContent = mode === 'approve'
        ? '按当前基地·项目·版本审核待审采购对象；检测未通过会拒绝。'
        : '按当前基地·项目·版本反审核已通过记录。';
    document.getElementById('poBatchAuditOperatorDisplay').textContent = sessionName() || '当前登录用户';
    document.getElementById('poBatchAuditRemarkLabel').innerHTML = mode === 'approve'
        ? '审核意见<span class="text-[#FF1E27]">*</span>'
        : '反审核原因<span class="text-[#FF1E27]">*</span>';
    document.getElementById('poBatchAuditRemark').value = '';
    document.getElementById('poBatchAuditFilterSummary').textContent =
        `${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}`;
    openDrawer('poBatchAuditDrawer');
}

function closeAuditDrawer() {
    closeDrawer('poBatchAuditDrawer');
}

async function submitAudit() {
    const mode = document.getElementById('poBatchAuditMode')?.value || 'approve';
    const scope = requireScope();
    if (!scope) return;
    const remark = document.getElementById('poBatchAuditRemark')?.value.trim() || '';
    if (!remark) {
        showToast(mode === 'approve' ? '审核意见必填' : '反审核原因必填', 'warning');
        return;
    }
    if (listState.submitting) return;
    listState.submitting = true;
    try {
        const path = mode === 'approve' ? '/batch-approve' : '/batch-reverse-audit';
        const body = mode === 'approve'
            ? { ...scope, audit_remark: remark }
            : { ...scope, reverse_audit_remark: remark };
        const res = await HttpClient.post(`${API_BASE}${path}`, body);
        showToast(res.message || '已提交', 'success');
        closeAuditDrawer();
        loadList(listState.page);
    } catch (error) {
        console.error('批量审核失败', error);
    } finally {
        listState.submitting = false;
    }
}

function openDeleteDrawer() {
    if (!listState.canDelete) return showToast('无删除权限', 'warning');
    const scope = requireScope();
    if (!scope) return;
    document.getElementById('poBatchDeleteSummary').textContent =
        `${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}`;
    openDrawer('poBatchDeleteDrawer');
}

function closeDeleteDrawer() {
    closeDrawer('poBatchDeleteDrawer');
}

async function submitDelete() {
    const scope = requireScope();
    if (!scope || listState.submitting) return;
    listState.submitting = true;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        showToast(res.message || '已删除', 'success');
        closeDeleteDrawer();
        loadList(1);
    } catch (error) {
        console.error('批量删除失败', error);
    } finally {
        listState.submitting = false;
    }
}

function openConfirmDrawer(id) {
    if (!listState.canUpdate) return showToast('无确认权限', 'warning');
    const row = listState.items.find((item) => item.id === id);
    if (!row) return;
    document.getElementById('poConfirmId').value = String(id);
    document.getElementById('poConfirmPart').innerHTML = `
        <div>${esc(row.part_number)} ${esc(row.part_name || '')}</div>
        ${row.internal_number
            ? `<div class="text-[10px] text-[#555555] mt-1" title="内部号（ERP）">${esc(row.internal_number)}</div>`
            : ''}
    `;
    document.getElementById('poConfirmStatus').value = row.confirm_status || 'pending';
    document.getElementById('poConfirmRemark').value = row.confirm_remark || '';
    initConfirmSupplierPicker(row.supplier_name || '', row.audit_status === 'approved').then(() => {
        syncConfirmSupplierEnabled();
    });
    syncConfirmSupplierEnabled();
    openDrawer('poConfirmDrawer');
}

function closeConfirmDrawer() {
    closeSupplierMenu();
    closeDrawer('poConfirmDrawer');
}

async function saveConfirm() {
    const id = document.getElementById('poConfirmId')?.value;
    if (!id || listState.submitting) return;
    listState.submitting = true;
    try {
        await HttpClient.patch(`${API_BASE}/items/${id}/confirm`, {
            confirm_status: val('poConfirmStatus'),
            confirm_remark: val('poConfirmRemark') || null,
        });
        if (val('poConfirmStatus') !== 'in_house') {
            await HttpClient.patch(`${API_BASE}/items/${id}/supplier`, {
                supplier_name: val('poConfirmSupplier') || null,
            });
        }
        showToast('确认已保存', 'success');
        closeConfirmDrawer();
        loadList(listState.page);
    } catch (error) {
        console.error('确认失败', error);
    } finally {
        listState.submitting = false;
    }
}

function openDetailDrawer(id) {
    const row = listState.items.find((item) => item.id === id);
    if (!row) return;
    const body = document.getElementById('poDetailBody');
    if (body) {
        body.innerHTML = [
            ['基地·项目·版本', `${row.location || ''} · ${row.vehicle_model || ''} · ${row.bom_version || ''}`],
            ['供货总成', `${row.l0_part_number} ${row.l0_part_name || ''}`],
            ['零件号', row.part_number],
            ['内部号', row.internal_number || '—'],
            ['零件名称', row.part_name || ''],
            ['对象种类', KIND_LABELS[row.object_kind] || SECTION_LABELS[row.section] || row.object_kind || ''],
            ['Excel', `${row.excel_filename || ''} 行 ${row.excel_row ?? ''}`],
            ['材料', `${row.material || ''} ${row.thickness_text || ''} ${row.material_mill || ''}`],
            ['焊接', row.weld_info || '—'],
            ['备注', row.remark || '—'],
            ['确认', CONFIRM_LABELS[row.confirm_status] || row.confirm_status],
            ['供应商', row.supplier_name || '未指定'],
            ['审核', AUDIT_LABELS[row.audit_status] || row.audit_status],
        ].map(([k, v]) => `<div><span class="text-[#555555]">${esc(k)}</span> ${esc(v)}</div>`).join('');
    }
    openDrawer('poDetailDrawer');
}

function closeDetailDrawer() {
    closeDrawer('poDetailDrawer');
}

async function exportExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const btn = document.getElementById('poExportBtn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#FF1E27] border-t-transparent rounded-full animate-spin"></div>导出中..`;
    }
    const params = queryParams();
    delete params.page;
    delete params.size;
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '采购对象清单.xlsx',
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
    render: procurementObjectListTemplate,
    init,
};
