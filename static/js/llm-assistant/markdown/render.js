/**
 * Markdown → 安全 HTML（必须经 DOMPurify）
 */

/**
 * @param {string} markdown
 * @returns {string}
 */
export function renderMarkdown(markdown) {
    const source = String(markdown || '');
    let html = '';
    try {
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            html = marked.parse(protectDomainNotation(source), { breaks: true, gfm: true });
        } else {
            html = fallbackMarkdownToHtml(source);
        }
    } catch {
        html = fallbackMarkdownToHtml(source);
    }

    if (typeof DOMPurify !== 'undefined' && typeof DOMPurify.sanitize === 'function') {
        html = DOMPurify.sanitize(html, {
            USE_PROFILES: { html: true },
            ADD_ATTR: ['class', 'style'],
            FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form'],
            FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
        });
    } else {
        html = escapeHtml(source).replace(/\n/g, '<br>');
    }

    return enhanceMarkdownTables(html);
}

/**
 * 业务符号在进 marked 之前转义，避免被当成格式。代码块原样保留。
 * - 1.80~2.00：单个 ~ 会配成 <del>
 * - 行首 >=2.30 / >2.30：> 会变成引用，大于号消失
 * - 1.2*800：数字之间的 * 会变成斜体
 * - <DC01>：尖括号会变成 HTML 标签，净化后牌号消失
 * - [说明](备注)：不是网址的方括号链接会把括号吃进地址
 * **加粗**、~~删除线~~、列表、表格、真正的 http 链接仍按 Markdown 渲染。
 * @param {string} markdown
 * @returns {string}
 */
function protectDomainNotation(markdown) {
    const stash = [];
    const stashed = markdown.replace(/```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`/g, (block) => {
        const token = `\u0000CODE${stash.length}\u0000`;
        stash.push(block);
        return token;
    });
    const protectedText = stashed
        .replace(/(?<!\\)</g, '\\<')
        .replace(/(?<!\\)>=/g, '\\>=')
        .replace(/^( {0,3})>(?=\d)/gm, '$1\\>')
        .replace(/^([ ]{0,3}(?:[-*+]|\d+\.)[ ]+)>(?=\d)/gm, '$1\\>')
        .replace(/(\d)~(\d)/g, '$1\\~$2')
        .replace(/(\d)\*(?=\d)/g, '$1\\*')
        .replace(/\[([^\]]+)\]\(([^)]*)\)/g, (full, label, target) => {
            if (/^(https?:|mailto:|tel:|\/)/i.test(String(target).trim())) {
                return full;
            }
            return `\\[${label}\\](${target})`;
        });
    return protectedText.replace(/\u0000CODE(\d+)\u0000/g, (_, index) => stash[Number(index)]);
}

/**
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * @param {string} markdown
 * @returns {string}
 */
function fallbackMarkdownToHtml(markdown) {
    const escaped = escapeHtml(markdown);
    return escaped
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

const SHORT_CELL_MAX = 10;

/**
 * 宽表在电脑上横向滚动。手机沿用记录列表：表头收成每格的标签，行收成卡片。
 * @param {string} html
 * @returns {string}
 */
function enhanceMarkdownTables(html) {
    if (typeof document === 'undefined' || !html || !String(html).includes('<table')) {
        return html;
    }
    const wrap = document.createElement('div');
    wrap.innerHTML = html;
    wrap.querySelectorAll('table').forEach((table) => {
        table.querySelectorAll('th').forEach((cell) => applyCellLayout(cell, true));
        table.querySelectorAll('td').forEach((cell) => applyCellLayout(cell, false));
        applyRecordList(table);
        if (table.parentElement?.classList.contains('table-scroll')) {
            return;
        }
        const holder = document.createElement('div');
        holder.className = 'table-scroll';
        table.parentNode.insertBefore(holder, table);
        holder.appendChild(table);
    });
    return wrap.innerHTML;
}

/**
 * 与记录列表同一套标记。窄屏样式在 style.css，宽屏仍是原表。
 * @param {HTMLTableElement} table
 */
function applyRecordList(table) {
    const labels = [...table.querySelectorAll('thead th')].map((cell) => (
        String(cell.textContent || '').replace(/\s+/g, ' ').trim()
    ));
    if (!labels.some(Boolean)) return;
    table.classList.add('record-list');
    table.querySelectorAll('tbody > tr').forEach((row) => {
        const cells = [...row.children].filter((cell) => cell.tagName === 'TD');
        const spanCell = cells.length === 1 && cells[0].colSpan > 1 ? cells[0] : null;
        row.classList.toggle('record-list-span', Boolean(spanCell));
        cells.forEach((cell, index) => {
            if (spanCell) {
                cell.removeAttribute('data-label');
                wrapRecordValue(cell);
                return;
            }
            const label = labels[index] || '';
            const text = String(cell.textContent || '').replace(/\s+/g, ' ').trim();
            const hasControl = Boolean(cell.querySelector('a, button, img'));
            if (!label && !text && !hasControl) {
                cell.classList.add('record-list-chrome');
                cell.removeAttribute('data-label');
                return;
            }
            if (label) cell.setAttribute('data-label', label);
            else cell.removeAttribute('data-label');
            wrapRecordValue(cell);
        });
    });
}

/**
 * @param {HTMLElement} cell
 */
function wrapRecordValue(cell) {
    if (cell.querySelector(':scope > .record-list-value')) return;
    const value = document.createElement('div');
    value.className = 'record-list-value';
    while (cell.firstChild) value.appendChild(cell.firstChild);
    cell.appendChild(value);
}

/**
 * @param {HTMLElement} cell
 * @param {boolean} isHeader
 */
function applyCellLayout(cell, isHeader) {
    const text = String(cell.textContent || '').replace(/\s+/g, ' ').trim();
    if (isHeader || isShortCell(text)) {
        cell.classList.add('cell-keep');
        cell.setAttribute('style', 'white-space:nowrap;word-break:keep-all;');
        return;
    }
    cell.classList.add('cell-wrap');
    cell.setAttribute('style', 'max-width:10.5em;word-break:break-word;overflow-wrap:break-word;');
}

/**
 * @param {string} text
 * @returns {boolean}
 */
function isShortCell(text) {
    if (!text) return true;
    if (/^-?\d[\d,]*\.?\d*%?$/.test(text)) return true;
    if (/^\d{4}-\d{1,2}$/.test(text)) return true;
    return Array.from(text).length <= SHORT_CELL_MAX;
}
