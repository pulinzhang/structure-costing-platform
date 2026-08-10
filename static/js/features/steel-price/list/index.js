/**
 * Steel Price List Page
 * 钢材价格表格浏览页面逻辑
 *
 * 抽屉式交互（与冲次费率 tonnage/index.js 对齐）：
 * - 新增 / 编辑  → editDrawer
 * - 查看详情     → viewDrawer
 * - 删除确认     → deleteDrawer
 */

import { steelPriceListTemplate, renderSteelPricePagination, renderSteelPriceRows } from './template.js';

// 状态管理
const steelPriceState = {
    records: [],
    total: 0,
    page: 1,
    size: 20,
    totalPages: 1,
    filtersLoaded: false,
};

// API 基础路径
const API_BASE = '/api/steel-prices';

// 抽屉动画时长（与 template 中 transition-transform duration-300 保持一致）
const DRAWER_ANIMATION_MS = 300;

/**
 * 打开抽屉 — 先 display:block，下一帧再 translate-x-0 触发滑入
 */
function openDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.style.display = 'flex';
    if (backdrop) backdrop.style.display = 'block';
    // 强制 reflow，让 transition 生效
    void drawer.offsetWidth;
    drawer.classList.remove('translate-x-full');
    drawer.classList.add('translate-x-0');
}

/**
 * 关闭抽屉 — translate-x-full 触发滑出，动画结束后再 display:none
 */
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

/**
 * 页面初始化
 */
function init() {
    bindEvents();
    loadData(1);
}

/**
 * 加载数据
 */
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
            year: getFilterValue('steelPriceYear'),
            month: getFilterValue('steelPriceMonth'),
            steel_type: getFilterValue('steelPriceType'),
            grade: document.getElementById('steelPriceGrade')?.value.trim(),
            steel_mill: getFilterValue('steelPriceMill'),
        };

        const response = await HttpClient.get(API_BASE, { params });
        const payload = response.data || {};
        const records = Array.isArray(payload.list) ? payload.list : [];

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
            steelPriceState.filtersLoaded = true;
        }
    } catch (error) {
        console.error('加载钢材价格失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="13" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
                        加载数据失败，请重试
                    </td>
                </tr>`;
        }
    } finally {
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

/**
 * 渲染筛选下拉选项
 */
function renderFilters(filters) {
    fillSelect('steelPriceYear', filters.years, value => `${value} 年`);
    fillSelect('steelPriceMonth', filters.months, value => `${value} 月`);
    fillSelect('steelPriceType', filters.steel_types);
    fillSelect('steelPriceMill', filters.steel_mills);
}

function fillSelect(id, values = [], label = value => value) {
    const select = document.getElementById(id);
    if (!select) return;
    select.innerHTML =
        '<option value="">全部</option>' +
        values.map(value => `<option value="${esc(value)}">${esc(label(value))}</option>`).join('');
}

/**
 * 重置筛选
 */
function resetFilters() {
    ['steelPriceYear', 'steelPriceMonth', 'steelPriceType', 'steelPriceGrade', 'steelPriceMill']
        .forEach(id => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
    loadData(1);
}

/**
 * 绑定表格行内按钮事件
 */
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

/**
 * 绑定页面事件
 */
function bindEvents() {
    const btnAdd = document.getElementById('btnAddSteelPrice');
    if (btnAdd) btnAdd.addEventListener('click', () => openAddDrawer());

    const btnSearch = document.getElementById('steelPriceSearchButton');
    if (btnSearch) btnSearch.addEventListener('click', () => loadData(1));

    const gradeInput = document.getElementById('steelPriceGrade');
    if (gradeInput) {
        gradeInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                loadData(1);
            }
        });
    }

    const btnReset = document.getElementById('steelPriceResetFilterButton');
    if (btnReset) btnReset.addEventListener('click', () => resetFilters());

    // 分页
    const pagination = document.getElementById('steelPricePagination');
    if (pagination) {
        pagination.addEventListener('click', event => {
            const btn = event.target.closest('.steel-price-page-btn');
            if (btn && !btn.disabled) {
                const page = parseInt(btn.dataset.page);
                if (page) loadData(page);
            }
        });
    }

    bindEditDrawerEvents();
    bindViewDrawerEvents();
    bindDeleteDrawerEvents();
}

/**
 * 绑定编辑抽屉事件
 */
function bindEditDrawerEvents() {
    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');

    document.getElementById('closeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelEditBtn')?.addEventListener('click', close);
    document.getElementById('editDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitEditBtn')?.addEventListener('click', async event => {
        event.preventDefault();
        await saveRecord();
    });
    document.addEventListener('keydown', event => {
        const drawer = document.getElementById('editDrawer');
        if (event.key === 'Escape' && drawer && drawer.style.display === 'flex') {
            close();
        }
    });
}

/**
 * 绑定查看抽屉事件
 */
function bindViewDrawerEvents() {
    const close = () => closeDrawer('viewDrawer', 'viewDrawerBackdrop');

    document.getElementById('closeViewDrawer')?.addEventListener('click', close);
    document.getElementById('viewDrawerBackdrop')?.addEventListener('click', close);

    // 查看抽屉底部"编辑"按钮 → 直接关闭查看、打开编辑
    document.getElementById('viewDrawerEditBtn')?.addEventListener('click', () => {
        const recordId = Number(document.getElementById('editRecordId')?.value || 0);
        close();
        const record = steelPriceState.records.find(r => r.id === recordId);
        if (record) {
            setTimeout(() => openEditDrawer(record), DRAWER_ANIMATION_MS);
        }
    });

    document.addEventListener('keydown', event => {
        const drawer = document.getElementById('viewDrawer');
        if (event.key === 'Escape' && drawer && drawer.style.display === 'flex') {
            close();
        }
    });
}

/**
 * 绑定删除抽屉事件
 */
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

// ===== 抽屉业务函数 =====

/**
 * 打开新增抽屉
 */
function openAddDrawer() {
    setEditDrawerTitle('新增钢材价格');
    document.getElementById('editRecordId').value = '';
    document.getElementById('editForm').reset();

    // 设置合理默认值
    const yearInput = document.getElementById('editYear');
    if (yearInput) yearInput.value = new Date().getFullYear();
    const monthInput = document.getElementById('editMonth');
    if (monthInput) monthInput.value = new Date().getMonth() + 1;

    // 业务主键在新增场景可编辑，在编辑场景禁用
    setBusinessKeyReadonly(false);

    openDrawer('editDrawer', 'editDrawerBackdrop');
    setTimeout(() => document.getElementById('editSteelType')?.focus(), DRAWER_ANIMATION_MS);
}

/**
 * 打开编辑抽屉
 */
function openEditDrawer(record) {
    setEditDrawerTitle('编辑钢材价格');
    document.getElementById('editRecordId').value = record.id;

    document.getElementById('editYear').value = record.year;
    document.getElementById('editMonth').value = record.month;
    document.getElementById('editSteelType').value = record.steel_type || '';
    document.getElementById('editGrade').value = record.grade || '';
    document.getElementById('editReferenceSpec').value = record.reference_spec || '';
    document.getElementById('editSteelMill').value = record.steel_mill || '';
    document.getElementById('editThickness').value = record.thickness ?? '';
    document.getElementById('editBidPrice').value = record.bid_price ?? '';
    document.getElementById('editThicknessAdjustment').value = record.thickness_adjustment ?? '';
    document.getElementById('editProcessingFee').value = record.processing_fee ?? '';
    document.getElementById('editFinalPrice').value = record.final_price_per_ton ?? '';
    document.getElementById('editRemark').value = record.remark || '';

    // 编辑场景：业务主键禁用
    setBusinessKeyReadonly(true);

    openDrawer('editDrawer', 'editDrawerBackdrop');
    setTimeout(() => document.getElementById('editBidPrice')?.focus(), DRAWER_ANIMATION_MS);
}

/**
 * 打开查看抽屉
 */
function openViewDrawer(record) {
    // 为底部"编辑"按钮预设记录 id
    document.getElementById('editRecordId').value = record.id;

    fillViewField('view-year', record.year);
    fillViewField('view-month', record.month);
    fillViewField('view-grade', record.grade);
    fillViewField('view-thickness', formatDecimal(record.thickness, 4));
    fillViewField('view-steel-type', record.steel_type);
    fillViewField('view-reference-spec', record.reference_spec);
    fillViewField('view-steel-mill', record.steel_mill);
    fillViewField('view-bid-price', formatDecimal(record.bid_price));
    fillViewField('view-thickness-adjustment', formatDecimal(record.thickness_adjustment));
    fillViewField('view-processing-fee', formatDecimal(record.processing_fee));
    fillViewField('view-final-price', formatDecimal(record.final_price_per_ton));
    fillViewField('view-remark', record.remark || '—');
    fillViewField('view-created-at', formatDateTime(record.created_at));
    fillViewField('view-updated-at', formatDateTime(record.updated_at));

    openDrawer('viewDrawer', 'viewDrawerBackdrop');
}

/**
 * 打开删除确认抽屉
 */
function openDeleteDrawer(record) {
    document.getElementById('deleteRecordId').value = record.id;
    const summary = document.getElementById('deleteSummary');
    if (summary) {
        summary.innerHTML = `
            <span class="text-[#9e9e9e]">记录：</span>
            <span class="text-[#d32f2f] font-mono">${esc(record.year)}-${esc(String(record.month).padStart(2, '0'))}</span>
            <span class="text-[#9e9e9e]"> / </span>
            <span class="text-[#cccccc]">${esc(record.steel_type)}</span>
            <span class="text-[#9e9e9e]"> / </span>
            <span class="text-[#cccccc]">${esc(record.grade)}</span>
            <span class="text-[#9e9e9e]"> / </span>
            <span class="text-[#cccccc] font-mono">${esc(formatDecimal(record.thickness, 4))} mm</span>
        `;
    }
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
}

/**
 * 保存记录（新增或更新）
 */
async function saveRecord() {
    const recordId = document.getElementById('editRecordId').value;
    const isEdit = Boolean(recordId);

    const year = parseInt(document.getElementById('editYear').value);
    const month = parseInt(document.getElementById('editMonth').value);
    const steelType = document.getElementById('editSteelType').value.trim();
    const grade = document.getElementById('editGrade').value.trim();
    const referenceSpec = document.getElementById('editReferenceSpec').value.trim();
    const steelMill = document.getElementById('editSteelMill').value.trim();
    const thickness = parseFloat(document.getElementById('editThickness').value);
    const bidPrice = parseFloat(document.getElementById('editBidPrice').value);
    const thicknessAdjustment = parseFloat(document.getElementById('editThicknessAdjustment').value);
    const processingFee = parseFloat(document.getElementById('editProcessingFee').value);
    const finalPrice = parseFloat(document.getElementById('editFinalPrice').value);
    const remark = document.getElementById('editRemark').value.trim() || null;

    if (
        Number.isNaN(year) || Number.isNaN(month) ||
        Number.isNaN(thickness) || Number.isNaN(bidPrice) ||
        Number.isNaN(thicknessAdjustment) || Number.isNaN(processingFee) ||
        Number.isNaN(finalPrice)
    ) {
        showToast('请填写所有必填数值字段', 'warning');
        return;
    }
    if (!steelType || !grade || !referenceSpec || !steelMill) {
        showToast('请填写钢种、牌号、参考规格、钢厂', 'warning');
        return;
    }

    try {
        if (isEdit) {
            // 仅可编辑字段
            const payload = {
                bid_price: bidPrice,
                thickness_adjustment: thicknessAdjustment,
                processing_fee: processingFee,
                final_price_per_ton: finalPrice,
                remark,
                steel_type: steelType,
                steel_mill: steelMill,
                reference_spec: referenceSpec,
            };
            await HttpClient.put(`${API_BASE}/${recordId}`, payload);
            showToast('更新成功', 'success');
        } else {
            const payload = {
                year, month, steel_type: steelType, grade,
                reference_spec: referenceSpec, steel_mill: steelMill,
                thickness, bid_price: bidPrice,
                thickness_adjustment: thicknessAdjustment,
                processing_fee: processingFee,
                final_price_per_ton: finalPrice,
                remark,
            };
            await HttpClient.post(API_BASE, payload);
            showToast('创建成功', 'success');
        }

        closeDrawer('editDrawer', 'editDrawerBackdrop');
        // 重置筛选下拉的"已加载"标记，避免服务器侧选项变化（新增/删除）未生效
        steelPriceState.filtersLoaded = false;
        loadData(steelPriceState.page);
    } catch (error) {
        console.error('保存钢材价格失败:', error);
    }
}

/**
 * 删除记录
 */
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

// ===== 工具函数 =====

function setEditDrawerTitle(text) {
    const title = document.getElementById('editDrawerTitle');
    if (title) title.textContent = text;
}

function setBusinessKeyReadonly(readonly) {
    ['editYear', 'editMonth', 'editGrade', 'editThickness'].forEach(id => {
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

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: steelPriceListTemplate,
    init: () => init(),
};
