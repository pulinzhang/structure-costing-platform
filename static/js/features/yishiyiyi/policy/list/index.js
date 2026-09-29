/**
 * Steel Price Policy Download Page
 * 钢价政策下载页面逻辑
 * 用于测试部门核对数据，主子表联合查询导出 Excel
 */

import { policyDownloadTemplate, renderPolicyRows } from './template.js?v=53';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=6';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';
import {
    requireExportYearMonth,
    selectDefaultYear,
} from '../../../common/period-ui.js?v=7';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;

// 状态管理
const policyDownloadState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PREVIEW_PAGE_SIZE,
    totalPages: 1,
    filtersLoaded: false,
    pendingFilters: null,
    pendingSheetApplied: false,
    sheetRequestId: 0,
    isLoading: false,
};

// API 基础路径
const API_BASE = '/api/yishiyiyi/policy';
const GRADE_CATEGORY_API = '/api/masterdata/steel-grade-category';

/**
 * 页面初始化
 */
function init() {
    bindEvents();
    bindPagination({
        selectId: 'policyPageSize',
        buttonsId: 'policyPagination',
        getSize: () => policyDownloadState.pageSize,
        setSize: (size) => {
            policyDownloadState.pageSize = size;
        },
        onPage: (page) => previewData(page),
        options: PREVIEW_PAGE_SIZE_OPTIONS,
        defaultSize: DEFAULT_PREVIEW_PAGE_SIZE,
    });
    policyDownloadState.pendingFilters = readHashFilters();
    loadFilterOptions().then(async () => {
        applyPendingFiltersToSelects();
        const pendingCategory = policyDownloadState.pendingFilters?.category_name;
        if (pendingCategory) {
            await loadGradesForCategory(pendingCategory);
        }
        await loadSheetNames();
        updateConditionsDisplay();
        previewData(1);
    });
    applyPermissionUi();
}

function readHashFilters() {
    const hash = window.location.hash || '';
    const qIndex = hash.indexOf('?');
    if (qIndex < 0) return null;
    const params = new URLSearchParams(hash.slice(qIndex + 1));
    const year = params.get('year') || '';
    const month = params.get('month') || '';
    const category_name = params.get('category_name') || '';
    const steel_mill = params.get('steel_mill') || '';
    const sheet_name = params.get('sheet_name') || '';
    const grade_value = params.get('grade_value') || '';
    if (!year && !month && !category_name && !steel_mill && !sheet_name && !grade_value) return null;
    return { year, month, category_name, steel_mill, sheet_name, grade_value };
}

function setSelectValue(id, value) {
    const select = document.getElementById(id);
    if (!select || value == null || value === '') return;
    const text = String(value);
    if (![...select.options].some((opt) => opt.value === text)) {
        select.insertAdjacentHTML(
            'beforeend',
            `<option value="${esc(text)}">${esc(text)}</option>`,
        );
    }
    select.value = text;
}

function applyPendingFiltersToSelects() {
    const pending = policyDownloadState.pendingFilters;
    if (!pending) return;
    setSelectValue('policyDownloadYear', pending.year);
    setSelectValue('policyDownloadMonth', pending.month);
    setSelectValue('policyDownloadCategory', pending.category_name);
    const millInput = document.getElementById('policyDownloadMill');
    if (millInput && pending.steel_mill) {
        millInput.value = pending.steel_mill;
    }
    const gradeInput = document.getElementById('policyDownloadGrade');
    if (gradeInput && pending.grade_value) {
        gradeInput.value = pending.grade_value;
    }
}

function applyPermissionUi() {
    if (typeof can !== 'function') return;
    if (!can('op:steel-price-policy-download:export')) {
        document.getElementById('btnExportPolicy')?.classList.add('hidden');
    }
    if (!can('op:steel-price-policy-download:delete')) {
        document.getElementById('btnDeletePolicy')?.classList.add('hidden');
        document.getElementById('policyMoreWrap')?.classList.add('hidden');
    }
}

/**
 * 加载筛选下拉选项（年度/钢厂来自政策；分类/牌号来自牌号分类档案）
 */
async function loadFilterOptions() {
    try {
        const [policyRes, categoryRes] = await Promise.all([
            HttpClient.get(`${API_BASE}/options`),
            HttpClient.get(`${GRADE_CATEGORY_API}/categories`),
        ]);
        const data = policyRes.data || {};
        const categories = Array.isArray(categoryRes.data) ? categoryRes.data : [];

        // 填充年度选项（从后端获取）
        if (data.years && Array.isArray(data.years)) {
            fillSelect('policyDownloadYear', data.years.map(y => ({
                value: y,
                label: fmtYear(y),
            })));
        } else {
            // Fallback: 当前年份前后3年
            const currentYear = new Date().getFullYear();
            const years = [];
            for (let y = currentYear - 3; y <= currentYear + 1; y++) {
                years.push({ value: y, label: fmtYear(y) });
            }
            fillSelect('policyDownloadYear', years);
        }
        if (!policyDownloadState.pendingFilters?.year) {
            selectDefaultYear('policyDownloadYear');
        }

        // 填充月份
        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: fmtMonth(i + 1),
        }));
        fillSelect('policyDownloadMonth', months);

        // 分类：档案 canonical（冷轧/镀锌/酸洗）
        fillSelect(
            'policyDownloadCategory',
            categories.map((item) => ({
                value: item.category_name,
                label: item.category_name,
            })),
        );

        fillDatalist('policyMillOptions', data.steel_mills || []);

        policyDownloadState.filtersLoaded = true;
    } catch (error) {
        console.error('加载筛选选项失败:', error);
        // Fallback: 当前年份前后3年
        const currentYear = new Date().getFullYear();
        const years = [];
        for (let y = currentYear - 3; y <= currentYear + 1; y++) {
                years.push({ value: y, label: fmtYear(y) });
        }
        fillSelect('policyDownloadYear', years);
        if (!policyDownloadState.pendingFilters?.year) {
            selectDefaultYear('policyDownloadYear');
        }

        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: fmtMonth(i + 1),
        }));
        fillSelect('policyDownloadMonth', months);
    }
}

async function loadGradesForCategory(categoryName) {
    const gradeInput = document.getElementById('policyDownloadGrade');
    const category = (categoryName || '').trim();
    if (!category) {
        fillDatalist('policyGradeOptions', []);
        if (gradeInput) {
            gradeInput.value = '';
            gradeInput.placeholder = '请先选择钢种大类';
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
        fillDatalist(
            'policyGradeOptions',
            Array.isArray(response.data) ? response.data : [],
        );
    } catch (error) {
        console.error('加载牌号列表失败:', error);
        fillDatalist('policyGradeOptions', []);
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

function fillDatalist(id, values = []) {
    const datalist = document.getElementById(id);
    if (!datalist) return;
    datalist.innerHTML = values
        .map((value) => `<option value="${esc(value)}">`)
        .join('');
}

/**
 * 绑定事件
 */
function bindEvents() {
    // 预览按钮
    const btnPreview = document.getElementById('btnPreview');
    if (btnPreview) {
        btnPreview.addEventListener('click', () => previewData(1));
    }

    // 导出按钮
    const btnExportPolicy = document.getElementById('btnExportPolicy');
    if (btnExportPolicy) {
        btnExportPolicy.addEventListener('click', () => exportExcel());
    }

    // 删除按钮（⋯ 菜单）
    const btnDelete = document.getElementById('btnDeletePolicy');
    if (btnDelete) {
        btnDelete.addEventListener('click', () => {
            moreMenu?.close();
            batchDeletePolicies();
        });
    }
    moreMenu = bindMoreMenu({
        wrapId: 'policyMoreWrap',
        btnId: 'policyMoreBtn',
        menuId: 'policyMoreMenu',
    });

    ['policyDownloadYear', 'policyDownloadMonth'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => reloadSheetsThenQuery());
    });

    const sheetSelect = document.getElementById('policyDownloadSheet');
    if (sheetSelect) {
        sheetSelect.addEventListener('change', () => queryAfterFilterSelect());
    }

    const categorySelect = document.getElementById('policyDownloadCategory');
    if (categorySelect) {
        categorySelect.addEventListener('change', () => {
            const gradeInput = document.getElementById('policyDownloadGrade');
            if (gradeInput) gradeInput.value = '';
            loadGradesForCategory(categorySelect.value);
            queryAfterFilterSelect();
        });
    }

    bindDatalistFilterInput('policyDownloadMill', {
        onChange: () => reloadSheetsThenQuery(),
        onEnter: () => reloadSheetsThenQuery(),
    });
    bindDatalistFilterInput('policyDownloadGrade');
}

/**
 * datalist 输入框：输入时刷新已选条件；回车查询；选中建议项后按 onChange 触发。
 */
function bindDatalistFilterInput(id, { onChange, onEnter } = {}) {
    const input = document.getElementById(id);
    if (!input) return;
    input.addEventListener('input', () => updateConditionsDisplay());
    input.addEventListener('change', () => {
        updateConditionsDisplay();
        if (typeof onChange === 'function') onChange();
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            if (typeof onEnter === 'function') onEnter();
            else previewData(1);
        }
    });
}

function queryAfterFilterSelect() {
    updateConditionsDisplay();
    previewData(1);
}

async function reloadSheetsThenQuery() {
    await loadSheetNames();
    queryAfterFilterSelect();
}

/**
 * 表页选项只看它前面的年度、月份、钢厂，按表页名去重。
 */
async function loadSheetNames() {
    const requestId = ++policyDownloadState.sheetRequestId;
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getTrimmedFilterValue('policyDownloadMill');
    const current = getFilterValue('policyDownloadSheet');
    const params = {};
    if (year) params.year = year;
    if (month) params.month = month;
    if (steelMill) params.steel_mill = steelMill;

    try {
        const response = await HttpClient.get(`${API_BASE}/sheet-names`, { params });
        if (requestId !== policyDownloadState.sheetRequestId) return;
        const names = Array.isArray(response.data) ? response.data : [];
        fillSelect(
            'policyDownloadSheet',
            names.map((name) => ({ value: name, label: name })),
        );
        const preferred = current || pendingSheetName();
        if (preferred && names.includes(preferred)) {
            const select = document.getElementById('policyDownloadSheet');
            if (select) select.value = preferred;
        }
    } catch (error) {
        console.error('加载表页失败:', error);
    }
}

function pendingSheetName() {
    if (policyDownloadState.pendingSheetApplied) return '';
    policyDownloadState.pendingSheetApplied = true;
    return policyDownloadState.pendingFilters?.sheet_name || '';
}

/**
 * 更新已选条件显示
 */
function updateConditionsDisplay() {
    const filters = collectFilters();
    const conditions = [];
    const period = fmtPeriod(filters.year, filters.month);
    if (period) conditions.push(period);
    if (filters.steel_mill) conditions.push(`钢厂: ${filters.steel_mill}`);
    if (filters.sheet_name) conditions.push(`表页: ${filters.sheet_name}`);
    if (filters.category_name) conditions.push(`钢种大类: ${filters.category_name}`);
    if (filters.grade_value) conditions.push(`牌号: ${filters.grade_value}`);

    const display = document.getElementById('selectedConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '全部';
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

function getTrimmedFilterValue(id) {
    return document.getElementById(id)?.value.trim() || '';
}

function collectFilters() {
    const pending = policyDownloadState.pendingFilters;
    return {
        year: getFilterValue('policyDownloadYear') || pending?.year || '',
        month: getFilterValue('policyDownloadMonth') || pending?.month || '',
        steel_mill: getTrimmedFilterValue('policyDownloadMill') || pending?.steel_mill || '',
        sheet_name: document.getElementById('policyDownloadSheet')
            ? getFilterValue('policyDownloadSheet')
            : (pending?.sheet_name || ''),
        category_name: getFilterValue('policyDownloadCategory') || pending?.category_name || '',
        grade_value: getTrimmedFilterValue('policyDownloadGrade') || pending?.grade_value || '',
    };
}

/**
 * 组装政策查询/导出请求参数：年度、月份、钢厂、表页、分类、牌号。
 * 牌号经后端牌号分类档案解析为大类后再匹配 CATEGORY 厚度政策。
 */
function applyFiltersToParams(params, filters) {
    if (filters.year) params.year = filters.year;
    if (filters.month) params.month = filters.month;
    if (filters.steel_mill) params.steel_mill = filters.steel_mill;
    if (filters.sheet_name) params.sheet_name = filters.sheet_name;
    if (filters.category_name) params.category_name = filters.category_name;
    if (filters.grade_value) params.grade_value = filters.grade_value;
}

/**
 * 预览数据
 */
async function previewData(page = 1) {
    if (policyDownloadState.isLoading) return;
    policyDownloadState.isLoading = true;
    setSearchBusy('btnPreview', true);

    const filters = collectFilters();
    const tableBody = document.getElementById('policyPreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="20" class="px-4 py-8 text-center">
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
        params.page = page;
        params.size = policyDownloadState.pageSize;

        const response = await HttpClient.get(`${API_BASE}/export-preview`, { params });
        const data = response.data || {};
        const records = Array.isArray(data.items) ? data.items : [];

        policyDownloadState.page = data.page || page;
        policyDownloadState.records = records;
        policyDownloadState.total = data.total || records.length;
        policyDownloadState.totalPages =
            data.total_pages ||
            Math.max(1, Math.ceil(policyDownloadState.total / policyDownloadState.pageSize));

        // 更新记录数
        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = policyDownloadState.total;
        }

        // 渲染预览表格
        if (tableBody) {
            tableBody.innerHTML = records.length
                ? renderPolicyRows(records)
                : `
                <tr>
                    <td colspan="20" class="px-4 py-8 text-center text-ink-dim text-xs">
                        当前筛选下暂无数据
                    </td>
                </tr>
            `;
        }
        paintPagination('policyPagination', policyDownloadState.page, policyDownloadState.totalPages);
        updateConditionsDisplay();
    } catch (error) {
        console.error('预览数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="20" class="px-4 py-8 text-center text-brand text-xs">
                        加载失败: ${esc(error.message || '未知错误')}
                    </td>
                </tr>
            `;
        }
        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = '0';
        }
        const pagination = document.getElementById('policyPagination');
        if (pagination) pagination.innerHTML = '';
    } finally {
        policyDownloadState.isLoading = false;
        setSearchBusy('btnPreview', false);
    }
}

/**
 * 导出 Excel
 */
async function exportExcel() {
    if (typeof can === 'function' && !can('op:steel-price-policy-download:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    const filters = collectFilters();

    if (!requireExportYearMonth(filters)) {
        return;
    }

    // 显示加载遮罩
    const loading = document.getElementById('downloadLoading');
    if (loading) loading.classList.remove('hidden');

    try {
        const params = {};
        applyFiltersToParams(params, filters);
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`, {
            params,
            headers: {
                Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            },
            defaultFilename: '加减价政策列表.xlsx',
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
        // 隐藏加载遮罩
        if (loading) loading.classList.add('hidden');
    }
}

/**
 * 批量删除政策
 */
async function batchDeletePolicies() {
    if (typeof can === 'function' && !can('op:steel-price-policy-download:delete')) {
        showToast('无删除权限', 'warning');
        return;
    }
    const year = getFilterValue('policyDownloadYear');
    const month = getFilterValue('policyDownloadMonth');
    const steelMill = getTrimmedFilterValue('policyDownloadMill');
    const sheetName = getFilterValue('policyDownloadSheet');

    // 年度、月份必填；钢厂、表页可选
    if (!year || !month) {
        showToast('删除必须选择年度和月份（钢厂可选）', 'warning');
        return;
    }

    const millLabel = steelMill || '全部钢厂';
    const sheetLabel = sheetName || '全部表页';
    const confirmed = await window.confirmAction(
        `确定要删除以下条件的政策数据吗？\n\n${fmtPeriod(year, month)} · 钢厂: ${millLabel} · 表页: ${sheetLabel}\n\n此操作不可恢复！`
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
            <div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>
            删除中...
        `;
    }

    try {
        const params = { year, month };
        if (steelMill) {
            params.steel_mill = steelMill;
        }
        if (sheetName) {
            params.sheet_name = sheetName;
        }
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
                            <div class="w-4 h-4 border border-line border-brand rounded-full animate-spin mr-2"></div>
                            <span class="text-[11px] text-ink-dim">正在刷新...</span>
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
    await previewData(1);
}

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: policyDownloadTemplate,
    init: () => init(),
    destroy() {
        moreMenu?.unbind();
        moreMenu = null;
    },
};
