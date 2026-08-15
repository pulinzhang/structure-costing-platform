/**
 * 列表分页每页条数。
 * - 常规列表：默认 10，可选 10 / 20 / 50 / 100
 * - 一事一议预览页：默认 200，可选 10 / 20 / 50 / 100 / 200
 */

export const PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100]);
export const DEFAULT_PAGE_SIZE = 10;

export const PREVIEW_PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100, 200]);
export const DEFAULT_PREVIEW_PAGE_SIZE = 200;

export function normalizePageSize(
    value,
    options = PAGE_SIZE_OPTIONS,
    fallback = DEFAULT_PAGE_SIZE,
) {
    const size = Number.parseInt(value, 10);
    return options.includes(size) ? size : fallback;
}

/**
 * 分页栏「每页」下拉 HTML（放在「共 N 条」旁）。
 * @param {string} selectId
 * @param {number} [currentSize]
 * @param {readonly number[]} [options]
 */
export function pageSizeSelectHtml(
    selectId,
    currentSize = DEFAULT_PAGE_SIZE,
    options = PAGE_SIZE_OPTIONS,
) {
    const fallback = options.includes(DEFAULT_PAGE_SIZE)
        ? DEFAULT_PAGE_SIZE
        : (options[0] ?? DEFAULT_PAGE_SIZE);
    const size = normalizePageSize(currentSize, options, fallback);
    const optionHtml = options
        .map((n) => `<option value="${n}"${n === size ? ' selected' : ''}>${n}</option>`)
        .join('');
    return `
        <label class="inline-flex items-center gap-1.5 shrink-0">
            <span class="text-[10px] font-mono text-[#555555]">每页</span>
            <select id="${selectId}"
                    class="h-6 min-w-[3.25rem] pl-1.5 pr-5 text-[10px] font-mono bg-[#121216] border border-[#22222A] text-[#8E8E93] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-sm">
                ${optionHtml}
            </select>
        </label>`;
}

/**
 * 绑定每页条数变更；变更后回调（通常 reload 第 1 页）。
 */
export function bindPageSizeSelect(
    selectId,
    {
        getSize,
        setSize,
        onChange,
        options = PAGE_SIZE_OPTIONS,
        defaultSize = DEFAULT_PAGE_SIZE,
    },
) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.value = String(normalizePageSize(getSize(), options, defaultSize));
    select.addEventListener('change', () => {
        const next = normalizePageSize(select.value, options, defaultSize);
        select.value = String(next);
        setSize(next);
        onChange(next);
    });
}

/**
 * 简易页码按钮（预览页等复用）。
 * @param {number} currentPage
 * @param {number} totalPages
 * @param {string} [btnClass]
 */
export function renderPageButtons(currentPage, totalPages, btnClass = 'page-btn') {
    if (totalPages <= 1) return '';
    let buttons = `
        <button type="button" class="${btnClass} flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    if (startPage > 1) {
        buttons += `<button type="button" class="${btnClass} flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button type="button" class="${btnClass} flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
        buttons += `<button type="button" class="${btnClass} flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button type="button" class="${btnClass} flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}
