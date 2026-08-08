/**
 * Steel Price Policy Download Page
 * 钢价政策下载页面逻辑
 * 用于测试部门核对数据，主子表联合查询导出 Excel
 */

import { policyDownloadTemplate, renderPolicyRows } from './template.js';

// 状态管理
const policyDownloadState = {
    records: [],
    total: 0,
    filtersLoaded: false,
};

// API 基础路径
const API_BASE = '/api/steel-price-policies';

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

        // 填充年度选项（从后端获取）
        if (data.years && Array.isArray(data.years)) {
            fillSelect('policyDownloadYear', data.years.map(y => ({
                value: y,
                label: `${y} 年`,
            })));
        } else {
            // Fallback: 当前年份前后3年
            const currentYear = new Date().getFullYear();
            const years = [];
            for (let y = currentYear - 3; y <= currentYear + 1; y++) {
                years.push({ value: y, label: `${y} 年` });
            }
            fillSelect('policyDownloadYear', years);
        }

        // 填充月份
        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: `${i + 1} 月`,
        }));
        fillSelect('policyDownloadMonth', months);

        // 填充钢厂选项（使用 datalist 实现输入搜索）
        const datalist = document.getElementById('steelMillOptions');
        if (datalist && data.steel_mills && Array.isArray(data.steel_mills)) {
            datalist.innerHTML = data.steel_mills
                .map(m => `<option value="${esc(m)}">`)
                .join('');
        }

        policyDownloadState.filtersLoaded = true;
    } catch (error) {
        console.error('加载筛选选项失败:', error);
        // Fallback: 当前年份前后3年
        const currentYear = new Date().getFullYear();
        const years = [];
        for (let y = currentYear - 3; y <= currentYear + 1; y++) {
            years.push({ value: y, label: `${y} 年` });
        }
        fillSelect('policyDownloadYear', years);

        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: `${i + 1} 月`,
        }));
        fillSelect('policyDownloadMonth', months);
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
    const btnPreview = document.getElementById('btnPreview');
    if (btnPreview) {
        btnPreview.addEventListener('click', () => previewData());
    }

    // 导出按钮
    const btnExport = document.getElementById('btnExport');
    if (btnExport) {
        btnExport.addEventListener('click', () => exportExcel());
    }

    // 查找实际绑定的导出按钮
    const btnExportPolicy = document.getElementById('btnExportPolicy');
    if (btnExportPolicy) {
        btnExportPolicy.addEventListener('click', () => exportExcel());
    }

    // 删除按钮
    const btnDelete = document.getElementById('btnDeletePolicy');
    if (btnDelete) {
        btnDelete.addEventListener('click', () => batchDeletePolicies());
    }

    // 年度变更时更新月份选项
    const yearSelect = document.getElementById('policyDownloadYear');
    if (yearSelect) {
        yearSelect.addEventListener('change', () => updateConditionsDisplay());
    }

    // 月份变更时更新条件显示
    const monthSelect = document.getElementById('policyDownloadMonth');
    if (monthSelect) {
        monthSelect.addEventListener('change', () => updateConditionsDisplay());
    }

    // 钢厂变更时更新条件显示（支持输入搜索）
    const millSelect = document.getElementById('policyDownloadMill');
    if (millSelect) {
        millSelect.addEventListener('input', () => updateConditionsDisplay());
    }
}

/**
 * 更新已选条件显示
 */
function updateConditionsDisplay() {
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const mill = getFilterValue('policyDownloadMill');

    const conditions = [];
    if (year) conditions.push(`年度: ${year}`);
    if (month) conditions.push(`月份: ${month}`);
    if (mill) conditions.push(`钢厂: ${mill}`);

    const display = document.getElementById('selectedConditions');
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
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getFilterValue('policyDownloadMill');

    if (!year && !month && !steelMill) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    const tableBody = document.getElementById('policyPreviewBody');
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
        if (year) params.year = year;
        if (month) params.month = month;
        if (steelMill) params.steel_mill = steelMill;
        // 预览时不分页，获取较多数据
        params.page = 1;
        params.size = 1000;

        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const data = response.data || {};
        const records = Array.isArray(data.list) ? data.list : [];

        policyDownloadState.records = records;
        policyDownloadState.total = data.total || records.length;

        // 更新记录数
        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = policyDownloadState.total;
        }

        // 渲染预览表格
        if (tableBody) {
            tableBody.innerHTML = renderPolicyRows(records);
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
        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = '0';
        }
    }
}

/**
 * 导出 Excel
 */
async function exportExcel() {
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getFilterValue('policyDownloadMill');

    if (!year && !month && !steelMill) {
        showToast('请至少选择一个筛选条件', 'warning');
        return;
    }

    // 显示加载遮罩
    const loading = document.getElementById('downloadLoading');
    if (loading) loading.classList.remove('hidden');

    try {
        // 构建查询参数
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (month) params.append('month', month);
        if (steelMill) params.append('steel_mill', steelMill);

        // 使用 fetch 下载文件
        const response = await fetch(`${API_BASE}/export?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // 获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = '厚度加减价导出.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
                // 解码中文文件名
                filename = decodeURIComponent(filename);
            }
        }

        // 下载文件
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
        // 隐藏加载遮罩
        if (loading) loading.classList.add('hidden');
    }
}

/**
 * 批量删除政策
 */
async function batchDeletePolicies() {
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getFilterValue('policyDownloadMill');

    // 年度+月份+钢厂必须同时选择
    if (!year || !month || !steelMill) {
        showToast('年度、月份、钢厂必须同时选择', 'warning');
        return;
    }

    const confirmed = window.confirm(
        `确定要删除以下条件的政策数据吗？\n\n年度: ${year} | 月份: ${month} | 钢厂: ${steelMill}\n\n此操作不可恢复！`
    );

    if (!confirmed) {
        return;
    }

    // 显示删除中的加载状态
    const btnDelete = document.getElementById('btnDeletePolicy');
    const originalText = btnDelete ? btnDelete.innerHTML : '';
    if (btnDelete) {
        btnDelete.disabled = true;
        btnDelete.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            删除中...
        `;
    }

    try {
        const params = { year, month, steel_mill: steelMill };
        const response = await HttpClient.delete(`${API_BASE}/batch`, { params });

        // 先显示成功提示
        showToast(response.message || '删除成功', 'success');

        // 清空当前预览数据，立即给用户视觉反馈
        policyDownloadState.records = [];
        policyDownloadState.total = 0;
        const tableBody = document.getElementById('policyPreviewBody');
        const recordCount = document.getElementById('recordCount');
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

        // 短暂延迟后重新加载预览，确保用户看到刷新过程
        await new Promise(resolve => setTimeout(resolve, 300));

        // 重新获取预览数据
        await refreshPreview();

    } catch (error) {
        console.error('删除政策失败:', error);
        showToast(`删除失败: ${error.message}`, 'error');
    } finally {
        // 恢复按钮状态
        if (btnDelete) {
            btnDelete.disabled = false;
            btnDelete.innerHTML = originalText;
        }
    }
}

/**
 * 刷新预览数据（供删除成功后调用）
 */
async function refreshPreview() {
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getFilterValue('policyDownloadMill');

    try {
        const params = {};
        if (year) params.year = year;
        if (month) params.month = month;
        if (steelMill) params.steel_mill = steelMill;
        params.page = 1;
        params.size = 1000;

        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const data = response.data || {};
        const records = Array.isArray(data.list) ? data.list : [];

        policyDownloadState.records = records;
        policyDownloadState.total = data.total || records.length;

        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = policyDownloadState.total;
        }

        const tableBody = document.getElementById('policyPreviewBody');
        if (tableBody) {
            tableBody.innerHTML = renderPolicyRows(records);
        }
    } catch (error) {
        console.error('刷新预览失败:', error);
        const tableBody = document.getElementById('policyPreviewBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="16" class="px-4 py-8 text-center text-[#d32f2f] text-xs">
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
    render: policyDownloadTemplate,
    init: () => init(),
};
