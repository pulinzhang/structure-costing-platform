/**
 * 冲压零件价格一览
 */

import {
    partCostListTemplate,
    renderCostPagination,
    renderCostRows,
    updatePartCostHud,
    shortPartNumber,
    syncBreakdownColumnVisibility,
} from './template.js?v=25';

const API_BASE = '/api/stamping/part-costs';
const CASCADE_API = '/api/stamping/filters/cascade';
const PAGE_SIZE = 10;

const FILTER_IDS = [
    'costYearFilter',
    'costMonthFilter',
    'costLocationFilter',
    'costSupplierFilter',
    'costAuditFilter',
];

const listState = {
    page: 1,
    total: 0,
    totalPages: 1,
    items: [],
    canDelete: true,
    canApprove: true,
    canReverse: true,
    canExport: true,
    breakdownColsOpen: false,
    _onDocClick: null,
};

function init() {
    applyPermissionUi();
    bindEvents();
    fillMonthOptions();
    fillAuditOptions();
    applyQueryFromHash();
    FILTER_IDS.forEach((id) => syncFilterChip(id));
    syncBatchBarVisibility();
    syncBreakdownColumnVisibility(false);
    loadYearOptions().then(() => {
        loadCascadeFilters().then(() => syncBatchBarVisibility());
        loadList(1);
    });
}

function destroy() {
    closeDetailDrawer();
    setExportMenuOpen(false);
    closeAllFilterMenus();
    if (listState._onDocClick) {
        document.removeEventListener('click', listState._onDocClick);
        listState._onDocClick = null;
    }
}

function applyPermissionUi() {
    listState.canDelete = typeof can === 'function' ? can('op:stamping-part-cost:delete') : true;
    listState.canApprove = typeof can === 'function' ? can('op:stamping-part-cost:approve') : true;
    listState.canReverse = typeof can === 'function' ? can('op:stamping-part-cost:reverse') : true;
    listState.canExport = typeof can === 'function' ? can('op:stamping-part-cost:export') : true;
    if (!listState.canDelete) document.getElementById('costBatchDeleteBtn')?.classList.add('hidden');
    if (!listState.canApprove) document.getElementById('costBatchApproveBtn')?.classList.add('hidden');
    if (!listState.canReverse) document.getElementById('costBatchReverseBtn')?.classList.add('hidden');
    if (!listState.canExport) {
        document.getElementById('costExportWrap')?.classList.add('hidden');
    }
}

function hasBatchScope() {
    const f = getFilters();
    return Boolean(f.year && f.month && f.location && f.stamping_supplier);
}

function hasAnyBatchPermission() {
    return listState.canApprove || listState.canReverse || listState.canDelete;
}

/** 年/月/基地/工厂齐全时才露出批量条（本页批量为「按范围」，非勾选行） */
function syncBatchBarVisibility() {
    const bar = document.getElementById('costBatchBar');
    const show = hasBatchScope() && hasAnyBatchPermission();
    if (bar) {
        bar.classList.toggle('hidden', !show);
        bar.classList.toggle('flex', show);
    }
}

function setExportMenuOpen(isOpen) {
    const menu = document.getElementById('costExportMenu');
    const trigger = document.getElementById('costExportMenuBtn');
    if (!menu) return;
    menu.classList.toggle('hidden', !isOpen);
    if (trigger) trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

function applyQueryFromHash() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return;
    const params = new URLSearchParams(hash.slice(qIndex + 1));
    const map = {
        year: 'costYearFilter',
        month: 'costMonthFilter',
        location: 'costLocationFilter',
        stamping_supplier: 'costSupplierFilter',
    };
    Object.entries(map).forEach(([key, id]) => {
        const value = params.get(key);
        if (value) {
            const el = document.getElementById(id);
            if (el) {
                el.value = value;
                syncFilterChip(id);
            }
        }
    });
}

function toggleBreakdownColumns() {
    listState.breakdownColsOpen = !listState.breakdownColsOpen;
    syncBreakdownColumnVisibility(listState.breakdownColsOpen);
}

function setListLoading(isLoading) {
    const loading = document.getElementById('costLoading');
    const empty = document.getElementById('costEmpty');
    if (loading) loading.classList.toggle('hidden', !isLoading);
    if (isLoading && empty) empty.classList.add('hidden');
}

function setListEmpty(isEmpty) {
    const empty = document.getElementById('costEmpty');
    if (empty) empty.classList.toggle('hidden', !isEmpty);
}

function closeAllFilterMenus(exceptChip = null) {
    document.querySelectorAll('.cost-filter-chip').forEach((chip) => {
        if (exceptChip && chip === exceptChip) return;
        const menu = chip.querySelector('.cost-filter-menu');
        const trigger = chip.querySelector('.cost-filter-trigger');
        menu?.classList.add('hidden');
        trigger?.setAttribute('aria-expanded', 'false');
    });
}

/** 根据隐藏 select 同步暗色菜单与触发器文案 */
function syncFilterChip(selectId) {
    const select = document.getElementById(selectId);
    const chip = document.querySelector(`.cost-filter-chip[data-filter-id="${selectId}"]`);
    if (!select || !chip) return;

    const labelEl = chip.querySelector('.cost-filter-label');
    const menu = chip.querySelector('.cost-filter-menu');
    if (!labelEl || !menu) return;

    const current = String(select.value ?? '');
    const selectedOpt = Array.from(select.options).find((opt) => opt.value === current);
    labelEl.textContent = selectedOpt ? selectedOpt.textContent : (select.dataset.emptyLabel || '全部');
    labelEl.classList.toggle('text-[#E8E8ED]', Boolean(current));
    labelEl.classList.toggle('text-[#8E8E93]', !current);

    const idleClass =
        'w-full px-3 py-1.5 text-left text-[11px] font-mono transition-colors text-[#9e9e9e] hover:bg-[#161620] hover:text-[#ffffff]';
    const activeClass =
        'w-full px-3 py-1.5 text-left text-[11px] font-mono transition-colors bg-[#161620] text-[#ffffff]';

    menu.innerHTML = Array.from(select.options)
        .map((opt) => {
            const value = opt.value;
            const isActive = value === current;
            return `<button type="button" role="option" data-value="${esc(value)}" aria-selected="${isActive}"
                class="${isActive ? activeClass : idleClass}">${esc(opt.textContent || '')}</button>`;
        })
        .join('');
}

function onFilterValueChange(selectId) {
    syncFilterChip(selectId);
    syncBatchBarVisibility();
    if (selectId === 'costYearFilter' || selectId === 'costLocationFilter') {
        loadCascadeFilters().then(() => syncBatchBarVisibility());
    }
}

function bindEvents() {
    document.getElementById('costSearchBtn')?.addEventListener('click', () => {
        syncBatchBarVisibility();
        loadList(1);
    });
    document.getElementById('costToggleBreakdownCols')?.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleBreakdownColumns();
    });
    document.getElementById('costResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('costPartNumberFilter')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            syncBatchBarVisibility();
            loadList(1);
        }
    });

    document.querySelectorAll('.cost-filter-chip').forEach((chip) => {
        const selectId = chip.dataset.filterId;
        const trigger = chip.querySelector('.cost-filter-trigger');
        const menu = chip.querySelector('.cost-filter-menu');
        trigger?.addEventListener('click', (event) => {
            event.stopPropagation();
            setExportMenuOpen(false);
            const isOpen = menu && !menu.classList.contains('hidden');
            closeAllFilterMenus();
            if (!isOpen && menu) {
                menu.classList.remove('hidden');
                trigger.setAttribute('aria-expanded', 'true');
            }
        });
        menu?.addEventListener('click', (event) => {
            const item = event.target.closest('[data-value]');
            if (!item || !selectId) return;
            event.stopPropagation();
            const select = document.getElementById(selectId);
            if (!select) return;
            const nextValue = item.getAttribute('data-value') ?? '';
            if (select.value !== nextValue) {
                select.value = nextValue;
                onFilterValueChange(selectId);
            } else {
                syncFilterChip(selectId);
            }
            closeAllFilterMenus();
        });
    });

    document.getElementById('costBatchApproveBtn')?.addEventListener('click', () => batchApprove());
    document.getElementById('costBatchReverseBtn')?.addEventListener('click', () => batchReverse());
    document.getElementById('costBatchDeleteBtn')?.addEventListener('click', () => batchDelete());
    document.getElementById('costExportMenuBtn')?.addEventListener('click', (event) => {
        event.stopPropagation();
        closeAllFilterMenus();
        const menu = document.getElementById('costExportMenu');
        const isOpen = menu && !menu.classList.contains('hidden');
        setExportMenuOpen(!isOpen);
    });
    document.getElementById('costExportBtn')?.addEventListener('click', () => {
        setExportMenuOpen(false);
        exportExcel('process_sheet');
    });
    document.getElementById('costExportDetailBtn')?.addEventListener('click', () => {
        setExportMenuOpen(false);
        exportExcel('detail');
    });
    listState._onDocClick = (event) => {
        const exportWrap = document.getElementById('costExportWrap');
        if (exportWrap && !exportWrap.contains(event.target)) {
            setExportMenuOpen(false);
        }
        if (!event.target.closest('.cost-filter-chip')) {
            closeAllFilterMenus();
        }
    };
    document.addEventListener('click', listState._onDocClick);
    document.getElementById('costPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.cost-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadList(page);
        }
    });
}

function emptyOptionLabel(select) {
    return select?.dataset?.emptyLabel || '全部';
}

function fillMonthOptions() {
    const select = document.getElementById('costMonthFilter');
    if (!select) return;
    const emptyLabel = emptyOptionLabel(select);
    select.innerHTML =
        `<option value="">${esc(emptyLabel)}</option>` +
        Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${i + 1}</option>`).join('');
    syncFilterChip('costMonthFilter');
}

function fillAuditOptions() {
    const select = document.getElementById('costAuditFilter');
    if (!select) return;
    const emptyLabel = emptyOptionLabel(select);
    select.innerHTML = `
        <option value="">${esc(emptyLabel)}</option>
        <option value="pending">待审</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
    `;
    syncFilterChip('costAuditFilter');
}

function fillSelect(id, values = [], preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    const emptyLabel = emptyOptionLabel(select);
    select.innerHTML =
        `<option value="">${esc(emptyLabel)}</option>` +
        values
            .map((value) => {
                const text = String(value);
                return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
            })
            .join('');
    if (preferredValue != null) select.value = String(preferredValue);
    syncFilterChip(id);
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        fillSelect('costYearFilter', Array.isArray(res.data) ? res.data : []);
    } catch (error) {
        console.error(error);
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: document.getElementById('costLocationFilter')?.value || '',
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('costLocationFilter', filters.locations || []);
        fillSelect('costSupplierFilter', filters.stamping_suppliers || []);
    } catch (error) {
        console.error(error);
    }
}

function resetFilters() {
    FILTER_IDS.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
        syncFilterChip(id);
    });
    const partEl = document.getElementById('costPartNumberFilter');
    if (partEl) partEl.value = '';
    syncBatchBarVisibility();
    loadCascadeFilters().then(() => syncBatchBarVisibility());
    loadList(1);
}

function getFilters() {
    const yearRaw = document.getElementById('costYearFilter')?.value;
    const monthRaw = document.getElementById('costMonthFilter')?.value;
    return {
        year: yearRaw ? Number(yearRaw) : undefined,
        month: monthRaw ? Number(monthRaw) : undefined,
        location: document.getElementById('costLocationFilter')?.value || undefined,
        stamping_supplier: document.getElementById('costSupplierFilter')?.value || undefined,
        audit_status: document.getElementById('costAuditFilter')?.value || undefined,
        part_number: document.getElementById('costPartNumberFilter')?.value?.trim() || undefined,
    };
}

function requireScope() {
    const f = getFilters();
    if (!f.year || !f.month || !f.location || !f.stamping_supplier) {
        showToast('批量操作须选定年度、月份、基地、冲压工厂', 'warning');
        return null;
    }
    return {
        year: f.year,
        month: f.month,
        location: f.location,
        stamping_supplier: f.stamping_supplier,
    };
}

async function loadList(page = 1) {
    const body = document.getElementById('costTableBody');
    if (!body) return;
    setListLoading(true);
    body.innerHTML = '';
    try {
        const filters = getFilters();
        const res = await HttpClient.get(API_BASE, {
            params: { ...filters, page, size: PAGE_SIZE },
        });
        const pageData = res.data || {};
        listState.page = pageData.page || page;
        listState.total = pageData.total || 0;
        listState.totalPages = pageData.total_pages || 1;
        listState.items = Array.isArray(pageData.items) ? pageData.items : [];
        setListLoading(false);
        renderRows(listState.items);
        updatePartCostHud(listState.total, pageData.filters?.summary || null);
        const pageInfo = document.getElementById('costPageInfo');
        if (pageInfo) {
            pageInfo.textContent = `第 ${listState.page} / ${Math.max(listState.totalPages, 1)} 页 · ${listState.total} 条`;
        }
        const pagination = document.getElementById('costPagination');
        if (pagination) {
            pagination.innerHTML = renderCostPagination(listState.page, listState.totalPages);
        }
        if (pageData.filters) {
            if (pageData.filters.years) fillSelect('costYearFilter', pageData.filters.years, filters.year);
            if (pageData.filters.locations) {
                fillSelect('costLocationFilter', pageData.filters.locations, filters.location);
            }
            if (pageData.filters.suppliers) {
                fillSelect('costSupplierFilter', pageData.filters.suppliers, filters.stamping_supplier);
            }
        }
        syncBatchBarVisibility();
    } catch (error) {
        setListLoading(false);
        body.innerHTML = '';
        setListEmpty(true);
        updatePartCostHud(0, null);
        syncBatchBarVisibility();
        showToast(error.message || '加载失败', 'error');
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
    body.innerHTML = renderCostRows(items, listState.breakdownColsOpen);
    syncBreakdownColumnVisibility(listState.breakdownColsOpen);
    body.querySelectorAll('.cost-row').forEach((row) => {
        row.addEventListener('click', () => {
            const costId = Number(row.dataset.id);
            if (costId) openDetail(costId);
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
    const titlePart = shortNo
        ? `${shortNo} · ${row.part_number || ''}`
        : (row.part_number || '');
    const backdrop = document.createElement('div');
    backdrop.id = 'costDetailBackdrop';
    backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm';
    const drawer = document.createElement('div');
    drawer.id = 'costDetailDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-[85] w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333]">
            <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase flex items-center gap-2">
                <span class="text-[#FF1E27] font-mono text-sm tracking-[0.14em]">${esc(shortNo || '')}</span>
                <span>核算详情 · ${esc(titlePart)}</span>
            </h5>
            <button type="button" id="closeCostDetailDrawer" class="w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] rounded-md">×</button>
        </div>
        <div class="flex-1 overflow-y-auto p-5 space-y-4 text-[11px] text-[#9e9e9e]">
            ${detailBlock('基础信息', [
                ['零件号', row.part_number || '-'],
                ['短号', shortNo || '-'],
                ['基地/工厂', `${row.location || '-'} / ${row.stamping_supplier || '-'}`],
                ['年月', `${row.year}-${String(row.month).padStart(2, '0')}`],
                ['车型/版本', `${row.vehicle_model || '-'} / ${row.version || '-'}`],
                ['零件名', row.part_name || '-'],
                ['材质/料厚', `${row.material || '-'} / ${fmtNum(row.thickness, 3)}`],
                ['料片尺寸', `${fmtNum(row.sheet_length, 2)} × ${fmtNum(row.sheet_width, 2)}`],
                ['可制件数', row.parts_per_sheet ?? '-'],
                ['成品单重', fmtNum(row.part_weight, 4)],
            ])}
            ${detailBlock(`过程量（密度 ${fmtNum(row.density, 2)} g/cm³ · 损耗 ${fmtNum((Number(row.material_loss_rate) || 0) * 1000, 2)}‰ · 废料回收 ${fmtNum((Number(row.scrap_recovery_rate) || 0) * 100, 1)}%）`, [
                ['材料消耗 kg', fmtNum(row.blank_weight_kg, 7)],
                ['零件净重 kg', fmtNum(row.finished_total_kg, 7)],
                ['废料重量 kg', fmtNum(row.scrap_weight_kg, 7)],
                ['材料利用率 %', fmtNum(row.material_utilization_pct, 2)],
            ])}
            ${detailBlock('取价溯源', [
                ['钢厂', row.steel_mill || '-'],
                ['钢材吨价', fmtNum(row.steel_ton_price, 2)],
                ['废料吨价', fmtNum(row.scrap_ton_price, 2)],
                ['钢材价ID', row.steel_price_id ?? '-'],
                ['废料价ID', row.scrap_price_id ?? '-'],
                ['加工费ID', row.process_fee_id ?? '-'],
            ])}
            ${detailBlock('材料成本分项（原材料成本 = ①−②−③）', [
                ['① 钢材采购（含损耗）', fmtNum(row.material_amount_sheet, 6)],
                ['② 损耗废料扣除（回收率）', fmtNum(row.loss_scrap_deduction, 6)],
                ['③ 边角废料扣除（回收率）', fmtNum(row.process_scrap_deduction, 6)],
                ['废料扣除合计 ②+③', fmtNum(row.scrap_amount_sheet, 6)],
                ['原材料成本 R', fmtNum(row.material_net_per_part, 6)],
                ['加工费', fmtNum(row.process_fee_amount, 3)],
            ])}
            <div class="bg-[#111] border border-[#262626] overflow-hidden">
                <div class="px-3 py-2 bg-[#0c0c0c] border-b border-[#181818] text-[10px] text-[#777] uppercase tracking-wider">单件成本</div>
                <div class="px-3 py-4 flex items-baseline justify-between gap-3">
                    <span class="text-[#8E8E93]">原材料 R + 加工费</span>
                    <span class="text-[22px] font-mono font-black tabular-nums text-[#FF1E27]"
                          style="text-shadow: 0 0 10px rgba(255,30,39,0.4);">￥${esc(fmtNum(row.unit_cost, 4))}</span>
                </div>
            </div>
            ${detailBlock('溯源', [
                ['Excel', row.excel_filename || '-'],
                ['Sheet/行', `${row.excel_sheet_name || '-'} / ${row.excel_row ?? '-'}`],
                ['批次', row.calc_batch_id || '-'],
                ['公式版本', row.formula_version || '-'],
                ['失败原因', row.calc_fail_reason || '-'],
            ])}
        </div>
    `;
    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    backdrop.addEventListener('click', closeDetailDrawer);
    document.getElementById('closeCostDetailDrawer')?.addEventListener('click', closeDetailDrawer);
}

function detailBlock(title, rows) {
    return `
        <div class="bg-[#111] border border-[#262626] overflow-hidden">
            <div class="px-3 py-2 bg-[#0c0c0c] border-b border-[#181818] text-[10px] text-[#777] uppercase tracking-wider">${esc(title)}</div>
            <div class="divide-y divide-[#1a1a1a]">
                ${rows
                    .map(
                        ([k, v]) => `
                    <div class="flex justify-between gap-3 px-3 py-2">
                        <span class="text-[#616161] shrink-0">${esc(k)}</span>
                        <span class="text-[#ccc] text-right break-all">${esc(String(v))}</span>
                    </div>`,
                    )
                    .join('')}
            </div>
        </div>`;
}

function closeDetailDrawer() {
    document.getElementById('costDetailBackdrop')?.remove();
    document.getElementById('costDetailDrawer')?.remove();
}

async function batchApprove() {
    if (!listState.canApprove) return showToast('无审核权限', 'warning');
    const scope = requireScope();
    if (!scope) return;
    if (!window.confirm('确认批量审核通过当前范围？')) return;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-approve`, scope);
        showToast(res.message || '审核完成', 'success');
        loadList(listState.page);
    } catch (error) {
        showToast(error.message || '审核失败', 'error');
    }
}

async function batchReverse() {
    if (!listState.canReverse) return showToast('无反审核权限', 'warning');
    const scope = requireScope();
    if (!scope) return;
    const remark = window.prompt('请输入反审核原因');
    if (!remark || !remark.trim()) {
        showToast('反审核原因必填', 'warning');
        return;
    }
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-reverse-audit`, {
            ...scope,
            reverse_audit_remark: remark.trim(),
        });
        showToast(res.message || '反审核完成', 'success');
        loadList(listState.page);
    } catch (error) {
        showToast(error.message || '反审核失败', 'error');
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
        showToast(error.message || '删除失败', 'error');
    }
}

async function exportExcel(exportFormat = 'process_sheet') {
    if (!listState.canExport) return showToast('无导出权限', 'warning');
    const filters = getFilters();
    if (!Object.values(filters).some(Boolean)) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        return;
    }
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params: {
                year: filters.year || undefined,
                month: filters.month || undefined,
                location: filters.location || undefined,
                stamping_supplier: filters.stamping_supplier || undefined,
                audit_status: filters.audit_status || undefined,
                part_number: filters.part_number || undefined,
                export_format: exportFormat,
            },
            defaultFilename: exportFormat === 'detail'
                ? '冲压零件价格核算明细.xlsx'
                : '冲压零件工艺清单核价.xlsx',
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
