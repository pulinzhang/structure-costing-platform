/**
 * Brabus HUD 原语（色走 token class）。
 * 交互钩子名（die-type-select）留在类串首位。
 * 变体用同一前缀拼，禁止再加零差 alias。
 */

const TH_CELL = 'px-2 py-2 text-[9px]';
const OPS_ICON_BASE =
    'inline-flex items-center justify-center w-7 h-7 rounded-sm text-ink-faint hover:bg-app-rowhover opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all';
const KPI_PAD = 'p-3.5';
const PANEL_HEAD = 'px-4 py-2.5 bg-app-deep';

/* —— 壳 / KPI —— */

export const HUD_SHELL =
    'bg-app-hud border border-line-hud overflow-hidden w-full max-w-full shadow-[var(--shadow-hud)]';

export const HUD_BAND =
    'px-5 pt-4 pb-3.5 border-b border-line-subtle bg-gradient-to-br from-app-main via-app-hud to-app-deep';

export const HUD_KPI_FOCUS =
    `bg-gradient-to-b from-brand-hud/15 to-app-deep border border-brand-hud/50 ${KPI_PAD} relative overflow-hidden`;

export const HUD_KPI_AUX =
    `bg-app-main/80 border border-line-hud ${KPI_PAD}`;

export const HUD_LED = 'hud-led';

export const HUD_FILTER =
    'hud-filter h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted appearance-none cursor-pointer focus:outline-none focus:border-brand-active rounded-[2px] transition-all';

export const HUD_INPUT =
    'h-9 px-3 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-faint rounded-[2px] focus:outline-none focus:border-brand-active transition-all';

/* —— 筛选 / 胶囊 —— */

export const FILTER_STRIP =
    'flex items-center justify-between gap-4 bg-app-deep border border-line-hud px-4 py-2.5 rounded-[2px] font-mono text-[11px] shadow-[inset_0_1px_0_rgb(var(--text-main)/0.02)]';

export const FILTER_ADVANCED =
    'hidden mt-3 pt-3 border-t border-line-hud';

export const FILTER_LABEL =
    'block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.14em]';

export const CAPSULE_IDLE =
    'bg-app-elevated border border-line-hud text-ink-muted px-2.5 py-1 rounded-[2px]';

const CAPSULE_ACTIVE =
    'bg-app-elevated border border-line-hud text-ink font-bold px-2.5 py-1 rounded-[2px]';

export function capsuleClass(isActive) {
    return isActive ? CAPSULE_ACTIVE : CAPSULE_IDLE;
}

/**
 * @param {string} id
 * @param {string} label
 * @param {boolean | { required?: boolean, emptyLabel?: string, widthClass?: string }} [requiredOrOpts]
 * @param {string} [emptyLabelArg]
 */
export function filterSelect(id, label, requiredOrOpts = false, emptyLabelArg) {
    const opts = requiredOrOpts && typeof requiredOrOpts === 'object'
        ? requiredOrOpts
        : { required: Boolean(requiredOrOpts), emptyLabel: emptyLabelArg };
    const required = Boolean(opts.required);
    const emptyLabel = opts.emptyLabel ?? (required ? '请选择' : '全部');
    const widthClass = opts.widthClass || 'w-32';
    const mark = required ? '<span class="text-brand">*</span>' : '';
    return `<label class="space-y-1">
        <span class="${FILTER_LABEL}">${label}${mark}</span>
        <select id="${id}" class="${widthClass} ${HUD_FILTER}">
            <option value="">${emptyLabel}</option>
        </select>
    </label>`;
}

/**
 * @param {string} id
 * @param {string} label
 * @param {string} [placeholder]
 * @param {{ widthClass?: string }} [opts]
 */
export function filterInput(id, label, placeholder = '', opts = {}) {
    const widthClass = opts.widthClass || 'w-32';
    return `<label class="space-y-1">
        <span class="${FILTER_LABEL}">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="${widthClass} ${HUD_INPUT}">
    </label>`;
}

export function filterInputWithDatalist(id, label, datalistId, opts = {}) {
    const widthClass = opts.widthClass || 'w-44';
    const placeholder = opts.placeholder || '输入搜索或选择牌号';
    const disabledAttr = opts.disabled ? ' disabled' : '';
    const disabledClass = opts.disabled ? ' disabled:opacity-50 disabled:cursor-not-allowed' : '';
    return `<label class="space-y-1">
        <span class="${FILTER_LABEL}">${label}</span>
        <input type="text" id="${id}" list="${datalistId}"${disabledAttr}
               class="${widthClass} ${HUD_INPUT}${disabledClass}"
               placeholder="${placeholder}">
        <datalist id="${datalistId}"></datalist>
    </label>`;
}

/* —— 密表 —— */

export const TR_HUD =
    'group relative font-mono text-[11px] border-b border-line-subtle hover:bg-app-rowhover data-[current=1]:bg-app-rowhover transition-colors duration-100';

export const ROW_LED =
    'absolute left-0 top-0 bottom-0 w-[2px] bg-brand-hud opacity-0 group-hover:opacity-70 group-data-[current=1]:opacity-100 transition-opacity';

export const TH_ROW =
    'border-b border-line-subtle bg-app-hud/95';

export const TH_TEXT =
    `${TH_CELL} text-left font-medium tracking-[0.08em] text-ink-faint`;

export const TH_NUM =
    `${TH_CELL} text-right font-medium tracking-[0.06em] text-ink-faint`;

export const TH_KEY =
    `${TH_CELL} text-left font-medium tracking-[0.08em] text-ink-muted`;

export const TH_FOCUS =
    `${TH_CELL} text-right font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10`;

export const OPS_TH =
    'p-0 w-9 sticky right-0 z-[3] bg-app-hud';

export const OPS_TD =
    'px-1 py-2 text-center align-middle sticky right-0 z-[2] brabus-bg-grid group-hover:bg-app-rowhover group-data-[current=1]:bg-app-rowhover';

export const OPS_ICON =
    `${OPS_ICON_BASE} hover:text-ink`;

export const OPS_ICON_DANGER =
    `${OPS_ICON_BASE} hover:text-danger`;

/* —— 抽屉 —— */

export const DRAWER_BACKDROP =
    'fixed inset-0 z-[80] bg-overlay/70 backdrop-blur-sm';

export const DRAWER_SHELL =
    'fixed inset-y-0 right-0 z-[85] max-w-[95vw] bg-app-main border-l border-line flex flex-col shadow-[var(--shadow-drawer)]';

export const DRAWER_CLOSE =
    'flex items-center justify-center w-8 h-8 rounded-[2px] text-ink-dim hover:text-ink hover:bg-brand transition-all';

/* —— 上传 —— */

export const UPLOAD_LABEL =
    'block text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-dim';

export const UPLOAD_INPUT =
    'appearance-none w-full h-[42px] pl-3.5 pr-11 bg-app-deep border border-line rounded-[2px] text-[11px] text-ink-muted cursor-pointer transition-all duration-150 hover:border-ink-dim focus:outline-none focus:border-brand focus:text-ink';

export const UPLOAD_DROPZONE =
    'border border-dashed border-line bg-app-deep rounded-[2px] px-6 py-7 text-center cursor-pointer transition-all duration-200 hover:border-ink-dim hover:bg-app-hud data-[dropzone-state=drag]:border-brand data-[dropzone-state=drag]:border-solid data-[dropzone-state=drag]:bg-brand/10 data-[dropzone-state=file]:border-brand data-[dropzone-state=file]:border-solid data-[dropzone-state=file]:bg-brand/10';

/* —— 按钮 —— */

export const BTN_GHOST =
    'inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 py-1.5 rounded-[2px] text-[11px] font-medium transition-all duration-200 hover:text-brand-hud hover:border-brand-hud/50 hover:bg-brand-hud/10';

export const BTN_SOLID =
    'inline-flex items-center gap-1.5 bg-brand text-ink-onbrand px-4 py-2 text-[11px] font-semibold rounded-[2px] hover:bg-brand-hover transition-all';

export const BTN_SOLID_DANGER =
    'inline-flex items-center gap-1.5 bg-danger text-ink-onbrand px-4 py-2 text-[11px] font-semibold rounded-[2px] hover:bg-brand-hover transition-all';

export const BTN_HUD_SAVE =
    'bg-brand-hud hover:bg-brand text-ink-onbrand px-5 py-1.5 text-xs font-semibold';

export const BTN_HUD_CREATE =
    'inline-flex items-center gap-1.5 bg-brand-hud hover:bg-brand text-ink-onbrand px-3 py-1.5 text-[11px] font-semibold rounded-[2px] transition-all';

export const BTN_HUD_CHIP =
    'h-8 px-4 bg-brand-hud hover:bg-brand text-ink-onbrand text-xs font-semibold';

export const BTN_ABORT =
    'h-7 px-4 text-[10px] bg-brand-hover hover:bg-danger text-ink-onbrand font-medium rounded-[2px] transition-colors disabled:opacity-30 disabled:cursor-not-allowed';

export const BTN_UPLOAD_SUBMIT =
    'inline-flex items-center gap-2 bg-brand text-ink-onbrand border border-brand px-7 h-11 rounded-[2px] text-[11px] font-bold tracking-[0.1em] transition-all duration-150 hover:bg-brand-hover hover:border-brand-hover disabled:bg-app-elevated disabled:border-line disabled:text-ink-dim disabled:cursor-not-allowed disabled:opacity-30 disabled:pointer-events-none';

export const BTN_FILTER_SEARCH =
    'inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-[2px] text-ink border border-brand/40 bg-gradient-to-b from-[rgb(var(--filter-search-from))] to-[rgb(var(--filter-search-to))] shadow-[0_1px_3px_rgb(var(--overlay)/0.4),inset_0_1px_0_rgb(var(--brabus-red)/0.1)] hover:text-ink transition-all duration-200';

export const BTN_FILE_SELECT =
    'inline-flex items-center gap-1.5 bg-app-deep text-ink-dim border border-line px-4 h-9 rounded-[2px] text-[10px] font-semibold tracking-[0.08em] transition-all duration-150 hover:border-brand hover:text-brand';

export const BTN_SAVE_DEFAULT =
    'inline-flex items-center justify-center gap-2 max-w-[260px] h-10 px-8 bg-app-main border border-app-elevated rounded-[2px] text-ink-dim text-[11px] font-medium tracking-[0.15em] uppercase cursor-pointer transition-all duration-200 hover:bg-brand hover:border-brand hover:text-ink-onbrand';

export const BTN_SAVE_ACTIVE =
    'inline-flex items-center justify-center gap-2 w-full h-10 bg-app-surface border border-brand rounded-[2px] text-ink text-[11px] font-medium tracking-[0.15em] uppercase cursor-pointer transition-all duration-200 hover:bg-brand hover:text-ink-onbrand';

export const BTN_PAGINATION_CURRENT =
    'flex items-center justify-center w-6 h-6 text-[10px] bg-brand-hud text-ink-onbrand';

export const BTN_MORE =
    'w-8 h-8 flex items-center justify-center text-ink-faint hover:text-ink transition-colors rounded-[2px]';

/* —— 零件档案 / 面板 —— */

export const DIE_TYPE_SELECT =
    'die-type-select appearance-none h-7 pl-2.5 pr-8 w-auto min-w-[9rem] bg-app-deep border border-transparent rounded-[2px] text-[10px] font-normal tracking-[0.08em] text-ink-muted cursor-pointer outline-none transition-all duration-150 hover:border-line hover:bg-app-hud hover:text-ink-muted focus:border-brand focus:bg-app-hud';

export const SKETCH_THUMBNAIL =
    'relative w-9 h-9 rounded-[2px] bg-app-main border border-line overflow-hidden cursor-pointer shrink-0 flex items-center justify-center transition-colors duration-200 hover:border-brand group/sketch';

export const SKETCH_PLACEHOLDER =
    'w-9 h-9 rounded-[2px] bg-app-elevated border border-dashed border-line flex items-center justify-center shrink-0 text-ink-dim';

export const ZOOM_OVERLAY =
    'absolute inset-0 bg-overlay/65 flex items-center justify-center opacity-0 transition-opacity duration-200 rounded-[2px] group-hover/sketch:opacity-100 text-ink [&_svg]:w-3.5 [&_svg]:h-3.5 [&_svg]:text-ink';

export const BRABUS_PANEL =
    'bg-app-surface border border-line overflow-hidden rounded-[2px]';

export const BRABUS_PANEL_HEADER =
    `${PANEL_HEAD} border-b border-line-subtle`;

export const BRABUS_SECTION_HEADER =
    `${BRABUS_PANEL_HEADER} border-t border-line`;

export const BRABUS_TABLE_WRAPPER =
    'bg-app-main border border-line';
