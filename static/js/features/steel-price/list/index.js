/**
 * Steel Price List Page
 * 钢材价格计算结果浏览 / 手工维护 / 审核
 */

import { steelPriceListTemplate, renderSteelPricePagination, renderSteelPriceRows } from './template.js?v=25';

const steelPriceState = {
    records: [],
    total: 0,
    page: 1,
    size: 20,
    totalPages: 1,
    filtersLoaded: false,
    currentViewId: null,
    pendingFilters: null,
};

const API_BASE = '/api/steel-prices';
const DRAWER_ANIMATION_MS = 300;
const AUDIT_LABEL = { pending: '待审', approved: '已通过', rejected: '已驳回' };

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
    steelPriceState.filtersLoaded = false;
    steelPriceState.pendingFilters = readHashFilters();
    loadData(1);
}

function readHashFilters() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return null;
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    const year = qs.get('year') || '';
    const month = qs.get('month') || '';
    const location = qs.get('location') || '';
    if (!year && !month && !location) return null;
    return { year, month, location };
}

async function loadData(page = 1) {
    const tableBody = document.getElementById('steelPriceTableBody');
    const emptyState = document.getElementById('steelPriceEmpty');
    const loadingState = document.getElementById('steelPriceLoading');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page,
            size: steelPriceState.size,
            year: getFilterValue('steelPriceYear') || steelPriceState.pendingFilters?.year || '',
            month: getFilterValue('steelPriceMonth') || steelPriceState.pendingFilters?.month || '',
            location: getFilterValue('steelPriceLocation') || steelPriceState.pendingFilters?.location || '',
            category_name: getFilterValue('steelPriceCategory'),
            grade: document.getElementById('steelPriceGrade')?.value.trim() || '',
            steel_mill: getFilterValue('steelPriceMill'),
            audit_status: getFilterValue('steelPriceAuditStatus'),
        };

        const response = await HttpClient.get(API_BASE, { params });
        const payload = response.data || {};
        const records = Array.isArray(payload.items) ? payload.items : [];

        steelPriceState.records = records;
        steelPriceState.total = payload.total || 0;
        steelPriceState.page = payload.page || page;
        steelPriceState.totalPages = payload.total_pages || 1;

        if (tableBody) {
            if (records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderSteelPriceRows(records);
                bindRowEvents();
            }
        }

        const total = document.getElementById('steelPriceTotal');
        if (total) total.textContent = `共 ${steelPriceState.total} 条`;

        const pagination = document.getElementById('steelPricePagination');
        if (pagination) {
            pagination.innerHTML = renderSteelPricePagination(
                steelPriceState.page,
                steelPriceState.totalPages
            );
        }

        if (!steelPriceState.filtersLoaded && payload.filters) {
            renderFilters(payload.filters);
            applyPendingFiltersToSelects();
            steelPriceState.filtersLoaded = true;
        }
    } catch (error) {
        console.error('加载钢材价格失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="19" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">加载数据失败，请重试</td>
                </tr>`;
        }
    } finally {
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

function renderFilters(filters) {
    fillSelect('steelPriceYear', filters.years || [], value => `${value} 年`);
    fillSelect('steelPriceMonth', filters.months || [], value => `${value} 月`);
    fillSelect('steelPriceLocation', filters.locations || []);
    fillSelect('steelPriceCategory', filters.category_names || []);
    fillSelect('steelPriceMill', filters.steel_mills || []);
    fillSelect(
        'steelPriceAuditStatus',
        filters.audit_statuses || [],
        value => AUDIT_LABEL[value] || value
    );
}

function fillSelect(id, values = [], label = value => value) {
    const select = document.getElementById(id);
    if (!select) return;
    select.innerHTML =
        '<option value="">全部</option>' +
        values.map(value => `<option value="${esc(value)}">${esc(label(value))}</option>`).join('');
}

function applyPendingFiltersToSelects() {
    const pending = steelPriceState.pendingFilters;
    if (!pending) return;
    setSelectValue('steelPriceYear', pending.year);
    setSelectValue('steelPriceMonth', pending.month);
    setSelectValue('steelPriceLocation', pending.location);
    steelPriceState.pendingFilters = null;
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select || value == null || value === '') return;
    const text = String(value);
    if (![...select.options].some(opt => opt.value === text)) {
        select.insertAdjacentHTML(
            'beforeend',
            `<option value="${esc(text)}">${esc(text)}</option>`
        );
    }
    select.value = text;
}

function resetFilters() {
    [
        'steelPriceYear',
        'steelPriceMonth',
        'steelPriceLocation',
        'steelPriceCategory',
        'steelPriceGrade',
        'steelPriceMill',
        'steelPriceAuditStatus',
    ].forEach(id => {
        const element = document.getElementById(id);
        if (element) element.value = '';
    });
    loadData(1);
}

function bindRowEvents() {
    document.querySelectorAll('#steelPriceTableBody .view-btn').forEach(btn => {
        btn.addEventListener('click', event => {
            const id = Number(event.target.closest('tr').dataset.id);
            const record = steelPriceState.records.find(r => r.id === id);
            if (record) openViewDrawer(record);
        });
    });
    document.querySelectorAll('#steelPriceTableBody .edit-btn').forEach(btn => {
        btn.addEventListener('click', event => {
            const id = Number(event.target.closest('tr').dataset.id);
            const record = steelPriceState.records.find(r => r.id === id);
            if (record) openEditDrawer(record);
        });
    });
    document.querySelectorAll('#steelPriceTableBody .delete-btn').forEach(btn => {
        btn.addEventListener('click', event => {
            const id = Number(event.target.closest('tr').dataset.id);
            const record = steelPriceState.records.find(r => r.id === id);
            if (record) openDeleteDrawer(record);
        });
    });
}

function bindEvents() {
    document.getElementById('steelPriceSearchButton')?.addEventListener('click', () => loadData(1));
    document.getElementById('steelPriceGrade')?.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
            event.preventDefault();
            loadData(1);
        }
    });
    document.getElementById('steelPriceResetFilterButton')?.addEventListener('click', () => resetFilters());
    document.getElementById('steelPriceBatchDeleteButton')?.addEventListener('click', () => batchDeleteByFilters());
    document.getElementById('steelPriceExportButton')?.addEventListener('click', () => exportExcel());

    document.getElementById('steelPricePagination')?.addEventListener('click', event => {
        const btn = event.target.closest('.steel-price-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page);
            if (page) loadData(page);
        }
    });

    bindEditDrawerEvents();
    bindViewDrawerEvents();
    bindDeleteDrawerEvents();
}

function collectBatchDeleteFilters() {
    return {
        year: getFilterValue('steelPriceYear'),
        month: getFilterValue('steelPriceMonth'),
        location: getFilterValue('steelPriceLocation'),
        category_name: getFilterValue('steelPriceCategory'),
        grade: document.getElementById('steelPriceGrade')?.value.trim() || '',
        steel_mill: getFilterValue('steelPriceMill'),
    };
}

function collectExportFilters() {
    return {
        year: getFilterValue('steelPriceYear'),
        month: getFilterValue('steelPriceMonth'),
        location: getFilterValue('steelPriceLocation'),
        category_name: getFilterValue('steelPriceCategory'),
        grade: document.getElementById('steelPriceGrade')?.value.trim() || '',
        steel_mill: getFilterValue('steelPriceMill'),
        audit_status: getFilterValue('steelPriceAuditStatus'),
    };
}

async function exportExcel() {
    const filters = collectExportFilters();
    if (
        !filters.year &&
        !filters.month &&
        !filters.location &&
        !filters.category_name &&
        !filters.grade &&
        !filters.steel_mill &&
        !filters.audit_status
    ) {
        showToast('请至少选择一个筛选条件后再导出', 'warning');
        return;
    }

    const btn = document.getElementById('steelPriceExportButton');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            导出中...
        `;
    }

    try {
        const params = new URLSearchParams();
        if (filters.year) params.append('year', filters.year);
        if (filters.month) params.append('month', filters.month);
        if (filters.location) params.append('location', filters.location);
        if (filters.category_name) params.append('category_name', filters.category_name);
        if (filters.grade) params.append('grade', filters.grade);
        if (filters.steel_mill) params.append('steel_mill', filters.steel_mill);
        if (filters.audit_status) params.append('audit_status', filters.audit_status);

        const response = await fetch(`${API_BASE}/export-download?${params.toString()}`, {
            method: 'GET',
        });
        if (!response.ok) {
            let message = `导出失败: HTTP ${response.status}`;
            try {
                const payload = await response.json();
                message = payload.detail || payload.message || message;
            } catch (_) {
                /* ignore */
            }
            throw new Error(message);
        }

        const contentDisposition = response.headers.get('Content-Disposition') || '';
        let filename = '钢材联动价格导出.xlsx';
        const match = contentDisposition.match(/filename\*=UTF-8''([^;]+)|filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
        if (match) {
            const raw = match[1] || match[2];
            if (raw) filename = decodeURIComponent(raw.replace(/['"]/g, ''));
        }

        const blob = await response.blob();
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
        console.error('导出钢材联动价格失败:', error);
        showToast(error.message || '导出失败', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function batchDeleteByFilters() {
    const filters = collectBatchDeleteFilters();
    if (!filters.year || !filters.month || !filters.location) {
        showToast('批量删除须选择年度、月份、基地', 'warning');
        return;
    }

    const parts = [
        `年度: ${filters.year}`,
        `月份: ${filters.month}`,
        `基地: ${filters.location}`,
    ];
    if (filters.category_name) parts.push(`钢种: ${filters.category_name}`);
    if (filters.grade) parts.push(`牌号: ${filters.grade}`);
    if (filters.steel_mill) parts.push(`钢厂: ${filters.steel_mill}`);

    const confirmed = window.confirm(
        `确定按以下条件批量删除未审核记录吗？\n\n${parts.join(' | ')}\n\n仅删除待审/已驳回；已审核通过的记录会跳过。此操作不可恢复！`
    );
    if (!confirmed) return;

    const btn = document.getElementById('steelPriceBatchDeleteButton');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中...
        `;
    }

    try {
        const body = {
            year: parseInt(filters.year, 10),
            month: parseInt(filters.month, 10),
            location: filters.location,
        };
        if (filters.category_name) body.category_name = filters.category_name;
        if (filters.grade) body.grade = filters.grade;
        if (filters.steel_mill) body.steel_mill = filters.steel_mill;

        const response = await HttpClient.post(`${API_BASE}/batch-delete`, body);
        const result = response.data || {};
        const deleted = result.deleted_count ?? 0;
        const skipped = result.skipped_approved_count ?? 0;
        showToast(
            response.message ||
                `已删除 ${deleted} 条` + (skipped ? `，跳过已审核 ${skipped} 条` : ''),
            deleted > 0 ? 'success' : 'warning'
        );
        steelPriceState.filtersLoaded = false;
        loadData(1);
    } catch (error) {
        console.error('批量删除钢材价格失败:', error);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');
    document.getElementById('closeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelEditBtn')?.addEventListener('click', close);
    document.getElementById('editDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitEditBtn')?.addEventListener('click', async event => {
        event.preventDefault();
        await saveRecord();
    });
}

function bindViewDrawerEvents() {
    const close = () => closeDrawer('viewDrawer', 'viewDrawerBackdrop');
    document.getElementById('closeViewDrawer')?.addEventListener('click', close);
    document.getElementById('viewDrawerBackdrop')?.addEventListener('click', close);

    document.getElementById('viewDrawerEditBtn')?.addEventListener('click', () => {
        const record = steelPriceState.records.find(r => r.id === steelPriceState.currentViewId);
        close();
        if (record) setTimeout(() => openEditDrawer(record), DRAWER_ANIMATION_MS);
    });

    document.getElementById('viewDrawerApproveBtn')?.addEventListener('click', () => handleApprove());
    document.getElementById('viewDrawerRejectBtn')?.addEventListener('click', () => handleReject());
    document.getElementById('viewDrawerReverseBtn')?.addEventListener('click', () => handleReverseAudit());
}

function bindDeleteDrawerEvents() {
    const close = () => closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
    document.getElementById('closeDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelDeleteBtn')?.addEventListener('click', close);
    document.getElementById('deleteDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', async () => {
        const id = Number(document.getElementById('deleteRecordId')?.value);
        if (id) await deleteRecord(id);
    });
}



function openEditDrawer(record) {
    if (record.audit_status === 'approved') {
        showToast('记录已审核通过，请先反审核后再编辑', 'warning');
        return;
    }
    setEditDrawerTitle('编辑钢材价格');
    document.getElementById('editRecordId').value = record.id;
    document.getElementById('editYear').value = record.year;
    document.getElementById('editMonth').value = record.month;
    document.getElementById('editLocation').value = record.location || '';
    document.getElementById('editSteelMill').value = record.steel_mill || '';
    document.getElementById('editCategoryName').value = record.category_name || '';
    document.getElementById('editGrade').value = record.grade || '';
    document.getElementById('editThickness').value = record.thickness ?? '';
    document.getElementById('editWidth').value = record.width ?? '';
    document.getElementById('editBasePrice').value = record.base_price ?? '';
    document.getElementById('editThicknessAdjustment').value = record.thickness_adjustment ?? 0;
    document.getElementById('editWidthAdjustment').value = record.width_adjustment ?? 0;
    document.getElementById('editZincAdjustment').value = record.zinc_adjustment ?? 0;
    document.getElementById('editProcessingFee').value = record.processing_fee ?? 0;
    document.getElementById('editOtherAdjustment').value = record.other_adjustment ?? 0;
    document.getElementById('editSpec').value = record.spec || '';
    document.getElementById('editRemark').value = record.remark || '';
    setBusinessKeyReadonly(true);
    openDrawer('editDrawer', 'editDrawerBackdrop');
}

function formatTrace(prefix, record) {
    const filename = record[`${prefix}_excel_filename`];
    const sheet = record[`${prefix}_sheet_name`];
    const row = record[`${prefix}_excel_row`];
    const col = record[`${prefix}_excel_col`];
    const refId = prefix === 'base' ? record.base_price_id : record[`${prefix}_policy_id`];
    const ladderId = prefix === 'base' ? null : record[`${prefix}_ladder_item_id`];

    if (filename == null && refId == null && ladderId == null && row == null && col == null) {
        return `<span class="text-[#616161]">${prefixLabel(prefix)}：未匹配</span>`;
    }

    const idLines = prefix === 'base'
        ? [`base_price_id=${esc(refId ?? '—')}`]
        : [
            `${prefix}_policy_id=${esc(refId ?? '—')}`,
            `${prefix}_ladder_item_id=${esc(ladderId ?? '—')}`,
        ];
    const excelLine = [
        `${prefix}_excel_filename=${esc(filename || '—')}`,
        `${prefix}_sheet_name=${esc(sheet || '—')}`,
        `${prefix}_excel_row=${esc(row ?? '—')}`,
        `${prefix}_excel_col=${esc(col ?? '—')}`,
    ].join(' · ');

    return `
        <div>
            <div class="text-[#777777] mb-1">${prefixLabel(prefix)}</div>
            <div class="font-mono text-[10px] text-[#9e9e9e] space-y-0.5">
                ${idLines.map(line => `<div>${line}</div>`).join('')}
                <div>${excelLine}</div>
            </div>
        </div>
    `;
}

function prefixLabel(prefix) {
    return {
        base: '基础价溯源',
        thickness: '厚度加价溯源',
        width: '宽度加价溯源',
        zinc: '锌层加价溯源',
    }[prefix] || prefix;
}

function openViewDrawer(record) {
    steelPriceState.currentViewId = record.id;
    fillViewField('view-year', record.year);
    fillViewField('view-month', record.month);
    fillViewField('view-location', record.location);
    fillViewField('view-steel-mill', record.steel_mill);
    fillViewField('view-category-name', record.category_name);
    fillViewField('view-grade', record.grade);
    fillViewField('view-thickness', formatDecimal(record.thickness, 2));
    fillViewField('view-width', formatWidthPlain(record.width));
    fillViewField('view-spec', record.spec || '—');
    fillViewField('view-base-price', formatDecimal(record.base_price, 2));
    fillAdjustmentViewField('view-thickness-adjustment', record.thickness_adjustment);
    fillAdjustmentViewField('view-width-adjustment', record.width_adjustment);
    fillViewField('view-zinc-adjustment', formatDecimal(record.zinc_adjustment, 2));
    fillViewField('view-processing-fee', formatDecimalOrDash(record.processing_fee));
    fillViewField('view-other-adjustment', formatDecimal(record.other_adjustment, 2));
    fillViewField('view-final-price', formatDecimal(record.final_price_per_ton, 2));
    fillViewField('view-audit-status', AUDIT_LABEL[record.audit_status] || record.audit_status);
    fillViewField('view-audited-by', record.audited_by || '—');
    fillViewField('view-audited-at', formatDateTime(record.audited_at));
    fillViewField('view-audit-remark', record.audit_remark || '—');
    fillViewField('view-reverse-audited-by', record.reverse_audited_by || '—');
    fillViewField('view-reverse-audited-at', formatDateTime(record.reverse_audited_at));
    fillViewField('view-reverse-audit-remark', record.reverse_audit_remark || '—');
    fillViewField('view-match-status', record.match_status);
    fillViewField('view-calc-batch-id', record.calc_batch_id);
    fillViewField('view-calculated-at', formatDateTime(record.calculated_at));

    document.getElementById('view-trace-base').innerHTML = formatTrace('base', record);
    document.getElementById('view-trace-thickness').innerHTML = formatTrace('thickness', record);
    document.getElementById('view-trace-width').innerHTML = formatTrace('width', record);
    document.getElementById('view-trace-zinc').innerHTML = formatTrace('zinc', record);

    const approved = record.audit_status === 'approved';
    const pending = record.audit_status === 'pending';
    const rejected = record.audit_status === 'rejected';
    toggleHidden('viewDrawerApproveBtn', !(pending || rejected));
    toggleHidden('viewDrawerRejectBtn', !pending);
    toggleHidden('viewDrawerReverseBtn', !approved);
    toggleHidden('viewDrawerEditBtn', approved);

    openDrawer('viewDrawer', 'viewDrawerBackdrop');
}

function toggleHidden(id, shouldHide) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden', shouldHide);
}

function openDeleteDrawer(record) {
    if (record.audit_status === 'approved') {
        showToast('记录已审核通过，请先反审核后再删除', 'warning');
        return;
    }
    document.getElementById('deleteRecordId').value = record.id;
    const summary = document.getElementById('deleteSummary');
    if (summary) {
        summary.innerHTML = `
            <span class="text-[#d32f2f] font-mono">${esc(record.year)}-${esc(String(record.month).padStart(2, '0'))}</span>
            <span class="text-[#9e9e9e]"> / ${esc(record.location)} / ${esc(record.steel_mill)} / ${esc(record.grade)}</span>
            <span class="text-[#9e9e9e]"> / ${esc(formatDecimal(record.thickness, 2))}*${esc(formatWidthPlain(record.width))}</span>
        `;
    }
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
}

async function saveRecord() {
    const recordId = document.getElementById('editRecordId').value;
    if (!recordId) return;

    const basePrice = parseFloat(document.getElementById('editBasePrice').value);
    const thicknessAdjustment = parseFloat(document.getElementById('editThicknessAdjustment').value);
    const widthAdjustment = parseFloat(document.getElementById('editWidthAdjustment').value);
    const zincAdjustment = parseFloat(document.getElementById('editZincAdjustment').value);
    const processingFee = parseFloat(document.getElementById('editProcessingFee').value);
    const otherAdjustment = parseFloat(document.getElementById('editOtherAdjustment').value);
    const spec = document.getElementById('editSpec').value.trim() || null;
    const remark = document.getElementById('editRemark').value.trim() || null;

    if (
        Number.isNaN(basePrice) ||
        Number.isNaN(thicknessAdjustment) || Number.isNaN(widthAdjustment) ||
        Number.isNaN(zincAdjustment) || Number.isNaN(processingFee) ||
        Number.isNaN(otherAdjustment)
    ) {
        showToast('请填写所有必填数值字段', 'warning');
        return;
    }

    try {
        await HttpClient.put(`${API_BASE}/${recordId}`, {
            base_price: basePrice,
            thickness_adjustment: thicknessAdjustment,
            width_adjustment: widthAdjustment,
            zinc_adjustment: zincAdjustment,
            processing_fee: processingFee,
            other_adjustment: otherAdjustment,
            spec,
            remark,
        });
        showToast('更新成功', 'success');
        closeDrawer('editDrawer', 'editDrawerBackdrop');
        steelPriceState.filtersLoaded = false;
        loadData(steelPriceState.page);
    } catch (error) {
        console.error('保存钢材价格失败:', error);
    }
}

async function deleteRecord(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
        const nextPage = steelPriceState.records.length === 1 && steelPriceState.page > 1
            ? steelPriceState.page - 1
            : steelPriceState.page;
        steelPriceState.filtersLoaded = false;
        loadData(nextPage);
    } catch (error) {
        console.error('删除钢材价格失败:', error);
    }
}

async function handleApprove() {
    const id = steelPriceState.currentViewId;
    if (!id) return;
    const auditedBy = window.prompt('请输入审核人姓名（经理）');
    if (!auditedBy || !auditedBy.trim()) return;
    const auditRemark = window.prompt('审核意见（可选）') || null;
    try {
        await HttpClient.post(`${API_BASE}/${id}/approve`, {
            audited_by: auditedBy.trim(),
            audit_remark: auditRemark,
        });
        showToast('审核通过', 'success');
        closeDrawer('viewDrawer', 'viewDrawerBackdrop');
        steelPriceState.filtersLoaded = false;
        loadData(steelPriceState.page);
    } catch (error) {
        console.error('审核通过失败:', error);
    }
}

async function handleReject() {
    const id = steelPriceState.currentViewId;
    if (!id) return;
    const auditedBy = window.prompt('请输入审核人姓名（经理）');
    if (!auditedBy || !auditedBy.trim()) return;
    const auditRemark = window.prompt('驳回原因（可选）') || null;
    try {
        await HttpClient.post(`${API_BASE}/${id}/reject`, {
            audited_by: auditedBy.trim(),
            audit_remark: auditRemark,
        });
        showToast('已驳回', 'success');
        closeDrawer('viewDrawer', 'viewDrawerBackdrop');
        steelPriceState.filtersLoaded = false;
        loadData(steelPriceState.page);
    } catch (error) {
        console.error('审核驳回失败:', error);
    }
}

async function handleReverseAudit() {
    const id = steelPriceState.currentViewId;
    if (!id) return;
    const reverseAuditedBy = window.prompt('请输入反审核人姓名（经理）');
    if (!reverseAuditedBy || !reverseAuditedBy.trim()) return;
    const reverseAuditRemark = window.prompt('反审核原因（必填）');
    if (!reverseAuditRemark || !reverseAuditRemark.trim()) {
        showToast('反审核原因必填', 'warning');
        return;
    }
    try {
        await HttpClient.post(`${API_BASE}/${id}/reverse-audit`, {
            reverse_audited_by: reverseAuditedBy.trim(),
            reverse_audit_remark: reverseAuditRemark.trim(),
        });
        showToast('反审核成功', 'success');
        closeDrawer('viewDrawer', 'viewDrawerBackdrop');
        steelPriceState.filtersLoaded = false;
        loadData(steelPriceState.page);
    } catch (error) {
        console.error('反审核失败:', error);
    }
}

function setEditDrawerTitle(text) {
    const title = document.getElementById('editDrawerTitle');
    if (title) title.textContent = text;
}

function setBusinessKeyReadonly(readonly) {
    [
        'editYear',
        'editMonth',
        'editLocation',
        'editSteelMill',
        'editCategoryName',
        'editGrade',
        'editThickness',
        'editWidth',
    ].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.readOnly = readonly;
            element.classList.toggle('opacity-60', readonly);
            element.classList.toggle('cursor-not-allowed', readonly);
        }
    });
}

function fillViewField(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value ?? '—';
}

/** 厚度/宽度加价：BRABUS 极客风（冷钛白 / 暗红 / 低饱和灰） */
function fillAdjustmentViewField(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = formatAdjustmentSigned(value);
    element.classList.remove(
        'text-[#cccccc]',
        'text-[#4caf50]',
        'text-[#ef5350]',
        'text-[#9e9e9e]',
        'text-[#E0E0E0]',
        'text-[#C62828]',
        'text-[#444444]'
    );
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric) || numeric === 0) {
        element.classList.add('text-[#444444]');
    } else if (numeric > 0) {
        element.classList.add('text-[#E0E0E0]');
    } else {
        element.classList.add('text-[#C62828]');
    }
}

function formatDecimal(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

/** 加工费：为 0 时显示 -- */
function formatDecimalOrDash(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric) || numeric === 0) {
        return '--';
    }
    return formatDecimal(numeric, digits);
}

/** 厚度/宽度加价：显式 +/- 号；0 → -- */
function formatAdjustmentSigned(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric) || numeric === 0) {
        return '--';
    }
    const absText = Math.abs(numeric).toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
    return numeric > 0 ? `+${absText}` : `-${absText}`;
}

/** 宽度：整数、无千分位 */
function formatWidthPlain(value) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return String(Math.round(numeric));
}

function formatDateTime(value) {
    if (!value) return '—';
    try {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        const pad = n => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    } catch (error) {
        return value;
    }
}

export const pageConfig = {
    render: steelPriceListTemplate,
    init: () => init(),
};
