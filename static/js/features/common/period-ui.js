/**
 * 生失效展示 / 年+月筛 / SOP 上传说明（对齐项目一览 fillYearMonthSelects）。
 */

export const SOP_INTRO =
    '本页只导入 SOP（该项目第一次标准化投产）。投产使用后换号、新旧并存，必须走工程变更，不要在本页操作。';

export const SOP_EXISTING =
    '该项目已有 SOP。再导只更新文件里已有对象的属性，不会删除未出现的行。文件里出现新号将整单拒绝。换号请走工程变更。';

export function fmtPeriodRange(effectiveYear, effectiveMonth, expiryYear, expiryMonth) {
    const start = typeof fmtPeriod === 'function'
        ? fmtPeriod(effectiveYear, effectiveMonth)
        : '';
    if (!start) return '—';
    const end = expiryYear && expiryMonth
        ? (typeof fmtPeriod === 'function' ? fmtPeriod(expiryYear, expiryMonth) : '')
        : '未结束';
    return `${start} – ${end}`;
}

/** 开始月、到期月都有 = 该树已被后续工程变更截到失效月，列表用红字。 */
export function hasClosedPeriod(effectiveYear, effectiveMonth, expiryYear, expiryMonth) {
    return Boolean(effectiveYear && effectiveMonth && expiryYear && expiryMonth);
}

export function wallClockYearMonth() {
    const clock = new Date();
    return { year: clock.getFullYear(), month: clock.getMonth() + 1 };
}

export function monthOptionsHtml(selected) {
    const items = [];
    for (let month = 1; month <= 12; month += 1) {
        const label = typeof fmtMonth === 'function'
            ? fmtMonth(month)
            : `${String(month).padStart(2, '0')}月`;
        const isSelected = Number(selected) === month ? ' selected' : '';
        items.push(`<option value="${month}"${isSelected}>${label}</option>`);
    }
    return items.join('');
}

export function yearOptionsHtml(selected, extraYears) {
    const years = new Set(extraYears || []);
    const current = selected || new Date().getFullYear();
    years.add(current);
    for (let year = current - 3; year <= current + 8; year += 1) {
        years.add(year);
    }
    return [...years].sort((a, b) => a - b).map((year) => {
        const label = typeof fmtYear === 'function' ? fmtYear(year) : `${year}年`;
        const isSelected = Number(selected) === year ? ' selected' : '';
        return `<option value="${year}"${isSelected}>${label}</option>`;
    }).join('');
}

export function fillYearMonthSelects(prefix, effectiveYear, effectiveMonth, expiryYear, expiryMonth) {
    const extra = [effectiveYear, expiryYear].filter(Boolean);
    const effYear = document.getElementById(`${prefix}EffectiveYear`);
    const effMonth = document.getElementById(`${prefix}EffectiveMonth`);
    const expYear = document.getElementById(`${prefix}ExpiryYear`);
    const expMonth = document.getElementById(`${prefix}ExpiryMonth`);
    if (effYear) effYear.innerHTML = yearOptionsHtml(effectiveYear, extra);
    if (effMonth) effMonth.innerHTML = monthOptionsHtml(effectiveMonth);
    if (expYear) {
        expYear.innerHTML = `<option value="">尚未失效</option>${yearOptionsHtml(expiryYear, extra)}`;
        expYear.value = expiryYear ? String(expiryYear) : '';
    }
    if (expMonth) {
        expMonth.innerHTML = `<option value="">—</option>${monthOptionsHtml(expiryMonth)}`;
        expMonth.value = expiryMonth ? String(expiryMonth) : '';
    }
    if (effYear && effectiveYear) effYear.value = String(effectiveYear);
    if (effMonth && effectiveMonth) effMonth.value = String(effectiveMonth);
}

export function fillAsOfSelects(prefix, year, month) {
    const yearEl = document.getElementById(`${prefix}Year`);
    const monthEl = document.getElementById(`${prefix}Month`);
    if (yearEl) {
        yearEl.innerHTML = yearOptionsHtml(year);
        yearEl.value = String(year);
    }
    if (monthEl) {
        monthEl.innerHTML = monthOptionsHtml(month);
        monthEl.value = String(month);
    }
}

export function readPeriod(prefix) {
    const effectiveYear = Number(document.getElementById(`${prefix}EffectiveYear`)?.value || 0);
    const effectiveMonth = Number(document.getElementById(`${prefix}EffectiveMonth`)?.value || 0);
    const expiryYearRaw = document.getElementById(`${prefix}ExpiryYear`)?.value || '';
    const expiryMonthRaw = document.getElementById(`${prefix}ExpiryMonth`)?.value || '';
    const expiryYear = expiryYearRaw ? Number(expiryYearRaw) : null;
    const expiryMonth = expiryMonthRaw ? Number(expiryMonthRaw) : null;
    if (!effectiveYear || !effectiveMonth) {
        showToast('请填写生效年、月', 'warning');
        return null;
    }
    if ((expiryYear && !expiryMonth) || (!expiryYear && expiryMonth)) {
        showToast('失效年与失效月必须同空或同有', 'warning');
        return null;
    }
    return {
        effective_year: effectiveYear,
        effective_month: effectiveMonth,
        expiry_year: expiryYear,
        expiry_month: expiryMonth,
    };
}

export function readAsOf(prefix) {
    const year = Number(document.getElementById(`${prefix}Year`)?.value || 0);
    const month = Number(document.getElementById(`${prefix}Month`)?.value || 0);
    const includeExpired = Boolean(document.getElementById(`${prefix}IncludeExpired`)?.checked);
    if (!year || !month) {
        showToast('请选择查看年、月', 'warning');
        return null;
    }
    return { year, month, include_expired: includeExpired };
}

const AS_OF_FILTER_STYLES = {
    parts: {
        wrap: 'space-y-1',
        label: 'block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]',
        select:
            'w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors',
    },
    die: {
        wrap: 'flex flex-col gap-1',
        label: 'text-[10px] text-[#555555] tracking-wider',
        select:
            'h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]',
    },
};

export function asOfFilterHtml(prefix, options = {}) {
    const includeExpired = options.includeExpired === true;
    const style = AS_OF_FILTER_STYLES[options.variant] || AS_OF_FILTER_STYLES.die;
    const checkbox = includeExpired
        ? `<label class="flex items-center gap-1.5 h-9 mt-5">
            <input id="${prefix}IncludeExpired" type="checkbox"
                   class="w-3.5 h-3.5 accent-[#d32f2f]">
            <span class="text-[10px] text-[#8E8E93]">含已失效</span>
        </label>`
        : '';
    return `
        <label class="${style.wrap}">
            <span class="${style.label}">查看年</span>
            <select id="${prefix}Year" class="${style.select}"></select>
        </label>
        <label class="${style.wrap}">
            <span class="${style.label}">查看月</span>
            <select id="${prefix}Month" class="${style.select}"></select>
        </label>
        ${checkbox}
    `;
}

export function periodEditorHtml(prefix) {
    const inputClass = 'w-full h-8 px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]';
    return `
        <div class="grid grid-cols-2 gap-2">
            <label class="flex flex-col gap-1">
                <span class="text-[10px] text-[#555555]">生效年</span>
                <select id="${prefix}EffectiveYear" class="${inputClass}"></select>
            </label>
            <label class="flex flex-col gap-1">
                <span class="text-[10px] text-[#555555]">生效月</span>
                <select id="${prefix}EffectiveMonth" class="${inputClass}"></select>
            </label>
            <label class="flex flex-col gap-1">
                <span class="text-[10px] text-[#555555]">失效年</span>
                <select id="${prefix}ExpiryYear" class="${inputClass}"></select>
            </label>
            <label class="flex flex-col gap-1">
                <span class="text-[10px] text-[#555555]">失效月</span>
                <select id="${prefix}ExpiryMonth" class="${inputClass}"></select>
            </label>
        </div>
    `;
}

export function sopBannerHtml() {
    return `
        <div id="sopBanner" class="mx-5 mt-4 mb-0 px-4 py-3 border border-[#2c2c2c] bg-[#161616] text-[11px] text-[#c8c8c8] leading-relaxed">
            <p class="text-[#ffb74d] mb-1">${SOP_INTRO}</p>
            <p id="sopBannerDetail" class="text-[#888888] mb-0">选项目后显示本文件按项目 SOP 时段。</p>
        </div>
    `;
}

export function renderSopBanner({ hasSop, startLabel, endLabel }) {
    const detail = document.getElementById('sopBannerDetail');
    if (!detail) return;
    if (hasSop) {
        detail.textContent = SOP_EXISTING;
        return;
    }
    if (startLabel) {
        detail.textContent = `本文件按项目 SOP 时段：${startLabel} – ${endLabel || '未结束'}。时段来自项目档案，本页不能改。`;
        return;
    }
    detail.textContent = '本文件按项目档案登记的开始月–结束月写入。时段本页不能改。';
}

export async function loadProjectPeriod(location, vehicleModel) {
    if (!location || !vehicleModel) return null;
    try {
        const res = await HttpClient.get('/api/masterdata/vehicle-models');
        const items = res.data?.items || [];
        const row = items.find((item) =>
            item.location === location && item.vehicle_model === vehicleModel
        );
        if (!row) return null;
        return {
            startLabel: typeof fmtPeriod === 'function'
                ? fmtPeriod(row.effective_year, row.effective_month)
                : '',
            endLabel: row.expiry_year && row.expiry_month
                ? (typeof fmtPeriod === 'function' ? fmtPeriod(row.expiry_year, row.expiry_month) : '')
                : '未结束',
        };
    } catch (_) {
        return null;
    }
}

/** 一事一议列表：年度筛默认当年（可改 / 可清空）。 */
export const EXPORT_YEAR_MONTH_REQUIRED_MESSAGE =
    '导出须选定年度和月份（一事一议按月定价）';

export function selectDefaultYear(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const year = String(wallClockYearMonth().year);
    const escape = typeof esc === 'function' ? esc : (value) => String(value ?? '');
    const label = typeof fmtYear === 'function' ? fmtYear(year) : `${year}年`;
    if (![...select.options].some((opt) => opt.value === year)) {
        select.insertAdjacentHTML(
            'beforeend',
            `<option value="${escape(year)}">${escape(label)}</option>`,
        );
    }
    select.value = year;
}

/** 一事一议导出：必须锁年 + 月。通过返回 true。 */
export function requireExportYearMonth(filters) {
    if (!filters?.year || !filters?.month) {
        if (typeof showToast === 'function') {
            showToast(EXPORT_YEAR_MONTH_REQUIRED_MESSAGE, 'warning');
        }
        return false;
    }
    return true;
}
