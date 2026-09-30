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

function visibleText(cell) {
    const value = cell.querySelector(':scope > .record-list-value');
    return ((value || cell).textContent || '').replace(/\s+/g, ' ').trim();
}

function realCells(row) {
    return [...row.children].filter((cell) => cell.tagName === 'TD' && !cell.classList.contains('record-list-carry'));
}

function carryCell(row, col, text) {
    let carry = [...row.children].find((cell) => (
        cell.classList.contains('record-list-carry') && Number(cell.dataset.recordCol) === col
    ));
    if (!carry) {
        carry = document.createElement('td');
        carry.className = 'record-list-carry';
        carry.dataset.recordCol = String(col);
        row.appendChild(carry);
    }
    if (visibleText(carry) !== text) carry.textContent = text;
    return carry;
}

function orderCells(row, cells) {
    const current = [...row.children].filter((cell) => cell.tagName === 'TD');
    const same = current.length === cells.length && current.every((cell, index) => cell === cells[index]);
    if (!same) cells.forEach((cell) => row.appendChild(cell));
}

/**
 * 桌面用 rowspan 把牌号等合并到后续厚度行。那些行的 DOM 里没有这些格子，
 * 按子节点序号贴表头就会把加减价标成牌号。这里按视觉列号贴，并把合并值补进后续行。
 */
function rowPlans(rows) {
    const active = new Map();
    return rows.map((row) => {
        const cells = realCells(row);
        const spanCell = cells.find((cell) => cell.colSpan > 1);
        if (spanCell) {
            active.clear();
            return { row, spanCell, cells };
        }
        let col = 0;
        const placed = [];
        cells.forEach((cell) => {
            while (active.has(col)) col += 1;
            placed.push({ cell, col });
            const down = cell.rowSpan || 1;
            const width = cell.colSpan || 1;
            if (down > 1) {
                for (let offset = 0; offset < width; offset += 1) {
                    active.set(col + offset, { cell, left: down, start: col });
                }
            }
            col += width;
        });
        const holes = [];
        active.forEach((span, covered) => {
            if (span.start === covered && !placed.some((item) => item.col === covered)) {
                holes.push({ col: covered, source: span.cell });
            }
        });
        const expired = [];
        active.forEach((span, covered) => {
            span.left -= 1;
            if (span.left <= 0) expired.push(covered);
        });
        expired.forEach((covered) => active.delete(covered));
        return { row, placed, holes };
    });
}

function stampTable(table) {
    if (table.closest('#llmAssistantPanel, #sidebar')) return;
    const heads = [...table.querySelectorAll('thead th')];
    if (!heads.length) return;
    const labels = heads.map(headerLabel);
    if (!labels.some(Boolean)) return;
    table.classList.add('record-list');
    const plans = rowPlans([...table.querySelectorAll('tbody > tr')]);
    plans.forEach((plan) => {
        const { row } = plan;
        row.classList.toggle('record-list-span', Boolean(plan.spanCell));
        row.classList.toggle('record-list-section', Boolean(plan.spanCell) && plan.cells.length > 1);
        if (plan.spanCell) {
            plan.cells.forEach((cell) => {
                if (cell !== plan.spanCell) {
                    stampCell(cell, '', true, false);
                    return;
                }
                stampCell(cell, '', false, false);
                cell.classList.remove('record-list-omit', 'record-list-chrome');
                cell.removeAttribute('data-label');
            });
            return;
        }
        const byCol = new Map(plan.placed.map((item) => [item.col, item.cell]));
        const wanted = new Set(plan.holes.map((hole) => hole.col));
        row.querySelectorAll(':scope > td.record-list-carry').forEach((cell) => {
            if (!wanted.has(Number(cell.dataset.recordCol))) cell.remove();
        });
        plan.holes.forEach((hole) => {
            byCol.set(hole.col, carryCell(row, hole.col, visibleText(hole.source)));
        });
        const ordered = [...byCol.keys()].sort((left, right) => left - right).map((col) => byCol.get(col));
        orderCells(row, ordered);
        ordered.forEach((cell) => {
            const col = [...byCol.entries()].find(([, node]) => node === cell)[0];
            const omit = columnOmitted(table, col) || cell.classList.contains('hidden');
            const label = labels[col] || '';
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
