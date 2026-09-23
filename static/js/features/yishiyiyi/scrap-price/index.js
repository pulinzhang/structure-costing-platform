/**
 * 废料月度销售价 — 页面逻辑
 * 一次加载整月矩阵，一次提交保存
 */

import {
    scrapPriceTemplate,
    renderScrapRows,
    renderMonthChips,
    fmtTelemetry,
    fmtPrice,
    parsePriceInput,
    comparePriceStrings,
    subtractPriceStrings,
} from './template.js?v=28';
import { bindMoreMenu } from '../../../ui/more-menu.js?v=6';

const API_BASE = '/api/yishiyiyi/scrap-price';
const DRAWER_ANIMATION_MS = 300;
const SCRAP_CATEGORY_STEEL = '钢材';
const SCRAP_CATEGORY_ALUMINUM = '铝板';

/** @type {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void } | null} */
let moreMenu = null;
const SCRAP_CATEGORY_LABELS = {
    [SCRAP_CATEGORY_STEEL]: '钢材料',
    [SCRAP_CATEGORY_ALUMINUM]: '铝材',
};

const scrapState = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    scrapCategory: SCRAP_CATEGORY_STEEL,
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
    return fmtPeriod(year, month);
}

async function fetchMonthsForYear(year) {
    if (year === scrapState.year && Array.isArray(scrapState.months)) {
        return scrapState.months;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/months`, {
            params: { year, scrap_category: scrapState.scrapCategory },
        });
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
        toMeta.textContent = `已有 ${hit.filled_count}/${hit.required_count ?? hit.filled_count}`;
        warn.classList.remove('hidden');
        confirmBtn.textContent = '覆盖并复制';
    } else {
        toMeta.textContent = '尚未维护';
        warn.classList.add('hidden');
        confirmBtn.textContent = `复制到 ${fmtMonth(tm)}`;
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

function setYearMenuOpen(isOpen) {
    const menu = document.getElementById('scrapYearMenu');
    const trigger = document.getElementById('scrapYearTrigger');
    if (!menu || !trigger) return;
    menu.classList.toggle('hidden', !isOpen);
    trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

/** 同步深色年度选择器与隐藏 select */
function syncYearPicker() {
    const yearSelect = document.getElementById('scrapYearSelect');
    const label = document.getElementById('scrapYearLabel');
    const menu = document.getElementById('scrapYearMenu');
    if (!yearSelect || !label || !menu) return;

    label.textContent = fmtYear(scrapState.year);
    yearSelect.value = String(scrapState.year);

    const itemClass =
        'w-full px-3 py-1.5 text-left text-[12px] font-mono tabular-nums transition-colors ';
    const idleClass = 'text-ink-muted hover:bg-app-surface hover:text-ink';
    const activeClass = 'bg-app-surface text-ink';

    menu.innerHTML = Array.from(yearSelect.options)
        .map((opt) => {
            const y = Number(opt.value);
            const isActive = y === scrapState.year;
            return `<button type="button" role="option" data-year="${y}" aria-selected="${isActive}"
                class="${itemClass}${isActive ? activeClass : idleClass}">${esc(fmtYear(y))}</button>`;
        })
        .join('');
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
    if (!hasMore) document.getElementById('scrapMoreWrap')?.classList.add('hidden');
}

function syncCategoryButtons() {
    const steelOn = scrapState.scrapCategory === SCRAP_CATEGORY_STEEL;
    const steelBtn = document.getElementById('scrapCategorySteelBtn');
    const aluBtn = document.getElementById('scrapCategoryAluminumBtn');
    if (steelBtn) {
        steelBtn.classList.toggle('bg-brand', steelOn);
        steelBtn.classList.toggle('border-brand', steelOn);
        steelBtn.classList.toggle('text-ink-onbrand', steelOn);
        steelBtn.classList.toggle('bg-transparent', !steelOn);
        steelBtn.classList.toggle('border-line', !steelOn);
        steelBtn.classList.toggle('text-ink-dim', !steelOn);
    }
    if (aluBtn) {
        aluBtn.classList.toggle('bg-brand', !steelOn);
        aluBtn.classList.toggle('border-brand', !steelOn);
        aluBtn.classList.toggle('text-ink-onbrand', !steelOn);
        aluBtn.classList.toggle('bg-transparent', steelOn);
        aluBtn.classList.toggle('border-line', steelOn);
        aluBtn.classList.toggle('text-ink-dim', steelOn);
    }
}

async function switchScrapCategory(category) {
    if (category === scrapState.scrapCategory) return;
    scrapState.scrapCategory = category;
    syncCategoryButtons();
    await loadMonthList();
    await loadMonthSheet();
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

    if (meta) {
        const n = sheet?.required_count ?? sheet?.locations?.length ?? 0;
        meta.textContent = n ? `${n} 个基地` : '无已启用基地';
    }

    if (!sheet) {
        badge.textContent = '—';
        if (status) status.textContent = '';
        if (hint) hint.textContent = '';
        return;
    }

    badge.textContent = fmtPeriod(sheet.year, sheet.month);
    const denom = sheet.required_count ?? 0;
    if (status) {
        if (sheet.is_complete) {
            status.textContent = '已完整';
        } else if (sheet.is_saved) {
            status.textContent = `已录 ${sheet.filled_count}/${denom}`;
        } else {
            status.textContent = '未录入';
        }
    }

    if (hint) {
        hint.textContent = sheet.is_complete
            ? '修改后点击保存'
            : denom
                ? `保存需填满 ${denom} 行大盘价`
                : '请先在基地页启用基地';
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
                `<option value="${y}" ${y === scrapState.year ? 'selected' : ''}>${esc(fmtYear(y))}</option>`
        )
        .join('');

    monthSelect.innerHTML = Array.from({ length: 12 }, (_, i) => i + 1)
        .map(
            (m) =>
                `<option value="${m}" ${m === scrapState.month ? 'selected' : ''}>${esc(fmtMonth(m))}</option>`
        )
        .join('');

    syncYearPicker();
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

    const market = parsePriceInput(marketInput.value);
    const deductionRaw = deductionInput.value?.trim() ?? '';
    const deduction = deductionRaw === '' ? '0.00' : parsePriceInput(deductionRaw);
    if (market == null || deduction == null) {
        netEl.textContent = '—';
        return;
    }
    netEl.textContent = fmtTelemetry(subtractPriceStrings(market, deduction));
}

/** 录入中只保留数字与最多一个小数点，小数最多 2 位 */
function sanitizePriceTyping(raw) {
    let cleaned = String(raw ?? '').replace(/[^\d.]/g, '');
    const dotIndex = cleaned.indexOf('.');
    if (dotIndex !== -1) {
        cleaned =
            cleaned.slice(0, dotIndex + 1) +
            cleaned.slice(dotIndex + 1).replace(/\./g, '');
        const [integerPart, fractionPart = ''] = cleaned.split('.');
        cleaned = `${integerPart}.${fractionPart.slice(0, 2)}`;
    }
    return cleaned;
}

function applyPriceTypingSanitize(input) {
    const before = input.value;
    const cleaned = sanitizePriceTyping(before);
    if (cleaned === before) return;
    const cursor = input.selectionStart;
    input.value = cleaned;
    if (typeof cursor === 'number') {
        const delta = before.length - cleaned.length;
        const nextPos = Math.max(0, cursor - delta);
        input.setSelectionRange(nextPos, nextPos);
    }
}

function formatPriceFieldOnBlur(input) {
    const raw = input.value?.trim() ?? '';
    if (raw === '' || raw === '.') {
        input.value = '';
        return;
    }
    const n = parsePriceInput(raw);
    if (n == null) {
        input.value = '';
        showToast('请输入有效金额（仅数字）', 'warning');
        return;
    }
    input.value = fmtPrice(n);
}

function formatPriceFieldOnFocus(input) {
    const n = parsePriceInput(input.value);
    if (n == null) return;
    // 编辑时去掉千分位，保留两位小数，便于输入
    input.value = n;
}

function bindRowInputEvents() {
    const tbody = document.getElementById('scrapPriceTableBody');
    if (!tbody) return;
    tbody.querySelectorAll('tr[data-location]').forEach((rowEl) => {
        rowEl.querySelectorAll('.scrap-market, .scrap-deduction').forEach((input) => {
            input.addEventListener('beforeinput', (e) => {
                if (e.inputType === 'insertText' && e.data && /[^\d.]/.test(e.data)) {
                    e.preventDefault();
                }
            });
            input.addEventListener('focus', () => formatPriceFieldOnFocus(input));
            input.addEventListener('blur', () => {
                formatPriceFieldOnBlur(input);
                recalcRowNet(rowEl);
            });
            input.addEventListener('input', () => {
                applyPriceTypingSanitize(input);
                recalcRowNet(rowEl);
            });
            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const text = e.clipboardData?.getData('text') ?? '';
                const cleaned = sanitizePriceTyping(text);
                const start = input.selectionStart ?? input.value.length;
                const end = input.selectionEnd ?? input.value.length;
                const next = sanitizePriceTyping(
                    input.value.slice(0, start) + cleaned + input.value.slice(end)
                );
                input.value = next;
                const pos = Math.min(start + cleaned.length, next.length);
                input.setSelectionRange(pos, pos);
                recalcRowNet(rowEl);
            });
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
        const market_price = parsePriceInput(marketRaw);
        const deduction_fee =
            deductionRaw === '' ? '0.00' : parsePriceInput(deductionRaw);
        if (market_price == null) {
            errors.push(`${location}: 大盘价无效`);
            return;
        }
        if (deduction_fee == null) {
            errors.push(`${location}: 扣费无效`);
            return;
        }
        if (comparePriceStrings(deduction_fee, market_price) > 0) {
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
            params: { year: scrapState.year, scrap_category: scrapState.scrapCategory },
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
            params: {
                year: scrapState.year,
                month: scrapState.month,
                scrap_category: scrapState.scrapCategory,
            },
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
    const required = scrapState.sheet?.required_count ?? items.length;
    if (items.length !== required) {
        showToast(`保存需要完整 ${required} 行数据`, 'warning');
        return;
    }

    scrapState.isSaving = true;
    const btn = document.getElementById('btnScrapSave');
    if (btn) btn.disabled = true;

    try {
        const res = await HttpClient.put(`${API_BASE}/month`, {
            year: scrapState.year,
            month: scrapState.month,
            scrap_category: scrapState.scrapCategory,
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
    const label = fmtPeriod(scrapState.year, scrapState.month);
    const categoryLabel = SCRAP_CATEGORY_LABELS[scrapState.scrapCategory] || '';
    if (!await window.confirmAction(`确认删除 ${label} ${categoryLabel}废料销售价？此操作不可恢复。`)) {
        return;
    }
    try {
        const res = await HttpClient.delete(`${API_BASE}/month`, {
            params: {
                year: scrapState.year,
                month: scrapState.month,
                scrap_category: scrapState.scrapCategory,
            },
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
            scrap_category: scrapState.scrapCategory,
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
    document.getElementById('scrapCategorySteelBtn')?.addEventListener('click', () => {
        switchScrapCategory(SCRAP_CATEGORY_STEEL);
    });
    document.getElementById('scrapCategoryAluminumBtn')?.addEventListener('click', () => {
        switchScrapCategory(SCRAP_CATEGORY_ALUMINUM);
    });

    document.getElementById('btnScrapLoad')?.addEventListener('click', async () => {
        readSelectorsIntoState();
        await loadMonthList();
        await loadMonthSheet();
    });

    document.getElementById('scrapYearSelect')?.addEventListener('change', async () => {
        readSelectorsIntoState();
        syncYearPicker();
        await loadMonthList();
        await loadMonthSheet();
    });

    document.getElementById('scrapYearTrigger')?.addEventListener('click', (e) => {
        e.stopPropagation();
        moreMenu?.close();
        const menu = document.getElementById('scrapYearMenu');
        const isOpen = menu && !menu.classList.contains('hidden');
        setYearMenuOpen(!isOpen);
    });

    document.getElementById('scrapYearMenu')?.addEventListener('click', async (e) => {
        const item = e.target.closest('[data-year]');
        if (!item) return;
        e.stopPropagation();
        const year = Number(item.dataset.year);
        if (!year || year === scrapState.year) {
            setYearMenuOpen(false);
            return;
        }
        scrapState.year = year;
        const yearSelect = document.getElementById('scrapYearSelect');
        if (yearSelect) yearSelect.value = String(year);
        setYearMenuOpen(false);
        syncYearPicker();
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

    moreMenu = bindMoreMenu({
        wrapId: 'scrapMoreWrap',
        btnId: 'btnScrapMore',
        menuId: 'scrapMoreMenu',
        onToggle: () => setYearMenuOpen(false),
    });

    document.addEventListener('click', (e) => {
        const yearPicker = document.getElementById('scrapYearPicker');
        if (yearPicker && !yearPicker.contains(e.target)) {
            setYearMenuOpen(false);
        }
    });

    document.getElementById('btnScrapSave')?.addEventListener('click', () => {
        saveMonth();
    });
    document.getElementById('btnScrapExport')?.addEventListener('click', () => {
        moreMenu?.close();
        exportExcel();
    });
    document.getElementById('btnScrapDelete')?.addEventListener('click', () => {
        moreMenu?.close();
        deleteMonth();
    });
    document.getElementById('btnScrapCopy')?.addEventListener('click', () => {
        moreMenu?.close();
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
    syncCategoryButtons();
    await loadFilterOptions();
    await pickDefaultMonth();
    fillYearMonthSelects();
    await loadMonthSheet();
}

export const pageConfig = {
    render: scrapPriceTemplate,
    init,
    destroy() {
        moreMenu?.unbind();
        moreMenu = null;
    },
};
