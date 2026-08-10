/**
 * Steel Price Calc Page
 * 钢价计算 — 过滤条件 + 批量计算触发控制台
 */

import { steelPriceCalcTemplate } from './template.js';

const STAMPING_CASCADE_FILTERS_API = '/api/stamping/filters/cascade';
const STEEL_PRICE_CALC_STATS_API = '/api/dashboard/stats/steel-price-calc';

const calcState = {
    isCalculating: false,
    calcStartTime: null,
    calcTimer: null,
    stats: {
        base_price_count: 0,
        adjustment_rule_count: 0,
        thickness_row_count: 0,
    },
};

export function init() {
    bindEvents();
    loadStampingFilters();
    loadCalcStats();
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcStats());
    document.getElementById('calcMonth')?.addEventListener('change', () => loadCalcStats());

    document.getElementById('calcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['calcSupplier', 'calcVehicleModel', 'calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });
    document.getElementById('calcSupplier')?.addEventListener('change', () => {
        resetDependentFilters(['calcVehicleModel', 'calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        resetDependentFilters(['calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());

    document.getElementById('goToResultPageBtn')?.addEventListener('click', () => {
        if (typeof window.switchTab === 'function') {
            window.switchTab('result-query');
        } else {
            showToast('请前往系统导航栏的"结果查询"页面', 'warning');
        }
    });
}

function getSelectedPeriod() {
    const now = new Date();
    let year = parseInt(document.getElementById('calcYear')?.value, 10);
    let month = parseInt(document.getElementById('calcMonth')?.value, 10);
    if (Number.isNaN(year)) year = now.getFullYear();
    if (Number.isNaN(month)) month = now.getMonth() + 1;
    return { year, month };
}

function resetDependentFilters(ids) {
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
}

function resetFilters() {
    ['calcLocation', 'calcSupplier', 'calcVehicleModel', 'calcVersion'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    const now = new Date();
    const yearEl = document.getElementById('calcYear');
    const monthEl = document.getElementById('calcMonth');
    if (yearEl) yearEl.value = String(now.getFullYear());
    if (monthEl) monthEl.value = String(now.getMonth() + 1);

    loadStampingFilters();
    loadCalcStats();
    hideCompleteBanner();
    resetProgress();
}

async function loadStampingFilters() {
    try {
        const params = {
            location: document.getElementById('calcLocation')?.value || '',
            stamping_supplier: document.getElementById('calcSupplier')?.value || '',
            vehicle_model: document.getElementById('calcVehicleModel')?.value || '',
        };
        const response = await HttpClient.get(STAMPING_CASCADE_FILTERS_API, { params });
        const filters = response.data || {};

        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcSupplier', filters.stamping_suppliers || []);
        fillSelect('calcVehicleModel', filters.vehicle_models || []);
        fillSelect('calcVersion', filters.versions || []);
    } catch (error) {
        console.error('加载冲压筛选选项失败:', error);
    }
}

async function loadCalcStats() {
    const { year, month } = getSelectedPeriod();
    const location = document.getElementById('calcLocation')?.value || '';
    const stampingSupplier = document.getElementById('calcSupplier')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';

    try {
        const params = { year, month };
        if (location) params.location = location;
        if (stampingSupplier) params.stamping_supplier = stampingSupplier;
        if (vehicleModel) params.vehicle_model = vehicleModel;

        const response = await HttpClient.get(STEEL_PRICE_CALC_STATS_API, { params });
        const stats = response.data || {};
        const filters = stats.filters || {};

        renderPeriodFilters(filters, year, month);

        const baseCount = Number(stats.base_price_count) || 0;
        const adjustmentCount = Number(stats.adjustment_rule_count) || 0;
        const thicknessCount = Number(stats.thickness_row_count) || 0;

        renderCalcStats({
            base_price_count: baseCount,
            adjustment_rule_count: adjustmentCount,
            thickness_row_count: thicknessCount,
        });
        validateDataPreparation(
            document.getElementById('calcLocation')?.value || '',
            year,
            month,
            baseCount,
            adjustmentCount,
            thicknessCount
        );
    } catch (error) {
        console.error('加载钢价计算统计失败:', error);
        renderCalcStats({
            base_price_count: 0,
            adjustment_rule_count: 0,
            thickness_row_count: 0,
        });
        validateDataPreparation(location, year, month, 0, 0, 0);
        showToast('加载数据依据失败', 'error');
    }
}

function renderPeriodFilters(filters, year, month) {
    const years = Array.isArray(filters.years) ? filters.years.slice() : [];
    const months = Array.isArray(filters.months) ? filters.months.slice() : [];

    if (!years.includes(year)) years.unshift(year);
    if (!months.includes(month)) months.push(month);
    months.sort((a, b) => a - b);

    fillSelect('calcYear', years, value => `${value} 年`, String(year));
    fillSelect('calcMonth', months, value => `${value} 月`, String(month));
}

function renderCalcStats(stats) {
    calcState.stats = stats;
    setCountHtml('cntBasePrice', stats.base_price_count, '条');
    setCountHtml('cntAdjustment', stats.adjustment_rule_count, '条');
    setCountHtml('cntThicknessRows', stats.thickness_row_count, '行');
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

function fillSelect(id, values = [], label = value => value, preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        '<option value="">全部</option>' +
        values.map(v => {
            const value = String(v);
            return `<option value="${esc(value)}"${value === String(current) ? ' selected' : ''}>${esc(label(v))}</option>`;
        }).join('');
}

function startCalculation() {
    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';

    if (Number.isNaN(year) || Number.isNaN(month)) {
        showToast('请填写完整的计算年度与月份', 'warning');
        return;
    }
    if (!location) {
        showToast('请选择生产基地', 'warning');
        return;
    }

    const { base_price_count, adjustment_rule_count, thickness_row_count } = calcState.stats;
    if (base_price_count <= 0 || adjustment_rule_count <= 0 || thickness_row_count <= 0) {
        showToast('当前所选条件数据未就绪，无法计算', 'warning');
        return;
    }

    const filterParams = {
        location,
        stamping_supplier: document.getElementById('calcSupplier')?.value || '',
        vehicle_model: document.getElementById('calcVehicleModel')?.value || '',
        version: document.getElementById('calcVersion')?.value || '',
        year,
        month,
    };

    hideCompleteBanner();
    calcState.isCalculating = true;
    calcState.calcStartTime = Date.now();

    const area = document.getElementById('calcProgressArea');
    if (area) area.classList.remove('hidden');

    const statusEl = document.getElementById('calcProgressStatus');
    if (statusEl) statusEl.textContent = `正在执行 ${year}年第${month}期过滤范围批处理...`;

    const startBtn = document.getElementById('startCalcBtn');
    if (startBtn) {
        startBtn.setAttribute('disabled', 'true');
        startBtn.classList.add('opacity-50', 'pointer-events-none');
    }

    calcState.calcTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - calcState.calcStartTime) / 1000);
        const timeEl = document.getElementById('calcProgressTime');
        if (timeEl) timeEl.textContent = `耗时: ${elapsed}s`;
    }, 1000);

    simulateBatchExecution(filterParams);
}

function simulateBatchExecution() {
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            finishCalculation();
        }
        updateProgress(Math.min(progress, 100));
    }, 400);
}

function updateProgress(percent) {
    const rounded = Math.round(percent);
    const bar = document.getElementById('calcProgressBar');
    if (bar) bar.style.width = `${rounded}%`;
    const percentEl = document.getElementById('calcProgressPercent');
    if (percentEl) percentEl.textContent = `${rounded}%`;
}

function finishCalculation() {
    calcState.isCalculating = false;
    if (calcState.calcTimer) {
        clearInterval(calcState.calcTimer);
        calcState.calcTimer = null;
    }

    const progressArea = document.getElementById('calcProgressArea');
    if (progressArea) progressArea.classList.add('hidden');

    const completeBanner = document.getElementById('calcCompleteBanner');
    if (completeBanner) completeBanner.classList.remove('hidden');

    const startBtn = document.getElementById('startCalcBtn');
    if (startBtn) {
        startBtn.removeAttribute('disabled');
        startBtn.classList.remove('opacity-50', 'pointer-events-none');
    }

    showToast('钢价批处理涡轮执行完毕', 'success');
    loadCalcStats();
}

function hideCompleteBanner() {
    const banner = document.getElementById('calcCompleteBanner');
    if (banner) banner.classList.add('hidden');
}

function resetProgress() {
    const area = document.getElementById('calcProgressArea');
    if (area) area.classList.add('hidden');
    const bar = document.getElementById('calcProgressBar');
    if (bar) bar.style.width = '0%';
    const percent = document.getElementById('calcProgressPercent');
    if (percent) percent.textContent = '0%';
}

function validateDataPreparation(location, year, month, cntBasePrice, cntAdjustment, cntThickness) {
    const startBtn = document.getElementById('startCalcBtn');
    const errorBanner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn) return;

    const isLocationSelected = Boolean(location);
    const isPeriodSelected = Boolean(year && month);
    const isDataValid = cntBasePrice > 0 && cntAdjustment > 0 && cntThickness > 0;
    const isReady = isLocationSelected && isPeriodSelected && isDataValid;

    startBtn.disabled = !isReady;
    if (isReady) {
        errorBanner?.classList.add('hidden');
    } else {
        errorBanner?.classList.remove('hidden');
    }
}

export const pageConfig = {
    render: steelPriceCalcTemplate,
    init: () => init(),
};
