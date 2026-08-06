/**
 * Steel Base Price Download Page
 * 基准价格导出页面逻辑
 */

import { basePriceDownloadTemplate, renderBasePriceRows } from './template.js';

// 状态管理
const basePriceDownloadState = {
    records: [],
    total: 0,
    filtersLoaded: false,
};

// API 基础路径
const API_BASE = '/api/steel-base-prices';

/**
 * 页面初始化
 */
function init() {
    bindEvents();
    loadFilterOptions();
}

/**
 * 加载筛选下拉选项
 */
async function loadFilterOptions() {
    try {
        const response = await HttpClient.get(`${API_BASE}/options`);
        const data = response.data || {};

        // 填充年度选项
        if (data.years && Array.isArray(data.years)) {
            fillSelect('basePriceDownloadYear', data.years.map(y => ({
                value: y,
                label: `${y} 年`,
            })));
        } else {
            const currentYear = new Date().getFullYear();
            const years = [];
            for (let y = currentYear - 3; y <= currentYear + 1; y++) {
                years.push({ value: y, label: `${y} 年` });
            }
            fillSelect('basePriceDownloadYear', years);
        }

        // 填充月份
        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: `${i + 1} 月`,
        }));
        fillSelect('basePriceDownloadMonth', months);

        // 填充基地选项
        const locationDatalist = document.getElementById('basePriceLocationOptions');
        if (locationDatalist && data.locations && Array.isArray(data.locations)) {
            locationDatalist.innerHTML = data.locations
                .map(m => `<option value="${esc(m)}">`)
                .join('');
        }

        // 填充钢厂选项
        const millDatalist = document.getElementById('basePriceMillOptions');
        if (millDatalist && data.steel_mills && Array.isArray(data.steel_mills)) {
            millDatalist.innerHTML = data.steel_mills
                .map(m => `<option value="${esc(m)}">`)
                .join('');
        }

        basePriceDownloadState.filtersLoaded = true;
    } catch (error) {
        console.error('加载筛选选项失败:', error);
        const currentYear = new Date().getFullYear();
        const years = [];
        for (let y = currentYear - 3; y <= currentYear + 1; y++) {
            years.push({ value: y, label: `${y} 年` });
        }
        fillSelect('basePriceDownloadYear', years);

        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: `${i + 1} 月`,
        }));
        fillSelect('basePriceDownloadMonth', months);
    }
}

function fillSelect(id, options = []) {
    const select = document.getElementById(id);
    if (!select) return;
    select.innerHTML =
        '<option value="">全部</option>' +
        options.map(opt => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            return `<option value="${esc(value)}">${esc(label)}</option>`;
        }).join('');
}

/**
 * 绑定事件
 */
function bindEvents() {
    // 预览按钮
    const btnPreview = document.getElementById('btnPreviewBasePrice');
    if (btnPreview) {
        btnPreview.addEventListener('click', () => previewData());
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

    // 年度变更时更新条件显示
    const yearSelect = document.getElementById('basePriceDownloadYear');
    if (yearSelect) {
        yearSelect.addEventListener('change', () => updateConditionsDisplay());
    }

    // 月份变更时更新条件显示
    const monthSelect = document.getElementById('basePriceDownloadMonth');
    if (monthSelect) {
        monthSelect.addEventListener('change', () => updateConditionsDisplay());
    }

    // 基地变更时更新条件显示
    const locationInput = document.getElementById('basePriceDownloadLocation');
    if (locationInput) {
        locationInput.addEventListener('input', () => updateConditionsDisplay());
    }

    // 钢厂变更时更新条件显示
    const millInput = document.getElementById('basePriceDownloadMill');
    if (millInput) {
        millInput.addEventListener('input', () => updateConditionsDisplay());
    }
}

/**
 * 更新已选条件显示
 */
function updateConditionsDisplay() {
    const year = getFilterValue('basePriceDownloadYear');
    const month = getFilterValue('basePriceDownloadMonth');
    const location = getFilterValue('basePriceDownloadLocation');
    const mill = getFilterValue('basePriceDownloadMill');

    const conditions = [];
    if (year) conditions.push(`年度: ${year}`);
    if (month) conditions.push(`月份: ${month}`);
    if (location) conditions.push(`基地: ${location}`);
    if (mill) conditions.push(`钢厂: ${mill}`);

    const display = document.getElementById('selectedBasePriceConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '请选择筛选条件';
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

/**
 * 预览数据
 */
async function previewData() {
    const year = getFilterValue('basePriceDownloadYear');
    const month = getFilterValue('basePriceDownloadMonth');
    const location = getFilterValue('basePriceDownloadLocation');
    const mill = getFilterValue('basePriceDownloadMill');

    if (!year && !month && !location && !mill) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    const tableBody = document.getElementById('basePricePreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="12" class="px-4 py-8 text-center">
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
        if (year) params.year = parseInt(year, 10);
        if (month) params.month = parseInt(month, 10);
        if (location) params.location = location;
        if (mill) params.steel_mill = mill;
        params.page = 1;
        params.size = 1000;

        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const data = response.data || {};
        const records = Array.isArray(data.list) ? data.list : (Array.isArray(data.data) ? data.data : []);

        basePriceDownloadState.records = records;
        basePriceDownloadState.total = data.total || records.length;

        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) {
            recordCount.textContent = basePriceDownloadState.total;
        }

        if (tableBody) {
            tableBody.innerHTML = renderBasePriceRows(records);
        }
    } catch (error) {
        console.error('预览数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-4 py-8 text-center text-[#d32f2f] text-xs">
                        加载失败: ${esc(error.message || '未知错误')}
                    </td>
                </tr>
            `;
        }
        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) {
            recordCount.textContent = '0';
        }
    }
}

/**
 * 导出 Excel
 */
async function exportExcel() {
    const year = getFilterValue('basePriceDownloadYear');
    const month = getFilterValue('basePriceDownloadMonth');
    const location = getFilterValue('basePriceDownloadLocation');
    const mill = getFilterValue('basePriceDownloadMill');

    if (!year && !month && !location && !mill) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    const loading = document.getElementById('basePriceDownloadLoading');
    if (loading) loading.classList.remove('hidden');

    try {
        const params = new URLSearchParams();
        if (year) params.append('year', parseInt(year, 10));
        if (month) params.append('month', parseInt(month, 10));
        if (location) params.append('location', location);
        if (mill) params.append('steel_mill', mill);

        const response = await fetch(`${API_BASE}/export?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = '基准价格导出.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
                filename = decodeURIComponent(filename);
            }
        }

        const blob = await response.blob();
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
        showToast(`导出失败: ${error.message}`, 'error');
    } finally {
        if (loading) loading.classList.add('hidden');
    }
}

/**
 * 批量删除基准价格
 */
async function batchDeleteBasePrices() {
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
        const params = { 
            year: parseInt(year, 10), 
            month: parseInt(month, 10) 
        };
        if (location) params.location = location;
        if (mill) params.steel_mill = mill;
        const response = await HttpClient.delete(`${API_BASE}/batch`, { params });

        showToast(response.message || '删除成功', 'success');

        basePriceDownloadState.records = [];
        basePriceDownloadState.total = 0;
        const tableBody = document.getElementById('basePricePreviewBody');
        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) recordCount.textContent = '0';
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-4 py-8 text-center">
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
    const year = getFilterValue('basePriceDownloadYear');
    const month = getFilterValue('basePriceDownloadMonth');
    const location = getFilterValue('basePriceDownloadLocation');
    const mill = getFilterValue('basePriceDownloadMill');

    try {
        const params = {};
        if (year) params.year = parseInt(year, 10);
        if (month) params.month = parseInt(month, 10);
        if (location) params.location = location;
        if (mill) params.steel_mill = mill;
        params.page = 1;
        params.size = 1000;

        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const data = response.data || {};
        const records = Array.isArray(data.list) ? data.list : (Array.isArray(data.data) ? data.data : []);

        basePriceDownloadState.records = records;
        basePriceDownloadState.total = data.total || records.length;

        const recordCount = document.getElementById('basePriceRecordCount');
        if (recordCount) {
            recordCount.textContent = basePriceDownloadState.total;
        }

        const tableBody = document.getElementById('basePricePreviewBody');
        if (tableBody) {
            tableBody.innerHTML = renderBasePriceRows(records);
        }
    } catch (error) {
        console.error('刷新预览失败:', error);
        const tableBody = document.getElementById('basePricePreviewBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-4 py-8 text-center text-[#d32f2f] text-xs">
                        刷新失败: ${esc(error.message || '未知错误')}
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: basePriceDownloadTemplate,
    init: () => init(),
};
