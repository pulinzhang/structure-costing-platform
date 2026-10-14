/**
 * 冲压零件价格列表
 */

import { DRAWER_SHELL, DRAWER_BACKDROP, BTN_SOLID } from '../../../../ui/classes.js?v=15';
import {
    partCostListTemplate,
    renderCostRows,
    updatePartCostHud,
    syncOptionalColumnVisibility,
} from './template.js?v=89';
import { shortPartNumber } from '../../../../domain/part-identity.js?v=5';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=11';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=7';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=6';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';
import { setCurrentTableRow } from '../../../../ui/table-row.js?v=3';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;
/** @type {{ paint: () => void, setOpen: (isOpen: boolean) => void, unbind: () => void } | null} */
let filterBar = null;

const API_BASE = '/api/costing/stamping-part-cost';
const CASCADE_API = '/api/stamping/filters/cascade';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '批量操作须选定年度、月份、基地、项目';
const EXPORT_VEHICLE_REQUIRED_MESSAGE = '导出须选定项目。';

const FILTER_IDS = [
    'costYearFilter',
    'costMonthFilter',
    'costLocationFilter',
    'costVehicleModelFilter',
    'costVersionFilter',
    'costSupplierFilter',
    'costAuditFilter',
    'costPartNumberFilter',
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
    canUpdate: true,
    massColsOpen: false,
    breakdownColsOpen: false,
    feeColsOpen: false,
    pendingFilters: null,
    batchAuditSubmitting: false,
    isLoading: false,
    _onEscClose: null,
};

function optionalColumnFlags() {
    return {
        massOpen: listState.massColsOpen,
        breakdownOpen: listState.breakdownColsOpen,
        feeOpen: listState.feeColsOpen,
    };
}

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
    bindPagination({
        selectId: 'costPageSize',
        buttonsId: 'costPagination',
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onPage: (page) => loadList(page),
    });
    fillMonthOptions();
    fillAuditOptions();
    listState.pendingFilters = readHashFilters();
    syncOptionalColumnVisibility(optionalColumnFlags());
    loadYearOptions().then(async () => {
        await loadCascadeFilters();
        applyPendingFiltersToSelects();
        filterBar?.paint();
        loadList(1);
    });
}

function destroy() {
    moreMenu?.unbind();
    moreMenu = null;
    filterBar?.unbind();
    filterBar = null;
    closeDetailDrawer();
}

function applyPermissionUi() {
    listState.canDelete = typeof can === 'function' ? can('op:stamping-part-cost:delete') : true;
    listState.canApprove = typeof can === 'function' ? can('op:stamping-part-cost:approve') : true;
    listState.canReverse = typeof can === 'function' ? can('op:stamping-part-cost:reverse') : true;
    listState.canExport = typeof can === 'function' ? can('op:stamping-part-cost:export') : true;
    listState.canUpdate = typeof can === 'function' ? can('op:stamping-part-cost:update') : true;
    if (!listState.canDelete) document.getElementById('costBatchDeleteBtn')?.classList.add('hidden');
    if (!listState.canApprove) document.getElementById('costBatchApproveBtn')?.classList.add('hidden');
    if (!listState.canReverse) document.getElementById('costBatchReverseBtn')?.classList.add('hidden');
    if (!listState.canExport) {
        document.getElementById('costExportBtn')?.classList.add('hidden');
    }
    const moreItems = ['costBatchApproveBtn', 'costBatchReverseBtn', 'costBatchDeleteBtn']
        .map((id) => document.getElementById(id))
        .filter((el) => el && !el.classList.contains('hidden'));
    if (!moreItems.length) {
        document.getElementById('costMoreWrap')?.classList.add('hidden');
    }
}

function setAdvancedOpen(isOpen) {
    filterBar?.setOpen(isOpen);
}

function readHashFilters() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return null;
    const params = new URLSearchParams(hash.slice(qIndex + 1));
    const year = params.get('year') || '';
    const month = params.get('month') || '';
    const location = params.get('location') || '';
    const stamping_supplier = params.get('stamping_supplier') || '';
    const vehicle_model = params.get('vehicle_model') || '';
    const version = params.get('version') || '';
    if (!year && !month && !location && !stamping_supplier && !vehicle_model && !version) return null;
    return { year, month, location, stamping_supplier, vehicle_model, version };
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
    setSelectValue('costYearFilter', pending.year);
    setSelectValue('costMonthFilter', pending.month);
    setSelectValue('costLocationFilter', pending.location);
    setSelectValue('costVehicleModelFilter', pending.vehicle_model);
    setSelectValue('costVersionFilter', pending.version);
    setSelectValue('costSupplierFilter', pending.stamping_supplier);
    listState.pendingFilters = null;
}

function toggleOptionalColumnGroup(stateKey) {
    listState[stateKey] = !listState[stateKey];
    syncOptionalColumnVisibility(optionalColumnFlags());
}

function setListLoading(isLoading) {
    listState.isLoading = isLoading;
    setSearchBusy('costSearchBtn', isLoading);
    const loading = document.getElementById('costLoading');
    const empty = document.getElementById('costEmpty');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading && empty) empty.classList.add('hidden');
}

function setListEmpty(isEmpty) {
    const empty = document.getElementById('costEmpty');
    if (empty) empty.classList.toggle('hidden', !isEmpty);
}

function bindEvents() {
    filterBar = bindFilterBar({
        prefix: 'cost',
        searchId: 'costSearchBtn',
        capsules: [
            {
                capsuleId: 'costCapsulePeriod',
                fieldIds: ['costYearFilter', 'costMonthFilter'],
                idleLabel: '全部期间',
                display: () => window.fmtPeriod(
                    document.getElementById('costYearFilter')?.value,
                    document.getElementById('costMonthFilter')?.value,
                ),
            },
            { capsuleId: 'costCapsuleLocation', fieldId: 'costLocationFilter', idleLabel: '全部基地' },
            { capsuleId: 'costCapsuleVehicle', fieldId: 'costVehicleModelFilter', idleLabel: '全部项目' },
            { capsuleId: 'costCapsuleVersion', fieldId: 'costVersionFilter', idleLabel: '全部版本' },
            { capsuleId: 'costCapsuleSupplier', fieldId: 'costSupplierFilter', idleLabel: '全部工厂' },
        ],
        countFieldIds: FILTER_IDS,
        resetId: 'costResetBtn',
        enterFieldIds: ['costPartNumberFilter'],
        onSearch: () => loadList(1),
        onReset: () => resetFilters(),
    });
    [
        ['costToggleMassCols', 'massColsOpen'],
        ['costToggleBreakdownCols', 'breakdownColsOpen'],
        ['costToggleFeeCols', 'feeColsOpen'],
    ].forEach(([buttonId, stateKey]) => {
        document.getElementById(buttonId)?.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            toggleOptionalColumnGroup(stateKey);
        });
    });

    document.getElementById('costYearFilter')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => {
            filterBar?.paint();
            loadList(1);
        });
    });
    document.getElementById('costMonthFilter')?.addEventListener('change', () => {
        loadList(1);
    });
    document.getElementById('costLocationFilter')?.addEventListener('change', () => {
        const vehicleEl = document.getElementById('costVehicleModelFilter');
        const versionEl = document.getElementById('costVersionFilter');
        const supplierEl = document.getElementById('costSupplierFilter');
        if (vehicleEl) vehicleEl.value = '';
        if (versionEl) versionEl.value = '';
        if (supplierEl) supplierEl.value = '';
        loadCascadeFilters().then(() => {
            filterBar?.paint();
            loadList(1);
        });
    });
    document.getElementById('costVehicleModelFilter')?.addEventListener('change', () => {
        const versionEl = document.getElementById('costVersionFilter');
        const supplierEl = document.getElementById('costSupplierFilter');
        if (versionEl) versionEl.value = '';
        if (supplierEl) supplierEl.value = '';
        loadCascadeFilters().then(() => {
            filterBar?.paint();
            loadList(1);
        });
    });
    document.getElementById('costVersionFilter')?.addEventListener('change', () => {
        const supplierEl = document.getElementById('costSupplierFilter');
        if (supplierEl) supplierEl.value = '';
        loadCascadeFilters().then(() => {
            filterBar?.paint();
            loadList(1);
        });
    });
    document.getElementById('costSupplierFilter')?.addEventListener('change', () => {
        loadList(1);
    });
    document.getElementById('costAuditFilter')?.addEventListener('change', () => {
        loadList(1);
    });

    moreMenu = bindMoreMenu({
        wrapId: 'costMoreWrap',
        btnId: 'costMoreBtn',
        menuId: 'costMoreMenu',
    });
    document.getElementById('costBatchApproveBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('approve');
    });
    document.getElementById('costBatchReverseBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        openBatchAuditDrawer('reverse');
    });
    document.getElementById('costBatchDeleteBtn')?.addEventListener('click', () => {
        moreMenu?.close();
        batchDelete();
    });
    bindBatchAuditDrawerEvents();
    document.getElementById('costExportBtn')?.addEventListener('click', () => exportExcel());
}

function fillMonthOptions() {
    const select = document.getElementById('costMonthFilter');
    if (!select) return;
    select.innerHTML =
        `<option value="">全部</option>` +
        Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${esc(fmtMonth(i + 1))}</option>`).join('');
}

function fillAuditOptions() {
    const select = document.getElementById('costAuditFilter');
    if (!select) return;
    select.innerHTML = `
        <option value="">全部</option>
        <option value="pending">待审</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
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
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        fillSelect(
            'costYearFilter',
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
            location: document.getElementById('costLocationFilter')?.value || pending?.location || '',
            vehicle_model: document.getElementById('costVehicleModelFilter')?.value || pending?.vehicle_model || '',
            version: document.getElementById('costVersionFilter')?.value || pending?.version || '',
            stamping_supplier: document.getElementById('costSupplierFilter')?.value || pending?.stamping_supplier || '',
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('costLocationFilter', filters.locations || [], pending?.location || null);
        fillSelect('costVehicleModelFilter', filters.vehicle_models || [], pending?.vehicle_model || null);
        fillSelect('costVersionFilter', filters.versions || [], pending?.version || null);
        fillSelect('costSupplierFilter', filters.stamping_suppliers || [], pending?.stamping_supplier || null);
        filterBar?.paint();
    } catch (error) {
        console.error(error);
    }
}

function resetFilters() {
    FILTER_IDS.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    loadCascadeFilters().then(() => filterBar?.paint());
    loadList(1);
}

function getFilters() {
    const pending = listState.pendingFilters;
    const yearRaw = document.getElementById('costYearFilter')?.value || pending?.year || '';
    const monthRaw = document.getElementById('costMonthFilter')?.value || pending?.month || '';
    return {
        year: yearRaw ? Number(yearRaw) : undefined,
        month: monthRaw ? Number(monthRaw) : undefined,
        location: document.getElementById('costLocationFilter')?.value || pending?.location || undefined,
        vehicle_model: document.getElementById('costVehicleModelFilter')?.value || pending?.vehicle_model || undefined,
        version: document.getElementById('costVersionFilter')?.value || pending?.version || undefined,
        stamping_supplier: document.getElementById('costSupplierFilter')?.value || pending?.stamping_supplier || undefined,
        audit_status: document.getElementById('costAuditFilter')?.value || undefined,
        part_number: document.getElementById('costPartNumberFilter')?.value?.trim() || undefined,
    };
}

function requireScope() {
    const f = getFilters();
    if (!f.year || !f.month || !f.location || !f.vehicle_model) {
        setAdvancedOpen(true);
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return null;
    }
    const scope = {
        year: f.year,
        month: f.month,
        location: f.location,
        vehicle_model: f.vehicle_model,
    };
    if (f.version) scope.version = f.version;
    if (f.stamping_supplier) scope.stamping_supplier = f.stamping_supplier;
    return scope;
}

function requireAuditScope() {
    const scope = requireScope();
    if (!scope) return null;
    const auditScope = { ...scope };
    delete auditScope.stamping_supplier;
    return auditScope;
}

async function loadList(page = 1) {
    const body = document.getElementById('costTableBody');
    if (!body) return;
    if (listState.isLoading) return;
    setListLoading(true);
    body.innerHTML = '';
    filterBar?.paint();
    try {
        const filters = getFilters();
        const res = await HttpClient.get(API_BASE, {
            params: { ...filters, page, size: listState.pageSize },
        });
        const pageData = res.data || {};
        listState.page = pageData.page || page;
        listState.total = pageData.total || 0;
        listState.totalPages = pageData.total_pages || 1;
        listState.items = Array.isArray(pageData.items) ? pageData.items : [];
        renderRows(listState.items);
        updatePartCostHud(listState.total, pageData.filters?.summary || null);
        const pageInfo = document.getElementById('costPageInfo');
        if (pageInfo) {
            pageInfo.textContent = `第${listState.page} / ${Math.max(listState.totalPages, 1)} 页· ${listState.total} 条`;
        }
        paintPagination('costPagination', listState.page, listState.totalPages);
        if (pageData.filters) {
            if (pageData.filters.years) fillSelect('costYearFilter', pageData.filters.years, filters.year, fmtYear);
            if (pageData.filters.locations) {
                fillSelect('costLocationFilter', pageData.filters.locations, filters.location);
            }
            if (pageData.filters.vehicle_models) {
                fillSelect('costVehicleModelFilter', pageData.filters.vehicle_models, filters.vehicle_model);
            }
            if (pageData.filters.versions) {
                fillSelect('costVersionFilter', pageData.filters.versions, filters.version);
            }
            if (pageData.filters.suppliers) {
                fillSelect('costSupplierFilter', pageData.filters.suppliers, filters.stamping_supplier);
            }
        }
        filterBar?.paint();
    } catch (error) {
        setListLoading(false);
        body.innerHTML = '';
        setListEmpty(true);
        updatePartCostHud(0, null);
        filterBar?.paint();
        showToast(error.message || '加载失败', 'error');
    } finally {
        setListLoading(false);
    }
}

function renderRows(items) {
    const body = document.getElementById('costTableBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = '';
        setListEmpty(true);
        return;
    }
    setListEmpty(false);
    body.innerHTML = renderCostRows(items, optionalColumnFlags());
    syncOptionalColumnVisibility(optionalColumnFlags());
    body.querySelectorAll('.btn-open-detail').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const costId = Number(btn.dataset.id);
            if (costId) openDetail(costId);
            setCurrentTableRow(body.closest('table'), btn.closest('tr'));
        });
    });
}

async function openDetail(costId) {
    try {
        const res = await HttpClient.get(`${API_BASE}/${costId}`);
        showDetailDrawer(res.data || {});
    } catch (error) {
        showToast(error.message || '加载详情失败', 'error');
    }
}

function showDetailDrawer(row) {
    closeDetailDrawer();
    const shortNo = shortPartNumber(row.part_number);

    const backdrop = document.createElement('div');
    backdrop.id = 'costDetailBackdrop';
    backdrop.className = DRAWER_BACKDROP;

    const drawer = document.createElement('div');
    drawer.id = 'costDetailDrawer';
    drawer.className = `${DRAWER_SHELL} w-[620px] font-mono text-[11px]`;

    const failStatus = row.calc_status === 'failed';
    const isApproved = row.audit_status === 'approved';
    const canEditUnitCost = failStatus && listState.canUpdate && !isApproved;
    const auditText =
        row.audit_status === 'approved'
            ? '已审核'
            : row.audit_status === 'rejected'
              ? '已驳回'
              : '待审核';
    const auditBadgeColor =
        row.audit_status === 'approved'
            ? 'text-ink-muted bg-app-rowhover border-line'
            : row.audit_status === 'rejected'
              ? 'text-danger bg-brand-hud/10 border-danger/30'
              : 'text-brand-hud bg-brand-hud/10 border-brand-hud/30';

    const unitCostDisplay =
        row.unit_cost == null || row.unit_cost === ''
            ? '—'
            : `￥${esc(fmtNum(row.unit_cost, 4))}`;

    const heroCostHtml = canEditUnitCost
        ? `
            <div class="text-right shrink-0 w-[200px]">
                <label class="block text-[9px] text-ink-dim mb-1 tracking-wider">最终成本（元）</label>
                <div class="flex items-center justify-end gap-1">
                    <span class="text-brand-hud text-sm font-bold">￥</span>
                    <input type="number" id="costManualUnitCost" min="0" step="0.000001"
                           value="${row.unit_cost == null ? '' : esc(String(row.unit_cost))}"
                           class="w-full h-9 px-2 text-right text-[16px] font-black tabular-nums bg-app-hud border border-brand-hud/40 text-brand-hud placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm"
                           placeholder="0.0000">
                </div>
            </div>
        `
        : `
            <div class="text-right shrink-0">
                <div class="text-[28px] font-black tabular-nums text-brand-hud leading-none">
                    ${unitCostDisplay}
                </div>
            </div>
        `;

    const editPanelHtml = canEditUnitCost
        ? `
        <div class="px-6 py-4 border-b border-line-subtle bg-app-hud shrink-0 space-y-3">
            <div class="flex items-center gap-2 text-[10px] text-brand-hud">
                <span class="w-1.5 h-1.5 bg-brand-hud rounded-full"></span>
                <span class="font-bold tracking-wider">计算失败 · 可手工录入最终成本</span>
            </div>
            ${row.calc_fail_reason ? `
                <div class="text-[10px] text-ink-muted leading-relaxed bg-brand-hud/10 border border-brand-hud/20 px-3 py-2 rounded-sm">
                    失败原因：${esc(row.calc_fail_reason)}
                </div>
            ` : ''}
            <div>
                <label class="block text-[9px] text-ink-dim mb-1.5 tracking-wider">
                    备注 <span class="text-brand-hud">*</span>
                </label>
                <textarea id="costManualRemark" rows="3" maxlength="500"
                          class="w-full px-3 py-2 text-[11px] bg-app-hud border border-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm resize-none"
                          placeholder="必填：说明手工改价原因">${esc(row.remark || '')}</textarea>
            </div>
            <div class="flex items-center justify-end gap-2">
                <button type="button" id="costManualSaveBtn"
                        class="${BTN_SOLID} justify-center">
                    保存最终成本
                </button>
            </div>
        </div>
        `
        : failStatus && isApproved
          ? `
        <div class="px-6 py-3 border-b border-line-subtle bg-app-hud shrink-0 text-[10px] text-ink-muted">
            已审核通过，请先反审核后再手工改价。
        </div>
        `
          : '';

    drawer.innerHTML = `
        <div class="px-6 py-4 flex items-center justify-between shrink-0 bg-app-main border-b border-line-subtle">
            <div class="flex items-center gap-3 min-w-0">
                ${shortNo ? `
                    <div class="flex items-center justify-center px-2.5 py-1 bg-brand-hud/10 border border-brand-hud/40 text-brand-hud font-black text-[14px] tracking-widest tabular-nums rounded-sm shrink-0">
                        ${esc(shortNo)}
                    </div>
                ` : ''}
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <h5 class="text-[13px] font-bold tracking-wide text-ink truncate">${esc(row.part_name || '零件核算详情')}</h5>
                        <span class="text-[9px] px-1.5 py-0.5 border ${auditBadgeColor} rounded-sm shrink-0">${auditText}</span>
                    </div>
                    <div class="text-[10px] text-ink-faint tracking-wide mt-0.5 truncate">${esc(row.part_number || '—')}</div>
                </div>
            </div>
            <button type="button" id="closeCostDetailDrawer"
                    class="w-7 h-7 flex items-center justify-center bg-app-main border border-line-hud text-ink-dim hover:text-ink hover:border-brand-hud/50 hover:bg-brand-hud/10 rounded-sm transition-all shrink-0 ml-4"
                    title="关闭">
                ✕
            </button>
        </div>

        <div class="px-6 py-4 border-b border-line-subtle bg-app-deep relative overflow-hidden shrink-0">
            <div class="absolute right-0 top-0 bottom-0 w-40 bg-gradient-to-l from-brand-hud/[0.12] to-transparent pointer-events-none"></div>
            <div class="flex items-end justify-between relative z-10 gap-4">
                <div class="min-w-0">
                    <div class="text-[9px] font-bold tracking-widest text-brand-hud mb-1.5 flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 bg-brand-hud rounded-full animate-pulse"></span>
                        单件核算成本
                    </div>
                    <div class="text-[10px] text-ink-dim font-mono">
                        直接成本 <span class="text-ink">￥${fmtNum(row.direct_cost, 2)}</span>
                        <span class="text-ink-faint mx-1">=</span>
                        R <span class="text-ink">￥${fmtNum(row.material_net_per_part, 2)}</span>
                        <span class="text-ink-faint mx-1">+</span>
                        加工费 <span class="text-ink">￥${fmtNum(row.process_fee_amount, 2)}</span>
                        <span class="text-ink-faint mx-1">+</span>
                        模具费 <span class="text-ink">￥${fmtNum(row.die_fee_amount, 2)}</span>
                        <span class="text-ink-faint mx-1">+</span>
                        检具费 <span class="text-ink">￥${fmtNum(row.gauge_fee_amount, 2)}</span>
                    </div>
                </div>
                ${heroCostHtml}
            </div>
        </div>

        ${editPanelHtml}

        <div class="flex-1 overflow-y-auto p-6 space-y-4 text-ink-muted bg-app-hud">
            ${detailBlock('基础属总', [
                ['零件号', row.part_number || '—'],
                ['短号', shortNo || '—'],
                ['零件名称', row.part_name || '—'],
                ['基地 / 工厂', `${row.location || '—'} / ${row.stamping_supplier || '—'}`],
                ['核算年月', fmtPeriod(row.year, row.month) || '—'],
                ['项目 / 版本', `${row.vehicle_model || '—'} / ${row.version || '—'}`],
                ['材质 / 厚度', `${row.material || '—'} / ${row.thickness || '—'} mm`],
                ['料片尺寸', `${row.sheet_length || '—'} × ${row.sheet_width || '—'} mm`],
                ['可制件数', row.parts_per_sheet ?? '—'],
                ['是否利废（本月）', row.is_offal_nested ? '是' : '否'],
                ['是否摆剪（本月）', row.has_swing_shear ? '是' : '否'],
                ['摆剪加价（本月）', row.has_swing_shear ? `${fmtNum(row.swing_shear_fee_per_ton, 2)} 元/吨` : '—'],
                ['利用哪类废料（本月）', row.offal_source || '—'],
                ['成品单重', `${fmtNum(row.part_weight, 4)} kg`],
            ])}

            ${detailBlock('过程计算量', [
                [
                    '密度 / 损耗/ 回收',
                    `${fmtNum(row.density, 2)} g/cm³ · ${fmtNum(scaleDecimalByPow10(row.material_loss_rate, 3, 2) ?? '0', 2)}‰ · ${fmtNum(scaleDecimalByPow10(row.scrap_recovery_rate, 2, 1) ?? '0', 1)}%`,
                ],
                ['预估单件材料消耗M', `${fmtNum(row.blank_weight_kg, 7)} kg`],
                ['零件净量', `${fmtNum(row.finished_total_kg, 7)} kg`],
                ['废料重量 O', `${fmtNum(row.scrap_weight_kg, 7)} kg`],
                [
                    '材料利用率',
                    `<span class="text-ink font-bold">${fmtNum(row.material_utilization_pct, 2)} %</span>`,
                ],
            ])}

            ${detailBlock('价格与吨价', [
                ['钢厂', row.is_offal_nested ? '—' : (row.steel_mill || '—')],
                ['钢材吨价 P', row.is_offal_nested ? '—（利废不按新板价）' : (row.steel_ton_price ? `${row.steel_ton_price} 元/吨` : '—')],
                ['废料吨价 Q', `￥${fmtNum(row.scrap_ton_price, 2)} /t${row.is_offal_nested ? '（利废：R = 成品净重 × 废料单价）' : ''}`],
            ])}

            ${detailBlock(row.is_offal_nested ? '原材料成本（利废：R = 成品净重 × 废料单价）' : '原材料成本拆解（R = ①−②−③）', [
                [row.is_offal_nested ? '①成品净重×废料单价' : '①钢材采购成本（含损耗）', `￥${fmtNum(row.material_amount_sheet, 4)}`],
                ['②损耗废料扣除（回收率）', `￥${fmtNum(row.loss_scrap_deduction, 4)}`],
                ['③边角废料扣除（回收率）', `￥${fmtNum(row.process_scrap_deduction, 4)}`],
                ['废料扣除小计（② + ③）', `￥${fmtNum(row.scrap_amount_sheet, 4)}`],
                [
                    '原材料净成本 R',
                    `<span class="text-brand-hud font-semibold">￥${fmtNum(row.material_net_per_part, 4)}</span>`,
                ],
                ['加工费', `￥${fmtNum(row.process_fee_amount, 3)}`],
                ['模具费', `￥${fmtNum(row.die_fee_amount, 4)}`],
                ['检具费', `￥${fmtNum(row.gauge_fee_amount, 4)}`],
            ])}

            ${detailBlock('成品费率费用', [
                [
                    '直接成本（R + 加工费 + 模具费 + 检具费）',
                    `<span class="text-ink font-semibold">￥${fmtNum(row.direct_cost, 4)}</span>`,
                ],
                ['仓储+包装管理费用', `<span class="text-ink-dim">￥${fmtNum(row.finished_warehouse_packaging_fee, 4)}</span>`],
                ['管理费', `<span class="text-ink-dim">￥${fmtNum(row.finished_management_fee, 4)}</span>`],
                ['财务费', `<span class="text-ink-dim">￥${fmtNum(row.finished_finance_fee, 4)}</span>`],
                ['税前利润', `<span class="text-ink-dim">￥${fmtNum(row.finished_pretax_profit_fee, 4)}</span>`],
                [
                    '单件成本',
                    `<span class="text-brand-hud font-semibold">￥${fmtNum(row.unit_cost, 4)}</span>`,
                ],
            ])}

            ${detailBlock('状态与来源', [
                [
                    '计算状态',
                    failStatus
                        ? `<span class="text-brand-hud font-bold bg-brand-hud/10 px-1.5 py-0.5 border border-brand-hud/30">失败（${esc(row.calc_fail_reason || '未知原因')}）</span>`
                        : '<span class="text-ink">正常</span>',
                ],
                ['备注', row.remark || '—'],
                ['来源文件', row.excel_filename || '—'],
                ['工作表', row.excel_sheet_name || '—'],
                ['行号', row.excel_row != null ? `第${row.excel_row} 行` : '—'],
            ])}
        </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);

    const closeHandler = () => closeDetailDrawer();
    backdrop.addEventListener('click', closeHandler);
    document.getElementById('closeCostDetailDrawer')?.addEventListener('click', closeHandler);
    listState._onEscClose = (event) => {
        if (event.key === 'Escape') closeDetailDrawer();
    };
    document.addEventListener('keydown', listState._onEscClose);

    if (canEditUnitCost) {
        document.getElementById('costManualSaveBtn')?.addEventListener('click', () => {
            saveManualUnitCost(row.id);
        });
    }
}

async function saveManualUnitCost(costId) {
    if (!listState.canUpdate) {
        showToast('无改价权限', 'warning');
        return;
    }
    const unitCostEl = document.getElementById('costManualUnitCost');
    const remarkEl = document.getElementById('costManualRemark');
    const unitCostRaw = (unitCostEl?.value || '').trim();
    const remark = (remarkEl?.value || '').trim();

    if (!unitCostRaw) {
        showToast('请录入最终成本', 'warning');
        unitCostEl?.focus();
        return;
    }
    const unitCost = parseDecimalInput(unitCostRaw, 6);
    if (unitCost == null) {
        showToast('最终成本须为非负数', 'warning');
        unitCostEl?.focus();
        return;
    }
    if (!remark) {
        showToast('备注不能为空', 'warning');
        remarkEl?.focus();
        return;
    }

    const saveBtn = document.getElementById('costManualSaveBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...'
    }
    try {
        const res = await HttpClient.patch(`${API_BASE}/${costId}`, {
            unit_cost: unitCost,
            remark,
        });
        showToast(res.message || '最终成本已保存', 'success');
        await loadList(listState.page);
        showDetailDrawer(res.data || {});
    } catch (error) {
        showToast(error.message || '保存失败', 'error');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = '保存最终成本'
        }
    }
}

function detailBlock(title, rows) {
    return `
        <div class="bg-app-hud border border-line-subtle overflow-hidden rounded-sm">
            <div class="px-4 py-2 bg-app-main border-b border-line-subtle text-[10px] font-bold text-ink-muted tracking-wider flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3 bg-brand-hud shrink-0"></span>
                    <span>${esc(title)}</span>
                </div>
            </div>
            <div class="divide-y divide-line-hud">
                ${rows
                    .map(([k, v]) => {
                        const isHtml =
                            typeof v === 'string' && (v.startsWith('<span') || v.includes('</span>'));
                        return `
                        <div class="flex items-center justify-between gap-4 px-4 py-2 hover:bg-app-main transition-colors">
                            <span class="text-ink-faint shrink-0 text-[10px]">${esc(k)}</span>
                            <span class="text-ink text-right font-mono text-[10px] break-all tabular-nums">${isHtml ? v : esc(String(v))}</span>
                        </div>`;
                    })
                    .join('')}
            </div>
        </div>`;
}

function closeDetailDrawer() {
    document.getElementById('costDetailBackdrop')?.remove();
    document.getElementById('costDetailDrawer')?.remove();
    if (listState._onEscClose) {
        document.removeEventListener('keydown', listState._onEscClose);
        listState._onEscClose = null;
    }
}

function bindBatchAuditDrawerEvents() {
    document.getElementById('closeCostBatchAuditDrawer')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('cancelCostBatchAuditBtn')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('costBatchAuditDrawerBackdrop')?.addEventListener('click', closeBatchAuditDrawer);
    document.getElementById('confirmCostBatchAuditBtn')?.addEventListener('click', () => submitBatchAudit());
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
    const scope = requireAuditScope();
    if (!scope) return;

    const modeEl = document.getElementById('costBatchAuditMode');
    const titleEl = document.getElementById('costBatchAuditDrawerTitle');
    const hintEl = document.getElementById('costBatchAuditHint');
    const operatorLabel = document.getElementById('costBatchAuditOperatorLabel');
    const remarkLabel = document.getElementById('costBatchAuditRemarkLabel');
    const operatorDisplay = document.getElementById('costBatchAuditOperatorDisplay');
    const remarkEl = document.getElementById('costBatchAuditRemark');
    const summaryEl = document.getElementById('costBatchAuditFilterSummary');
    const confirmBtn = document.getElementById('confirmCostBatchAuditBtn');

    if (modeEl) modeEl.value = isApprove ? 'approve' : 'reverse';
    if (titleEl) titleEl.textContent = isApprove ? '批量审核' : '批量反审核';
    if (hintEl) {
        hintEl.textContent = isApprove
            ? '按年度、月份、基地、项目处理待审记录（整车各厂）；版本可选。已通过记录会跳过。'
            : '按年度、月份、基地、项目处理已通过记录（整车各厂）；版本可选。其余状态会跳过。反审核意见必填。';
    }
    if (operatorLabel) operatorLabel.textContent = isApprove ? '审核人' : '反审核人';
    if (operatorDisplay) {
        operatorDisplay.textContent = getSessionDisplayName() || '（当前登录用户）';
    }
    if (remarkLabel) {
        remarkLabel.innerHTML = isApprove
            ? '审核意见<span class="text-brand">*</span>'
            : '反审核意见<span class="text-brand">*</span>';
    }
    if (remarkEl) {
        remarkEl.value = '';
        remarkEl.placeholder = isApprove ? '请填写审核意见（必填）' : '请填写反审核原因（必填）';
    }
    if (summaryEl) {
        summaryEl.textContent =
            `${fmtPeriod(scope.year, scope.month)} · 基地 ${scope.location} · 项目 ${scope.vehicle_model}`
            + ` · 版本 ${scope.version || '全部'} · 工厂 整车`;
    }
    if (confirmBtn) {
        confirmBtn.textContent = isApprove ? '确认审核通过' : '确认反审核';
        confirmBtn.className =
            BTN_SOLID;
    }

    openDrawer('costBatchAuditDrawer', 'costBatchAuditDrawerBackdrop');
}

function closeBatchAuditDrawer() {
    if (listState.batchAuditSubmitting) return;
    closeDrawer('costBatchAuditDrawer', 'costBatchAuditDrawerBackdrop');
}

async function submitBatchAudit() {
    if (listState.batchAuditSubmitting) return;
    const mode = document.getElementById('costBatchAuditMode')?.value || 'approve';
    const isApprove = mode === 'approve';
    const scope = requireAuditScope();
    if (!scope) return;

    const remark = document.getElementById('costBatchAuditRemark')?.value.trim() || '';
    if (!remark) {
        showToast(isApprove ? '审核意见必填' : '反审核意见必填', 'warning');
        return;
    }

    const confirmBtn = document.getElementById('confirmCostBatchAuditBtn');
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
            response = await HttpClient.post(`${API_BASE}/batch-reverse-audit`, body);
        }
        const result = response.data || {};
        const updated = result.updated_count ?? 0;
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
        showToast(error.message || (isApprove ? '审核失败' : '反审核失败'), 'error');
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
    if (!await window.confirmAction('确认删除当前范围未审核记录？已审核将跳过。')) return;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        showToast(res.message || '删除完成', 'success');
        loadList(1);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

async function exportExcel() {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const filters = getFilters();
    if (!filters.vehicle_model) {
        setAdvancedOpen(true);
        showToast(EXPORT_VEHICLE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params: {
                year: filters.year || undefined,
                month: filters.month || undefined,
                location: filters.location || undefined,
                stamping_supplier: filters.stamping_supplier || undefined,
                vehicle_model: filters.vehicle_model,
                version: filters.version || undefined,
                audit_status: filters.audit_status || undefined,
                part_number: filters.part_number || undefined,
            },
            defaultFilename: '冲压零件核价结果.xlsx',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(`导出成功: ${filename}`, 'success');
    } catch (error) {
        if (!error.status) {
            showToast(error.message || '导出失败', 'error');
        }
    }
}

export const pageConfig = {
    render: partCostListTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
