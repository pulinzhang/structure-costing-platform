/**
 * BOM 焊接费列表：HUD + 筛选 + 明细抽屉 + 批量审核/反审核/删除
 */

import {
    l0WeldingFeeListTemplate,
    renderL0WeldingFeeRows,
    renderL0WeldingFeePagination,
    updateL0WeldingFeeHud,
    updateL0WeldingFeeFilterCapsules,
    renderFeeDetailItems,
    resolveL0ShortPartNumber,
} from './template.js?v=8';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/bom/l0-welding-fees';
const DRAWER_ANIMATION_MS = 300;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目、版本';

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
    bindPageSizeSelect('l0wfPageSize', {
        getSize: () => feeState.pageSize,
        setSize: (size) => {
            feeState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
    fillAuditStatusOptions();
    applyHashFilters();
    loadFilterOptions().then(() => {
        updateCapsules();
        loadData(1);
    });
}

function destroy() {
    closeDetailDrawer();
    closeDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    if (!canFn('op:bom-l0-welding-fee-list:export')) {
        document.getElementById('l0wfExportBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-l0-welding-fee-list:approve')) {
        document.getElementById('l0wfBatchApproveBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-l0-welding-fee-list:reverse')) {
        document.getElementById('l0wfBatchReverseBtn')?.classList.add('hidden');
    }
    if (!canFn('op:bom-l0-welding-fee-list:delete')) {
        document.getElementById('l0wfBatchDeleteBtn')?.classList.add('hidden');
    }
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
    ['year', 'location', 'vehicle_model', 'bom_version'].forEach((key) => {
        const value = qs.get(key);
        if (!value) return;
        const idMap = {
            year: 'l0wfYearFilter',
            location: 'l0wfLocationFilter',
            vehicle_model: 'l0wfVehicleModelFilter',
            bom_version: 'l0wfBomVersionFilter',
        };
        const el = document.getElementById(idMap[key]);
        if (el) el.dataset.pending = value;
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

function getFilters() {
    const yearRaw = val('l0wfYearFilter');
    return {
        year: yearRaw ? Number(yearRaw) : null,
        location: val('l0wfLocationFilter') || null,
        vehicle_model: val('l0wfVehicleModelFilter') || null,
        bom_version: val('l0wfBomVersionFilter') || null,
        audit_status: val('l0wfAuditStatusFilter') || null,
        part_number: val('l0wfPartNumberFilter') || null,
        onlyPartial: feeState.onlyPartial,
    };
}

function updateCapsules() {
    updateL0WeldingFeeFilterCapsules(getFilters());
}

function fillSelect(id, values = [], preferred = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const pending = select.dataset.pending || null;
    const current = preferred ?? pending ?? select.value;
    delete select.dataset.pending;
    select.innerHTML =
        `<option value="">全部</option>` +
        values.map((v) => {
            const text = String(v);
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
        }).join('');
}

async function loadFilterOptions() {
    try {
        const yearRes = await HttpClient.get(`${API_BASE}/filters/years`);
        fillSelect('l0wfYearFilter', yearRes.data || []);
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
    document.getElementById('l0wfAuditStatusFilter')?.addEventListener('change', () => {
        updateCapsules();
        loadData(1);
    });
    document.getElementById('l0wfPartNumberFilter')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') loadData(1);
    });
    document.getElementById('l0wfPartNumberFilter')?.addEventListener('input', updateCapsules);

    document.getElementById('l0wfPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-wf-page]');
        if (!btn || btn.disabled) return;
        const page = Number(btn.getAttribute('data-wf-page'));
        if (Number.isFinite(page) && page >= 1) loadData(page);
    });

    document.getElementById('l0wfTableBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action="detail"]');
        if (!btn) return;
        event.preventDefault();
        event.stopPropagation();
        openDetailDrawer(Number(btn.dataset.id));
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
}

function resetFilters() {
    feeState.onlyPartial = false;
    ['l0wfYearFilter', 'l0wfLocationFilter', 'l0wfVehicleModelFilter', 'l0wfBomVersionFilter', 'l0wfAuditStatusFilter', 'l0wfPartNumberFilter']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
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
    return {
        year: f.year,
        location: f.location,
        vehicle_model: f.vehicle_model,
        bom_version: f.bom_version,
    };
}

async function loadData(page = feeState.page) {
    const body = document.getElementById('l0wfTableBody');
    const empty = document.getElementById('l0wfEmpty');
    if (body) {
        body.innerHTML = `<tr><td colspan="13" class="py-10 text-center text-[#555]">
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

        updateL0WeldingFeeHud(
            feeState.summary,
            f.bom_version || (f.vehicle_model ? f.vehicle_model : '—'),
        );
        updateCapsules();

        const totalLabel = document.getElementById('l0wfTotalLabel');
        if (totalLabel) totalLabel.textContent = `共 ${feeState.total} 条`;

        const pagination = document.getElementById('l0wfPagination');
        if (pagination) {
            pagination.innerHTML = renderL0WeldingFeePagination(feeState.page, feeState.totalPages);
        }

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
            body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
        }
    }
}

async function openDetailDrawer(feeId) {
    if (!feeId) return;
    try {
        const res = await HttpClient.get(`${API_BASE}/${feeId}`);
        const fee = res.data || {};
        showDetailDrawer(fee);
    } catch (error) {
        showToast(error.message || '加载明细失败', 'error');
    }
}

function closeDetailDrawer() {
    document.getElementById('l0wfDetailBackdrop')?.remove();
    document.getElementById('l0wfDetailDrawer')?.remove();
}

function showDetailDrawer(fee) {
    closeDetailDrawer();
    const shortNo = resolveL0ShortPartNumber(fee.part_number);
    const backdrop = document.createElement('div');
    backdrop.id = 'l0wfDetailBackdrop';
    backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm';

    const drawer = document.createElement('div');
    drawer.id = 'l0wfDetailDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-[85] w-[720px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333]">
            <div>
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">成品焊接费明细</h5>
                <p class="text-[12px] text-[#F0F0F2] mt-1 font-mono">
                    ${esc(shortNo)}
                    <span class="text-[10px] text-[#555] ml-2">${esc(fee.part_number || '')}</span>
                </p>
            </div>
            <button type="button" id="l0wfDetailClose"
                    class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        </div>
        <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] grid grid-cols-2 gap-2 shrink-0">
            <div>范围：${esc(fee.year)} · ${esc(fee.location)} · ${esc(fee.vehicle_model)} · ${esc(fee.bom_version)}</div>
            <div class="text-right">成品焊接费 <span class="font-mono text-[#FF1E27] text-[12px] font-bold">${esc(fmtNum(fee.total_l0_welding_fee, 4))}</span></div>
            <div>工艺 ${esc(fee.process_line_count ?? 0)} · 命中 ${esc(fee.matched_line_count ?? 0)} · 缺单价 ${esc(fee.missing_price_count ?? 0)}</div>
            <div class="text-right">${esc(fee.part_name || '-')}</div>
        </div>
        <div class="px-5 py-2.5 border-b border-[#222] shrink-0">
            <div class="text-[9px] tracking-wider text-[#555555] mb-1">焊接信息原文</div>
            <p class="text-[11px] text-[#6E6E73] leading-relaxed whitespace-pre-wrap break-words mb-0">${esc((fee.weld_info_raw || '').trim() || '—')}</p>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain">
            <table class="w-full border-collapse">
                <thead class="sticky top-0 bg-[#121212]">
                    <tr class="border-b border-[#222] text-[9px] text-[#555]">
                        <th class="px-2 py-2 text-left font-medium">标准工艺</th>
                        <th class="px-2 py-2 text-right font-medium">过程量</th>
                        <th class="px-2 py-2 text-right font-medium">单价</th>
                        <th class="px-2 py-2 text-left font-medium">单位</th>
                        <th class="px-2 py-2 text-right font-medium">行费</th>
                        <th class="px-2 py-2 text-center font-medium">匹配</th>
                    </tr>
                </thead>
                <tbody>${renderFeeDetailItems(fee.items || [])}</tbody>
            </table>
        </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    backdrop.addEventListener('click', closeDetailDrawer);
    document.getElementById('l0wfDetailClose')?.addEventListener('click', closeDetailDrawer);
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
    if (label) label.textContent = isReverse ? '反审核原因（必填）' : '审核意见（可选）';
    if (remark) {
        remark.value = '';
        remark.placeholder = isReverse ? '请填写反审核原因' : '可选';
    }
    if (scopeEl) {
        scopeEl.textContent = `${scope.year} · ${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}`;
    }
    openDrawer('l0wfBatchAuditDrawer', 'l0wfBatchAuditBackdrop');
}

async function submitBatchAudit() {
    if (feeState.batchAuditSubmitting) return;
    const scope = requireScope();
    if (!scope) return;
    const mode = feeState.batchAuditMode;
    const remark = (document.getElementById('l0wfBatchAuditRemark')?.value || '').trim();
    if (mode === 'reverse' && !remark) {
        showToast('反审核原因必填', 'warning');
        return;
    }

    const body = { ...scope };
    const url = mode === 'approve' ? `${API_BASE}/batch-approve` : `${API_BASE}/batch-reverse-audit`;
    if (mode === 'approve') body.audit_remark = remark || null;
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
    if (!window.confirm(`确定删除未审核的成品焊接费？\n${scope.year} · ${scope.location} · ${scope.vehicle_model} · ${scope.bom_version}\n已审核记录将跳过。`)) {
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
    if (typeof can === 'function' && !can('op:bom-l0-welding-fee-list:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const f = getFilters();
    const params = {};
    if (f.year) params.year = f.year;
    if (f.location) params.location = f.location;
    if (f.vehicle_model) params.vehicle_model = f.vehicle_model;
    if (f.bom_version) params.bom_version = f.bom_version;
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
            defaultFilename: '成品焊接费导出.xlsx',
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
