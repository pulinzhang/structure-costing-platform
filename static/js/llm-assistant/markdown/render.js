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
        return DOMPurify.sanitize(html, {
            USE_PROFILES: { html: true },
            FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form'],
            FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
        });
    }

    return escapeHtml(source).replace(/\n/g, '<br>');
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
