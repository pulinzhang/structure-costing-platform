/**
 * 焊接单价维护页面逻辑
 */

import { weldingUnitPriceTemplate, renderTableRows, renderPagination, unitPriceInputValue, parseUnitPriceInput } from './template.js?v=4';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const weldingUnitPriceState = {
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
const API_BASE = '/api/bom/welding-unit-price';
const DRAWER_ANIMATION_MS = 300;

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
    loadFilterOptions();
    loadData();
    bindEvents();
    bindPageSizeSelect('weldingUnitPricePageSize', {
        getSize: () => weldingUnitPriceState.pageSize,
        setSize: (size) => {
            weldingUnitPriceState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    applyPermissionUi();
}

function applyPermissionUi() {
    const canCreate = typeof window.can === 'function' ? window.can('op:bom-welding-unit-price:create') : true;
    const canCopy = typeof window.can === 'function' ? window.can('op:bom-welding-unit-price:copy') : true;
    const canExport = typeof window.can === 'function' ? window.can('op:bom-welding-unit-price:export') : true;
    const canDelete = typeof window.can === 'function' ? window.can('op:bom-welding-unit-price:delete') : true;
    if (!canCreate) document.getElementById('btnAddWeldingUnitPrice')?.classList.add('hidden');
    if (!canCopy) document.getElementById('btnCopyTemplate')?.classList.add('hidden');
    if (!canExport) document.getElementById('btnExportWeldingUnitPrice')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnBatchDeleteWeldingUnitPrice')?.classList.add('hidden');
}

async function loadFilterOptions() {
    try {
        const [locRes, yearRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/filters/locations`),
            HttpClient.get(`${API_BASE}/filters/years`),
        ]);
        weldingUnitPriceState.locations = Array.isArray(locRes.data) ? locRes.data : [];
        weldingUnitPriceState.years = Array.isArray(yearRes.data) ? yearRes.data : [];

        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter) {
            let options = `<option value="">请选择基地</option>`;
            const known = ['大连', '芜湖', '鄂尔多斯', '青岛'];
            const merged = [...new Set([...known, ...weldingUnitPriceState.locations])];
            merged.forEach((loc) => {
                options += `<option value="${esc(loc)}">${esc(loc)}</option>`;
            });
            locationFilter.innerHTML = options;
            if (weldingUnitPriceState.selectedLocation) {
                locationFilter.value = weldingUnitPriceState.selectedLocation;
            }
        }

        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) {
            const currentYear = new Date().getFullYear();
            let options = `<option value="">请选择年份</option>`;
            weldingUnitPriceState.years.forEach((year) => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            if (!weldingUnitPriceState.years.includes(currentYear)) {
                options += `<option value="${currentYear}">${currentYear} 年</option>`;
            }
            yearFilter.innerHTML = options;
            if (weldingUnitPriceState.selectedYear) {
                yearFilter.value = weldingUnitPriceState.selectedYear;
            }
        }

        const sourceYearSelect = document.getElementById('sourceYear');
        if (sourceYearSelect) {
            let options = `<option value="">请选择源年份</option>`;
            weldingUnitPriceState.years.forEach((year) => {
                options += `<option value="${year}">${year} 年</option>`;
            });
            sourceYearSelect.innerHTML = options;
        }
    } catch (error) {
        console.error('加载筛选项失败:', error);
    }
}

async function loadData(page = 1) {
    if (weldingUnitPriceState.isLoading) return;
    weldingUnitPriceState.isLoading = true;

    const tableBody = document.getElementById('weldingUnitPriceTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCountPagination = document.getElementById('totalCountPagination');
    const paginationBtns = document.getElementById('paginationBtns');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page,
            size: weldingUnitPriceState.pageSize,
        };

        if (weldingUnitPriceState.selectedLocation) {
            params.location = weldingUnitPriceState.selectedLocation;
        }
        if (weldingUnitPriceState.selectedYear) {
            params.year = weldingUnitPriceState.selectedYear;
        }

        const res = await HttpClient.get(`${API_BASE}/paginate`, { params });
        const pageResult = res.data || {};

        weldingUnitPriceState.records = pageResult.items || [];
        weldingUnitPriceState.total = pageResult.total || 0;
        weldingUnitPriceState.page = pageResult.page || page;
        weldingUnitPriceState.totalPages = pageResult.total_pages || 1;

        if (tableBody) {
            if (weldingUnitPriceState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(weldingUnitPriceState.records);
                bindTableRowEvents();
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${weldingUnitPriceState.total} 条`;
        }

        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(
                weldingUnitPriceState.page,
                weldingUnitPriceState.totalPages,
                weldingUnitPriceState.total
            );
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
                        加载数据失败，请重试
                    </td>
                </tr>
            `;
        }
    } finally {
        weldingUnitPriceState.isLoading = false;
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function bindTableRowEvents() {
    document.querySelectorAll('.edit-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = weldingUnitPriceState.records.find((r) => r.id === id);
            if (record) openEditDrawer(record);
        });
    });

    document.querySelectorAll('.delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            openDeleteDrawer(id);
        });
    });
}

function bindEvents() {
    document.getElementById('btnAddWeldingUnitPrice')?.addEventListener('click', () => openAddDrawer());
    document.getElementById('btnExportWeldingUnitPrice')?.addEventListener('click', () => exportExcel());
    document.getElementById('btnBatchDeleteWeldingUnitPrice')?.addEventListener('click', () => batchDeleteByFilters());
    document.getElementById('btnFilter')?.addEventListener('click', () => {
        const locationFilter = document.getElementById('locationFilter');
        const yearFilter = document.getElementById('yearFilter');
        weldingUnitPriceState.selectedLocation = locationFilter ? (locationFilter.value || null) : null;
        weldingUnitPriceState.selectedYear = yearFilter ? (yearFilter.value || null) : null;
        loadData(1);
    });
    document.getElementById('btnCopyTemplate')?.addEventListener('click', () => openCopyDrawer());

    bindEditDrawerEvents();
    bindCopyDrawerEvents();
    bindDeleteDrawerEvents();
    bindPaginationEvents();
}

function bindEditDrawerEvents() {
    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');
    document.getElementById('closeEditDrawer')?.addEventListener('click', close);
    document.getElementById('cancelEditBtn')?.addEventListener('click', close);
    document.getElementById('editDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitEditBtn')?.addEventListener('click', async (e) => {
        e.preventDefault();
        await saveRecord();
    });
    document.addEventListener('keydown', (e) => {
        const drawer = document.getElementById('editDrawer');
        if (e.key === 'Escape' && drawer && drawer.style.display === 'flex') {
            close();
        }
    });
}

function bindCopyDrawerEvents() {
    const close = () => closeDrawer('copyDrawer', 'copyDrawerBackdrop');
    document.getElementById('closeCopyDrawer')?.addEventListener('click', close);
    document.getElementById('cancelCopyBtn')?.addEventListener('click', close);
    document.getElementById('copyDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('submitCopyBtn')?.addEventListener('click', async (e) => {
        e.preventDefault();
        await copyTemplate();
    });
}

function bindDeleteDrawerEvents() {
    const close = () => closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
    document.getElementById('closeDeleteDrawer')?.addEventListener('click', close);
    document.getElementById('cancelDeleteBtn')?.addEventListener('click', close);
    document.getElementById('deleteDrawerBackdrop')?.addEventListener('click', close);
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', async () => {
        const id = parseInt(document.getElementById('deleteRecordId')?.value, 10);
        if (id) await deleteRecord(id);
    });
}

function bindPaginationEvents() {
    document.getElementById('paginationBtns')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadData(page);
        }
    });
}

function openAddDrawer() {
    const title = document.getElementById('editDrawerTitle');
    const recordId = document.getElementById('editRecordId');
    const locationInput = document.getElementById('editLocation');
    const yearInput = document.getElementById('editYear');
    const itemNameInput = document.getElementById('editItemName');
    const unitInput = document.getElementById('editUnit');
    const unitPriceInput = document.getElementById('editUnitPrice');
    const remarkInput = document.getElementById('editRemark');
    const form = document.getElementById('editForm');

    if (title) title.textContent = '新增费用';
    if (recordId) recordId.value = '';
    if (form) form.reset();
    if (locationInput) {
        locationInput.value = weldingUnitPriceState.selectedLocation || DEFAULT_LOCATION;
        locationInput.disabled = false;
    }
    if (yearInput) {
        yearInput.value = new Date().getFullYear();
        yearInput.disabled = false;
    }
    if (itemNameInput) {
        itemNameInput.value = '';
        itemNameInput.disabled = false;
    }
    if (unitInput) unitInput.value = '';
    if (unitPriceInput) unitPriceInput.value = '';
    if (remarkInput) remarkInput.value = '';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (itemNameInput) setTimeout(() => itemNameInput.focus(), DRAWER_ANIMATION_MS);
}

function openEditDrawer(record) {
    const title = document.getElementById('editDrawerTitle');
    const recordId = document.getElementById('editRecordId');
    const locationInput = document.getElementById('editLocation');
    const yearInput = document.getElementById('editYear');
    const itemNameInput = document.getElementById('editItemName');
    const unitInput = document.getElementById('editUnit');
    const unitPriceInput = document.getElementById('editUnitPrice');
    const remarkInput = document.getElementById('editRemark');

    if (title) title.textContent = '编辑费用';
    if (recordId) recordId.value = record.id;
    if (locationInput) {
        locationInput.value = record.location;
        locationInput.disabled = true;
    }
    if (yearInput) {
        yearInput.value = record.year;
        yearInput.disabled = true;
    }
    if (itemNameInput) {
        itemNameInput.value = record.item_name;
        itemNameInput.disabled = true;
    }
    if (unitInput) unitInput.value = record.unit || '';
    if (unitPriceInput) unitPriceInput.value = unitPriceInputValue(record.unit_price);
    if (remarkInput) remarkInput.value = record.remark || '';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (unitPriceInput) setTimeout(() => unitPriceInput.focus(), DRAWER_ANIMATION_MS);
}

function openDeleteDrawer(id) {
    const recordIdInput = document.getElementById('deleteRecordId');
    if (recordIdInput) recordIdInput.value = id;
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
}

function openCopyDrawer() {
    const copyLocation = document.getElementById('copyLocation');
    const sourceYearSelect = document.getElementById('sourceYear');
    const targetYearInput = document.getElementById('targetYear');
    const form = document.getElementById('copyForm');

    if (form) form.reset();
    if (copyLocation) {
        copyLocation.value = weldingUnitPriceState.selectedLocation || DEFAULT_LOCATION;
    }
    if (sourceYearSelect && weldingUnitPriceState.years.length > 0) {
        sourceYearSelect.value = weldingUnitPriceState.years[0] || '';
    }
    if (targetYearInput) {
        targetYearInput.value = new Date().getFullYear() + 1;
    }

    openDrawer('copyDrawer', 'copyDrawerBackdrop');
}

async function exportExcel() {
    const btn = document.getElementById('btnExportWeldingUnitPrice');
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
                location: weldingUnitPriceState.selectedLocation || undefined,
                year: weldingUnitPriceState.selectedYear || undefined,
            },
            defaultFilename: '焊接单价导出.xlsx',
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
        console.error('导出焊接单价失败:', error);
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

async function batchDeleteByFilters() {
    if (typeof window.can === 'function' && !window.can('op:bom-welding-unit-price:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (weldingUnitPriceState.isBatchDeleting) return;

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
        `确定批量删除以下焊接单价吗？\n\n基地: ${location} | 年度: ${year}\n\n将删除该基地该年全部记录，此操作不可恢复！`
    );
    if (!confirmed) return;

    const btn = document.getElementById('btnBatchDeleteWeldingUnitPrice');
    const originalHtml = btn ? btn.innerHTML : '';
    weldingUnitPriceState.isBatchDeleting = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中..
        `;
    }

    try {
        const res = await HttpClient.post(`${API_BASE}/batch-delete`, { location, year });
        const data = res.data || {};
        showToast(
            res.message || data.message || `已删除 ${data.deleted_count ?? 0} 条`,
            'success'
        );
        weldingUnitPriceState.selectedLocation = location;
        weldingUnitPriceState.selectedYear = String(year);
        await loadData(1);
        await loadFilterOptions();
    } catch (error) {
        console.error('批量删除焊接单价失败:', error);
        if (!error.status) {
            showToast(error.message || '批量删除失败', 'error');
        }
    } finally {
        weldingUnitPriceState.isBatchDeleting = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

async function saveRecord() {
    const recordId = document.getElementById('editRecordId')?.value;
    const location = document.getElementById('editLocation')?.value?.trim();
    const year = parseInt(document.getElementById('editYear')?.value, 10);
    const itemName = document.getElementById('editItemName')?.value?.trim();
    const unit = document.getElementById('editUnit')?.value?.trim();
    const unitPrice = parseUnitPriceInput(document.getElementById('editUnitPrice')?.value);
    const remark = document.getElementById('editRemark')?.value?.trim() || null;

    if (!recordId && (!location || !year || !itemName || !unit || !unitPrice)) {
        showToast('请填写所有必填项（费用须为最多4位小数的数字）', 'warning');
        return;
    }
    if (recordId && (!unit || !unitPrice)) {
        showToast('请填写单位和费用（费用须为最多4位小数的数字）', 'warning');
        return;
    }

    try {
        if (recordId) {
            await HttpClient.put(`${API_BASE}/${recordId}`, {
                unit,
                unit_price: unitPrice,
                remark,
            });
            showToast('更新成功', 'success');
        } else {
            await HttpClient.post(API_BASE, {
                location,
                year,
                item_name: itemName,
                unit,
                unit_price: unitPrice,
                remark,
            });
            showToast('创建成功', 'success');
        }

        closeDrawer('editDrawer', 'editDrawerBackdrop');
        loadData(weldingUnitPriceState.page);
        loadFilterOptions();
    } catch (error) {
        console.error('保存失败:', error);
    }
}

async function deleteRecord(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');
        loadData(weldingUnitPriceState.page);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

async function copyTemplate() {
    const location = document.getElementById('copyLocation')?.value?.trim();
    const sourceYear = parseInt(document.getElementById('sourceYear')?.value, 10);
    const targetYear = parseInt(document.getElementById('targetYear')?.value, 10);

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
        showToast(`成功将「${location}」从 ${sourceYear} 年复制到 ${targetYear} 年`, 'success');
        closeDrawer('copyDrawer', 'copyDrawerBackdrop');
        loadData(1);
        loadFilterOptions();
    } catch (error) {
        console.error('复制失败:', error);
    }
}

export const pageConfig = {
    render: weldingUnitPriceTemplate,
    init: () => init(),
};
