/**
 * Steel Base Price Download Page
 * 基准价格导出页面逻辑
 */

import { basePriceDownloadTemplate } from './template.js?v=28';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    bindPageSizeSelect,
    renderPageButtons,
} from '../../../../page-size.js?v=2';

// 状态管理
const basePriceDownloadState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PREVIEW_PAGE_SIZE,
    totalPages: 1,
    filterLoadToken: 0,
};

// API 基础路径
const API_BASE = '/api/yishiyiyi/base-price';

/**
 * 页面初始化
 */
function init() {
    bindEvents();
    bindPageSizeSelect('basePricePageSize', {
        getSize: () => basePriceDownloadState.pageSize,
        setSize: (size) => {
            basePriceDownloadState.pageSize = size;
        },
        onChange: () => previewData(1),
        options: PREVIEW_PAGE_SIZE_OPTIONS,
        defaultSize: DEFAULT_PREVIEW_PAGE_SIZE,
    });
    // DOM 重建后必须重新拉选项；先同步填月份，避免接口返回前下拉空白
    fillMonthOptions();
    loadFilterOptions();
    applyPermissionUi();
}

function applyPermissionUi() {
    if (typeof can !== 'function') return;
    if (!can('op:base-price-download:export')) {
        document.getElementById('btnExportBasePrice')?.classList.add('hidden');
    }
    if (!can('op:base-price-download:delete')) {
        document.getElementById('btnDeleteBasePrice')?.classList.add('hidden');
    }
}

function buildYearOptions(years) {
    if (Array.isArray(years) && years.length) {
        return years.map(y => ({ value: y, label: `${y} 年` }));
    }
    const currentYear = new Date().getFullYear();
    const fallback = [];
    for (let y = currentYear - 3; y <= currentYear + 1; y++) {
        fallback.push({ value: y, label: `${y} 年` });
    }
    return fallback;
}

function fillMonthOptions() {
    const months = Array.from({ length: 12 }, (_, i) => ({
        value: i + 1,
        label: `${i + 1} 月`,
    }));
    fillSelect('basePriceDownloadMonth', months);
}

/**
 * 加载筛选下拉选项
 */
async function loadFilterOptions() {
    const token = ++basePriceDownloadState.filterLoadToken;
    try {
        const response = await HttpClient.get(`${API_BASE}/options`);
        if (token !== basePriceDownloadState.filterLoadToken) return;

        const data = response.data || {};
        fillSelect('basePriceDownloadYear', buildYearOptions(data.years));
        fillMonthOptions();
        fillSelect('basePriceDownloadLocation', data.locations || []);
        fillSelect('basePriceDownloadCategory', data.category_names || []);
        fillSelect('basePriceDownloadMill', data.steel_mills || []);
    } catch (error) {
        if (token !== basePriceDownloadState.filterLoadToken) return;
        console.error('加载筛选选项失败:', error);
        fillSelect('basePriceDownloadYear', buildYearOptions());
        fillMonthOptions();
    }
}

function fillSelect(id, options = []) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    select.innerHTML =
        '<option value="">全部</option>' +
        options.map(opt => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            return `<option value="${esc(value)}">${esc(label)}</option>`;
        }).join('');
    if (current && Array.from(select.options).some(opt => opt.value === current)) {
        select.value = current;
    }
}

/**
 * 绑定事件
 */
function bindEvents() {
    // 预览按钮
    const btnPreview = document.getElementById('btnPreviewBasePrice');
    if (btnPreview) {
        btnPreview.addEventListener('click', () => previewData(1));
    }

    // 导出按钮
    const btnExport = document.getElementById('btnExportBasePrice');
    if (btnExport) {
        btnExport.addEventListener('click', () => exportExcel());
    }

    // 删除按钮
    const btnDelete = document.getElementById('btnDeleteBasePrice');
    if (btnDelete) {
        btnDelete.addEventListener('click', () => batchDeleteBasePrices());
    }

    ['basePriceDownloadYear', 'basePriceDownloadMonth', 'basePriceDownloadLocation', 'basePriceDownloadCategory', 'basePriceDownloadMill']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => updateConditionsDisplay());
        });

    const gradeInput = document.getElementById('basePriceDownloadGrade');
    if (gradeInput) {
        gradeInput.addEventListener('input', () => updateConditionsDisplay());
        gradeInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                previewData(1);
            }
        });
    }

    document.getElementById('basePricePagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.base-price-page-btn');
        if (!btn || btn.disabled) return;
        const page = Number(btn.getAttribute('data-page'));
        if (Number.isFinite(page) && page >= 1) previewData(page);
    });
}

/**
 * 更新已选条件显示
 */
function updateConditionsDisplay() {
    const filters = collectFilters();
    const conditions = [];
    if (filters.year) conditions.push(`年度: ${filters.year}`);
    if (filters.month) conditions.push(`月份: ${filters.month}`);
    if (filters.location) conditions.push(`基地: ${filters.location}`);
    if (filters.category_name) conditions.push(`钢种: ${filters.category_name}`);
    if (filters.grade) conditions.push(`牌号: ${filters.grade}`);
    if (filters.steel_mill) conditions.push(`钢厂: ${filters.steel_mill}`);

    const display = document.getElementById('selectedBasePriceConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '请选择筛选条件';
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

function collectFilters() {
    return {
        year: getFilterValue('basePriceDownloadYear'),
        month: getFilterValue('basePriceDownloadMonth'),
        location: getFilterValue('basePriceDownloadLocation'),
        category_name: getFilterValue('basePriceDownloadCategory'),
        grade: document.getElementById('basePriceDownloadGrade')?.value.trim() || '',
        steel_mill: getFilterValue('basePriceDownloadMill'),
    };
}

function hasAnyFilter(filters) {
    return !!(filters.year || filters.month || filters.location || filters.category_name || filters.grade || filters.steel_mill);
}

function applyFiltersToParams(params, filters) {
    if (filters.year) params.year = parseInt(filters.year, 10);
    if (filters.month) params.month = parseInt(filters.month, 10);
    if (filters.location) params.location = filters.location;
    if (filters.category_name) params.category_name = filters.category_name;
    if (filters.grade) params.grade = filters.grade;
    if (filters.steel_mill) params.steel_mill = filters.steel_mill;
}

/**
 * 预览数据
 */
async function previewData(page = 1) {
    const filters = collectFilters();

    if (!hasAnyFilter(filters)) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    const tableBody = document.getElementById('basePricePreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
<td colspan="16" class="px-4 py-8 text-center">
                            <div class="flex items-center justify-center">
                                <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin mr-2"></div>
                                <span class="text-[11px] text-[#616161]">加载中...</span>
                            </div>
                        </td>
            </tr>
        `;
    }

    try {
        const params = {};
        applyFiltersToParams(params, filters);
        params.page = page;
        params.size = basePriceDownloadState.pageSize;
        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        // 支持分页响应格式 { items: [...], total: N } 或直接数组
        const payload = response.data;
        const records = Array.isArray(payload)
            ? payload
            : Array.isArray(payload?.items) ? payload.items : [];
        const total = payload?.total ?? records.length;
        basePriceDownloadState.page = payload?.page || page;
        basePriceDownloadState.records = records;
        basePriceDownloadState.total = total;
        basePriceDownloadState.totalPages =
            payload?.total_pages ||
            Math.max(1, Math.ceil(total / basePriceDownloadState.pageSize));

        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) {
            recordCount.textContent = total;
        }

        if (tableBody) {
            tableBody.innerHTML = renderBasePriceRows(records);
        }
        const pagination = document.getElementById('basePricePagination');
        if (pagination) {
            pagination.innerHTML = renderPageButtons(
                basePriceDownloadState.page,
                basePriceDownloadState.totalPages,
                'base-price-page-btn',
            );
        }
    } catch (error) {
        console.error('预览数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="16" class="px-4 py-8 text-center text-[#d32f2f] text-xs">
                        加载失败: ${esc(error.message || '未知错误')}
                    </td>
                </tr>
            `;
        }
        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) {
            recordCount.textContent = '0';
        }
        const pagination = document.getElementById('basePricePagination');
        if (pagination) pagination.innerHTML = '';
    }
}

/**
 * 导出 Excel
 */
async function exportExcel() {
    if (typeof can === 'function' && !can('op:base-price-download:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const filters = collectFilters();

    if (!hasAnyFilter(filters)) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    const loading = document.getElementById('basePriceDownloadLoading');
    if (loading) loading.classList.remove('hidden');

    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params: {
                year: filters.year ? parseInt(filters.year, 10) : undefined,
                month: filters.month ? parseInt(filters.month, 10) : undefined,
                location: filters.location,
                category_name: filters.category_name,
                grade: filters.grade,
                steel_mill: filters.steel_mill,
            },
            defaultFilename: '基准价格导出.xlsx',
        });

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast(`导出成功: ${filename}`, 'success');
    } catch (error) {
        console.error('导出 Excel 失败:', error);
        if (!error.status) {
            showToast(`导出失败: ${error.message}`, 'error');
        }
    } finally {
        if (loading) loading.classList.add('hidden');
    }
}

/**
 * 批量删除基准价格
 */
async function batchDeleteBasePrices() {
    if (typeof can === 'function' && !can('op:base-price-download:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const year = getFilterValue('basePriceDownloadYear');
    const month = getFilterValue('basePriceDownloadMonth');
    const location = getFilterValue('basePriceDownloadLocation');
    const mill = getFilterValue('basePriceDownloadMill');

    if (!year || !month) {
        showToast('年度、月份必须同时选择', 'warning');
        return;
    }

    const confirmed = window.confirm(
        `确定要删除以下条件的基准价格数据吗？\n\n年度: ${year} | 月份: ${month} | 基地: ${location || '全部'} | 钢厂: ${mill || '全部'}\n\n此操作不可恢复！`
    );

    if (!confirmed) {
        return;
    }

    const btnDelete = document.getElementById('btnDeleteBasePrice');
    const originalText = btnDelete ? btnDelete.innerHTML : '';
    if (btnDelete) {
        btnDelete.disabled = true;
        btnDelete.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中...
        `;
    }

    try {
        const body = {
            year: parseInt(year, 10),
            month: parseInt(month, 10),
        };
        if (location) body.location = location;
        if (mill) body.steel_mill = mill;
        await HttpClient.post(`${API_BASE}/batch-delete`, body);
        showToast('删除成功', 'success');

        basePriceDownloadState.records = [];
        basePriceDownloadState.total = 0;
        const tableBody = document.getElementById('basePricePreviewBody');
        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) recordCount.textContent = '0';
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="16" class="px-4 py-8 text-center">
                        <div class="flex items-center justify-center">
                            <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin mr-2"></div>
                            <span class="text-[11px] text-[#616161]">正在刷新...</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        await new Promise(resolve => setTimeout(resolve, 300));
        await refreshPreview();

    } catch (error) {
        console.error('删除基准价格失败:', error);
        showToast(`删除失败: ${error.message}`, 'error');
    } finally {
        if (btnDelete) {
            btnDelete.disabled = false;
            btnDelete.innerHTML = originalText;
        }
    }
}

/**
 * 刷新预览数据
 */
async function refreshPreview() {
    await previewData(1);
}

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: basePriceDownloadTemplate,
    init: () => init(),
};

// ===== 本地渲染辅助函数 =====

function renderBasePriceRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return `
            <tr>
                <td colspan="16" class="px-4 py-8 text-center text-[#616161] text-xs">
                    无数据
                </td>
            </tr>
        `;
    }
    return records.map((record, index) => `
        <tr class="group border-b border-[#181818] transition-colors duration-150 hover:bg-[#ffffff]/[0.015]">
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap font-mono text-right tabular-nums">${index + 1}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.year || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#606060] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.month || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.location || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.steel_mill || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap">${esc(record.category_name || '')}</td>
            <td class="px-3 py-2 text-[11px] font-medium text-[#a0a0a0] whitespace-nowrap">${esc(record.grade || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap">${esc(record.spec || '')}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono text-right tabular-nums">${formatDecimal(record.thick, 2)}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono text-right tabular-nums">${formatInteger(record.width)}</td>
            <td class="px-3 py-2 text-[11px] text-[#888888] whitespace-nowrap font-mono text-right tabular-nums">${formatDecimal(record.base_price, 2)}</td>
            <td class="px-3 py-2 text-[11px] text-[#686868] whitespace-nowrap font-mono text-right tabular-nums">${formatDecimal(record.processing_fee, 2)}</td>
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap truncate max-w-[200px]">${esc(record.excel_filename || '—')}</td>
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap">${esc(record.sheet_name || '—')}</td>
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_row ?? '—')}</td>
            <td class="px-3 py-2 text-[11px] text-[#505050] whitespace-nowrap font-mono text-right tabular-nums">${esc(record.excel_col ?? '—')}</td>
        </tr>`).join('');
}

function formatDecimal(value, digits = 2) {
    if (value === null || value === undefined) return '';
    const num = Number(value);
    if (Number.isNaN(num)) return '';
    return num.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

function formatInteger(value) {
    if (value === null || value === undefined) return '';
    const num = Number(value);
    if (Number.isNaN(num)) return '';
    return Math.round(num).toString();
}
