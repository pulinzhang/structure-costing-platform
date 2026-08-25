/**
 * 中标钢厂厚度价格一览表 — 页面逻辑
 */

import {
    winningThicknessDownloadTemplate,
    renderWinningThicknessRows,
} from './template.js?v=8';

const winningThicknessState = {
    records: [],
    total: 0,
    filterLoadToken: 0,
};

const API_BASE = '/api/yishiyiyi/winning-thickness';

function init() {
    bindEvents();
    fillMonthOptions();
    loadFilterOptions();
    applyPermissionUi();
}

function applyPermissionUi() {
    if (typeof can !== 'function') return;
    if (!can('op:winning-thickness-download:export')) {
        document.getElementById('btnExportWinningThickness')?.classList.add('hidden');
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
    fillSelect('winningThicknessMonth', months, true);
}

async function loadFilterOptions() {
    const token = ++winningThicknessState.filterLoadToken;
    try {
        const response = await HttpClient.get(`${API_BASE}/options`);
        if (token !== winningThicknessState.filterLoadToken) return;

        const data = response.data || {};
        fillSelect('winningThicknessYear', buildYearOptions(data.years), true);
        fillMonthOptions();
        fillSelect('winningThicknessLocation', data.locations || [], true);
        fillSelect('winningThicknessCategory', data.category_names || [], false);
        fillSelect('winningThicknessMill', data.steel_mills || [], false);
    } catch (error) {
        if (token !== winningThicknessState.filterLoadToken) return;
        console.error('加载筛选选项失败:', error);
        fillSelect('winningThicknessYear', buildYearOptions(), true);
        fillMonthOptions();
    }
}

function fillSelect(id, options = [], required = false) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    const placeholder = required ? '请选择' : '全部';
    select.innerHTML =
        `<option value="">${placeholder}</option>` +
        options.map(opt => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            return `<option value="${esc(value)}">${esc(label)}</option>`;
        }).join('');
    if (current && Array.from(select.options).some(opt => opt.value === current)) {
        select.value = current;
    }
}

function bindEvents() {
    document.getElementById('btnPreviewWinningThickness')?.addEventListener('click', () => previewData());
    document.getElementById('btnExportWinningThickness')?.addEventListener('click', () => exportExcel());

    [
        'winningThicknessYear',
        'winningThicknessMonth',
        'winningThicknessLocation',
        'winningThicknessCategory',
        'winningThicknessMill',
    ].forEach(id => {
        document.getElementById(id)?.addEventListener('change', () => updateConditionsDisplay());
    });

    const gradeInput = document.getElementById('winningThicknessGrade');
    if (gradeInput) {
        gradeInput.addEventListener('input', () => updateConditionsDisplay());
        gradeInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                previewData();
            }
        });
    }
}

function updateConditionsDisplay() {
    const filters = collectFilters();
    const conditions = [];
    if (filters.year) conditions.push(`年度: ${filters.year}`);
    if (filters.month) conditions.push(`月份: ${filters.month}`);
    if (filters.location) conditions.push(`基地: ${filters.location}`);
    if (filters.category_name) conditions.push(`钢种: ${filters.category_name}`);
    if (filters.grade) conditions.push(`牌号: ${filters.grade}`);
    if (filters.steel_mill) conditions.push(`钢厂: ${filters.steel_mill}`);

    const display = document.getElementById('selectedWinningThicknessConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '请选择基地、年度、月份';
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

function collectFilters() {
    return {
        year: getFilterValue('winningThicknessYear'),
        month: getFilterValue('winningThicknessMonth'),
        location: getFilterValue('winningThicknessLocation'),
        category_name: getFilterValue('winningThicknessCategory'),
        grade: document.getElementById('winningThicknessGrade')?.value.trim() || '',
        steel_mill: getFilterValue('winningThicknessMill'),
    };
}

function requireCoreFilters(filters) {
    if (!filters.year || !filters.month || !filters.location) {
        showToast('请先选择基地、年度、月份', 'warning');
        return false;
    }
    return true;
}

function applyFiltersToParams(params, filters) {
    params.year = parseInt(filters.year, 10);
    params.month = parseInt(filters.month, 10);
    params.location = filters.location;
    if (filters.category_name) params.category_name = filters.category_name;
    if (filters.grade) params.grade = filters.grade;
    if (filters.steel_mill) params.steel_mill = filters.steel_mill;
}

async function previewData() {
    const filters = collectFilters();
    if (!requireCoreFilters(filters)) return;

    const tableBody = document.getElementById('winningThicknessPreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="px-4 py-8 text-center">
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
        params.page = 1;
        params.size = 500;
        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const payload = response.data;
        const records = Array.isArray(payload?.items) ? payload.items : [];
        const total = payload?.total ?? records.length;
        winningThicknessState.records = records;
        winningThicknessState.total = total;

        const recordCount = document.getElementById('winningThicknessRecordCount');
        if (recordCount) recordCount.textContent = total;

        if (tableBody) {
            tableBody.innerHTML = renderWinningThicknessRows(records);
        }
        updateConditionsDisplay();
    } catch (error) {
        console.error('查询失败:', error);
        showToast(error.message || '查询失败', 'error');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="px-4 py-8 text-center text-[#ef5350] text-xs">加载失败</td>
                </tr>
            `;
        }
    }
}

async function exportExcel() {
    if (typeof can === 'function' && !can('op:winning-thickness-download:export')) {
        showToast('无导出权限', 'warning');
        return;
    }

    const filters = collectFilters();
    if (!requireCoreFilters(filters)) return;

    const loading = document.getElementById('winningThicknessDownloadLoading');
    loading?.classList.remove('hidden');

    try {
        const params = {};
        applyFiltersToParams(params, filters);
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params,
            defaultFilename: `中标钢厂厚度价格一览表_${filters.year}年_${filters.month}月_${filters.location}.xlsx`,
        });

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    } catch (error) {
        console.error('导出失败:', error);
        showToast(error.message || '导出失败', 'error');
    } finally {
        loading?.classList.add('hidden');
    }
}

export const pageConfig = {
    render: winningThicknessDownloadTemplate,
    init: () => init(),
};
