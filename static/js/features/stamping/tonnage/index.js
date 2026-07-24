/**
 * Tonnage Price Page
 * 吨位价格维护页面逻辑
 */

import { tonnagePriceTemplate, renderTableRows, renderPagination } from './template.js';

// 状态管理
const tonnagePriceState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    selectedYear: null,
    years: [],
    isLoading: false,
};

// API 基础路径
const API_BASE = '/api/stamping/tonnage-price';

/**
 * 页面初始化
 */
function init() {
    // 加载年份选项
    loadYearOptions();
    // 加载数据
    loadData();
    // 绑定事件
    bindEvents();
}

/**
 * 加载年份下拉选项
 */
async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/options/years`);
        tonnagePriceState.years = res.data || [];

        // 渲染年份筛选下拉
        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">全部年份</option>`;
            tonnagePriceState.years.forEach(year => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            // 确保包含当前年份
            if (!tonnagePriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
        }

        // 渲染复制弹窗的源年份下拉
        const sourceYearSelect = document.getElementById('sourceYear');
        if (sourceYearSelect) {
            let options = `<option value="">请选择源年份</option>`;
            tonnagePriceState.years.forEach(year => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            sourceYearSelect.innerHTML = options;
        }
    } catch (error) {
        console.error('加载年份选项失败:', error);
    }
}

/**
 * 加载数据
 */
async function loadData(page = 1) {
    if (tonnagePriceState.isLoading) return;
    tonnagePriceState.isLoading = true;

    const tableBody = document.getElementById('tonnagePriceTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCount = document.getElementById('totalCount');
    const paginationBtns = document.getElementById('paginationBtns');

    // 显示加载中
    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page: page,
            size: tonnagePriceState.pageSize,
        };

        if (tonnagePriceState.selectedYear) {
            params.year = tonnagePriceState.selectedYear;
        }

        const res = await HttpClient.get(API_BASE, { params });

        tonnagePriceState.records = res.data || [];
        tonnagePriceState.total = res.total || 0;
        tonnagePriceState.page = page;
        tonnagePriceState.totalPages = Math.ceil(tonnagePriceState.total / tonnagePriceState.pageSize) || 1;

        // 渲染表格
        if (tableBody) {
            if (tonnagePriceState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(tonnagePriceState.records);
                // 绑定表格行内按钮事件
                bindTableRowEvents();
            }
        }

        // 更新总计
        if (totalCount) {
            totalCount.textContent = `共 ${tonnagePriceState.total} 条`;
        }

        // 渲染分页
        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(
                tonnagePriceState.page,
                tonnagePriceState.totalPages,
                tonnagePriceState.total
            );
        }

    } catch (error) {
        console.error('加载数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
                        加载数据失败，请重试
                    </td>
                </tr>
            `;
        }
    } finally {
        tonnagePriceState.isLoading = false;
        if (loadingState) loadingState.classList.add('hidden');
    }
}

/**
 * 绑定表格行内按钮事件
 */
function bindTableRowEvents() {
    // 编辑按钮
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id);
            const record = tonnagePriceState.records.find(r => r.id === id);
            if (record) {
                openEditModal(record);
            }
        });
    });

    // 删除按钮
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id);
            openDeleteModal(id);
        });
    });
}

/**
 * 绑定事件
 */
function bindEvents() {
    // 新增按钮
    const btnAdd = document.getElementById('btnAddTonnagePrice');
    if (btnAdd) {
        btnAdd.addEventListener('click', () => openAddModal());
    }

    // 查询按钮
    const btnFilter = document.getElementById('btnFilter');
    if (btnFilter) {
        btnFilter.addEventListener('click', () => {
            const yearFilter = document.getElementById('yearFilter');
            tonnagePriceState.selectedYear = yearFilter ? yearFilter.value || null : null;
            loadData(1);
        });
    }

    // 复制模板按钮
    const btnCopy = document.getElementById('btnCopyTemplate');
    if (btnCopy) {
        btnCopy.addEventListener('click', () => openCopyModal());
    }

    // 编辑弹窗事件
    bindEditModalEvents();

    // 复制弹窗事件
    bindCopyModalEvents();

    // 删除弹窗事件
    bindDeleteModalEvents();

    // 分页按钮
    bindPaginationEvents();
}

/**
 * 绑定编辑弹窗事件
 */
function bindEditModalEvents() {
    const modal = document.getElementById('editModal');
    const closeBtn = document.getElementById('closeEditModal');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const backdrop = document.getElementById('editModalBackdrop');
    const form = document.getElementById('editForm');

    // 关闭弹窗
    const closeModal = () => {
        if (modal) modal.classList.add('hidden');
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);

    // 表单提交
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveRecord();
        });
    }
}

/**
 * 绑定复制弹窗事件
 */
function bindCopyModalEvents() {
    const modal = document.getElementById('copyModal');
    const closeBtn = document.getElementById('closeCopyModal');
    const cancelBtn = document.getElementById('cancelCopyBtn');
    const backdrop = document.getElementById('copyModalBackdrop');
    const form = document.getElementById('copyForm');

    const closeModal = () => {
        if (modal) modal.classList.add('hidden');
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await copyTemplate();
        });
    }
}

/**
 * 绑定删除弹窗事件
 */
function bindDeleteModalEvents() {
    const modal = document.getElementById('deleteModal');
    const closeBtn = document.getElementById('closeDeleteModal');
    const cancelBtn = document.getElementById('cancelDeleteBtn');
    const backdrop = document.getElementById('deleteModalBackdrop');
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    const closeModal = () => {
        if (modal) modal.classList.add('hidden');
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);

    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            const id = parseInt(document.getElementById('deleteRecordId')?.value);
            if (id) {
                await deleteRecord(id);
            }
        });
    }
}

/**
 * 绑定分页事件
 */
function bindPaginationEvents() {
    const container = document.getElementById('paginationBtns');
    if (container) {
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('.page-btn');
            if (btn && !btn.disabled) {
                const page = parseInt(btn.dataset.page);
                if (page) {
                    loadData(page);
                }
            }
        });
    }
}

/**
 * 打开新增弹窗
 */
function openAddModal() {
    const modal = document.getElementById('editModal');
    const title = document.getElementById('editModalTitle');
    const recordId = document.getElementById('editRecordId');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');
    const form = document.getElementById('editForm');

    if (title) title.textContent = '新增价格';
    if (recordId) recordId.value = '';
    if (yearInput) yearInput.value = new Date().getFullYear();
    if (tonnageInput) tonnageInput.value = '';
    if (priceInput) priceInput.value = '';
    if (form) form.reset();
    if (yearInput) yearInput.value = new Date().getFullYear();

    if (modal) modal.classList.remove('hidden');
    if (tonnageInput) tonnageInput.focus();
}

/**
 * 打开编辑弹窗
 */
function openEditModal(record) {
    const modal = document.getElementById('editModal');
    const title = document.getElementById('editModalTitle');
    const recordId = document.getElementById('editRecordId');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');

    if (title) title.textContent = '编辑价格';
    if (recordId) recordId.value = record.id;
    if (yearInput) yearInput.value = record.year;
    if (tonnageInput) tonnageInput.value = record.tonnage;
    if (priceInput) priceInput.value = record.price_per_stroke;

    if (modal) modal.classList.remove('hidden');
    if (priceInput) priceInput.focus();
}

/**
 * 打开删除确认弹窗
 */
function openDeleteModal(id) {
    const modal = document.getElementById('deleteModal');
    const recordIdInput = document.getElementById('deleteRecordId');
    if (recordIdInput) recordIdInput.value = id;
    if (modal) modal.classList.remove('hidden');
}

/**
 * 打开复制模板弹窗
 */
function openCopyModal() {
    const modal = document.getElementById('copyModal');
    const sourceYearSelect = document.getElementById('sourceYear');
    const targetYearInput = document.getElementById('targetYear');
    const form = document.getElementById('copyForm');

    if (form) form.reset();
    if (sourceYearSelect && tonnagePriceState.years.length > 0) {
        sourceYearSelect.value = tonnagePriceState.years[0] || '';
    }
    if (targetYearInput) {
        targetYearInput.value = new Date().getFullYear() + 1;
    }

    if (modal) modal.classList.remove('hidden');
}

/**
 * 保存记录（新增或更新）
 */
async function saveRecord() {
    const recordId = document.getElementById('editRecordId')?.value;
    const year = parseInt(document.getElementById('editYear')?.value);
    const tonnage = parseInt(document.getElementById('editTonnage')?.value);
    const price = parseFloat(document.getElementById('editPrice')?.value);

    if (!year || !tonnage || isNaN(price)) {
        showToast('请填写所有必填项', 'warning');
        return;
    }

    const data = {
        year,
        tonnage,
        price_per_stroke: price,
    };

    try {
        if (recordId) {
            // 更新
            await HttpClient.put(`${API_BASE}/${recordId}`, data);
            showToast('更新成功', 'success');
        } else {
            // 新增
            await HttpClient.post(API_BASE, data);
            showToast('创建成功', 'success');
        }

        // 关闭弹窗
        const modal = document.getElementById('editModal');
        if (modal) modal.classList.add('hidden');

        // 刷新数据
        loadData(tonnagePriceState.page);
        loadYearOptions();

    } catch (error) {
        console.error('保存失败:', error);
    }
}

/**
 * 删除记录
 */
async function deleteRecord(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');

        // 关闭弹窗
        const modal = document.getElementById('deleteModal');
        if (modal) modal.classList.add('hidden');

        // 刷新数据
        loadData(tonnagePriceState.page);

    } catch (error) {
        console.error('删除失败:', error);
    }
}

/**
 * 复制价格模板
 */
async function copyTemplate() {
    const sourceYear = parseInt(document.getElementById('sourceYear')?.value);
    const targetYear = parseInt(document.getElementById('targetYear')?.value);

    if (!sourceYear || !targetYear) {
        showToast('请选择源年份和目标年份', 'warning');
        return;
    }

    if (sourceYear === targetYear) {
        showToast('源年份和目标年份不能相同', 'warning');
        return;
    }

    try {
        await HttpClient.post(`${API_BASE}/copy`, {
            source_year: sourceYear,
            target_year: targetYear,
        });

        showToast(`成功从 ${sourceYear} 年复制到 ${targetYear} 年`, 'success');

        // 关闭弹窗
        const modal = document.getElementById('copyModal');
        if (modal) modal.classList.add('hidden');

        // 刷新数据
        loadData(1);
        loadYearOptions();

    } catch (error) {
        console.error('复制失败:', error);
    }
}

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: tonnagePriceTemplate,
    init: () => init(),
};
