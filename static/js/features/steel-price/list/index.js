/**
 * Steel Price List Page
 * 钢材价格计算结果浏览 / 手工维护 / 审核
 */

import { steelPriceListTemplate, renderSteelPricePagination, renderSteelPriceRows } from './template.js';

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
            grade: document.getElementById('steelPriceGrade')?.value.trim(),
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
    fillSelect('steelPriceYear', filters.years, value => `${value} 年`);
    fillSelect('steelPriceMonth', filters.months, value => `${value} 月`);
    fillSelect('steelPriceLocation', filters.locations);
    fillSelect('steelPriceCategory', filters.category_names);
    fillSelect('steelPriceMill', filters.steel_mills);
    fillSelect(
        'steelPriceAuditStatus',
        filters.audit_statuses,
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
    fillViewField('view-thickness', formatDecimal(record.thickness, 4));
    fillViewField('view-width', formatDecimal(record.width, 2));
    fillViewField('view-spec', record.spec || '—');
    fillViewField('view-base-price', formatDecimal(record.base_price));
    fillViewField('view-thickness-adjustment', formatDecimal(record.thickness_adjustment));
    fillViewField('view-width-adjustment', formatDecimal(record.width_adjustment));
    fillViewField('view-zinc-adjustment', formatDecimal(record.zinc_adjustment));
    fillViewField('view-processing-fee', formatDecimal(record.processing_fee));
    fillViewField('view-other-adjustment', formatDecimal(record.other_adjustment));
    fillViewField('view-final-price', formatDecimal(record.final_price_per_ton));
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
            <span class="text-[#9e9e9e]"> / ${esc(formatDecimal(record.thickness, 4))}*${esc(formatDecimal(record.width, 2))}</span>
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

function formatDecimal(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
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
