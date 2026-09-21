/**
 * HUD 表上指标卡：靶心 / 辅卡 / 待办切态。
 * 各页只传标题、数字槽、脚注；禁止再复制扫光线与 HUD_KPI_* 壳。
 */

import { HUD_KPI_FOCUS, HUD_KPI_AUX } from './classes.js?v=12';

const SCANLINE =
    'absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-brand-hud to-transparent hud-kpi-line-glow';
const PULSE_DOT = 'w-2 h-2 rounded-full bg-brand-hud animate-pulse hud-kpi-dot-glow';
const BTN_CHROME =
    'text-left w-full relative overflow-hidden group transition-all duration-200 cursor-pointer focus:outline-none';

const SHELL_FOCUS = `hud-kpi-card-glow ${HUD_KPI_FOCUS}`;
const SHELL_AUX = `${HUD_KPI_AUX} backdrop-blur-sm`;
const SHELL_OK = `hud-kpi-aux-inset ${HUD_KPI_AUX} backdrop-blur-sm`;
const SHELL_WARN = 'bg-app-main/80 border border-warn/30 p-3.5 relative overflow-hidden backdrop-blur-sm';

const TITLE_FOCUS = 'text-brand-hud text-[10px] font-bold tracking-widest';
const TITLE_AUX = 'text-ink-faint text-[10px] tracking-wider';
const TITLE_AUX_TODO = 'text-ink-faint text-[10px] font-bold tracking-widest';
const TITLE_WARN = 'text-warn/80 text-[10px] tracking-wider';
const TITLE_OK = 'text-ok text-[10px] font-bold tracking-widest';

const VALUE_FOCUS =
    'text-[26px] font-black text-brand-hud font-mono mt-1 tracking-tight tabular-nums leading-none hud-kpi-num-glow';
const VALUE_AUX =
    'text-[22px] font-black text-ink mt-1 tracking-tight tabular-nums leading-none';
const VALUE_TEXT = 'text-[14px] font-bold text-ink mt-1 truncate';
const VALUE_TODO_IDLE =
    'text-[26px] font-black text-ink-dim font-mono mt-1 tracking-tight tabular-nums leading-none';
const VALUE_TODO_OK =
    'text-[26px] font-black text-ok font-mono mt-1 tracking-tight tabular-nums leading-none';
const VALUE_WELD_ALERT =
    'text-[26px] font-black text-brand-hud font-mono mt-1 tracking-tight tabular-nums leading-none';

const UNIT_FOCUS = 'text-[10px] text-brand-hud/70 ml-1 font-bold';
const UNIT_AUX = 'text-[10px] text-ink-faint ml-1 font-bold';

const META_FOCUS = 'text-[9px] font-mono text-brand-hud/60 mt-2';
const META_AUX = 'text-[9px] font-mono text-ink-dim mt-2';
const HINT_ALERT = 'text-[9px] font-mono text-brand-hud/60 mt-2';
const HINT_OK = 'text-[9px] font-mono text-ok/70 mt-2';
const HINT_AUX = 'text-[9px] font-mono text-ink-faint mt-2';

const SHELL_FOCUS_PARTS = SHELL_FOCUS.split(/\s+/).filter(Boolean);
const SHELL_AUX_PARTS = SHELL_AUX.split(/\s+/).filter(Boolean);
const SHELL_OK_PARTS = SHELL_OK.split(/\s+/).filter(Boolean);
const RING_PARTS = ['ring-1', 'border-brand-hud/40'];
const HOVER_ALERT = ['hover:border-brand-hud/80', 'focus-visible:border-brand-hud'];
const HOVER_OK = ['hover:border-line-hud', 'focus-visible:border-ok/40'];

function titleClass({ variant, tone, as }) {
    if (variant === 'focus') return TITLE_FOCUS;
    if (tone === 'warn') return TITLE_WARN;
    if (as === 'button') return TITLE_AUX_TODO;
    return TITLE_AUX;
}

function valueClass({ variant, valueKind, as }) {
    if (valueKind === 'text') return VALUE_TEXT;
    if (variant === 'focus') return VALUE_FOCUS;
    if (as === 'button') return VALUE_TODO_IDLE;
    return VALUE_AUX;
}

function footHtml(spec, isFocus) {
    if (spec.rows && spec.rows.length) {
        const lines = spec.rows.map((row) => `
                    <div class="flex items-center justify-between gap-2">
                        <span>${row.label}</span>
                        <span class="text-ink-muted tabular-nums whitespace-nowrap">${row.valueHtml}</span>
                    </div>`).join('');
        return `<div class="text-[9px] font-mono text-ink-dim mt-2 space-y-1.5">${lines}</div>`;
    }
    if (spec.footer && spec.footer.length) {
        const cells = spec.footer.map((row) => `
                    <span>${row.label}</span>
                    <span class="text-ink-muted tabular-nums">${row.valueHtml}</span>`).join('');
        return `<div class="text-[9px] font-mono text-ink-dim mt-2 flex items-center justify-between gap-2">${cells}</div>`;
    }
    if (spec.metaHtml != null || spec.meta != null) {
        const metaId = spec.metaId ? ` id="${spec.metaId}"` : '';
        const body = spec.metaHtml != null ? spec.metaHtml : spec.meta;
        const cls = isFocus ? META_FOCUS : META_AUX;
        return `<div${metaId} class="${cls}">${body}</div>`;
    }
    return '';
}

function valueBlockHtml(spec, variant) {
    const rowsOnly = spec.rows && spec.rows.length
        && spec.valueHtml == null
        && !spec.valueId
        && !spec.valueWrapId
        && !spec.unit;
    if (rowsOnly) return '';
    if (spec.valueHtml == null && !spec.valueId && !spec.valueWrapId && !spec.unit) return '';
    const wrapId = spec.valueWrapId || spec.valueId;
    const wrapAttr = wrapId ? ` id="${wrapId}"` : '';
    const unitCls = variant === 'focus' ? UNIT_FOCUS : UNIT_AUX;
    const unit = spec.unit ? `<span class="${unitCls}">${spec.unit}</span>` : '';
    const inner = spec.valueHtml == null ? '' : spec.valueHtml;
    return `<div${wrapAttr} class="${valueClass({
        variant,
        valueKind: spec.valueKind,
        as: spec.as,
    })}">${inner}${unit}</div>`;
}

/**
 * @param {{
 *   variant?: 'focus' | 'aux',
 *   tone?: 'warn',
 *   title: string,
 *   titleId?: string,
 *   valueHtml?: string,
 *   valueId?: string,
 *   valueWrapId?: string,
 *   valueKind?: 'text',
 *   unit?: string,
 *   meta?: string,
 *   metaHtml?: string,
 *   metaId?: string,
 *   footer?: Array<{ label: string, valueHtml: string }>,
 *   rows?: Array<{ label: string, valueHtml: string }>,
 *   pulse?: boolean,
 *   pulseId?: string,
 *   pulseHidden?: boolean,
 *   glowId?: string,
 *   glowHidden?: boolean,
 *   as?: 'button' | 'div',
 *   id?: string,
 *   attrs?: string,
 *   extraClass?: string,
 *   titleAttr?: string,
 * }} spec
 */
export function hudKpiCardHtml(spec) {
    const variant = spec.variant || 'aux';
    const isFocus = variant === 'focus';
    const tag = spec.as === 'button' ? 'button' : 'div';
    const typeAttr = tag === 'button' ? ' type="button"' : '';
    const idAttr = spec.id ? ` id="${spec.id}"` : '';
    const extra = spec.extraClass ? ` ${spec.extraClass}` : '';
    const attrs = spec.attrs ? ` ${spec.attrs}` : '';
    const titleAttr = spec.titleAttr ? ` title="${spec.titleAttr}"` : '';
    const aria = tag === 'button' ? ' aria-pressed="false"' : '';

    let shell;
    if (isFocus) shell = SHELL_FOCUS;
    else if (spec.tone === 'warn') shell = SHELL_WARN;
    else shell = SHELL_AUX;
    if (tag === 'button') shell = `${BTN_CHROME} ${shell}`;

    const showScan = isFocus || Boolean(spec.glowId);
    const scanHidden = isFocus ? Boolean(spec.glowHidden) : Boolean(spec.glowId);
    const glowIdAttr = spec.glowId ? ` id="${spec.glowId}"` : '';
    const scan = showScan
        ? `<div${glowIdAttr} class="${scanHidden ? 'hidden ' : ''}${SCANLINE}"></div>`
        : '';

    const showPulse = Boolean(spec.pulse) || Boolean(spec.pulseId);
    const pulseHidden = spec.pulse ? Boolean(spec.pulseHidden) : Boolean(spec.pulseId);
    const pulseIdAttr = spec.pulseId ? ` id="${spec.pulseId}"` : '';
    const pulse = showPulse
        ? `<span${pulseIdAttr} class="${pulseHidden ? 'hidden ' : ''}${PULSE_DOT}"></span>`
        : '';

    const titleIdAttr = spec.titleId ? ` id="${spec.titleId}"` : '';
    const titleEl = `<span${titleIdAttr} class="${titleClass({
        variant,
        tone: spec.tone,
        as: spec.as,
    })}">${spec.title}</span>`;
    const head = pulse
        ? `<div class="flex justify-between items-start">${titleEl}${pulse}</div>`
        : titleEl;

    return `
                            <${tag}${typeAttr}${idAttr}${titleAttr}${aria}${attrs} class="${shell}${extra}">
                                ${scan}
                                ${head}
                                ${valueBlockHtml(spec, variant)}
                                ${footHtml(spec, isFocus)}
                            </${tag}>`;
}

function stripParts(el, parts) {
    parts.forEach((cls) => el.classList.remove(cls));
}

function addParts(el, parts) {
    parts.forEach((cls) => {
        if (cls) el.classList.add(cls);
    });
}

/**
 * @param {string} cardId
 * @param {{
 *   mode: 'alert' | 'ok' | 'aux',
 *   pressed?: boolean,
 *   shell?: boolean,
 *   glowId?: string,
 *   pulseId?: string,
 *   titleId?: string,
 *   valueWrapId?: string,
 *   hintId?: string,
 * }} spec
 */
export function paintHudKpiAlert(cardId, spec) {
    const card = document.getElementById(cardId);
    if (!card) return;
    const isAlert = spec.mode === 'alert';
    const useShell = spec.shell !== false;

    if (spec.glowId) {
        document.getElementById(spec.glowId)?.classList.toggle('hidden', !isAlert);
    }
    if (spec.pulseId) {
        document.getElementById(spec.pulseId)?.classList.toggle('hidden', !isAlert);
    }

    if (useShell) {
        card.setAttribute('aria-pressed', spec.pressed ? 'true' : 'false');
        stripParts(card, [
            ...SHELL_FOCUS_PARTS,
            ...SHELL_AUX_PARTS,
            ...SHELL_OK_PARTS,
            ...RING_PARTS,
            ...HOVER_ALERT,
            ...HOVER_OK,
        ]);
        addParts(card, BTN_CHROME.split(/\s+/));
        if (isAlert) {
            addParts(card, SHELL_FOCUS_PARTS);
            addParts(card, HOVER_ALERT);
            if (spec.pressed) addParts(card, RING_PARTS);
        } else if (spec.mode === 'ok') {
            addParts(card, SHELL_OK_PARTS);
            addParts(card, HOVER_OK);
        } else {
            addParts(card, SHELL_AUX_PARTS);
            addParts(card, HOVER_OK);
        }
        const title = spec.titleId ? document.getElementById(spec.titleId) : null;
        if (title) {
            title.className = isAlert ? TITLE_FOCUS : (spec.mode === 'ok' ? TITLE_OK : TITLE_AUX_TODO);
        }
        const valueWrap = spec.valueWrapId ? document.getElementById(spec.valueWrapId) : null;
        if (valueWrap) {
            valueWrap.className = isAlert
                ? VALUE_FOCUS
                : (spec.mode === 'ok' ? VALUE_TODO_OK : VALUE_TODO_IDLE);
        }
        const hint = spec.hintId ? document.getElementById(spec.hintId) : null;
        if (hint) {
            hint.className = isAlert ? HINT_ALERT : (spec.mode === 'ok' ? HINT_OK : HINT_AUX);
        }
        return;
    }

    const valueWrap = spec.valueWrapId ? document.getElementById(spec.valueWrapId) : null;
    if (valueWrap) {
        valueWrap.className = isAlert ? VALUE_WELD_ALERT : VALUE_TODO_IDLE;
    }
}
