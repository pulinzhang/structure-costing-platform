import { DRAWER_BACKDROP } from '../../../ui/classes.js?v=12';
/**
 * 废料月度销售价 — 价格矩阵视觉层（非表格填表）
 * 基地锚点 · 净价 Hero · 扣费弱化 · 备注隐式 · 中文极简
 * DOM ID / 字段 / 事件契约保持不变
 */

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../ui/more-menu.js?v=5';

/** 金额展示：固定 2 位小数 + 千分位（输入框用，空值返回 ''） */
export function fmtPrice(value) {
    if (value === null || value === undefined || value === '') return '';
    const fixed = formatDecimalFixed(value, 2, { allowNegative: true });
    return fixed == null ? '' : withThousandsSep(fixed);
}

/** 金额展示：固定 2 位小数（只读净价用，空/无效返回 —） */
export function fmtTelemetry(value) {
    const formatted = fmtPrice(value);
    return formatted === '' ? '—' : formatted;
}

/**
 * 解析金额输入：去掉千分位后规范为 2 位小数字符串；失败返回 null。
 * 提交给后端用字符串，避免 JS Number 尾差。
 */
export function parsePriceInput(raw) {
    if (raw === null || raw === undefined) return null;
    const cleaned = String(raw)
        .trim()
        .replace(/,/g, '')
        .replace(/，/g, '')
        .replace(/\s/g, '');
    if (cleaned === '') return null;
    return parseDecimalInput(cleaned, 2);
}

/** 比较两个金额字符串（已规范为两位小数）；a>b 返回 1，相等 0，否则 -1 */
export function comparePriceStrings(a, b) {
    return compareDecimalStrings(a, b, 2) ?? 0;
}

/** a - b，返回两位小数字符串（可为负） */
export function subtractPriceStrings(a, b) {
    const left = formatDecimalFixed(a, 2, { allowNegative: true });
    const right = formatDecimalFixed(b, 2, { allowNegative: true });
    if (left == null || right == null) return '0.00';
    const toScaled = (s) => {
        const negative = s.startsWith('-');
        const body = negative ? s.slice(1) : s;
        const [i, f = ''] = body.split('.');
        const scaled = BigInt(i || '0') * 100n + BigInt((f + '00').slice(0, 2));
        return negative ? -scaled : scaled;
    };
    const diff = toScaled(left) - toScaled(right);
    const neg = diff < 0n;
    const abs = neg ? -diff : diff;
    const intPart = abs / 100n;
    const frac = abs % 100n;
    return `${neg ? '-' : ''}${intPart.toString()}.${frac.toString().padStart(2, '0')}`;
}

/** 大盘价：次级数字，右对齐 */
const MARKET_INPUT =
    'scrap-cell-input w-full max-w-[9.5rem] ml-auto block bg-transparent border-0 border-b border-transparent ' +
    'text-right text-[12px] font-mono tabular-nums text-ink-muted placeholder:text-ink-faint ' +
    'focus:outline-none focus:border-brand focus:text-ink-muted ' +
    'disabled:opacity-40 transition-[border-color,color] duration-150 px-0 py-0.5';

/** 扣费：更弱，一眼看出是减项，右对齐；聚焦下划线与大盘价同为红色 */
const DEDUCTION_INPUT =
    'scrap-cell-input w-full max-w-[8.5rem] ml-auto block bg-transparent border-0 border-b border-transparent ' +
    'text-right text-[12px] font-mono tabular-nums text-ink-faint placeholder:text-ink-faint ' +
    'focus:outline-none focus:border-brand focus:text-ink-muted ' +
    'disabled:opacity-40 transition-[border-color,color] duration-150 px-0 py-0.5';

/** 备注：默认隐藏，悬停/聚焦/有内容时显现 */
const REMARK_INPUT =
    'scrap-remark w-full bg-transparent border-0 border-b border-transparent ' +
    'text-left text-[11px] text-ink-dim placeholder:text-ink-faint ' +
    'focus:outline-none focus:border-line focus:text-ink-muted ' +
    'disabled:opacity-40 transition-opacity duration-150 px-0 py-0.5';

export function scrapPriceTemplate() {
    return `
        <div class="w-full max-w-[1400px] mx-auto px-6 lg:px-8 py-4">

            <!-- 顶栏 -->
            <div class="flex items-start justify-between gap-6 mb-10">
                <div class="min-w-0 flex items-baseline gap-3 flex-wrap">
                    <h2 class="text-[14px] font-medium text-ink shrink-0">废料月度销售价</h2>
                    <div class="flex items-center gap-1.5" role="group" aria-label="废料类别">
                        <button id="scrapCategorySteelBtn" type="button"
                                class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-brand border border-brand text-ink-onbrand transition-all">
                            钢材料
                        </button>
                        <button id="scrapCategoryAluminumBtn" type="button"
                                class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-transparent border border-line text-ink-dim hover:text-ink transition-all">
                            铝材
                        </button>
                    </div>
                    <p id="scrapMonthBadge" class="text-[12px] font-mono tabular-nums text-ink-dim tracking-wide">—</p>
                    <span id="scrapMonthStatus" class="text-[11px] text-ink-faint"></span>
                </div>
                <div class="flex items-center gap-2 shrink-0 pt-0.5">
                    ${moreMenuShellHtml({
                        wrapId: 'scrapMoreWrap',
                        btnId: 'btnScrapMore',
                        menuId: 'scrapMoreMenu',
                        itemsHtml: [
                            moreMenuItemHtml({ id: 'btnScrapExport', label: '导出' }),
                            moreMenuItemHtml({ id: 'btnScrapCopy', label: '复制月度' }),
                            moreMenuItemHtml({ id: 'btnScrapDelete', label: '删除本月', danger: true }),
                        ].join(''),
                    })}
                    <button id="btnScrapSave"
                            class="inline-flex items-center h-8 px-4 text-[12px] font-semibold bg-brand text-ink-onbrand hover:bg-brand-hover transition-colors">
                        保存
                    </button>
                </div>
            </div>

            <!-- 年份 + 月份时间轴 -->
            <div class="mb-10">
                <div class="flex items-center gap-3 mb-4">
                    <!-- 原生 select 隐藏：供逻辑读写；可见层为深色自定义下拉 -->
                    <select id="scrapYearSelect" class="hidden" aria-hidden="true" tabindex="-1"></select>
                    <div class="relative" id="scrapYearPicker">
                        <button type="button" id="scrapYearTrigger"
                                class="inline-flex items-center gap-1.5 h-7 pl-0 pr-1 text-[13px] font-mono tabular-nums text-ink hover:text-brand transition-colors focus:outline-none"
                                aria-haspopup="listbox" aria-expanded="false" aria-controls="scrapYearMenu">
                            <span id="scrapYearLabel">—</span>
                            <svg class="w-3 h-3 text-ink-dim shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 9l-7 7-7-7"/>
                            </svg>
                        </button>
                        <div id="scrapYearMenu" role="listbox"
                             class="hidden absolute left-0 top-full mt-1 z-[50] min-w-[88px] max-h-56 overflow-y-auto py-1 bg-app-surface border border-line shadow-[0_8px_24px_rgb(var(--overlay)/0.55)]">
                        </div>
                    </div>
                    <select id="scrapMonthSelect" class="hidden" aria-hidden="true"></select>
                    <button id="btnScrapLoad" type="button" class="hidden" tabindex="-1" aria-hidden="true">加载</button>
                </div>
                <div id="scrapMonthChips" class="flex flex-wrap items-end gap-x-5 gap-y-2 min-h-[28px]">
                    <span class="text-[12px] text-ink-faint">加载中…</span>
                </div>
            </div>

            <!-- 价格矩阵 -->
            <div class="relative brabus-bg-grid" id="scrapTableWrap">
                <table class="w-full border-collapse table-fixed">
                    <colgroup>
                        <col class="w-[22%]">
                        <col class="w-[18%]">
                        <col class="w-[16%]">
                        <col class="w-[22%]">
                        <col class="w-[22%]">
                    </colgroup>
                    <thead>
                        <tr class="border-b border-app-surface">
                            <th class="pb-4 pr-6 text-left text-[10px] font-medium text-ink-faint tracking-[0.16em]">基地</th>
                            <th class="pb-4 px-4 text-right text-[10px] font-medium text-ink-faint tracking-[0.16em]">大盘价</th>
                            <th class="pb-4 px-4 text-right text-[10px] font-medium text-ink-faint tracking-[0.16em]">扣费</th>
                            <th class="pb-4 px-4 text-right text-[10px] font-medium text-ink-dim tracking-[0.16em]">净价</th>
                            <th class="pb-4 pl-6 text-left text-[10px] font-medium text-ink-faint tracking-[0.16em]"></th>
                        </tr>
                    </thead>
                    <tbody id="scrapPriceTableBody">
                    </tbody>
                </table>
                <div id="scrapLoading"
                     class="hidden absolute inset-0 bg-app-main/65 flex items-center justify-center">
                    <div class="w-5 h-5 border border-line border-brand rounded-full animate-spin"></div>
                </div>
            </div>

            <div class="mt-10 pt-5 border-t border-line-subtle flex items-center justify-between gap-4">
                <span id="scrapFooterMeta" class="text-[11px] text-ink-faint tracking-[0.08em]">—</span>
                <span id="scrapFooterHint" class="text-[11px] text-ink-faint text-right"></span>
            </div>
        </div>

        <!-- 复制月度：紧凑「源月 → 目标月」面板（保留全部 DOM ID） -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="scrapCopyBackdrop" style="display:none"></div>
        <div id="scrapCopyDrawer"
             class="fixed left-1/2 top-1/2 z-[85] w-[420px] max-w-[calc(100vw-2rem)] h-[540px] max-h-[calc(100vh-2rem)]
                    -translate-x-1/2 -translate-y-1/2 opacity-0 scale-95
                    bg-app-main border border-line-subtle flex flex-col overflow-hidden
                    transition-all duration-300 ease-out"
             style="display:none;">
            <div class="px-5 py-4 flex items-center justify-between shrink-0 border-b border-app-surface">
                <h5 class="text-[13px] font-medium text-ink">复制月度</h5>
                <button type="button" id="closeScrapCopyDrawer"
                        class="flex items-center justify-center w-8 h-8 text-ink-dim hover:text-ink transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 overflow-y-auto px-5 py-5">
                <!-- 隐藏源月字段，供现有逻辑读取 -->
                <input type="hidden" id="copySourceYear" value="">
                <input type="hidden" id="copySourceMonth" value="">

                <!-- 源月份 -->
                <div class="mb-1">
                    <p class="text-[11px] text-ink-dim">源月份</p>
                    <p id="copyFromDisplay" class="mt-2 text-[22px] font-mono tabular-nums text-ink tracking-wide">—</p>
                    <p id="copyFromMeta" class="mt-1.5 text-[11px] text-ink-dim">—</p>
                </div>

                <div class="my-5 flex justify-center text-ink-faint text-[16px] leading-none" aria-hidden="true">↓</div>

                <!-- 目标月份 -->
                <div class="mb-6">
                    <p class="text-[11px] text-ink-dim">目标月份</p>
                    <div class="mt-2 flex items-baseline gap-2">
                        <input id="copyTargetYear" type="number"
                               class="w-[4.5rem] bg-transparent border-0 border-b border-line px-0 py-1
                                      text-[22px] font-mono tabular-nums text-ink tracking-wide
                                      focus:outline-none focus:border-brand rounded-none">
                        <span class="text-[18px] text-ink-faint font-mono">·</span>
                        <input id="copyTargetMonth" type="number" min="1" max="12"
                               class="w-12 bg-transparent border-0 border-b border-line px-0 py-1
                                      text-[22px] font-mono tabular-nums text-ink tracking-wide
                                      focus:outline-none focus:border-brand rounded-none">
                    </div>
                    <p id="copyToMeta" class="mt-2 text-[11px] text-ink-dim">尚未维护</p>
                    <div id="copyOverwriteWarn" class="hidden mt-3 space-y-1">
                        <p class="text-[12px] text-danger">⚠ 该月份已有数据</p>
                        <p class="text-[11px] text-danger">复制将覆盖现有数据</p>
                    </div>
                </div>

                <!-- 复制内容（轻量） -->
                <div class="pt-4 border-t border-line-subtle">
                    <p class="text-[11px] text-ink-faint mb-3">将复制以下内容</p>
                    <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-ink-dim">
                        <span>大盘价</span>
                        <span>扣费</span>
                        <span>净价</span>
                        <span>备注</span>
                    </div>
                </div>
            </div>

            <div class="px-5 py-4 border-t border-app-surface flex items-center justify-between gap-3 shrink-0 bg-app-main">
                <button type="button" id="cancelScrapCopy"
                        class="h-8 px-2 text-[12px] text-ink-muted hover:text-ink transition-colors shrink-0">
                    取消
                </button>
                <button type="button" id="confirmScrapCopy"
                        class="h-8 px-4 text-[12px] font-semibold bg-brand text-ink-onbrand hover:bg-brand-hover transition-colors shrink-0 whitespace-nowrap">
                    复制
                </button>
            </div>
        </div>
    `;
}

/**
 * @param {Array<{location:string, market_price?:number|null, deduction_fee?:number|null, net_price?:number|null, remark?:string|null}>} items
 * @param {{ editable: boolean }} opts
 */
export function renderScrapRows(items, { editable }) {
    if (!items || items.length === 0) {
        return `
            <tr>
                <td colspan="5" class="py-20 text-center text-[12px] text-ink-faint">暂无数据</td>
            </tr>
        `;
    }

    return items
        .map((item, index) => {
            const location = esc(item.location);
            const market =
                item.market_price === null || item.market_price === undefined
                    ? ''
                    : fmtPrice(item.market_price);
            const deduction =
                item.deduction_fee === null || item.deduction_fee === undefined
                    ? ''
                    : fmtPrice(item.deduction_fee);
            const net =
                item.net_price === null || item.net_price === undefined
                    ? '—'
                    : fmtTelemetry(item.net_price);
            const remark = item.remark ? esc(item.remark) : '';
            const hasRemark = Boolean(remark);
            const remarkVisibility = hasRemark
                ? 'opacity-100'
                : 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100';
            const disabledAttr = editable ? '' : 'disabled';

            return `
                <tr class="group border-b border-line-subtle hover:bg-ink/[0.012] transition-colors"
                    data-row-index="${index}" data-location="${location}">
                    <td class="py-5 pr-6 whitespace-nowrap align-middle">
                        <div class="flex items-center gap-3">
                            <span class="w-px h-4 bg-app-elevated group-hover:bg-brand transition-colors shrink-0"></span>
                            <span class="text-[15px] font-medium text-ink tracking-wide">${location}</span>
                        </div>
                    </td>
                    <td class="py-5 px-4 text-right align-middle">
                        <input type="text" inputmode="decimal" autocomplete="off"
                               class="scrap-market ${MARKET_INPUT}"
                               data-field="market_price"
                               value="${market}"
                               placeholder="—"
                               ${disabledAttr}>
                    </td>
                    <td class="py-5 px-4 text-right align-middle">
                        <input type="text" inputmode="decimal" autocomplete="off"
                               class="scrap-deduction ${DEDUCTION_INPUT}"
                               data-field="deduction_fee"
                               value="${deduction}"
                               placeholder="—"
                               ${disabledAttr}>
                    </td>
                    <td class="py-5 px-4 text-right align-middle">
                        <span class="scrap-net inline-block min-w-[7rem] text-right text-[17px] leading-none font-mono font-semibold tabular-nums text-ink tracking-wide">
                            ${net}
                        </span>
                    </td>
                    <td class="py-5 pl-6 align-middle">
                        <div class="${remarkVisibility} transition-opacity duration-150">
                            <input type="text"
                                   class="${REMARK_INPUT}"
                                   data-field="remark"
                                   value="${remark}"
                                   placeholder="备注"
                                   maxlength="200"
                                   ${disabledAttr}>
                        </div>
                    </td>
                </tr>
            `;
        })
        .join('');
}

/**
 * 年份内 1–12 月时间轴
 * @param {Array<{year:number, month:number, is_complete:boolean, filled_count:number}>} months
 * @param {{year:number, month:number}} selected
 */
export function renderMonthChips(months, selected) {
    const year = selected.year;
    const byMonth = new Map(
        (months || [])
            .filter((m) => m.year === year)
            .map((m) => [m.month, m])
    );

    return Array.from({ length: 12 }, (_, i) => {
        const month = i + 1;
        const meta = byMonth.get(month);
        const isActive = selected.month === month;
        const hasData = Boolean(meta);
        const label = fmtMonth(month);

        let cls =
            'scrap-month-chip relative pb-1.5 text-[12px] font-mono tabular-nums transition-colors ';
        if (isActive) {
            cls += 'text-ink';
        } else if (hasData) {
            cls += 'text-ink-muted hover:text-ink';
        } else {
            cls += 'text-ink-faint hover:text-ink-dim';
        }

        const underline = isActive
            ? '<span class="absolute left-0 right-0 bottom-0 h-px bg-brand"></span>'
            : '';
        const title = meta
            ? `${fmtPeriod(year, month)} · ${meta.filled_count}/${meta.required_count ?? meta.filled_count}`
            : fmtPeriod(year, month);

        return `
            <button type="button"
                    class="${cls}"
                    data-year="${year}"
                    data-month="${month}"
                    title="${title}">
                ${label}${underline}
            </button>
        `;
    }).join('');
}
