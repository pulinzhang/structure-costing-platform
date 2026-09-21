/**
 * 中标钢厂厚度价格一览表 — 页面逻辑
 *
 * 预览为扁平行：每个牌号 × 各厚度阶梯一行；前端按牌号合并展示。
 */

import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=5';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=3';
import {
    winningThicknessDownloadTemplate,
    renderWinningThicknessRows,
} from './template.js?v=23';
import {
    requireExportYearMonth,
    selectDefaultYear,
} from '../../../common/period-ui.js?v=6';

const winningThicknessState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PREVIEW_PAGE_SIZE,
    filterLoadToken: 0,
    isLoading: false,
};

const API_BASE = '/api/yishiyiyi/winning-thickness';
const GRADE_CATEGORY_API = '/api/masterdata/steel-grade-category';

function init() {
    bindEvents();
    bindPagination({
        selectId: 'winningThicknessPageSize',
        buttonsId: 'winningThicknessPagination',
        getSize: () => winningThicknessState.pageSize,
        setSize: (size) => {
            winningThicknessState.pageSize = size;
        },
        onPage: (page) => {
            winningThicknessState.page = page;
            previewData();
        },
        options: PREVIEW_PAGE_SIZE_OPTIONS,
        defaultSize: DEFAULT_PREVIEW_PAGE_SIZE,
    });
    fillMonthOptions();
    loadFilterOptions().then(() => {
        updateConditionsDisplay();
        previewData();
    });
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
        return years.map(y => ({ value: y, label: fmtYear(y) }));
    }
    const currentYear = new Date().getFullYear();
    const fallback = [];
    for (let y = currentYear - 3; y <= currentYear + 1; y++) {
        fallback.push({ value: y, label: fmtYear(y) });
    }
    return fallback;
}

function fillMonthOptions() {
    const months = Array.from({ length: 12 }, (_, i) => ({
        value: i + 1,
        label: fmtMonth(i + 1),
    }));
    fillSelect('winningThicknessMonth', months, false);
}

async function loadFilterOptions() {
    const token = ++winningThicknessState.filterLoadToken;
    try {
        const [optionsRes, categoryRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/options`),
            HttpClient.get(`${GRADE_CATEGORY_API}/categories`),
        ]);
        if (token !== winningThicknessState.filterLoadToken) return;

        const data = optionsRes.data || {};
        const categories = Array.isArray(categoryRes.data) ? categoryRes.data : [];

        fillSelect('winningThicknessYear', buildYearOptions(data.years), false);
        selectDefaultYear('winningThicknessYear');
        fillMonthOptions();
        fillSelect('winningThicknessLocation', data.locations || [], false);
        fillSelect(
            'winningThicknessCategory',
            categories.map((item) => ({
                value: item.category_name,
                label: item.category_name,
            })),
            false,
        );
        fillSelect('winningThicknessMill', data.steel_mills || [], false);
    } catch (error) {
        if (token !== winningThicknessState.filterLoadToken) return;
        console.error('加载筛选选项失败:', error);
        fillSelect('winningThicknessYear', buildYearOptions(), false);
        selectDefaultYear('winningThicknessYear');
        fillMonthOptions();
    }
}

async function loadGradesForCategory(categoryName) {
    const datalist = document.getElementById('winningThicknessGradeOptions');
    const gradeInput = document.getElementById('winningThicknessGrade');
    if (!datalist) return;

    const category = (categoryName || '').trim();
    if (!category) {
        datalist.innerHTML = '';
        if (gradeInput) {
            gradeInput.value = '';
            gradeInput.placeholder = '请先选择分类';
            gradeInput.disabled = true;
        }
        return;
    }

    if (gradeInput) {
        gradeInput.disabled = false;
        gradeInput.placeholder = '输入搜索或选择牌号';
    }

    try {
        const response = await HttpClient.get(`${GRADE_CATEGORY_API}/grades`, {
            params: { category_name: category },
        });
        const grades = Array.isArray(response.data) ? response.data : [];
        datalist.innerHTML = grades.map((g) => `<option value="${esc(g)}">`).join('');
    } catch (error) {
        console.error('加载牌号列表失败:', error);
        datalist.innerHTML = '';
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
    document.getElementById('btnPreviewWinningThickness')?.addEventListener('click', () => {
        winningThicknessState.page = 1;
        previewData();
    });
    document.getElementById('btnExportWinningThickness')?.addEventListener('click', () => exportExcel());


    [
        'winningThicknessYear',
        'winningThicknessMonth',
        'winningThicknessLocation',
        'winningThicknessMill',
    ].forEach(id => {
        document.getElementById(id)?.addEventListener('change', () => queryAfterFilterSelect());
    });

    const categorySelect = document.getElementById('winningThicknessCategory');
    if (categorySelect) {
        categorySelect.addEventListener('change', () => {
            const gradeInput = document.getElementById('winningThicknessGrade');
            if (gradeInput) gradeInput.value = '';
            loadGradesForCategory(categorySelect.value);
            queryAfterFilterSelect();
        });
    }

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

function queryAfterFilterSelect() {
    updateConditionsDisplay();
    winningThicknessState.page = 1;
    previewData();
}

function updateConditionsDisplay() {
    const filters = collectFilters();
    const conditions = [];
    const period = fmtPeriod(filters.year, filters.month);
    if (period) conditions.push(period);
    if (filters.location) conditions.push(`基地: ${filters.location}`);
    if (filters.steel_mill) conditions.push(`钢厂: ${filters.steel_mill}`);
    if (filters.category_name) conditions.push(`分类: ${filters.category_name}`);
    if (filters.grade) conditions.push(`牌号: ${filters.grade}`);

    const display = document.getElementById('selectedWinningThicknessConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '全部';
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
        steel_mill: getFilterValue('winningThicknessMill'),
        category_name: getFilterValue('winningThicknessCategory'),
        grade: document.getElementById('winningThicknessGrade')?.value.trim() || '',
    };
}

/**
 * 组装一览表查询参数。
 * category_name / grade 传给后端，用于筛选牌号分类档案行（再与基价、大类政策组合）。
 */
function applyFiltersToParams(params, filters) {
    if (filters.year) params.year = parseInt(filters.year, 10);
    if (filters.month) params.month = parseInt(filters.month, 10);
    if (filters.location) params.location = filters.location;
    if (filters.steel_mill) params.steel_mill = filters.steel_mill;
    if (filters.category_name) params.category_name = filters.category_name;
    if (filters.grade) params.grade = filters.grade;
}

async function previewData() {
    if (winningThicknessState.isLoading) return;
    winningThicknessState.isLoading = true;
    setSearchBusy('btnPreviewWinningThickness', true);

    const filters = collectFilters();
    const tableBody = document.getElementById('winningThicknessPreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="px-4 py-8 text-center">
                    <div class="flex items-center justify-center">
                        <div class="w-4 h-4 border border-line border-brand rounded-full animate-spin mr-2"></div>
                        <span class="text-[11px] text-ink-dim">加载中...</span>
                    </div>
                </td>
            </tr>
        `;
    }

    try {
        const params = {};
        applyFiltersToParams(params, filters);
        params.page = winningThicknessState.page;
        params.size = winningThicknessState.pageSize;
        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const payload = response.data;
        const records = Array.isArray(payload?.items) ? payload.items : [];
        const total = payload?.total ?? records.length;
        const pageSize = payload?.page_size ?? winningThicknessState.pageSize;
        const page = payload?.page ?? winningThicknessState.page;
        winningThicknessState.records = records;
        winningThicknessState.total = total;
        winningThicknessState.page = page;
        winningThicknessState.pageSize = pageSize;

        const recordCount = document.getElementById('winningThicknessRecordCount');
        if (recordCount) recordCount.textContent = total;

        if (tableBody) {
            tableBody.innerHTML = records.length
                ? renderWinningThicknessRows(records)
                : `
                <tr>
                    <td colspan="10" class="px-4 py-8 text-center text-ink-dim text-xs">
                        当前筛选下暂无数据
                    </td>
                </tr>
            `;
        }

        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        paintPagination('winningThicknessPagination', page, totalPages);

        updateConditionsDisplay();
    } catch (error) {
        console.error('查询失败:', error);
        showToast(error.message || '查询失败', 'error');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="px-4 py-8 text-center text-danger text-xs">加载失败</td>
                </tr>
            `;
        }
    } finally {
        winningThicknessState.isLoading = false;
        setSearchBusy('btnPreviewWinningThickness', false);
    }
}

async function exportExcel() {
    if (typeof can === 'function' && !can('op:winning-thickness-download:export')) {
        showToast('无导出权限', 'warning');
        return;
    }

    const filters = collectFilters();
    if (!requireExportYearMonth(filters)) return;

    const loading = document.getElementById('winningThicknessDownloadLoading');
    loading?.classList.remove('hidden');

    try {
        const params = {};
        applyFiltersToParams(params, filters);
        const period = fmtPeriod(filters.year, filters.month);
        const defaultName = [
            '中标钢厂厚度价格一览表',
            period,
            filters.location,
        ].filter(Boolean).join('_') + '.xlsx';
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params,
            defaultFilename: defaultName,
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
