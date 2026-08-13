/**
 * 废料月度销售价 — 页面逻辑
 * 一次加载整月矩阵，一次提交保存
 */

import {
    scrapPriceTemplate,
    renderScrapRows,
    renderMonthChips,
    fmtTelemetry,
} from './template.js?v=9';

const API_BASE = '/api/stamping/scrap-prices';
const DRAWER_ANIMATION_MS = 300;

const scrapState = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    sheet: null,
    months: [],
    years: [],
    isLoading: false,
    isSaving: false,
};

function canOp(code) {
    return typeof can === 'function' ? can(code) : true;
}

function openDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.style.display = 'flex';
    if (backdrop) backdrop.style.display = 'block';
    void drawer.offsetWidth;
    drawer.classList.remove('opacity-0', 'scale-95', 'translate-x-full');
    drawer.classList.add('opacity-100', 'scale-100');
}

function closeDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.classList.remove('opacity-100', 'scale-100');
    drawer.classList.add('opacity-0', 'scale-95');
    setTimeout(() => {
        drawer.style.display = 'none';
        if (backdrop) backdrop.style.display = 'none';
    }, DRAWER_ANIMATION_MS);
}

function formatYmLabel(year, month) {
    return `${year} · ${String(month).padStart(2, '0')}`;
}

async function fetchMonthsForYear(year) {
    if (year === scrapState.year && Array.isArray(scrapState.months)) {
        return scrapState.months;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/months`, { params: { year } });
        return Array.isArray(res.data) ? res.data : [];
    } catch (_) {
        return [];
    }
}

async function refreshCopyPanelState() {
    const ty = Number(document.getElementById('copyTargetYear')?.value);
    const tm = Number(document.getElementById('copyTargetMonth')?.value);
    const toMeta = document.getElementById('copyToMeta');
    const warn = document.getElementById('copyOverwriteWarn');
    const confirmBtn = document.getElementById('confirmScrapCopy');
    if (!toMeta || !warn || !confirmBtn) return;

    if (!ty || !tm || tm < 1 || tm > 12) {
        toMeta.textContent = '请选择有效目标月';
        warn.classList.add('hidden');
        confirmBtn.textContent = '复制';
        return;
    }

    const months = await fetchMonthsForYear(ty);
    const hit = months.find((m) => Number(m.month) === tm);
    const hasData = Boolean(hit && hit.filled_count > 0);

    if (hasData) {
        toMeta.textContent = `已有 ${hit.filled_count}/6`;
        warn.classList.remove('hidden');
        confirmBtn.textContent = '覆盖并复制';
    } else {
        toMeta.textContent = '尚未维护';
        warn.classList.add('hidden');
        confirmBtn.textContent = `复制到 ${String(tm).padStart(2, '0')} 月`;
    }
}

async function openCopyDrawer() {
    const sy = document.getElementById('copySourceYear');
    const sm = document.getElementById('copySourceMonth');
    const ty = document.getElementById('copyTargetYear');
    const tm = document.getElementById('copyTargetMonth');
    const fromDisplay = document.getElementById('copyFromDisplay');
    const fromMeta = document.getElementById('copyFromMeta');

    const sourceYear = scrapState.year;
    const sourceMonth = scrapState.month;
    if (sy) sy.value = String(sourceYear);
    if (sm) sm.value = String(sourceMonth);

    let targetYear = sourceYear;
    let targetMonth = sourceMonth === 12 ? 1 : sourceMonth + 1;
    if (sourceMonth === 12) targetYear = sourceYear + 1;
    if (ty) ty.value = String(targetYear);
    if (tm) tm.value = String(targetMonth);

    if (fromDisplay) fromDisplay.textContent = formatYmLabel(sourceYear, sourceMonth);
    const filled =
        scrapState.sheet?.filled_count ??
        scrapState.months.find((m) => m.month === sourceMonth)?.filled_count ??
        0;
    if (fromMeta) fromMeta.textContent = `${filled} / 6 基地`;

    openDrawer('scrapCopyDrawer', 'scrapCopyBackdrop');
    await refreshCopyPanelState();
}

function setMoreMenuOpen(isOpen) {
    const menu = document.getElementById('scrapMoreMenu');
    if (!menu) return;
    menu.classList.toggle('hidden', !isOpen);
}

function applyPermissionUi() {
    const canSave =
        canOp('op:scrap-price:create') || canOp('op:scrap-price:update');
    const canCopy = canOp('op:scrap-price:copy');
    const canDelete = canOp('op:scrap-price:delete');
    const canExport = canOp('op:scrap-price:export');

    if (!canSave) document.getElementById('btnScrapSave')?.classList.add('hidden');
    if (!canCopy) document.getElementById('btnScrapCopy')?.classList.add('hidden');
    if (!canDelete) document.getElementById('btnScrapDelete')?.classList.add('hidden');
    if (!canExport) document.getElementById('btnScrapExport')?.classList.add('hidden');

    const hasMore = canCopy || canDelete || canExport;
    if (!hasMore) document.getElementById('btnScrapMore')?.classList.add('hidden');
}

function setLoading(isLoading) {
    scrapState.isLoading = isLoading;
    const el = document.getElementById('scrapLoading');
    if (el) el.classList.toggle('hidden', !isLoading);
}

function updateBadge(sheet) {
    const badge = document.getElementById('scrapMonthBadge');
    const status = document.getElementById('scrapMonthStatus');
    const hint = document.getElementById('scrapFooterHint');
    const meta = document.getElementById('scrapFooterMeta');
    if (!badge) return;

    if (meta) meta.textContent = '6 个基地';

    if (!sheet) {
        badge.textContent = '—';
        if (status) status.textContent = '';
        if (hint) hint.textContent = '';
        return;
    }

    badge.textContent = `${sheet.year} · ${String(sheet.month).padStart(2, '0')}`;
    if (status) {
        if (sheet.is_complete) {
            status.textContent = '已完整';
        } else if (sheet.is_saved) {
            status.textContent = `已录 ${sheet.filled_count}/6`;
        } else {
            status.textContent = '未录入';
        }
    }

    if (hint) {
        hint.textContent = sheet.is_complete
            ? '修改后点击保存'
            : '保存需填满 6 行大盘价';
    }
}

function fillYearMonthSelects() {
    const yearSelect = document.getElementById('scrapYearSelect');
    const monthSelect = document.getElementById('scrapMonthSelect');
    if (!yearSelect || !monthSelect) return;

    const years = new Set(scrapState.years || []);
    years.add(scrapState.year);
    const nowYear = new Date().getFullYear();
    years.add(nowYear);
    years.add(nowYear - 1);
    years.add(nowYear + 1);

    const sortedYears = Array.from(years).sort((a, b) => b - a);
    yearSelect.innerHTML = sortedYears
        .map(
            (y) =>
                `<option value="${y}" ${y === scrapState.year ? 'selected' : ''}>${y}</option>`
        )
        .join('');

    monthSelect.innerHTML = Array.from({ length: 12 }, (_, i) => i + 1)
        .map(
            (m) =>
                `<option value="${m}" ${m === scrapState.month ? 'selected' : ''}>${m} 月</option>`
        )
        .join('');
}

function renderChips() {
    const wrap = document.getElementById('scrapMonthChips');
    if (!wrap) return;
    wrap.innerHTML = renderMonthChips(scrapState.months, {
        year: scrapState.year,
        month: scrapState.month,
    });
}

function recalcRowNet(rowEl) {
    const marketInput = rowEl.querySelector('.scrap-market');
    const deductionInput = rowEl.querySelector('.scrap-deduction');
    const netEl = rowEl.querySelector('.scrap-net');
    if (!marketInput || !deductionInput || !netEl) return;

    const market = parseFloat(marketInput.value);
    const deduction = parseFloat(deductionInput.value || '0');
    if (Number.isNaN(market) || Number.isNaN(deduction)) {
        netEl.textContent = '—';
        return;
    }
    netEl.textContent = fmtTelemetry(market - deduction);
}

function bindRowInputEvents() {
    const tbody = document.getElementById('scrapPriceTableBody');
    if (!tbody) return;
    tbody.querySelectorAll('tr[data-location]').forEach((rowEl) => {
        rowEl.querySelectorAll('.scrap-market, .scrap-deduction').forEach((input) => {
            input.addEventListener('input', () => recalcRowNet(rowEl));
        });
    });
}

function collectItemsFromDom() {
    const tbody = document.getElementById('scrapPriceTableBody');
    const rows = Array.from(tbody?.querySelectorAll('tr[data-location]') || []);
    const items = [];
    const errors = [];

    rows.forEach((rowEl) => {
        const location = rowEl.getAttribute('data-location');
        const marketRaw = rowEl.querySelector('.scrap-market')?.value?.trim() ?? '';
        const deductionRaw =
            rowEl.querySelector('.scrap-deduction')?.value?.trim() ?? '';
        const remark = rowEl.querySelector('.scrap-remark')?.value?.trim() || null;

        if (marketRaw === '') {
            errors.push(`${location}: 请填写大盘价`);
            return;
        }
        const market_price = Number(marketRaw);
        const deduction_fee = deductionRaw === '' ? 0 : Number(deductionRaw);
        if (Number.isNaN(market_price) || market_price < 0) {
            errors.push(`${location}: 大盘价无效`);
            return;
        }
        if (Number.isNaN(deduction_fee) || deduction_fee < 0) {
            errors.push(`${location}: 扣费无效`);
            return;
        }
        if (deduction_fee > market_price) {
            errors.push(`${location}: 扣费不能大于大盘价`);
            return;
        }
        items.push({ location, market_price, deduction_fee, remark });
    });

    return { items, errors };
}

async function loadFilterOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/options`);
        scrapState.years = Array.isArray(res.data?.years) ? res.data.years : [];
    } catch (_) {
        scrapState.years = [];
    }
}

async function loadMonthList() {
    try {
        const res = await HttpClient.get(`${API_BASE}/months`, {
            params: { year: scrapState.year },
        });
        scrapState.months = Array.isArray(res.data) ? res.data : [];
    } catch (_) {
        scrapState.months = [];
    }
    renderChips();
}

async function loadMonthSheet() {
    if (scrapState.isLoading) return;
    setLoading(true);
    try {
        const res = await HttpClient.get(`${API_BASE}/month`, {
            params: { year: scrapState.year, month: scrapState.month },
        });
        scrapState.sheet = res.data || null;
        const editable =
            canOp('op:scrap-price:create') || canOp('op:scrap-price:update');
        const tbody = document.getElementById('scrapPriceTableBody');
        if (tbody) {
            tbody.innerHTML = renderScrapRows(scrapState.sheet?.items || [], {
                editable,
            });
            bindRowInputEvents();
        }
        updateBadge(scrapState.sheet);
        fillYearMonthSelects();
        renderChips();
    } catch (_) {
        scrapState.sheet = null;
        updateBadge(null);
    } finally {
        setLoading(false);
    }
}

async function saveMonth() {
    if (scrapState.isSaving) return;
    const { items, errors } = collectItemsFromDom();
    if (errors.length) {
        showToast(errors[0], 'warning');
        return;
    }
    if (items.length !== 6) {
        showToast('保存需要完整 6 行数据', 'warning');
        return;
    }

    scrapState.isSaving = true;
    const btn = document.getElementById('btnScrapSave');
    if (btn) btn.disabled = true;

    try {
        const res = await HttpClient.put(`${API_BASE}/month`, {
            year: scrapState.year,
            month: scrapState.month,
            items,
        });
        scrapState.sheet = res.data || null;
        showToast(res.message || '保存成功', 'success');
        await loadMonthList();
        await loadMonthSheet();
    } catch (_) {
        // toast 已由 HttpClient 处理
    } finally {
        scrapState.isSaving = false;
        if (btn) btn.disabled = false;
    }
}

async function deleteMonth() {
    if (!scrapState.sheet?.is_saved) {
        showToast('本月尚无数据可删', 'warning');
        return;
    }
    const label = `${scrapState.year}-${String(scrapState.month).padStart(2, '0')}`;
    if (!window.confirm(`确认删除 ${label} 整月废料销售价？此操作不可恢复。`)) {
        return;
    }
    try {
        const res = await HttpClient.delete(`${API_BASE}/month`, {
            params: { year: scrapState.year, month: scrapState.month },
        });
        showToast(res.message || '已删除', 'success');
        await loadMonthList();
        await loadMonthSheet();
    } catch (_) {
        // toast handled
    }
}

async function confirmCopy() {
    const source_year = Number(document.getElementById('copySourceYear')?.value);
    const source_month = Number(document.getElementById('copySourceMonth')?.value);
    const target_year = Number(document.getElementById('copyTargetYear')?.value);
    const target_month = Number(document.getElementById('copyTargetMonth')?.value);

    if (
        !source_year ||
        !source_month ||
        !target_year ||
        !target_month ||
        source_month < 1 ||
        source_month > 12 ||
        target_month < 1 ||
        target_month > 12
    ) {
        showToast('请填写有效的源/目标年月', 'warning');
        return;
    }

    try {
        const res = await HttpClient.post(`${API_BASE}/copy-month`, {
            source_year,
            source_month,
            target_year,
            target_month,
        });
        showToast(res.message || '复制成功', 'success');
        closeDrawer('scrapCopyDrawer', 'scrapCopyBackdrop');
        scrapState.year = target_year;
        scrapState.month = target_month;
        await loadFilterOptions();
        fillYearMonthSelects();
        await loadMonthList();
        await loadMonthSheet();
    } catch (_) {
        // toast handled
    }
}

async function exportExcel() {
    if (!canOp('op:scrap-price:export')) {
        showToast('无导出权限', 'warning');
        return;
    }
    try {
        // 导出全部年份汇总表（跨年空行）；若只要当前年可改为传 year
        const { blob, filename } = await HttpClient.download(`${API_BASE}/export`);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename || '废料月度销售价.xlsx';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        showToast('导出成功', 'success');
    } catch (_) {
        // toast 已由 HttpClient 处理
    }
}

function readSelectorsIntoState() {
    const year = Number(document.getElementById('scrapYearSelect')?.value);
    const month = Number(document.getElementById('scrapMonthSelect')?.value);
    if (year) scrapState.year = year;
    if (month) scrapState.month = month;
}

function bindEvents() {
    document.getElementById('btnScrapLoad')?.addEventListener('click', async () => {
        readSelectorsIntoState();
        await loadMonthList();
        await loadMonthSheet();
    });

    document.getElementById('scrapYearSelect')?.addEventListener('change', async () => {
        readSelectorsIntoState();
        await loadMonthList();
        await loadMonthSheet();
    });

    document.getElementById('scrapMonthSelect')?.addEventListener('change', async () => {
        readSelectorsIntoState();
        await loadMonthSheet();
    });

    document.getElementById('scrapMonthChips')?.addEventListener('click', async (e) => {
        const chip = e.target.closest('.scrap-month-chip');
        if (!chip) return;
        scrapState.year = Number(chip.dataset.year);
        scrapState.month = Number(chip.dataset.month);
        fillYearMonthSelects();
        await loadMonthSheet();
        renderChips();
    });

    document.getElementById('btnScrapMore')?.addEventListener('click', (e) => {
        e.stopPropagation();
        const menu = document.getElementById('scrapMoreMenu');
        const isOpen = menu && !menu.classList.contains('hidden');
        setMoreMenuOpen(!isOpen);
    });

    document.addEventListener('click', (e) => {
        const wrap = document.getElementById('scrapMoreWrap');
        if (wrap && !wrap.contains(e.target)) {
            setMoreMenuOpen(false);
        }
    });

    document.getElementById('btnScrapSave')?.addEventListener('click', () => {
        saveMonth();
    });
    document.getElementById('btnScrapExport')?.addEventListener('click', () => {
        setMoreMenuOpen(false);
        exportExcel();
    });
    document.getElementById('btnScrapDelete')?.addEventListener('click', () => {
        setMoreMenuOpen(false);
        deleteMonth();
    });
    document.getElementById('btnScrapCopy')?.addEventListener('click', () => {
        setMoreMenuOpen(false);
        openCopyDrawer();
    });
    document.getElementById('copyTargetYear')?.addEventListener('input', () => {
        refreshCopyPanelState();
    });
    document.getElementById('copyTargetMonth')?.addEventListener('input', () => {
        refreshCopyPanelState();
    });
    document.getElementById('closeScrapCopyDrawer')?.addEventListener('click', () => {
        closeDrawer('scrapCopyDrawer', 'scrapCopyBackdrop');
    });
    document.getElementById('scrapCopyBackdrop')?.addEventListener('click', () => {
        closeDrawer('scrapCopyDrawer', 'scrapCopyBackdrop');
    });
    document.getElementById('cancelScrapCopy')?.addEventListener('click', () => {
        closeDrawer('scrapCopyDrawer', 'scrapCopyBackdrop');
    });
    document.getElementById('confirmScrapCopy')?.addEventListener('click', () => {
        confirmCopy();
    });
}

async function pickDefaultMonth() {
    await loadMonthList();
    if (scrapState.months.length > 0) {
        const latest = scrapState.months[0];
        scrapState.year = latest.year;
        scrapState.month = latest.month;
    }
}

async function init() {
    applyPermissionUi();
    bindEvents();
    await loadFilterOptions();
    await pickDefaultMonth();
    fillYearMonthSelects();
    await loadMonthSheet();
}

export const pageConfig = {
    render: scrapPriceTemplate,
    init,
};
