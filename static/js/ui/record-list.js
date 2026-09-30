/**
 * 手机列表：把现有表格收成「标签 + 值」的卡片，操作钮保持可点。
 * 桌面仍是原表。各页继续写表头和单元格，不另做一套行模板。
 */

const PHONE_QUERY = '(max-width: 639.98px)';

export function isPhoneLayout() {
    return window.matchMedia(PHONE_QUERY).matches;
}

function headerLabel(th) {
    return (th.textContent || '').replace(/\s+/g, ' ').trim();
}

function columnOmitted(table, index) {
    const th = table.querySelectorAll('thead th')[index];
    if (th && th.classList.contains('hidden')) return true;
    const col = table.querySelectorAll('col')[index];
    return Boolean(col && col.classList.contains('hidden'));
}

function isChromeCell(cell) {
    if ((cell.innerText || '').trim()) return false;
    return !cell.querySelector('button, a, input, img, select, textarea');
}

function stampCell(cell, label, omit, chrome) {
    cell.classList.toggle('record-list-omit', omit);
    cell.classList.toggle('record-list-chrome', chrome && !omit);
    if (omit || chrome) {
        cell.removeAttribute('data-label');
        return;
    }
    if (label) cell.setAttribute('data-label', label);
    else cell.removeAttribute('data-label');
    if (cell.querySelector(':scope > .record-list-value')) return;
    const value = document.createElement('div');
    value.className = 'record-list-value';
    while (cell.firstChild) value.appendChild(cell.firstChild);
    cell.appendChild(value);
}

function stampTable(table) {
    if (table.closest('#llmAssistantPanel, #sidebar')) return;
    const heads = [...table.querySelectorAll('thead th')];
    if (!heads.length) return;
    const labels = heads.map(headerLabel);
    if (!labels.some(Boolean)) return;
    table.classList.add('record-list');
    table.querySelectorAll('tbody > tr').forEach((row) => {
        const cells = [...row.children];
        const spanCell = cells.find((cell) => cell.tagName === 'TD' && cell.colSpan > 1);
        const section = Boolean(spanCell) && cells.length > 1;
        row.classList.toggle('record-list-span', Boolean(spanCell));
        row.classList.toggle('record-list-section', section);
        if (spanCell) {
            cells.forEach((cell) => {
                if (cell.tagName !== 'TD') return;
                if (cell !== spanCell) {
                    stampCell(cell, '', true, false);
                    return;
                }
                stampCell(cell, '', false, false);
                cell.classList.remove('record-list-omit', 'record-list-chrome');
                cell.removeAttribute('data-label');
            });
            return;
        }
        cells.forEach((cell, index) => {
            if (cell.tagName !== 'TD') return;
            const omit = columnOmitted(table, index) || cell.classList.contains('hidden');
            const label = labels[index] || '';
            const chrome = !omit && !label && isChromeCell(cell);
            stampCell(cell, label, omit, chrome);
        });
    });
}

function stampAll() {
    if (!isPhoneLayout()) return;
    document.querySelectorAll('table').forEach(stampTable);
}

export function installRecordLists() {
    let pending = false;
    let stamping = false;
    const schedule = () => {
        if (pending || stamping || !isPhoneLayout()) return;
        pending = true;
        requestAnimationFrame(() => {
            pending = false;
            stamping = true;
            try {
                stampAll();
            } finally {
                stamping = false;
            }
        });
    };
    const observer = new MutationObserver(() => {
        if (stamping) return;
        schedule();
    });
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class'],
    });
    window.matchMedia(PHONE_QUERY).addEventListener('change', schedule);
    schedule();
}
