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
            html = marked.parse(source, { breaks: true, gfm: true });
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
 * 宽表横向滚动；短单元格禁止拆字，长文本限宽换行。
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
