import { dieFeeListTemplate, renderDieFeeRows } from './template.js?v=1';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/stamping/die-fees';
const SCOPE_REQUIRED_MESSAGE = '请先选择年度、基地、项目';

const feeState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    items: [],
    onlyZero: false,
    canUpdate: true,
    canDelete: true,
    canApprove: true,
    canReverse: true,
    canExport: true,
};

function parseHashParams() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return {};
    return Object.fromEntries(new URLSearchParams(hash.slice(qIndex + 1)));
}

function readScope() {
    return {
        year: Number(document.getElementById('dieFeeYear')?.value),
        location: document.getElementById('dieFeeLocation')?.value || '',
        vehicle_model: document.getElementById('dieFeeVehicle')?.value || '',
    };
}

function hasScope(scope) {
    return scope.year >= 2000 && scope.location && scope.vehicle_model;
}

function init() {
    feeState.canUpdate = typeof can === 'function' ? can('op:stamping-die-fee:update') : true;
    feeState.canDelete = typeof can === 'function' ? can('op:stamping-die-fee:delete') : true;
    feeState.canApprove = typeof can === 'function' ? can('op:stamping-die-fee:approve') : true;
    feeState.canReverse = typeof can === 'function' ? can('op:stamping-die-fee:reverse') : true;
    feeState.canExport = typeof can === 'function' ? can('op:stamping-die-fee:export') : true;
    if (!feeState.canExport) document.getElementById('dieFeeExportBtn')?.classList.add('hidden');
    if (!feeState.canApprove) document.getElementById('dieFeeApproveBtn')?.classList.add('hidden');
    if (!feeState.canReverse) document.getElementById('dieFeeReverseBtn')?.classList.add('hidden');
    if (!feeState.canDelete) document.getElementById('dieFeeDeleteScopeBtn')?.classList.add('hidden');

    const yearEl = document.getElementById('dieFeeYear');
    const params = parseHashParams();
    if (yearEl) yearEl.value = params.year || String(new Date().getFullYear());

    bindPageSizeSelect('dieFeePageSize', {
        getSize: () => feeState.pageSize,
        setSize: (size) => {
            feeState.pageSize = size;
        },
        onChange: () => loadList(1),
    });
    bindEvents();
    loadFilters().then(() => {
        if (params.location) {
            const loc = document.getElementById('dieFeeLocation');
            if (loc) loc.value = params.location;
        }
        return loadFilters(true);
    }).then(() => {
        if (params.vehicle_model) {
            const veh = document.getElementById('dieFeeVehicle');
            if (veh) veh.value = params.vehicle_model;
        }
        renderEmpty();
        if (hasScope(readScope())) loadList(1);
    });
}

function bindEvents() {
    document.getElementById('dieFeeLocation')?.addEventListener('change', () => {
        loadFilters(true);
        renderEmpty();
    });
    document.getElementById('dieFeeSearchBtn')?.addEventListener('click', () => loadList(1));
    document.getElementById('dieFeePartNumber')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            loadList(1);
        }
    });
    document.getElementById('dieFeeOnlyZeroBtn')?.addEventListener('click', () => {
        feeState.onlyZero = !feeState.onlyZero;
        document.getElementById('dieFeeOnlyZeroBtn')?.classList.toggle('border-[#FF1E27]', feeState.onlyZero);
        document.getElementById('dieFeeOnlyZeroBtn')?.classList.toggle('text-white', feeState.onlyZero);
        loadList(1);
    });
    document.getElementById('dieFeeExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('dieFeeApproveBtn')?.addEventListener('click', () => batchAudit('approve'));
    document.getElementById('dieFeeReverseBtn')?.addEventListener('click', () => batchAudit('reverse'));
    document.getElementById('dieFeeDeleteScopeBtn')?.addEventListener('click', () => deleteScope());
    document.getElementById('dieFeeDrawerClose')?.addEventListener('click', () => closeDrawer());
    document.getElementById('dieFeeDrawerBackdrop')?.addEventListener('click', () => closeDrawer());
    document.getElementById('pageContent')?.addEventListener('click', (e) => {
        const actionBtn = e.target.closest('button[data-action]');
        if (actionBtn) {
            const id = Number(actionBtn.getAttribute('data-id'));
            const action = actionBtn.getAttribute('data-action');
            if (action === 'detail' || action === 'edit') openDetail(id, action === 'edit');
            if (action === 'delete') deleteOne(id);
            return;
        }
        const pageBtn = e.target.closest('#dieFeePagination button[data-page]');
        if (pageBtn && !pageBtn.disabled) loadList(Number(pageBtn.dataset.page));
    });
}

function fillSelect(id, values, preferred) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferred != null ? preferred : select.value;
    select.innerHTML =
        '<option value="">请选择</option>' +
        (values || []).map((value) => {
            const text = String(value);
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
        }).join('');
}

async function loadFilters(keepVehicle) {
    const location = document.getElementById('dieFeeLocation')?.value || '';
    const res = await HttpClient.get(`${API_BASE}/filters`, {
        params: location ? { location } : {},
    });
    const data = res.data || {};
    fillSelect('dieFeeLocation', data.locations || []);
    fillSelect('dieFeeVehicle', data.vehicle_models || [], keepVehicle ? undefined : '');
}

function renderEmpty() {
    const tbody = document.getElementById('dieFeeTbody');
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" class="py-16 text-center text-[#555555]">${SCOPE_REQUIRED_MESSAGE}，未选齐不会请求列表</td></tr>`;
    }
    const total = document.getElementById('dieFeeTotal');
    if (total) total.textContent = '';
    const hud = document.getElementById('dieFeeHud');
    if (hud) hud.textContent = '';
}

async function loadList(page) {
    const scope = readScope();
    if (!hasScope(scope)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        renderEmpty();
        return;
    }
    feeState.page = page || 1;
    const params = {
        year: scope.year,
        location: scope.location,
        vehicle_model: scope.vehicle_model,
        page: feeState.page,
        size: feeState.pageSize,
    };
    const partNumber = document.getElementById('dieFeePartNumber')?.value?.trim();
    const auditStatus = document.getElementById('dieFeeAuditStatus')?.value;
    if (partNumber) params.part_number = partNumber;
    if (auditStatus) params.audit_status = auditStatus;
    if (feeState.onlyZero) params.only_zero = true;
    const tbody = document.getElementById('dieFeeTbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="py-16 text-center text-[#555555]">加载中..</td></tr>`;
    const res = await HttpClient.get(API_BASE, { params });
    const data = res.data || {};
    feeState.items = data.items || [];
    feeState.total = data.total || 0;
    feeState.page = data.page || feeState.page;
    const filters = data.filters || {};
    const hud = document.getElementById('dieFeeHud');
    if (hud) {
        hud.textContent = `共 ${filters.total_count ?? feeState.total} 件 · 待审 ${filters.pending_count ?? '-'} · 已审 ${filters.approved_count ?? '-'} · 最终为 0：${filters.zero_count ?? '-'}`;
    }
    if (tbody) {
        tbody.innerHTML = renderDieFeeRows(feeState.items, {
            canUpdate: feeState.canUpdate,
            canDelete: feeState.canDelete,
        });
    }
    const totalEl = document.getElementById('dieFeeTotal');
    if (totalEl) totalEl.textContent = `共 ${feeState.total} 条`;
    renderPagination();
}

function renderPagination() {
    const wrap = document.getElementById('dieFeePagination');
    if (!wrap) return;
    const totalPages = feeState.total > 0 ? Math.ceil(feeState.total / feeState.pageSize) : 0;
    if (totalPages <= 1) {
        wrap.innerHTML = '';
        return;
    }
    let html = '';
    for (let i = 1; i <= totalPages; i += 1) {
        html += `<button type="button" data-page="${i}" class="flex items-center justify-center w-6 h-6 text-[10px] ${i === feeState.page ? 'bg-[#FF1E27] text-white' : 'text-[#585858] hover:text-[#c0c0c0]'}">${i}</button>`;
    }
    wrap.innerHTML = html;
}

async function openDetail(feeId, editing) {
    const res = await HttpClient.get(`${API_BASE}/${feeId}`);
    const row = res.data || {};
    const body = document.getElementById('dieFeeDrawerBody');
    const items = Array.isArray(row.items) ? row.items : [];
    const pending = row.audit_status !== 'approved';
    body.innerHTML = `
        <div class="space-y-3">
            <div class="text-[#F0F0F2] font-mono">${esc(row.part_number)} ${esc(row.part_name || '')}</div>
            <div>系统模具费 ${esc(fmtNum(row.die_fee, 4))} · 最终 ${esc(fmtNum(row.final_die_fee, 4))}</div>
            ${items.map((item) => `
                <div class="border border-[#222] p-2">
                    <div>${esc(item.process_seq)} ${esc(item.process_code || '')}</div>
                    <div class="text-[10px] text-[#555]">${esc(item.basis_text || '')}</div>
                    <div class="font-mono text-right text-[#FF1E27]">${esc(fmtNum(item.line_die_fee, 4))}</div>
                </div>`).join('')}
            ${editing && pending && feeState.canUpdate ? `
            <label class="block space-y-1">
                <span>调整金额</span>
                <input id="dieFeeAdjInput" class="w-full h-8 px-2 bg-[#0a0a0a] border border-[#2c2c2c] text-white" value="${row.adjustment_amount == null ? '' : esc(row.adjustment_amount)}">
            </label>
            <label class="block space-y-1">
                <span>备注</span>
                <textarea id="dieFeeRemarkInput" class="w-full h-20 px-2 py-1 bg-[#0a0a0a] border border-[#2c2c2c] text-white">${esc(row.remark || '')}</textarea>
            </label>
            <button type="button" id="dieFeeSaveAdj" data-id="${esc(row.id)}" class="h-8 px-4 bg-[#d32f2f] text-white text-[10px]">保存</button>
            ` : ''}
        </div>`;
    document.getElementById('dieFeeDrawerBackdrop')?.classList.remove('hidden');
    const drawer = document.getElementById('dieFeeDrawer');
    drawer?.classList.remove('hidden');
    drawer?.classList.remove('translate-x-full');
    document.getElementById('dieFeeSaveAdj')?.addEventListener('click', () => saveAdjustment(row.id));
}

function closeDrawer() {
    document.getElementById('dieFeeDrawerBackdrop')?.classList.add('hidden');
    const drawer = document.getElementById('dieFeeDrawer');
    drawer?.classList.add('hidden');
    drawer?.classList.add('translate-x-full');
}

async function saveAdjustment(feeId) {
    const adjRaw = document.getElementById('dieFeeAdjInput')?.value ?? '';
    const remark = document.getElementById('dieFeeRemarkInput')?.value || '';
    const body = { remark: remark.trim() || null };
    if (adjRaw.trim() === '') body.adjustment_amount = null;
    else body.adjustment_amount = adjRaw.trim();
    try {
        await HttpClient.put(`${API_BASE}/${feeId}`, body);
        showToast('已保存', 'success');
        closeDrawer();
        loadList(feeState.page);
    } catch (error) {
        showToast(error.message || '保存失败', 'error');
    }
}

async function deleteOne(feeId) {
    if (!window.confirm('删除该未审核模具费？')) return;
    await HttpClient.delete(`${API_BASE}/${feeId}`);
    showToast('已删除', 'success');
    loadList(feeState.page);
}

async function deleteScope() {
    const scope = readScope();
    if (!hasScope(scope)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (!window.confirm('删除该范围全部未审核记录？')) return;
    await HttpClient.delete(`${API_BASE}/scope`, { params: scope });
    showToast('已删除未审核', 'success');
    loadList(1);
}

async function batchAudit(kind) {
    const scope = readScope();
    if (!hasScope(scope)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (kind === 'approve') {
        const remark = window.prompt('审核意见（必填）');
        if (!remark || !remark.trim()) return;
        await HttpClient.post(`${API_BASE}/batch-approve`, { ...scope, audit_remark: remark.trim() });
        showToast('已审核', 'success');
    } else {
        const remark = window.prompt('反审核原因（必填）');
        if (!remark || !remark.trim()) return;
        await HttpClient.post(`${API_BASE}/batch-reverse-audit`, {
            ...scope,
            reverse_audit_remark: remark.trim(),
        });
        showToast('已反审核', 'success');
    }
    loadList(feeState.page);
}

async function exportExcel() {
    const scope = readScope();
    if (!hasScope(scope)) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    const params = {
        year: scope.year,
        location: scope.location,
        vehicle_model: scope.vehicle_model,
    };
    const partNumber = document.getElementById('dieFeePartNumber')?.value?.trim();
    const auditStatus = document.getElementById('dieFeeAuditStatus')?.value;
    if (partNumber) params.part_number = partNumber;
    if (auditStatus) params.audit_status = auditStatus;
    if (feeState.onlyZero) params.only_zero = true;
    await HttpClient.download(`${API_BASE}/export`, { params });
}

function destroy() {
    closeDrawer();
}

export const pageConfig = {
    render: dieFeeListTemplate,
    init,
    destroy,
};
