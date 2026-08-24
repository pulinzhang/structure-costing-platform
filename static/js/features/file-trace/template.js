/**
 * 文件溯源 — HUD 密表 + 筛选 + 详情抽屉
 */

import { pageSizeSelectHtml } from '../../page-size.js?v=2';

const CATEGORY_BADGE = 'inline-flex items-center px-2 py-0.5 text-[9px] font-semibold tracking-[0.06em] border border-[#2A2A35] text-[#8E8E93] bg-[#121218]';

export function fileTraceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3 border-b border-[#14141A] bg-[#0E0E12]">
                    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2 mb-3">
                        <select id="ftFilterCategory" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部分类</option>
                        </select>
                        <select id="ftFilterLocation" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部基地</option>
                        </select>
                        <select id="ftFilterYear" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部年度</option>
                        </select>
                        <select id="ftFilterMonth" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部月份</option>
                        </select>
                        <select id="ftFilterVehicle" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部车型</option>
                        </select>
                        <select id="ftFilterCreator" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                            <option value="">全部上传人</option>
                        </select>
                    </div>
                    <div class="flex flex-wrap items-end gap-2">
                        <div class="flex-1 min-w-[180px]">
                            <label class="block text-[9px] text-[#555555] mb-1 tracking-[0.08em]">文件名</label>
                            <input id="ftFilterFilename" type="text" placeholder="模糊搜索原件名"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                        </div>
                        <div>
                            <label class="block text-[9px] text-[#555555] mb-1 tracking-[0.08em]">上传时间起</label>
                            <input id="ftFilterFrom" type="date"
                                   class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                        </div>
                        <div>
                            <label class="block text-[9px] text-[#555555] mb-1 tracking-[0.08em]">上传时间止</label>
                            <input id="ftFilterTo" type="date"
                                   class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252]">
                        </div>
                        <button id="ftBtnSearch" type="button"
                                class="inline-flex items-center justify-center h-9 px-4 text-xs font-semibold bg-[#FF1E27] text-white rounded hover:bg-[#b71c1c] transition-all">
                            查询
                        </button>
                        <button id="ftBtnReset" type="button"
                                class="inline-flex items-center justify-center h-9 px-4 text-xs font-medium bg-transparent text-[#9e9e9e] border border-[#2c2c2c] rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                            重置
                        </button>
                    </div>
                </div>

                <div id="ftNoCategoryHint" class="hidden px-5 py-16 text-center border-b border-[#14141A]">
                    <div class="text-[#8E8E93] text-sm mb-2">暂无权限范围内的文件分类</div>
                    <div class="text-[#555555] text-xs">请联系管理员授权对应业务菜单后再查看溯源文件</div>
                </div>

                <div id="ftTableWrap" class="overflow-x-auto bg-[#0A0A0E]">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 980px;">
                        <colgroup>
                            <col style="width: 4px;">
                            <col style="width: 110px;">
                            <col style="width: 220px;">
                            <col style="width: 240px;">
                            <col style="width: 80px;">
                            <col style="width: 90px;">
                            <col style="width: 140px;">
                            <col style="width: 90px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">分类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">原件名</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">Scope</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">大小</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">上传人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">上传时间</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="ftTableBody"></tbody>
                    </table>
                </div>

                <div id="ftPagination" class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]"></div>
            </div>
        </div>

        <div id="ftDrawerBackdrop" class="fixed inset-0 bg-black/60 z-[80] hidden"></div>
        <aside id="ftDrawer" class="fixed top-0 right-0 h-full w-full max-w-md bg-[#121212] border-l border-[#2c2c2c] z-[85] translate-x-full transition-transform duration-200 overflow-y-auto"
               style="box-shadow: -8px 0 32px rgba(0,0,0,0.8);">
            <div class="flex items-center justify-between px-5 py-4 border-b border-[#222222]">
                <div>
                    <div class="text-xs text-[#555555] tracking-[0.1em]">FILE DETAIL</div>
                    <h3 class="text-sm font-semibold text-white mt-1">文件详情</h3>
                </div>
                <button id="ftDrawerClose" type="button" class="w-8 h-8 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white border border-[#2c2c2c] rounded">×</button>
            </div>
            <div id="ftDrawerBody" class="px-5 py-4 space-y-4 text-xs"></div>
        </aside>
    `;
}

function formatDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    return text.replace('T', ' ').slice(0, 19);
}

export function renderTableRows(items) {
    if (!items || !items.length) {
        return `<tr><td colspan="8" class="px-4 py-16 text-center text-[#555555] text-xs">暂无溯源文件</td></tr>`;
    }

    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    return items.map((item) => `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100" data-id="${item.id}">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <span class="${CATEGORY_BADGE}">${esc(item.file_category_label || item.file_category)}</span>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#F0F0F2] font-semibold truncate" title="${esc(item.original_filename)}">${esc(item.original_filename)}</div>
                <div class="text-[9px] text-[#3A3A42] truncate">${esc(item.extension || '')}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-[#8E8E93] truncate" title="${esc(item.scope_text || '')}">${esc(item.scope_text || '-')}</td>
            <td class="${numCell}">${esc(item.file_size_text || fmtNum(item.file_size, 0))}</td>
            <td class="px-2 py-2 text-[10px] text-[#8E8E93] truncate">${esc(item.created_by)}</td>
            <td class="px-2 py-2 text-[10px] text-[#8E8E93]">${esc(formatDateTime(item.created_at))}</td>
            <td class="px-1 py-2 text-center">
                <div class="inline-flex items-center gap-1">
                    <button type="button" data-action="detail" data-id="${item.id}"
                            class="w-7 h-7 inline-flex items-center justify-center text-[#8E8E93] hover:text-[#FF1E27] border border-transparent hover:border-[#FF1E27]/30 rounded opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                            title="详情">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>
                    <button type="button" data-action="download" data-id="${item.id}"
                            class="w-7 h-7 inline-flex items-center justify-center text-[#8E8E93] hover:text-[#FF1E27] border border-transparent hover:border-[#FF1E27]/30 rounded opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                            title="下载">${window.svgIcon('download', 'w-3.5 h-3.5')}</button>
                </div>
            </td>
        </tr>
    `).join('');
}

export function renderPagination(total, page, pageSize) {
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const buttons = [];
    for (let i = 1; i <= totalPages; i += 1) {
        if (totalPages > 7 && Math.abs(i - page) > 2 && i !== 1 && i !== totalPages) {
            if (i === 2 || i === totalPages - 1) buttons.push('<span class="px-2 text-[#555555]">…</span>');
            continue;
        }
        const active = i === page
            ? 'bg-[#FF1E27] text-white'
            : 'text-[#8E8E93] hover:text-white hover:bg-[#262626]';
        buttons.push(`<button type="button" data-page="${i}" class="min-w-[28px] h-7 px-2 text-[10px] font-mono rounded ${active}">${i}</button>`);
    }
    return `
        <div class="flex items-center gap-3">
            <span class="text-[10px] font-mono text-[#555555]">共 ${total} 条</span>
            ${pageSizeSelectHtml('ftPageSize', pageSize)}
        </div>
        <div class="flex items-center gap-0.5">${buttons.join('')}</div>
    `;
}

export function renderDrawerDetail(item) {
    const rows = [
        ['分类', item.file_category_label || item.file_category],
        ['原件名', item.original_filename],
        ['Scope', item.scope_text || '-'],
        ['SHA256', item.file_hash],
        ['大小', item.file_size_text || `${item.file_size} B`],
        ['扩展名', item.extension],
        ['上传人', item.created_by],
        ['上传时间', formatDateTime(item.created_at)],
        ['状态', item.status],
    ];
    const canDownload = typeof can === 'function' && can('op:file-trace:download');
    return `
        <dl class="space-y-3">
            ${rows.map(([label, value]) => `
                <div>
                    <dt class="text-[9px] text-[#555555] tracking-[0.08em] mb-1">${esc(label)}</dt>
                    <dd class="text-[11px] text-[#F0F0F2] font-mono break-all">${esc(value)}</dd>
                </div>
            `).join('')}
        </dl>
        ${canDownload ? `
            <button id="ftDrawerDownload" type="button" data-id="${item.id}"
                    class="w-full inline-flex items-center justify-center gap-2 bg-[#FF1E27] text-white px-4 py-2 text-xs font-semibold rounded hover:bg-[#b71c1c] transition-all mt-4">
                ${window.svgIcon('download', 'w-3.5 h-3.5')}
                下载原件
            </button>
        ` : ''}
    `;
}
