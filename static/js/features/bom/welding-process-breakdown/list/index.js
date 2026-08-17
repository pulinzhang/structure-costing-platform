/**
 * BOM 焊接工艺拆解列表 — 筛选查看 + 明细抽屉编辑
 */

import {
    weldingProcessBreakdownListTemplate,
    renderWpbTableRows,
    renderWpbDetailBody,
    renderWpbPagination,
    updateWpbHud,
    updateWpbCapsules,
    refreshWpbLineDerived,
} from './template.js?v=37';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/bom/welding-process-breakdown';
const DRAWER_MS = 300;

const wpbState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    location: null,
    vehicleModel: null,
    bomVersion: null,
    auditStatus: null,
    level: 0,
    processLineCountEq: null,
    partNumber: null,
    summary: null,
    isLoading: false,
    batchSubmitting: false,
    saving: false,
    advancedOpen: false,
    canView: false,
    canEdit: false,
    detailEditMode: false,
    currentNodeId: null,
    standardProcessNames: [],
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
    if (drawerId === 'wpbDetailDrawer') {
        wpbState.currentNodeId = null;
    }
    setTimeout(() => {
        drawer.style.display = 'none';
        if (backdrop) backdrop.style.display = 'none';
    }, DRAWER_MS);
}

function init() {
    applyHashQuery();
    mountDrawersToBody();
    bindEvents();
    bindPageSizeSelect('wpbPageSize', {
        getSize: () => wpbState.pageSize,
        setSize: (size) => {
            wpbState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
    if (wpbState.advancedOpen) {
        document.getElementById('wpbAdvancedFilterPanel')?.classList.remove('hidden');
        const label = document.getElementById('wpbAdvancedFilterLabel');
        if (label) label.textContent = '收起高级筛选';
    }
    loadData(1);
    updateWpbCapsules(wpbState);
}

/** 抽屉挂到 body，避免被主内容区 overflow 裁切；清掉重复 id */
function mountDrawersToBody() {
    const ids = [
        'wpbDetailBackdrop',
        'wpbDetailDrawer',
        'wpbBatchBackdrop',
        'wpbBatchDrawer',
    ];
    for (const id of ids) {
        const matches = [...document.querySelectorAll(`#${id}`)];
        // 保留最后一个（本次 render），其余丢弃
        const keep = matches.pop();
        matches.forEach((el) => el.remove());
        if (keep && keep.parentElement !== document.body) {
            document.body.appendChild(keep);
        }
    }
}

function destroy() {
    wpbState.currentNodeId = null;
    for (const id of [
        'wpbDetailBackdrop',
        'wpbDetailDrawer',
        'wpbBatchBackdrop',
        'wpbBatchDrawer',
    ]) {
        document.querySelectorAll(`#${id}`).forEach((el) => el.remove());
    }
}

function applyHashQuery() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return;
    const params = new URLSearchParams(hash.slice(queryIndex + 1));
    wpbState.location = params.get('location') || null;
    wpbState.vehicleModel = params.get('vehicle_model') || null;
    wpbState.bomVersion = params.get('bom_version') || null;
    if (wpbState.location || wpbState.vehicleModel || wpbState.bomVersion) {
        wpbState.advancedOpen = true;
    }
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    wpbState.canView = canFn('op:bom-welding-process-breakdown:view');
    wpbState.canEdit = canFn('op:bom-welding-process-breakdown:save-lines');
    const hide = (id, allowed) => {
        if (!allowed) document.getElementById(id)?.classList.add('hidden');
    };
    hide('btnWpbBatchApprove', canFn('op:bom-welding-process-breakdown:approve'));
    hide('btnWpbBatchReverse', canFn('op:bom-welding-process-breakdown:reverse'));
    hide('btnWpbBatchDelete', canFn('op:bom-welding-process-breakdown:delete'));
    hide('btnWpbExport', canFn('op:bom-welding-process-breakdown:export'));
}

function bindEvents() {
    document.getElementById('btnWpbFilter')?.addEventListener('click', () => {
        readFiltersFromDom();
        loadData(1);
    });
    document.getElementById('wpbResetFilterBtn')?.addEventListener('click', resetFilters);
    document.querySelector('[data-action="filter-zero-process"]')?.addEventListener('click', () => {
        const card = document.getElementById('wpbHudZeroProcessCard');
        if (!card || card.dataset.clickable !== '1') return;
        wpbState.advancedOpen = true;
        document.getElementById('wpbAdvancedFilterPanel')?.classList.remove('hidden');
        const label = document.getElementById('wpbAdvancedFilterLabel');
        if (label) label.textContent = '收起高级筛选';
        const levelEl = document.getElementById('wpbLevelFilter');
        if (levelEl) levelEl.value = '0';
        const el = document.getElementById('wpbProcessCountFilter');
        if (el) el.value = '0';
        readFiltersFromDom();
        loadData(1);
    });
    document.getElementById('wpbToggleAdvancedFilter')?.addEventListener('click', () => {
        wpbState.advancedOpen = !wpbState.advancedOpen;
        document.getElementById('wpbAdvancedFilterPanel')?.classList.toggle('hidden', !wpbState.advancedOpen);
        const label = document.getElementById('wpbAdvancedFilterLabel');
        if (label) label.textContent = wpbState.advancedOpen ? '收起高级筛选' : '展开高级筛选';
    });

    document.getElementById('wpbCloseDetailDrawer')?.addEventListener('click', () => closeDrawer('wpbDetailDrawer', 'wpbDetailBackdrop'));
    document.getElementById('wpbDetailBackdrop')?.addEventListener('click', () => closeDrawer('wpbDetailDrawer', 'wpbDetailBackdrop'));

    document.getElementById('btnWpbExport')?.addEventListener('click', () => exportL0Excel());
    document.getElementById('btnWpbBatchApprove')?.addEventListener('click', () => openBatchDrawer('approve'));
    document.getElementById('btnWpbBatchReverse')?.addEventListener('click', () => openBatchDrawer('reverse'));
    document.getElementById('btnWpbBatchDelete')?.addEventListener('click', () => openBatchDrawer('delete'));
    document.getElementById('wpbCloseBatchDrawer')?.addEventListener('click', () => closeDrawer('wpbBatchDrawer', 'wpbBatchBackdrop'));
    document.getElementById('wpbCancelBatch')?.addEventListener('click', () => closeDrawer('wpbBatchDrawer', 'wpbBatchBackdrop'));
    document.getElementById('wpbBatchBackdrop')?.addEventListener('click', () => closeDrawer('wpbBatchDrawer', 'wpbBatchBackdrop'));
    document.getElementById('wpbConfirmBatch')?.addEventListener('click', confirmBatch);

    document.getElementById('wpbTableBody')?.addEventListener('click', (event) => {
        const viewBtn = event.target.closest('[data-action="view-detail"]');
        if (viewBtn) {
            const id = Number(viewBtn.getAttribute('data-node-id'));
            if (id) openDetail(id, { edit: false });
            return;
        }
        const editBtn = event.target.closest('[data-action="edit-detail"]');
        if (editBtn) {
            const id = Number(editBtn.getAttribute('data-node-id'));
            if (id) openDetail(id, { edit: true });
        }
    });

    document.getElementById('wpbDetailBody')?.addEventListener('input', (event) => {
        const card = event.target.closest('[data-line-card]');
        if (card) refreshWpbLineDerived(card);
    });
    document.getElementById('wpbDetailBody')?.addEventListener('change', (event) => {
        const card = event.target.closest('[data-line-card]');
        if (card) refreshWpbLineDerived(card);
    });
    document.getElementById('wpbDetailBody')?.addEventListener('click', (event) => {
        if (event.target.closest('[data-action="save-all-lines"]')) {
            saveAllLines();
        }
    });

    document.getElementById('wpbPaginationBtns')?.addEventListener('click', (event) => {
        const btn = event.target.closest('button[data-page]');
        if (!btn || btn.disabled) return;
        const page = Number(btn.getAttribute('data-page'));
        if (page) loadData(page);
    });
}

function readFiltersFromDom() {
    wpbState.location = val('wpbLocationFilter') || null;
    wpbState.vehicleModel = val('wpbModelFilter') || null;
    wpbState.bomVersion = val('wpbVersionFilter') || null;
    wpbState.auditStatus = val('wpbAuditFilter') || null;
    const levelRaw = val('wpbLevelFilter');
    wpbState.level = levelRaw === '' ? null : Number(levelRaw);
    const processCountRaw = val('wpbProcessCountFilter');
    wpbState.processLineCountEq = processCountRaw === '' ? null : Number(processCountRaw);
    wpbState.partNumber = val('wpbPartNumberFilter') || null;
    updateWpbCapsules(wpbState);
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function resetFilters() {
    ['wpbLocationFilter', 'wpbModelFilter', 'wpbVersionFilter', 'wpbAuditFilter', 'wpbProcessCountFilter', 'wpbPartNumberFilter']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    const levelEl = document.getElementById('wpbLevelFilter');
    if (levelEl) levelEl.value = '0';
    readFiltersFromDom();
    loadData(1);
}

function fillSelect(id, values, emptyLabel = '全部') {
    const el = document.getElementById(id);
    if (!el) return;
    const current = el.value;
    let html = `<option value="">${emptyLabel}</option>`;
    (values || []).forEach((v) => {
        html += `<option value="${esc(v)}">${esc(v)}</option>`;
    });
    el.innerHTML = html;
    if (current) el.value = current;
}

async function loadData(page = 1) {
    if (wpbState.isLoading) return;
    wpbState.isLoading = true;
    const tbody = document.getElementById('wpbTableBody');
    const empty = document.getElementById('wpbEmptyState');
    const loading = document.getElementById('wpbLoadingState');
    if (tbody) tbody.innerHTML = '';
    empty?.classList.add('hidden');
    loading?.classList.remove('hidden');

    try {
        const params = {
            page,
            size: wpbState.pageSize,
        };
        if (wpbState.location) params.location = wpbState.location;
        if (wpbState.vehicleModel) params.vehicle_model = wpbState.vehicleModel;
        if (wpbState.bomVersion) params.bom_version = wpbState.bomVersion;
        if (wpbState.auditStatus) params.audit_status = wpbState.auditStatus;
        if (wpbState.level != null && !Number.isNaN(wpbState.level)) params.level = wpbState.level;
        if (wpbState.processLineCountEq != null && !Number.isNaN(wpbState.processLineCountEq)) {
            params.process_line_count_eq = wpbState.processLineCountEq;
        }
        if (wpbState.partNumber) params.part_number = wpbState.partNumber;

        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};
        wpbState.records = pageResult.items || [];
        wpbState.total = pageResult.total || 0;
        wpbState.page = pageResult.page || page;
        wpbState.totalPages = pageResult.total_pages || 1;
        const filters = pageResult.filters || {};
        wpbState.summary = filters.summary || null;
        if (Array.isArray(filters.standard_process_names) && filters.standard_process_names.length) {
            wpbState.standardProcessNames = filters.standard_process_names;
        }

        fillSelect('wpbLocationFilter', filters.locations);
        fillSelect('wpbModelFilter', filters.vehicle_models);
        fillSelect('wpbVersionFilter', filters.bom_versions);
        const auditEl = document.getElementById('wpbAuditFilter');
        if (auditEl && auditEl.options.length <= 1) {
            auditEl.innerHTML = `
                <option value="">全部</option>
                <option value="pending">待审</option>
                <option value="approved">已审</option>
            `;
        }
        if (wpbState.location) document.getElementById('wpbLocationFilter').value = wpbState.location;
        if (wpbState.vehicleModel) document.getElementById('wpbModelFilter').value = wpbState.vehicleModel;
        if (wpbState.bomVersion) document.getElementById('wpbVersionFilter').value = wpbState.bomVersion;
        if (wpbState.auditStatus) document.getElementById('wpbAuditFilter').value = wpbState.auditStatus;
        if (wpbState.level != null) document.getElementById('wpbLevelFilter').value = String(wpbState.level);
        if (wpbState.processLineCountEq != null) {
            document.getElementById('wpbProcessCountFilter').value = String(wpbState.processLineCountEq);
        }

        updateWpbHud(wpbState.summary);
        updateWpbCapsules(wpbState);

        if (tbody) {
            tbody.innerHTML = renderWpbTableRows(wpbState.records, {
                canView: wpbState.canView,
                canEdit: wpbState.canEdit,
            });
        }
        const totalEl = document.getElementById('wpbTotalCount');
        if (totalEl) totalEl.textContent = `共 ${wpbState.total} 条`;
        const pager = document.getElementById('wpbPaginationBtns');
        if (pager) pager.innerHTML = renderWpbPagination(wpbState.page, wpbState.totalPages);

        if (!wpbState.records.length) empty?.classList.remove('hidden');
    } catch (error) {
        console.error(error);
        empty?.classList.remove('hidden');
    } finally {
        loading?.classList.add('hidden');
        wpbState.isLoading = false;
    }
}

async function openDetail(nodeId, { edit = false } = {}) {
    if (edit ? !wpbState.canEdit : !wpbState.canView) return;
    wpbState.currentNodeId = nodeId;
    wpbState.detailEditMode = !!(edit && wpbState.canEdit);
    let node = wpbState.records.find((r) => r.id === nodeId);
    try {
        const res = await HttpClient.get(`${API_BASE}/nodes/${nodeId}`);
        if (res.data) node = res.data;
    } catch (error) {
        console.error(error);
    }
    const title = document.getElementById('wpbDetailTitle');
    if (title) {
        if (!node) {
            title.textContent = '拆解明细';
        } else {
            const n = Array.isArray(node.lines) ? node.lines.length : (Number(node.process_line_count) || 0);
            title.textContent = `${node.part_number} · L${node.level} · ${n}种`;
        }
    }
    const body = document.getElementById('wpbDetailBody');
    if (body) {
        body.innerHTML = renderWpbDetailBody(node, {
            canEdit: wpbState.detailEditMode,
            standardProcessNames: wpbState.standardProcessNames,
        });
    }
    openDrawer('wpbDetailDrawer', 'wpbDetailBackdrop');
}

async function saveAllLines() {
    if (wpbState.saving || !wpbState.detailEditMode || !wpbState.currentNodeId) return;
    const cards = [...document.querySelectorAll('#wpbDetailBody [data-line-card]')];
    if (!cards.length) {
        showToast('无工艺可保存', 'warning');
        return;
    }
    const lines = [];
    for (const card of cards) {
        const lineId = Number(card.getAttribute('data-line-card'));
        const processQty = card.querySelector('[data-field="process_qty"]')?.value?.trim();
        const processQtyUnit = card.querySelector('[data-field="process_qty_unit"]')?.value?.trim();
        const processQtySecondary = card.querySelector('[data-field="process_qty_secondary"]')?.value?.trim();
        const processQtySecondaryUnit = card.querySelector('[data-field="process_qty_secondary_unit"]')?.value?.trim();
        const standardProcessName = card.querySelector('[data-field="standard_process_name"]')?.value?.trim();
        if (!processQty) {
            showToast('过程量不能为空', 'warning');
            return;
        }
        lines.push({
            line_id: lineId,
            process_qty: processQty,
            process_qty_unit: processQtyUnit || null,
            process_qty_secondary: processQtySecondary || null,
            process_qty_secondary_unit: processQtySecondaryUnit || null,
            standard_process_name: standardProcessName || null,
        });
    }
    wpbState.saving = true;
    const saveBtn = document.getElementById('wpbSaveAllLines');
    if (saveBtn) saveBtn.disabled = true;
    try {
        const res = await HttpClient.patch(
            `${API_BASE}/nodes/${wpbState.currentNodeId}/lines`,
            { lines },
        );
        showToast('全部工艺已保存', 'success');
        const nodeId = wpbState.currentNodeId;
        await loadData(wpbState.page);
        if (res.data) {
            const title = document.getElementById('wpbDetailTitle');
            const n = Array.isArray(res.data.lines) ? res.data.lines.length : 0;
            if (title) title.textContent = `${res.data.part_number} · L${res.data.level} · ${n}种`;
            const body = document.getElementById('wpbDetailBody');
            if (body) {
                body.innerHTML = renderWpbDetailBody(res.data, {
                    canEdit: wpbState.detailEditMode,
                    standardProcessNames: wpbState.standardProcessNames,
                });
            }
        } else if (nodeId) {
            await openDetail(nodeId, { edit: wpbState.detailEditMode });
        }
    } catch (error) {
        console.error(error);
    } finally {
        wpbState.saving = false;
        if (saveBtn) saveBtn.disabled = false;
    }
}

function requireScope() {
    const location = wpbState.location || val('wpbLocationFilter');
    const vehicleModel = wpbState.vehicleModel || val('wpbModelFilter');
    const bomVersion = wpbState.bomVersion || val('wpbVersionFilter');
    if (!location || !vehicleModel || !bomVersion) {
        showToast('批量操作须同时选定基地、项目、版本', 'warning');
        return null;
    }
    return { location, vehicle_model: vehicleModel, bom_version: bomVersion };
}

function openBatchDrawer(mode) {
    const scope = requireScope();
    if (!scope) return;
    document.getElementById('wpbBatchMode').value = mode;
    const title = document.getElementById('wpbBatchTitle');
    const hint = document.getElementById('wpbBatchHint');
    const remarkLabel = document.getElementById('wpbBatchRemarkLabel');
    const remark = document.getElementById('wpbBatchRemark');
    const remarkWrap = document.getElementById('wpbBatchRemarkWrap');
    const summary = document.getElementById('wpbBatchScopeSummary');
    if (summary) {
        summary.textContent = `${scope.location} / ${scope.vehicle_model} / ${scope.bom_version}`;
    }
    if (remark) remark.value = '';
    if (mode === 'approve') {
        remarkWrap?.classList.remove('hidden');
        if (title) title.textContent = '批量审核';
        if (hint) hint.textContent = '将范围内待审主表标记为已审核；已审跳过。';
        if (remarkLabel) remarkLabel.textContent = '审核意见（可选）';
        if (remark) remark.placeholder = '可选填写审核意见';
    } else if (mode === 'reverse') {
        remarkWrap?.classList.remove('hidden');
        if (title) title.textContent = '批量反审核';
        if (hint) hint.textContent = '将范围内已审改回待审；反审核原因必填。';
        if (remarkLabel) remarkLabel.textContent = '反审核原因 *';
        if (remark) remark.placeholder = '必填';
    } else {
        remarkWrap?.classList.add('hidden');
        if (title) title.textContent = '批量删除';
        if (hint) hint.textContent = '仅删除未审核记录；已审跳过。此操作不可恢复。';
    }
    openDrawer('wpbBatchDrawer', 'wpbBatchBackdrop');
}

async function confirmBatch() {
    if (wpbState.batchSubmitting) return;
    const scope = requireScope();
    if (!scope) return;
    const mode = document.getElementById('wpbBatchMode')?.value || 'approve';
    const remark = (document.getElementById('wpbBatchRemark')?.value || '').trim();
    if (mode === 'reverse' && !remark) {
        showToast('反审核原因必填', 'warning');
        return;
    }
    wpbState.batchSubmitting = true;
    try {
        let res;
        if (mode === 'approve') {
            res = await HttpClient.post(`${API_BASE}/batch-approve`, {
                ...scope,
                audit_remark: remark || null,
            });
        } else if (mode === 'reverse') {
            res = await HttpClient.post(`${API_BASE}/batch-reverse-audit`, {
                ...scope,
                reverse_audit_remark: remark,
            });
        } else {
            res = await HttpClient.post(`${API_BASE}/batch-delete`, scope);
        }
        showToast(res.message || '操作成功', 'success');
        closeDrawer('wpbBatchDrawer', 'wpbBatchBackdrop');
        await loadData(wpbState.page);
    } catch (error) {
        console.error(error);
    } finally {
        wpbState.batchSubmitting = false;
    }
}

async function exportL0Excel() {
    const btn = document.getElementById('btnWpbExport');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>导出中…`;
    }
    try {
        readFiltersFromDom();
        const params = {};
        if (wpbState.location) params.location = wpbState.location;
        if (wpbState.vehicleModel) params.vehicle_model = wpbState.vehicleModel;
        if (wpbState.bomVersion) params.bom_version = wpbState.bomVersion;
        if (wpbState.partNumber) params.part_number = wpbState.partNumber;
        // 导出固定 L0；若列表已筛工艺数，一并带上
        if (wpbState.processLineCountEq != null && !Number.isNaN(wpbState.processLineCountEq)) {
            params.process_line_count_eq = wpbState.processLineCountEq;
        }
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            defaultFilename: '焊接工艺拆解_L0核对.xlsx',
        });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
        showToast(`已按当前筛选导出 L0：${filename}`, 'success');
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
    render: weldingProcessBreakdownListTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
