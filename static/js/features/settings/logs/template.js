/**
 * 操作日志 — 与用户管理同一套设置页表格（非 HUD）
 */

import { paginationBarHtml } from '../../../ui/page-size.js?v=6';
import { HUD_FILTER, HUD_INPUT, BTN_FILTER_SEARCH } from '../../../ui/classes.js?v=13';

export function logsTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-ink-muted">
            <div class="bg-app-main border border-line">

                <div class="p-3 border-b border-line-subtle flex flex-wrap items-center justify-between gap-3 bg-app-surface">
                    <div class="flex items-center gap-2 flex-wrap flex-1 min-w-0">
                        <input type="text" id="filterUsername" placeholder="账号 / 操作人"
                               class="w-36 ${HUD_INPUT}">

                        <select id="filterMenu"
                                class="max-w-[220px] ${HUD_FILTER}">
                            <option value="">全部功能</option>
                        </select>

                        <select id="filterPermission"
                                class="max-w-[180px] ${HUD_FILTER}">
                            <option value="">全部动作</option>
                        </select>

                        <select id="filterSuccess"
                                class="${HUD_FILTER}">
                            <option value="">全部结果</option>
                            <option value="true">成功</option>
                            <option value="false">失败</option>
                        </select>

                        <input type="datetime-local" id="filterCreatedFrom"
                               class="${HUD_INPUT}">
                        <input type="datetime-local" id="filterCreatedTo"
                               class="${HUD_INPUT}">

                        <button id="btnFilter"
                                class="${BTN_FILTER_SEARCH} h-8">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                        <button id="btnResetFilter"
                                class="h-8 px-3 text-[11px] text-ink-dim hover:text-ink-muted transition-all">
                            重置
                        </button>
                    </div>

                    <button id="btnExportLogs"
                            class="h-8 inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 text-xs hover:border-brand hover:text-brand transition-all">
                        ${window.svgIcon('download', 'w-3.5 h-3.5')}
                        导出
                    </button>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-app-deep border-b border-line text-ink-muted">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">时间</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">操作人</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">操作</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider w-[132px] max-w-[132px]">对象</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center whitespace-nowrap">结果</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">IP</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody" class="divide-y divide-line-subtle"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'totalCountPagination', selectId: 'logsPageSize', buttonsId: 'paginationBtns', wrapperId: 'paginationContainer', wrapperClass: 'flex items-center justify-between px-4 py-2.5 border-t border-line-subtle bg-app-deep' })}

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-app-surface border border-line text-ink-dim mb-2">
                        ${window.svgIcon('clipboard-list', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-ink-muted mb-1">暂无操作日志</p>
                    <p class="text-[11px] text-ink-dim">登录、写操作、导出和查看计算过程会出现在此</p>
                </div>

                <div id="loadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-line border-brand rounded-full animate-spin"></div>
                    <span class="text-[11px] text-ink-dim">加载中..</span>
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
            ? `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-ok bg-ok/20 border border-ok/40/40">成功</span>`
            : `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-danger bg-danger/20 border border-brand-hud/40/40">失败 ${esc(record.status_code)}</span>`;
        const operator = record.operator_name || record.username || '-';
        const operatorSub = record.username && record.operator_name && record.username !== record.operator_name
            ? `<div class="text-[11px] text-ink-dim font-mono">${esc(record.username)}</div>`
            : '';
        const catalogHit = record.permission_code ? catalog[record.permission_code] : null;
        const split = splitLogDisplay(record.summary, record.detail);
        const whatMain = split.what
            || (catalogHit && catalogHit.breadcrumb)
            || (record.module && record.action ? `${record.module} / ${record.action}` : '-');
        const objectText = split.objectText;
        const locationParts = [record.ip_country, record.ip_province, record.ip_city].filter((part) => part);
        const locationHint = locationParts.length
            ? `<div class="text-[11px] text-ink-dim">${esc(locationParts.join(' / '))}</div>`
            : '';

        const errorText = !record.success && record.error_message
            ? String(record.error_message)
            : '';
        const errorLine = errorText
            ? `<div class="max-w-[160px] mx-auto truncate text-[10px] text-ink-muted mt-1" title="${esc(errorText)}">${esc(errorText)}</div>`
            : '';

        return `
        <tr class="hover:bg-ink/[0.02] transition-colors border-b border-line-subtle">
            <td class="px-4 py-2.5 text-[11px] text-ink-dim font-mono whitespace-nowrap align-top">${esc(formatDateTime(record.created_at))}</td>
            <td class="px-4 py-2.5 whitespace-nowrap align-top">
                <div class="text-xs text-ink">${esc(operator)}</div>
                ${operatorSub}
            </td>
            <td class="px-4 py-2.5 align-top">
                <div class="text-xs text-ink-muted leading-5 break-words">${esc(whatMain)}</div>
            </td>
            <td class="px-4 py-2.5 w-[132px] max-w-[132px] align-top">
                <div class="text-[11px] text-ink-muted truncate" title="${esc(objectText)}">${esc(objectText || '-')}</div>
            </td>
            <td class="px-4 py-2.5 text-center align-top">
                <div class="inline-flex whitespace-nowrap">${successBadge}</div>
                ${errorLine}
            </td>
            <td class="px-4 py-2.5 whitespace-nowrap align-top">
                <div class="text-[11px] text-ink-muted font-mono">${esc(record.client_ip || '-')}</div>
                ${locationHint}
            </td>
        </tr>
        `;
    }).join('');
}
