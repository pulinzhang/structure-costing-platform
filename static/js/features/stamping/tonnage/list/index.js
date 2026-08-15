/**
 * Tonnage Price Page
 * 冲次单价维护页面逻辑
 *
 * 抽屉式交互（与零件列表/partDrawer 对齐）：
 * - 编辑/新增  →editDrawer
 * - 复制模板  →copyDrawer
 * - 删除确认  →deleteDrawer
 */

import { tonnagePriceTemplate, renderTableRows, renderPagination } from './template.js?v=8';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

// 状态管理
const tonnagePriceState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    selectedLocation: null,
    selectedYear: null,
    locations: [],
    years: [],
    isLoading: false,
    isBatchDeleting: false,
};

const DEFAULT_LOCATION = '青岛';

// API 基础路径
const API_BASE = '/api/stamping/tonnage-price';

// 抽屉动画时长（与 template 中transition-transform duration-300 保持一致）
const DRAWER_ANIMATION_MS = 300;

/**
 * 打开抽屉 —全display:block，下一帧再 translate-x-0 触发滑入
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
 * 关闭抽屉 —translate-x-full 触发滑出，动画结束后冲display:none
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
    loadFilterOptions();
    loadData();
    bindEvents();
    bindPageSizeSelect('tonnagePageSize', {
        getSize: () => tonnagePriceState.pageSize,
        setSize: (size) => {
            tonnagePriceState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
}

function applyPermissionUi() {
    const canCreate = typeof can === 'function' ? can('op:stamping-tonnage:create') : true;
    const canCopy = typeof can === 'function' ? can('op:stamping-tonnage:copy') : true;
    const canExport = typeof can === 'function' ? can('op:stamping-tonnage:export') : true;
    const canDelete = typeof can === 'function' ? can('op:stamping-tonnage:delete') : true;
    if (!canCreate) document.getElementById('btnAddTonnagePrice')?.classList.add('hidden');
    if (!canCopy) document.getElementById('btnCopyTemplate')?.classList.add('hidden');
    if (!canExport) document.getElementById('btnExportTonnagePrice')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnBatchDeleteTonnagePrice')?.classList.add('hidden');
}

/**
 * 加载基地 / 年份下拉选项
 */
async function loadFilterOptions() {
    try {
        const [locRes, yearRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/filters/locations`),
            HttpClient.get(`${API_BASE}/filters/years`),
        ]);
        tonnagePriceState.locations = Array.isArray(locRes.data) ? locRes.data : [];
        tonnagePriceState.years = Array.isArray(yearRes.data) ? yearRes.data : [];

        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter) {
            let options = `<option value="">请选择基地</option>`;
            const known = ['大连', '芜湖', '鄂尔多斯', '青岛'];
            const merged = [...new Set([...known, ...tonnagePriceState.locations])];
            merged.forEach(loc => {
                options += `<option value="${esc(loc)}">${esc(loc)}</option>`;
            });
            locationFilter.innerHTML = options;
            if (tonnagePriceState.selectedLocation) {
                locationFilter.value = tonnagePriceState.selectedLocation;
            }
        }

        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">请选择年份</option>`;
            tonnagePriceState.years.forEach(year => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            if (!tonnagePriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
            if (tonnagePriceState.selectedYear) {
                yearFilter.value = tonnagePriceState.selectedYear;
            }
        }

        const sourceYearSelect = document.getElementById('sourceYear');
        if (sourceYearSelect) {
            let options = `<option value="">请选择源年份</option>`;
            tonnagePriceState.years.forEach(year => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            sourceYearSelect.innerHTML = options;
        }
    } catch (error) {
        console.error('加载筛选项失败:', error);
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

        if (tonnagePriceState.selectedLocation) {
            params.location = tonnagePriceState.selectedLocation;
        }

        if (tonnagePriceState.selectedYear) {
            params.year = tonnagePriceState.selectedYear;
        }

        // 分页接口：使用/paginate 端点
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
            totalCountPagination.textContent = `全${tonnagePriceState.total} 条`;
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
                    <td colspan="5" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
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
            e.stopPropagation();
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
            e.stopPropagation();
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

    const btnExport = document.getElementById('btnExportTonnagePrice');
    if (btnExport) {
        btnExport.addEventListener('click', () => exportExcel());
    }

    const btnBatchDelete = document.getElementById('btnBatchDeleteTonnagePrice');
    if (btnBatchDelete) {
        btnBatchDelete.addEventListener('click', () => batchDeleteByFilters());
    }

    const btnFilter = document.getElementById('btnFilter');
    if (btnFilter) {
        btnFilter.addEventListener('click', () => {
            const locationFilter = document.getElementById('locationFilter');
            const yearFilter = document.getElementById('yearFilter');
            tonnagePriceState.selectedLocation = locationFilter ? (locationFilter.value || null) : null;
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
    const locationInput = document.getElementById('editLocation');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');
    const form = document.getElementById('editForm');

    if (title) title.textContent = '新增价格';
    if (recordId) recordId.value = '';
    if (form) form.reset();
    if (locationInput) {
        locationInput.value = tonnagePriceState.selectedLocation || DEFAULT_LOCATION;
        locationInput.disabled = false;
    }
    if (yearInput) {
        yearInput.value = new Date().getFullYear();
        yearInput.disabled = false;
    }
    if (tonnageInput) {
        tonnageInput.value = '';
        tonnageInput.disabled = false;
    }
    if (priceInput) priceInput.value = '';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (locationInput) setTimeout(() => locationInput.focus(), DRAWER_ANIMATION_MS);
}

/**
 * 打开编辑抽屉
 */
function openEditDrawer(record) {
    const title = document.getElementById('editDrawerTitle');
    const recordId = document.getElementById('editRecordId');
    const locationInput = document.getElementById('editLocation');
    const yearInput = document.getElementById('editYear');
    const tonnageInput = document.getElementById('editTonnage');
    const priceInput = document.getElementById('editPrice');

    if (title) title.textContent = '编辑价格';
    if (recordId) recordId.value = record.id;
    if (locationInput) {
        locationInput.value = record.location;
        locationInput.disabled = true;
    }
    if (yearInput) {
        yearInput.value = record.year;
        yearInput.disabled = true;
    }
    if (tonnageInput) {
        tonnageInput.value = record.tonnage;
        tonnageInput.disabled = true;
    }
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
    const copyLocation = document.getElementById('copyLocation');
    const sourceYearSelect = document.getElementById('sourceYear');
    const targetYearInput = document.getElementById('targetYear');
    const form = document.getElementById('copyForm');

    if (form) form.reset();
    if (copyLocation) {
        copyLocation.value = tonnagePriceState.selectedLocation || DEFAULT_LOCATION;
    }
    if (sourceYearSelect && tonnagePriceState.years.length > 0) {
        sourceYearSelect.value = tonnagePriceState.years[0] || '';
    }
    if (targetYearInput) {
        targetYearInput.value = new Date().getFullYear() + 1;
    }

    openDrawer('copyDrawer', 'copyDrawerBackdrop');
}

/**
 * 按当前筛选条件导出Excel
 */
async function exportExcel() {
    const btn = document.getElementById('btnExportTonnagePrice');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            导出中..
        `;
    }

    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params: {
                location: tonnagePriceState.selectedLocation || undefined,
                year: tonnagePriceState.selectedYear || undefined,
            },
            defaultFilename: '冲次单价导出.xlsx',
        });

        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);
        showToast(`导出成功: ${filename}`', 'success');
    } catch (error) {
        console.error('导出冲次单价失败:', error);
        if (!error.status) {
            showToast(error.message || '导出失败', 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

/**
 * 按基地+ 年度批量删除（两者必选）
 */
async function batchDeleteByFilters() {
    if (typeof can === 'function' && !can('op:stamping-tonnage:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (tonnagePriceState.isBatchDeleting) return;

    const locationFilter = document.getElementById('locationFilter');
    const yearFilter = document.getElementById('yearFilter');
    const location = locationFilter?.value?.trim() || '';
    const yearRaw = yearFilter?.value?.trim() || '';

    if (!location || !yearRaw) {
        showToast('批量删除须同时选择基地和年度', 'warning');
        return;
    }

    const year = parseInt(yearRaw, 10);
    if (!year || year < 2000 || year > 2100) {
        showToast('请选择正确的年度', 'warning');
        return;
    }

    const confirmed = window.confirm(
        `确定批量删除以下冲次单价吗？\n\n基地: ${location} | 年度: ${year}\n\n将删除该基地该年全部记录，此操作不可恢复！`
    );
    if (!confirmed) return;

    const btn = document.getElementById('btnBatchDeleteTonnagePrice');
    const originalHtml = btn ? btn.innerHTML : '';
    tonnagePriceState.isBatchDeleting = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中..
        `;
    }

    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, {
            location,
            year,
        });
        const data = res.data || {};
        showToast(
            res.message || data.message || `已删除${data.deleted_count ?? 0} 条`,
            'success'
        );
        tonnagePriceState.selectedLocation = location;
        tonnagePriceState.selectedYear = String(year);
        await loadData(1);
        await loadFilterOptions();
    } catch (error) {
        console.error('批量删除冲次单价失败:', error);
        if (!error.status) {
            showToast(error.message || '批量删除失败', 'error');
        }
    } finally {
        tonnagePriceState.isBatchDeleting = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

/**
 * 保存记录（新增或更新）
 */
async function saveRecord() {
    const recordId = document.getElementById('editRecordId')?.value;
    const location = document.getElementById('editLocation')?.value?.trim();
    const year = parseInt(document.getElementById('editYear')?.value);
    const tonnage = parseInt(document.getElementById('editTonnage')?.value);
    const price = parseFloat(document.getElementById('editPrice')?.value);

    if (!recordId && (!location || !year || !tonnage || isNaN(price))) {
        showToast('请填写所有必填项', 'warning');
        return;
    }
    if (recordId && isNaN(price)) {
        showToast('请填写单冲次价格', 'warning');
        return;
    }

    try {
        if (recordId) {
            await HttpClient.put(`${API_BASE}/${recordId}`, {
                price_per_stroke: price,
            });
            showToast('更新成功', 'success');
        } else {
            await HttpClient.post(API_BASE, {
                location,
                year,
                tonnage,
                price_per_stroke: price,
            });
            showToast('创建成功', 'success');
        }

        closeDrawer('editDrawer', 'editDrawerBackdrop');
        loadData(tonnagePriceState.page);
        loadFilterOptions();
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
    const location = document.getElementById('copyLocation')?.value?.trim();
    const sourceYear = parseInt(document.getElementById('sourceYear')?.value);
    const targetYear = parseInt(document.getElementById('targetYear')?.value);

    if (!location || !sourceYear || !targetYear) {
        showToast('请选择基地、源年份和目标年份', 'warning');
        return;
    }

    if (sourceYear === targetYear) {
        showToast('源年份和目标年份不能相同', 'warning');
        return;
    }

    try {
        await HttpClient.post(
            `${API_BASE}/copy-year?location=${encodeURIComponent(location)}&source_year=${sourceYear}&target_year=${targetYear}`
        );

        showToast(`成功将。{location}」从 ${sourceYear} 年复制到 ${targetYear} 年`', 'success');

        closeDrawer('copyDrawer', 'copyDrawerBackdrop');
        loadData(1);
        loadFilterOptions();
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
