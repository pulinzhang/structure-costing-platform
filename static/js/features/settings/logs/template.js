/**
 * 操作日志 — 与用户管理同一套设置页表格（非 HUD）
 */

import { paginationBarHtml } from '../../../ui/page-size.js?v=11';
import { BTN_GHOST, filterSelect, filterInput } from '../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../ui/filter-bar.js?v=6';

export function logsTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-ink-muted">
            <div class="bg-app-main border border-line">

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="flex items-center justify-end mb-3">
                        <button id="btnExportLogs"
                                class="${BTN_GHOST}">
                            ${window.svgIcon('download', 'w-3.5 h-3.5')}
                            导出
                        </button>
                    </div>
                    ${filterBarHtml({
                        prefix: 'logs',
                        searchId: 'btnFilter',
                        capsules: [
                            { capsuleId: 'logsCapsuleUsername', idleLabel: '全部账号' },
                            { capsuleId: 'logsCapsuleIp', idleLabel: '全部 IP' },
                            { capsuleId: 'logsCapsuleMenu', idleLabel: '全部功能' },
                            { capsuleId: 'logsCapsulePermission', idleLabel: '全部动作' },
                            { capsuleId: 'logsCapsuleSuccess', idleLabel: '全部结果' },
                            { capsuleId: 'logsCapsuleCreated', idleLabel: '全部时间' },
                        ],
                        fieldsHtml: [
                            filterInput('filterUsername', '账号 / 操作人', '账号 / 操作人', { widthClass: 'w-full sm:w-36' }),
                            filterInput('filterClientIp', 'IP 地址', 'IP 地址', { widthClass: 'w-full sm:w-36' }),
                            filterSelect('filterMenu', '功能', { emptyLabel: '全部功能', widthClass: 'w-full sm:w-52' }),
                            filterSelect('filterPermission', '动作', { emptyLabel: '全部动作', widthClass: 'w-full sm:w-44' }),
                            filterSelect('filterSuccess', '结果', {
                                emptyLabel: '全部结果',
                                options: [
                                    { value: 'true', label: '成功' },
                                    { value: 'false', label: '失败' },
                                ],
                            }),
                            filterInput('filterCreatedFrom', '开始时间', '', { type: 'datetime-local', widthClass: 'w-full sm:w-44' }),
                            filterInput('filterCreatedTo', '结束时间', '', { type: 'datetime-local', widthClass: 'w-full sm:w-44' }),
                            `<button id="btnResetFilter" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[720px] text-left text-xs border-collapse">
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

                ${paginationBarHtml({ infoId: 'totalCountPagination', selectId: 'logsPageSize', buttonsId: 'paginationBtns', wrapperId: 'paginationContainer', wrapperClass: 'flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-t border-line-subtle bg-app-deep' })}

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
