/**
 * Tonnage Price Page
 * 冲次费率维护页面逻辑
 *
 * 抽屉式交互（与零件列表 /partDrawer 对齐）：
 * - 编辑/新增  → editDrawer
 * - 复制模板  → copyDrawer
 * - 删除确认  → deleteDrawer
 */

import { tonnagePriceTemplate, renderTableRows, renderPagination } from './template.js';

// 状态管理
const tonnagePriceState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    selectedYear: null,
    years: [],
    isLoading: false,
};

// API 基础路径
const API_BASE = '/api/stamping/tonnage-price';

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
    loadYearOptions();
    loadData();
    bindEvents();
}

/**
 * 加载年份下拉选项
 */
async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        tonnagePriceState.years = Array.isArray(res.data) ? res.data : [];

        // 渲染年份筛选下拉
        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">全部年份</option>`;
            tonnagePriceState.years.forEach(year => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            if (!tonnagePriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
        }

        // 渲染复制抽屉的源年份下拉
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
    const totalCountPagination = document.getElementById('totalCountPagination');
    const paginationBtns = document.getElementById('paginationBtns');

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

        // 分页接口：使用 /paginate 端点
        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};

        tonnagePriceState.records = pageResult.items || [];
        tonnagePriceState.total = pageResult.total || 0;
        tonnagePriceState.page = pageResult.page || page;
        tonnagePriceState.totalPages = pageResult.total_pages || 1;

        if (tableBody) {
            if (tonnagePriceState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(tonnagePriceState.records);
                bindTableRowEvents();
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${tonnagePriceState.total} 条`;
        }

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
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id);
            const record = tonnagePriceState.records.find(r => r.id === id);
            if (record) {
                openEditDrawer(record);
            }
        });
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id);
            openDeleteDrawer(id);
        });
    });
}

/**
 * 绑定事件
 */
function bindEvents() {
    const btnAdd = document.getElementById('btnAddTonnagePrice');
    if (btnAdd) {
        btnAdd.addEventListener('click', () => openAddDrawer());
    }

    const btnFilter = document.getElementById('btnFilter');
    if (btnFilter) {
        btnFilter.addEventListener('click', () => {
            const yearFilter = document.getElementById('yearFilter');
            tonnagePriceState.selectedYear = yearFilter ? (yearFilter.value || null) : null;
            loadData(1);
        });
    }

    const btnCopy = document.getElementById('btnCopyTemplate');
    if (btnCopy) {
        btnCopy.addEventListener('click', () => openCopyDrawer());
    }

    bindEditDrawerEvents();
    bindCopyDrawerEvents();
    bindDeleteDrawerEvents();
    bindPaginationEvents();
}

/**
 * 绑定编辑抽屉事件
 */
function bindEditDrawerEvents() {
    const closeBtn = document.getElementById('closeEditDrawer');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const backdrop = document.getElementById('editDrawerBackdrop');
    const submitBtn = document.getElementById('submitEditBtn');

    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

    // 保存按钮（form submit 由按钮点击触发，等价于表单提交）
    if (submitBtn) {
        submitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await saveRecord();
        });
    }

    // Esc 关闭
    document.addEventListener('keydown', (e) => {
        const drawer = document.getElementById('editDrawer');
        if (e.key === 'Escape' && drawer && drawer.style.display === 'flex') {
            close();
        }
    });
}

/**
 * 绑定复制抽屉事件
 */
function bindCopyDrawerEvents() {
    const closeBtn = document.getElementById('closeCopyDrawer');
    const cancelBtn = document.getElementById('cancelCopyBtn');
    const backdrop = document.getElementById('copyDrawerBackdrop');
    const submitBtn = document.getElementById('submitCopyBtn');

    const close = () => closeDrawer('copyDrawer', 'copyDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

    if (submitBtn) {
        submitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await copyTemplate();
        });
    }
}

/**
 * 绑定删除抽屉事件
 */
function bindDeleteDrawerEvents() {
    const closeBtn = document.getElementById('closeDeleteDrawer');
    const cancelBtn = document.getElementById('cancelDeleteBtn');
    const backdrop = document.getElementById('deleteDrawerBackdrop');
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    const close = () => closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

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
 * 打开新增抽屉
 */
function openAddDrawer() {
    const title = document.getElementById('editDrawerTitle');
    const recordId = document.getElementById('editRecordId');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');
    const form = document.getElementById('editForm');

    if (title) title.textContent = '新增价格';
    if (recordId) recordId.value = '';
    if (form) form.reset();
    if (yearInput) yearInput.value = new Date().getFullYear();
    if (tonnageInput) tonnageInput.value = '';
    if (priceInput) priceInput.value = '';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (tonnageInput) setTimeout(() => tonnageInput.focus(), DRAWER_ANIMATION_MS);
}

/**
 * 打开编辑抽屉
 */
function openEditDrawer(record) {
    const title = document.getElementById('editDrawerTitle');
    const recordId = document.getElementById('editRecordId');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');

    if (title) title.textContent = '编辑价格';
    if (recordId) recordId.value = record.id;
    if (yearInput) yearInput.value = record.year;
    if (tonnageInput) tonnageInput.value = record.tonnage;
    if (priceInput) priceInput.value = record.price_per_stroke;

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (priceInput) setTimeout(() => priceInput.focus(), DRAWER_ANIMATION_MS);
}

/**
 * 打开删除确认抽屉
 */
function openDeleteDrawer(id) {
    const recordIdInput = document.getElementById('deleteRecordId');
    if (recordIdInput) recordIdInput.value = id;
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
}

/**
 * 打开复制模板抽屉
 */
function openCopyDrawer() {
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

    openDrawer('copyDrawer', 'copyDrawerBackdrop');
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
            await HttpClient.put(`${API_BASE}/${recordId}`, data);
            showToast('更新成功', 'success');
        } else {
            await HttpClient.post(API_BASE, data);
            showToast('创建成功', 'success');
        }

        closeDrawer('editDrawer', 'editDrawerBackdrop');
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

        closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
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
        await HttpClient.post(`${API_BASE}/copy-year?source_year=${sourceYear}&target_year=${targetYear}`);

        showToast(`成功从 ${sourceYear} 年复制到 ${targetYear} 年`, 'success');

        closeDrawer('copyDrawer', 'copyDrawerBackdrop');
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
