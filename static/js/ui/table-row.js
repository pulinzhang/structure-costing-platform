/**
 * 密表当前行：一表仅一行 data-current="1"。
 * @param {HTMLElement | null} tableEl
 * @param {HTMLElement | null} tr
 */
export function setCurrentTableRow(tableEl, tr) {
    if (!tableEl) return;
    tableEl.querySelectorAll('tr[data-current="1"]').forEach((row) => {
        if (row !== tr) row.removeAttribute('data-current');
    });
    if (tr && tableEl.contains(tr)) {
        tr.setAttribute('data-current', '1');
    }
}

export function clearCurrentTableRows(root = document) {
    const scope = root instanceof Element || root === document ? root : document;
    scope.querySelectorAll('tr[data-current="1"]').forEach((row) => {
        row.removeAttribute('data-current');
    });
}

/**
 * 操作列点击设当前行。禁止整行 click。
 * @param {ParentNode} [root]
 */
export function bindCurrentRowOnOps(root = document) {
    root.addEventListener('click', (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const btn = target.closest('[data-action], .btn-open-detail, .view-btn, .edit-btn');
        if (!btn) return;
        const tr = btn.closest('tr');
        const table = tr?.closest('table');
        if (table && tr) setCurrentTableRow(table, tr);
    });
}
