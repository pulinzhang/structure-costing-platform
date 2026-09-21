/**
 * 列表零件身份：短代码单独一列（关注点）；完整零件号与名称另列并弱化。
 * 短代码 = 零件号数字段末 4 位（与 BOM / 核算导出一致）。
 * 焊接分总成带 -N 时保留字母尾（501005123AA-1 → 5123AA-1）。
 */

function htmlEsc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

function shortWeldPartNumber(partNumber) {
    if (!partNumber) return null;
    const raw = String(partNumber).trim();
    if (!raw) return null;
    const match = raw.match(/(\d{4,})([A-Za-z]*)(-\d+)\s*$/);
    if (match) {
        const digitsTail = match[1].slice(-4);
        const letters = match[2] || '';
        const dashSuffix = match[3];
        return `${digitsTail}${letters}${dashSuffix}`;
    }
    return shortPartNumber(raw);
}

export function resolveBomNodeShortCode(partNumber, { level, nodeRole } = {}) {
    const full = String(partNumber || '').trim();
    if (!full) return null;
    const isSupply = Number(level) === 0 || nodeRole === 'supply';
    if (isSupply) return shortPartNumber(full);
    return shortWeldPartNumber(full);
}

/**
 * 短代码列：只显示短码。
 * @param {string|null|undefined} partNumber
 * @param {string|null} [shortCode] 覆盖默认末四位
 */
export function partShortCodeCellHtml(partNumber, shortCode) {
    const full = partNumber || '';
    const shortNo = shortCode === undefined
        ? shortPartNumber(full)
        : (shortCode || null);
    const display = shortNo || full || '—';
    const isShort = Boolean(shortNo);
    const klass = isShort
        ? 'text-[16px] font-mono font-bold tabular-nums text-ink tracking-[0.12em] leading-none group-hover:text-brand-hud transition-colors'
        : 'text-[10px] font-mono text-ink-muted tracking-wide truncate';
    return `<div class="${klass}" title="${htmlEsc(full)}">${htmlEsc(display)}</div>`;
}

/**
 * 零件列：完整零件号 + 名称，弱化。
 * @param {string|null|undefined} partNumber
 * @param {string|null|undefined} partName
 * @param {string} [extraHtml] 拼焊徽章、内部号等
 */
export function partNumberNameCellHtml(partNumber, partName, extraHtml = '') {
    const full = partNumber || '';
    const name = partName || '';
    const extra = extraHtml || '';
    const nameLine = name
        ? `<div class="text-[9px] text-ink-faint mt-0.5 truncate" title="${htmlEsc(name)}">${htmlEsc(name)}</div>`
        : '';
    return `
        <div class="text-[10px] font-mono text-ink-muted tracking-wide truncate" title="${htmlEsc(full)}">${htmlEsc(full) || '—'}</div>
        ${nameLine}
        ${extra}`;
}
