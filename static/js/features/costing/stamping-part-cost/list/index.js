/**
 * 冲压零件价格一览
 */

import {
    partCostListTemplate,
    renderCostPagination,
    renderCostRows,
    updatePartCostHud,
    updateCostFilterCapsules,
    shortPartNumber,
    syncBreakdownColumnVisibility,
} from './template.js?v=34';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/stamping/part-costs';
const CASCADE_API = '/api/stamping/filters/cascade';

const FILTER_IDS = [
    'costYearFilter',
    'costMonthFilter',
    'costLocationFilter',
    'costSupplierFilter',
    'costAuditFilter',
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
    breakdownColsOpen: false,
    advancedOpen: false,
    _onDocClick: null,
    _onEscClose: null,
};

function init() {
    applyPermissionUi();
    bindEvents();
    bindPageSizeSelect('costPageSize', {
        getSize: () => listState.pageSize,
        setSize: (size) => {
            listState.pageSize = size;
        },
        onChange: () => loadList(1),
    });
    fillMonthOptions();
    fillAuditOptions();
    applyQueryFromHash();
    updateCostFilterCapsules();
    syncBreakdownColumnVisibility(false);
    loadYearOptions().then(() => {
        loadCascadeFilters().then(() => updateCostFilterCapsules());
        loadList(1);
    });
}

function destroy() {
    closeDetailDrawer();
    setExportMenuOpen(false);
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
    listState.canUpdate = typeof can === 'function' ? can('op:stamping-part-cost:update') : true;
    if (!listState.canDelete) document.getElementById('costBatchDeleteBtn')?.classList.add('hidden');
    if (!listState.canApprove) document.getElementById('costBatchApproveBtn')?.classList.add('hidden');
    if (!listState.canReverse) document.getElementById('costBatchReverseBtn')?.classList.add('hidden');
    if (!listState.canExport) {
        document.getElementById('costExportWrap')?.classList.add('hidden');
    }
}

function setAdvancedOpen(isOpen) {
    listState.advancedOpen = isOpen;
    document.getElementById('costAdvancedFilterPanel')?.classList.toggle('hidden', !isOpen);
    const label = document.getElementById('costAdvancedFilterLabel');
    if (label) label.textContent = isOpen ? '收起高级筛选 : '展开高级筛选;
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
    let hasValue = false;
    Object.entries(map).forEach(([key, id]) => {
        const value = params.get(key);
        if (value) {
            const el = document.getElementById(id);
            if (el) {
                el.value = value;
                hasValue = true;
            }
        }
    });
    if (hasValue) setAdvancedOpen(true);
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

function onFilterChange() {
    updateCostFilterCapsules();
}

function bindEvents() {
    document.getElementById('costSearchBtn')?.addEventListener('click', () => {
        updateCostFilterCapsules();
        loadList(1);
    });
    document.getElementById('costToggleAdvancedFilter')?.addEventListener('click', () => {
        setAdvancedOpen(!listState.advancedOpen);
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
            updateCostFilterCapsules();
            loadList(1);
        }
    });
    document.getElementById('costPartNumberFilter')?.addEventListener('input', onFilterChange);

    document.getElementById('costYearFilter')?.addEventListener('change', () => {
        onFilterChange();
        loadCascadeFilters().then(() => {
            updateCostFilterCapsules();
            loadList(1);
        });
    });
    document.getElementById('costMonthFilter')?.addEventListener('change', () => {
        onFilterChange();
        loadList(1);
    });
    document.getElementById('costLocationFilter')?.addEventListener('change', () => {
        onFilterChange();
        loadCascadeFilters().then(() => {
            updateCostFilterCapsules();
            loadList(1);
        });
    });
    document.getElementById('costSupplierFilter')?.addEventListener('change', () => {
        onFilterChange();
        loadList(1);
    });
    document.getElementById('costAuditFilter')?.addEventListener('change', () => {
        onFilterChange();
        loadList(1);
    });

    document.getElementById('costBatchApproveBtn')?.addEventListener('click', () => batchApprove());
    document.getElementById('costBatchReverseBtn')?.addEventListener('click', () => batchReverse());
    document.getElementById('costBatchDeleteBtn')?.addEventListener('click', () => batchDelete());
    document.getElementById('costExportMenuBtn')?.addEventListener('click', (event) => {
        event.stopPropagation();
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

function fillMonthOptions() {
    const select = document.getElementById('costMonthFilter');
    if (!select) return;
    select.innerHTML =
        `<option value="">全部</option>` +
        Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${i + 1}</option>`).join('');
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

function fillSelect(id, values = [], preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        `<option value="">全部</option>` +
        values
            .map((value) => {
                const text = String(value);
                return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
            })
            .join('');
    if (preferredValue != null) select.value = String(preferredValue);
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
    });
    const partEl = document.getElementById('costPartNumberFilter');
    if (partEl) partEl.value = '';
    updateCostFilterCapsules();
    loadCascadeFilters().then(() => updateCostFilterCapsules());
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
        showToast('批量操作须选定年度、月份、基地、冲压工厂, 'warning');
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
    updateCostFilterCapsules();
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
        setListLoading(false);
        renderRows(listState.items);
        updatePartCostHud(listState.total, pageData.filters?.summary || null);
        const pageInfo = document.getElementById('costPageInfo');
        if (pageInfo) {
            pageInfo.textContent = `第${listState.page} / ${Math.max(listState.totalPages, 1)} 页· ${listState.total} 条`;
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
        updateCostFilterCapsules();
    } catch (error) {
        setListLoading(false);
        body.innerHTML = '';
        setListEmpty(true);
        updatePartCostHud(0, null);
        updateCostFilterCapsules();
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
    body.querySelectorAll('.btn-open-detail').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const costId = Number(btn.dataset.id);
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

    const backdrop = document.createElement('div');
    backdrop.id = 'costDetailBackdrop';
    backdrop.className = 'fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity duration-200';

    const drawer = document.createElement('div');
    drawer.id = 'costDetailDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-[85] w-[620px] max-w-[95vw] bg-[#0A0A0E] border-l border-[#1F1F2A] shadow-[-24px_0_60px_rgba(0,0,0,0.9)] flex flex-col font-mono text-[11px]';

    const failStatus = row.calc_status === 'failed';
    const isApproved = row.audit_status === 'approved';
    const canEditUnitCost = failStatus && listState.canUpdate && !isApproved;
    const auditText =
        row.audit_status === 'approved'
            ? '已审核
            : row.audit_status === 'rejected'
              ? '已驳回
              : '待审核;
    const auditBadgeColor =
        row.audit_status === 'approved'
            ? 'text-[#8E8E93] bg-[#161620] border-[#2A2A38]'
            : row.audit_status === 'rejected'
              ? 'text-[#ef5350] bg-[#1A080A] border-[#ef5350]/30'
              : 'text-[#FF1E27] bg-[#1A080A] border-[#FF1E27]/30';

    const unitCostDisplay =
        row.unit_cost == null || row.unit_cost === ''
            ? '—'
            : `￥${esc(fmtNum(row.unit_cost, 4))}`;

    const heroCostHtml = canEditUnitCost
        ? `
            <div class="text-right shrink-0 w-[200px]">
                <label class="block text-[9px] text-[#6E6E73] mb-1 tracking-wider">最终成本（元）</label>
                <div class="flex items-center justify-end gap-1">
                    <span class="text-[#FF1E27] text-sm font-bold">￥</span>
                    <input type="number" id="costManualUnitCost" min="0" step="0.000001"
                           value="${row.unit_cost == null ? '' : esc(String(row.unit_cost))}"
                           class="w-full h-9 px-2 text-right text-[16px] font-black tabular-nums bg-[#0A0A0E] border border-[#FF1E27]/40 text-[#FF1E27] placeholder:text-[#3A3A42] focus:outline-none focus:border-[#FF1E27] rounded-sm"
                           placeholder="0.0000">
                </div>
            </div>
        `
        : `
            <div class="text-right shrink-0">
                <div class="text-[28px] font-black tabular-nums text-[#FF1E27] leading-none"
                     style="text-shadow: 0 0 14px rgba(255,30,39,0.5);">
                    ${unitCostDisplay}
                </div>
            </div>
        `;

    const editPanelHtml = canEditUnitCost
        ? `
        <div class="px-6 py-4 border-b border-[#1A1A24] bg-[#0C0C10] shrink-0 space-y-3">
            <div class="flex items-center gap-2 text-[10px] text-[#FF1E27]">
                <span class="w-1.5 h-1.5 bg-[#FF1E27] rounded-full"></span>
                <span class="font-bold tracking-wider">计算失败 · 可手工录入最终成本</span>
            </div>
            ${row.calc_fail_reason ? `
                <div class="text-[10px] text-[#8E8E93] leading-relaxed bg-[#1A080A] border border-[#FF1E27]/20 px-3 py-2 rounded-sm">
                    失败原因：${esc(row.calc_fail_reason)}
                </div>
            ` : ''}
            <div>
                <label class="block text-[9px] text-[#6E6E73] mb-1.5 tracking-wider">
                    备注 <span class="text-[#FF1E27]">*</span>
                </label>
                <textarea id="costManualRemark" rows="3" maxlength="500"
                          class="w-full px-3 py-2 text-[11px] bg-[#0A0A0E] border border-[#2A2A38] text-[#E8E8ED] placeholder:text-[#555555] focus:outline-none focus:border-[#FF1E27] rounded-sm resize-none"
                          placeholder="必填：说明手工改价原因">${esc(row.remark || '')}</textarea>
            </div>
            <div class="flex items-center justify-end gap-2">
                <button type="button" id="costManualSaveBtn"
                        class="inline-flex items-center justify-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    保存最终成本
                </button>
            </div>
        </div>
        `
        : failStatus && isApproved
          ? `
        <div class="px-6 py-3 border-b border-[#1A1A24] bg-[#0C0C10] shrink-0 text-[10px] text-[#8E8E93]">
            已审核通过，请先反审核后再手工改价。
        </div>
        `
          : '';

    drawer.innerHTML = `
        <div class="px-6 py-4 flex items-center justify-between shrink-0 bg-[#0E0E12] border-b border-[#1A1A24]">
            <div class="flex items-center gap-3 min-w-0">
                ${shortNo ? `
                    <div class="flex items-center justify-center px-2.5 py-1 bg-[#1A080A] border border-[#FF1E27]/40 text-[#FF1E27] font-black text-[14px] tracking-widest tabular-nums rounded-sm shrink-0"
                         style="text-shadow: 0 0 10px rgba(255,30,39,0.45);">
                        ${esc(shortNo)}
                    </div>
                ` : ''}
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <h5 class="text-[13px] font-bold tracking-wide text-[#F0F0F2] truncate">${esc(row.part_name || '零件核算详情')}</h5>
                        <span class="text-[9px] px-1.5 py-0.5 border ${auditBadgeColor} rounded-sm shrink-0">${auditText}</span>
                    </div>
                    <div class="text-[10px] text-[#555555] tracking-wide mt-0.5 truncate">${esc(row.part_number || '—')}</div>
                </div>
            </div>
            <button type="button" id="closeCostDetailDrawer"
                    class="w-7 h-7 flex items-center justify-center bg-[#121216] border border-[#22222A] text-[#6E6E73] hover:text-[#F0F0F2] hover:border-[#FF1E27]/50 hover:bg-[#1A080A] rounded-sm transition-all shrink-0 ml-4"
                    title="关闭">
                ✕
            </button>
        </div>

        <div class="px-6 py-4 border-b border-[#1A1A24] bg-[#0F0708] relative overflow-hidden shrink-0">
            <div class="absolute right-0 top-0 bottom-0 w-40 bg-gradient-to-l from-[#FF1E27]/[0.12] to-transparent pointer-events-none"></div>
            <div class="flex items-end justify-between relative z-10 gap-4">
                <div class="min-w-0">
                    <div class="text-[9px] font-bold tracking-widest text-[#FF1E27] mb-1.5 flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 bg-[#FF1E27] rounded-full animate-pulse"></span>
                        单件核算成本
                    </div>
                    <div class="text-[10px] text-[#6E6E73] font-mono">
                        原材料 R <span class="text-[#E8E8ED]">￥${fmtNum(row.material_net_per_part, 2)}</span>
                        <span class="text-[#3A3A42] mx-1">+</span>
                        加工费<span class="text-[#E8E8ED]">￥${fmtNum(row.process_fee_amount, 2)}</span>
                    </div>
                </div>
                ${heroCostHtml}
            </div>
        </div>

        ${editPanelHtml}

        <div class="flex-1 overflow-y-auto p-6 space-y-4 text-[#8E8E93] bg-[#0A0A0E]">
            ${detailBlock('基础属总, [
                ['零件史, row.part_number || '—'],
                ['短号', shortNo || '—'],
                ['零件名称', row.part_name || '—'],
                ['基地 / 工厂', `${row.location || '—'} / ${row.stamping_supplier || '—'}`],
                ['核算年月', `${row.year}-${String(row.month).padStart(2, '0')}`],
                ['车型 / 版本', `${row.vehicle_model || '—'} / ${row.version || '—'}`],
                ['材质 / 厚度', `${row.material || '—'} / ${fmtNum(row.thickness, 3)} mm`],
                ['料片尺寸', `${fmtNum(row.sheet_length, 2)} × ${fmtNum(row.sheet_width, 2)} mm`],
                ['可制件数', row.parts_per_sheet ?? '—'],
                ['成品单重', `${fmtNum(row.part_weight, 4)} kg`],
            ])}

            ${detailBlock('过程计算量, [
                [
                    '密度 / 损耗/ 回收',
                    `${fmtNum(row.density, 2)} g/cm³ · ${fmtNum((Number(row.material_loss_rate) || 0) * 1000, 2)}—· ${fmtNum((Number(row.scrap_recovery_rate) || 0) * 100, 1)}%`,
                ],
                ['预估单件材料消耗M', `${fmtNum(row.blank_weight_kg, 7)} kg`],
                ['零件净量', `${fmtNum(row.finished_total_kg, 7)} kg`],
                ['废料重量 O', `${fmtNum(row.scrap_weight_kg, 7)} kg`],
                [
                    '材料利用率,
                    `<span class="text-[#F0F0F2] font-bold">${fmtNum(row.material_utilization_pct, 2)} %</span>`,
                ],
            ])}

            ${detailBlock('价格与吨价, [
                ['钢厂', row.steel_mill || '—'],
                ['钢材吨价 P', `￥${fmtNum(row.steel_ton_price, 2)} /t`],
                ['废料吨价 Q', `￥${fmtNum(row.scrap_ton_price, 2)} /t`],
            ])}

            ${detailBlock('原材料成本拆解（R = ①−③−③）', [
                ['③钢材采购成本（含损耗）', `￥${fmtNum(row.material_amount_sheet, 4)}`],
                ['③损耗废料扣除（回收率）', `￥${fmtNum(row.loss_scrap_deduction, 4)}`],
                ['③边角废料扣除（回收率）', `￥${fmtNum(row.process_scrap_deduction, 4)}`],
                ['废料扣除小计（② + ③）', `￥${fmtNum(row.scrap_amount_sheet, 4)}`],
                [
                    '原材料净成本 R',
                    `<span class="text-[#FF1E27] font-semibold">￥${fmtNum(row.material_net_per_part, 4)}</span>`,
                ],
                ['加工费', `￥${fmtNum(row.process_fee_amount, 3)}`],
            ])}

            ${detailBlock('状态与来源', [
                [
                    '计算状态',
                    failStatus
                        ? `<span class="text-[#FF1E27] font-bold bg-[#FF1E27]/10 px-1.5 py-0.5 border border-[#FF1E27]/30">失败（${esc(row.calc_fail_reason || '未知原因')}）</span>`
                        : '<span class="text-[#E8E8ED]">正常</span>',
                ],
                ['备注', row.remark || '—'],
                ['来源文件', row.excel_filename || '—'],
                ['工作表, row.excel_sheet_name || '—'],
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
        showToast('无改价权除, 'warning');
        return;
    }
    const unitCostEl = document.getElementById('costManualUnitCost');
    const remarkEl = document.getElementById('costManualRemark');
    const unitCostRaw = (unitCostEl?.value || '').trim();
    const remark = (remarkEl?.value || '').trim();

    if (!unitCostRaw) {
        showToast('请录入最终成本, 'warning');
        unitCostEl?.focus();
        return;
    }
    const unitCost = Number(unitCostRaw);
    if (!Number.isFinite(unitCost) || unitCost < 0) {
        showToast('最终成本须为非负数存, 'warning');
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
        saveBtn.textContent = '保存中—;
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
            saveBtn.textContent = '保存最终成本;
        }
    }
}

function detailBlock(title, rows) {
    return `
        <div class="bg-[#0C0C10] border border-[#1A1A24] overflow-hidden rounded-sm">
            <div class="px-4 py-2 bg-[#121218] border-b border-[#1A1A24] text-[10px] font-bold text-[#A0A0AB] tracking-wider flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3 bg-[#FF1E27] shrink-0"></span>
                    <span>${esc(title)}</span>
                </div>
            </div>
            <div class="divide-y divide-[#14141C]">
                ${rows
                    .map(([k, v]) => {
                        const isHtml =
                            typeof v === 'string' && (v.startsWith('<span') || v.includes('</span>'));
                        return `
                        <div class="flex items-center justify-between gap-4 px-4 py-2 hover:bg-[#121218] transition-colors">
                            <span class="text-[#555555] shrink-0 text-[10px]">${esc(k)}</span>
                            <span class="text-[#D1D1D6] text-right font-mono text-[10px] break-all tabular-nums">${isHtml ? v : esc(String(v))}</span>
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

async function batchApprove() {
    if (!listState.canApprove) return showToast('无审核权除, 'warning');
    const scope = requireScope();
    if (!scope) return;
    if (!window.confirm('确认批量审核通过当前范围（)) return;
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
        showToast('反审核原因必填, 'warning');
        return;
    }
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-reverse-audit`, {
            ...scope,
            reverse_audit_remark: remark.trim(),
        });
        showToast(res.message || '反审核完成, 'success');
        loadList(listState.page);
    } catch (error) {
        showToast(error.message || '反审核失败, 'error');
    }
}

async function batchDelete() {
    if (!listState.canDelete) return showToast('无删除权除, 'warning');
    const scope = requireScope();
    if (!scope) return;
    if (!window.confirm('确认删除当前范围未审核记录？已审核将跳过。)) return;
    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        showToast(res.message || '删除完成', 'success');
        loadList(1);
    } catch (error) {
        showToast(error.message || '删除失败', 'error');
    }
}

async function exportExcel(exportFormat = 'process_sheet') {
    if (!listState.canExport) return showToast('无导出权除, 'warning');
    const filters = getFilters();
    if (!Object.values(filters).some(Boolean)) {
        showToast('请至少选择一个筛选条件后再导出, 'warning');
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
