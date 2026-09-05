/**
 * Steel Price Policy Download Page
 * 钢价政策下载页面逻辑
 * 用于测试部门核对数据，主子表联合查询导出 Excel
 */

import { policyDownloadTemplate, renderPolicyRows } from './template.js?v=31';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    bindPageSizeSelect,
    renderPageButtons,
} from '../../../../page-size.js?v=2';

// 状态管理
const policyDownloadState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PREVIEW_PAGE_SIZE,
    totalPages: 1,
    filtersLoaded: false,
    pendingFilters: null,
};

// API 基础路径
const API_BASE = '/api/yishiyiyi/policy';
const GRADE_CATEGORY_API = '/api/yishiyiyi/steel-grade-category';

/**
 * 页面初始化
 */
function init() {
    bindEvents();
    bindPageSizeSelect('policyPageSize', {
        getSize: () => policyDownloadState.pageSize,
        setSize: (size) => {
            policyDownloadState.pageSize = size;
        },
        onChange: () => previewData(1),
        options: PREVIEW_PAGE_SIZE_OPTIONS,
        defaultSize: DEFAULT_PREVIEW_PAGE_SIZE,
    });
    policyDownloadState.pendingFilters = readHashFilters();
    loadFilterOptions().then(() => {
        applyPendingFiltersToSelects();
        const pendingCategory = policyDownloadState.pendingFilters?.category_name;
        if (pendingCategory) {
            loadGradesForCategory(pendingCategory);
        }
        updateConditionsDisplay();
        if (policyDownloadState.pendingFilters) {
            previewData(1);
        }
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
    const grade_value = params.get('grade_value') || '';
    if (!year && !month && !category_name && !steel_mill && !grade_value) return null;
    return { year, month, category_name, steel_mill, grade_value };
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
    const gradeInput = document.getElementById('policyDownloadGrade');
    if (gradeInput && pending.grade_value) {
        gradeInput.value = pending.grade_value;
    }
    const millInput = document.getElementById('policyDownloadMill');
    if (millInput && pending.steel_mill) {
        millInput.value = pending.steel_mill;
    }
}

function applyPermissionUi() {
    if (typeof can !== 'function') return;
    if (!can('op:steel-price-policy-download:export')) {
        document.getElementById('btnExportPolicy')?.classList.add('hidden');
        document.getElementById('btnExport')?.classList.add('hidden');
    }
    if (!can('op:steel-price-policy-download:delete')) {
        document.getElementById('btnDeletePolicy')?.classList.add('hidden');
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
                years.push({ value: y, label: fmtYear(y) });
        }
        fillSelect('policyDownloadYear', years);

        const months = Array.from({ length: 12 }, (_, i) => ({
            value: i + 1,
            label: fmtMonth(i + 1),
        }));
        fillSelect('policyDownloadMonth', months);
    }
}

async function loadGradesForCategory(categoryName) {
    const datalist = document.getElementById('policyGradeOptions');
    const gradeInput = document.getElementById('policyDownloadGrade');
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
        btnPreview.addEventListener('click', () => previewData(1));
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

    ['policyDownloadYear', 'policyDownloadMonth'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => updateConditionsDisplay());
    });

    const categorySelect = document.getElementById('policyDownloadCategory');
    if (categorySelect) {
        categorySelect.addEventListener('change', () => {
            const gradeInput = document.getElementById('policyDownloadGrade');
            if (gradeInput) gradeInput.value = '';
            loadGradesForCategory(categorySelect.value);
            updateConditionsDisplay();
        });
    }

    const gradeInput = document.getElementById('policyDownloadGrade');
    if (gradeInput) {
        gradeInput.addEventListener('input', () => updateConditionsDisplay());
        gradeInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                previewData(1);
            }
        });
    }

    // 钢厂变更时更新条件显示（支持输入搜索）
    const millSelect = document.getElementById('policyDownloadMill');
    if (millSelect) {
        millSelect.addEventListener('input', () => updateConditionsDisplay());
    }

    document.getElementById('policyPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.policy-page-btn');
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
    const period = fmtPeriod(filters.year, filters.month);
    if (period) conditions.push(period);
    if (filters.category_name) conditions.push(`分类: ${filters.category_name}`);
    if (filters.grade_value) conditions.push(`牌号: ${filters.grade_value}`);
    if (filters.steel_mill) conditions.push(`钢厂: ${filters.steel_mill}`);

    const display = document.getElementById('selectedConditions');
    if (display) {
        display.textContent = conditions.length > 0 ? conditions.join(' | ') : '请选择筛选条件';
    }
}

function getFilterValue(id) {
    return document.getElementById(id)?.value || '';
}

function collectFilters() {
    const pending = policyDownloadState.pendingFilters;
    return {
        year: getFilterValue('policyDownloadYear') || pending?.year || '',
        month: getFilterValue('policyDownloadMonth') || pending?.month || '',
        category_name: getFilterValue('policyDownloadCategory') || pending?.category_name || '',
        // grade_value：仅 UI 展示与级联选牌号，不传给政策 API（见 applyFiltersToParams）
        grade_value: document.getElementById('policyDownloadGrade')?.value.trim() || pending?.grade_value || '',
        steel_mill: getFilterValue('policyDownloadMill') || pending?.steel_mill || '',
    };
}

function hasAnyFilter(filters) {
    // 牌号仅 UI 级联辅助，不参与 API 筛选判定（见 applyFiltersToParams）
    return !!(filters.year || filters.month || filters.category_name || filters.steel_mill);
}

/**
 * 组装政策查询/导出请求参数。
 *
 * 注意：厚度政策已改为大类级存储（grade_type=CATEGORY），政策表不再按单牌号 grade_value 筛选。
 * 牌号输入框仅用于在牌号分类档案中级联定位分类；实际请求只传 category_name（冷轧/镀锌/酸洗）。
 * 切勿向 /export-preview、/export 传递 grade_value。
 */
function applyFiltersToParams(params, filters) {
    if (filters.year) params.year = filters.year;
    if (filters.month) params.month = filters.month;
    if (filters.category_name) params.category_name = filters.category_name;
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

    const tableBody = document.getElementById('policyPreviewBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="20" class="px-4 py-8 text-center">
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
            tableBody.innerHTML = renderPolicyRows(records);
        }
        const pagination = document.getElementById('policyPagination');
        if (pagination) {
            pagination.innerHTML = renderPageButtons(
                policyDownloadState.page,
                policyDownloadState.totalPages,
                'policy-page-btn',
            );
        }
    } catch (error) {
        console.error('预览数据失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="20" class="px-4 py-8 text-center text-[#d32f2f] text-xs">
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

    if (!hasAnyFilter(filters)) {
        showToast('请至少选择一个筛选条件', 'warning');
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
            defaultFilename: '加减价政策导出.xlsx',
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
    const steelMill = getFilterValue('policyDownloadMill');

    // 年度、月份必填；钢厂可选
    if (!year || !month) {
        showToast('删除必须选择年度和月份（钢厂可选）', 'warning');
        return;
    }

    const millLabel = steelMill || '全部钢厂';
    const confirmed = window.confirm(
        `确定要删除以下条件的政策数据吗？\n\n${fmtPeriod(year, month)} · 钢厂: ${millLabel}\n\n此操作不可恢复！`
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
        const params = { year, month };
        if (steelMill) {
            params.steel_mill = steelMill;
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
    await previewData(1);
}

/**
 * 页面配置导出
 */
export const pageConfig = {
    render: policyDownloadTemplate,
    init: () => init(),
};
