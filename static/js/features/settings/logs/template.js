/**
 * 操作日志 — 与用户管理同一套设置页表格（非 HUD）
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

export function logsTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-[#9e9e9e]">
            <div class="bg-[#121215] border border-[#2c2c2c]">

                <div class="p-3 border-b border-[#222222] flex flex-wrap items-center justify-between gap-3 bg-[#16161a]">
                    <div class="flex items-center gap-2 flex-wrap flex-1 min-w-0">
                        <input type="text" id="filterUsername" placeholder="账号 / 操作人"
                               class="w-36 h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">

                        <select id="filterMenu"
                                class="h-8 max-w-[220px] px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-pointer focus:outline-none focus:border-[#ff5252] transition-colors">
                            <option value="">全部功能</option>
                        </select>

                        <select id="filterPermission"
                                class="h-8 max-w-[180px] px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-pointer focus:outline-none focus:border-[#ff5252] transition-colors">
                            <option value="">全部动作</option>
                        </select>

                        <select id="filterSuccess"
                                class="h-8 px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-pointer focus:outline-none focus:border-[#ff5252] transition-colors">
                            <option value="">全部结果</option>
                            <option value="true">成功</option>
                            <option value="false">失败</option>
                        </select>

                        <input type="datetime-local" id="filterCreatedFrom"
                               class="h-8 px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-colors">
                        <input type="datetime-local" id="filterCreatedTo"
                               class="h-8 px-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-colors">

                        <button id="btnFilter"
                                class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-semibold text-[#c8c8c8] border border-[#8a2020] hover:text-white transition-all"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                        <button id="btnResetFilter"
                                class="h-8 px-3 text-[11px] text-[#616161] hover:text-[#9e9e9e] transition-all">
                            重置
                        </button>
                    </div>

                    <button id="btnExportLogs"
                            class="h-8 inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-3 text-xs hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all">
                        ${window.svgIcon('download', 'w-3.5 h-3.5')}
                        导出
                    </button>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-[#0e0e11] border-b border-[#2c2c2c] text-[#9e9e9e]">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">时间</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">操作人</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">操作</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider w-[132px] max-w-[132px]">对象</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center whitespace-nowrap">结果</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">IP</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody" class="divide-y divide-[#222222]"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-4 py-2.5 border-t border-[#222222] bg-[#0e0e11]" id="paginationContainer">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="totalCountPagination" class="text-xs text-[#616161] font-mono"></span>
                        ${pageSizeSelectHtml('logsPageSize')}
                    </div>
                    <div class="flex items-center gap-1" id="paginationBtns"></div>
                </div>

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-[#1e1e1e] border border-[#2c2c2c] text-[#616161] mb-2">
                        ${window.svgIcon('clipboard-list', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-[#9e9e9e] mb-1">暂无操作日志</p>
                    <p class="text-[11px] text-[#616161]">登录、写操作、导出和查看计算过程会出现在此</p>
                </div>

                <div id="loadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#616161]">加载中..</span>
                </div>
            </div>
        </div>
    `;
}

function esc(str) {
    if (typeof window.esc === 'function') return window.esc(str);
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function formatDateTime(value) {
    if (!value) return '-';
    return String(value).replace('T', ' ').slice(0, 19);
}

function isHttpTail(part) {
    return /^(GET|POST|PUT|PATCH|DELETE)\s\/api\//u.test(part);
}

function isObjectPart(part) {
    return (
        /^文件[= ]/u.test(part)
        || /^基地\s/u.test(part)
        || /^零件号\s/u.test(part)
        || /^\d{4}年/u.test(part)
    );
}

function stripFilePrefix(part) {
    return String(part || '').replace(/^文件[= ]/u, '').trim();
}

function cleanLegacyDetail(detail) {
    const raw = String(detail || '').trim();
    if (!raw) return '';
    const beforeAmp = raw.includes('&') ? raw.slice(0, raw.indexOf('&')) : raw;
    if (/^基地\s|^零件号\s|^文件[= ]/u.test(beforeAmp)) {
        return stripFilePrefix(beforeAmp);
    }
    return stripFilePrefix(raw);
}

function splitLogDisplay(summary, detail) {
    const parts = String(summary || '')
        .split(/\s·\s/u)
        .map((item) => item.trim())
        .filter(Boolean);
    const actionParts = [];
    const objectParts = [];
    for (const part of parts) {
        if (isHttpTail(part)) continue;
        if (isObjectPart(part)) {
            const cleaned = stripFilePrefix(part);
            if (cleaned) objectParts.push(cleaned);
            continue;
        }
        actionParts.push(part);
    }
    const fromDetail = cleanLegacyDetail(detail);
    if (
        fromDetail
        && !objectParts.some((item) => fromDetail.includes(item) || item.includes(fromDetail))
    ) {
        objectParts.push(fromDetail);
    }
    return {
        what: actionParts.join(' / ') || '',
        objectText: objectParts.join(' · '),
    };
}

/**
 * @param {Array} records
 * @param {{[code: string]: {label: string, breadcrumb: string}}} catalogByCode
 */
export function renderTableRows(records, catalogByCode) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    const catalog = catalogByCode || {};
    return records.map((record) => {
        const successBadge = record.success
            ? `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-[#4caf50] bg-[#2e7d32]/20 border border-[#2e7d32]/40">成功</span>`
            : `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-[#ef5350] bg-[#c62828]/20 border border-[#c62828]/40">失败 ${esc(record.status_code)}</span>`;
        const operator = record.operator_name || record.username || '-';
        const operatorSub = record.username && record.operator_name && record.username !== record.operator_name
            ? `<div class="text-[11px] text-[#616161] font-mono">${esc(record.username)}</div>`
            : '';
        const catalogHit = record.permission_code ? catalog[record.permission_code] : null;
        const split = splitLogDisplay(record.summary, record.detail);
        const whatMain = split.what
            || (catalogHit && catalogHit.breadcrumb)
            || (record.module && record.action ? `${record.module} / ${record.action}` : '-');
        const objectText = split.objectText;
        const locationParts = [record.ip_country, record.ip_province, record.ip_city].filter((part) => part);
        const locationHint = locationParts.length
            ? `<div class="text-[11px] text-[#616161]">${esc(locationParts.join(' / '))}</div>`
            : '';

        return `
        <tr class="hover:bg-[#ffffff]/[0.02] transition-colors border-b border-[#222222]">
            <td class="px-4 py-2.5 text-[11px] text-[#616161] font-mono whitespace-nowrap align-top">${esc(formatDateTime(record.created_at))}</td>
            <td class="px-4 py-2.5 whitespace-nowrap align-top">
                <div class="text-xs text-[#ffffff]">${esc(operator)}</div>
                ${operatorSub}
            </td>
            <td class="px-4 py-2.5 align-top">
                <div class="text-xs text-[#c8c8c8] leading-5 break-words">${esc(whatMain)}</div>
            </td>
            <td class="px-4 py-2.5 w-[132px] max-w-[132px] align-top">
                <div class="text-[11px] text-[#9e9e9e] truncate" title="${esc(objectText)}">${esc(objectText || '-')}</div>
            </td>
            <td class="px-4 py-2.5 text-center whitespace-nowrap align-top">${successBadge}</td>
            <td class="px-4 py-2.5 whitespace-nowrap align-top">
                <div class="text-[11px] text-[#9e9e9e] font-mono">${esc(record.client_ip || '-')}</div>
                ${locationHint}
            </td>
        </tr>
        `;
    }).join('');
}

/**
 * @param {number} currentPage
 * @param {number} totalPages
 */
export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === 1 ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-1 text-[#616161] text-xs">—</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn w-6 h-6 text-[11px] font-mono ${isActive ? 'bg-[#d32f2f] border border-[#d32f2f] text-white' : 'border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-1 text-[#616161] text-xs">—</span>`;
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === totalPages ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>
    `;

    return buttons;
}
