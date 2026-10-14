/**
 * 文件溯源 — HUD 密表 + 筛选 + 详情抽屉
 */

import { HUD_SHELL, OPS_TH, DRAWER_BACKDROP, BTN_GHOST, filterSelect, filterInput } from '../../ui/classes.js?v=15';
import { filterBarHtml } from '../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../ui/hud-table.js?v=3';


const CATEGORY_BADGE = 'inline-flex items-center px-2 py-0.5 text-[9px] font-semibold tracking-[0.06em] border border-line-hud text-ink-muted bg-app-main';

const FILE_STATUS_LABEL = {
    active: '当前文件',
    superseded: '已被新文件替换',
    missing: '文件缺失',
};

export function fileTraceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'ft',
                        searchId: 'ftBtnSearch',
                        capsules: [
                            { capsuleId: 'ftCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'ftCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'ftCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'ftCapsuleCategory', idleLabel: '全部分类' },
                            { capsuleId: 'ftCapsuleCreator', idleLabel: '全部上传人' },
                            { capsuleId: 'ftCapsuleFilename', idleLabel: '全部文件名' },
                            { capsuleId: 'ftCapsuleUploaded', idleLabel: '全部上传时间' },
                        ],
                        fieldsHtml: [
                            filterSelect('ftFilterYear', '年度', { emptyLabel: '全部年度' }),
                            filterSelect('ftFilterMonth', '月份', { emptyLabel: '全部月份' }),
                            filterSelect('ftFilterLocation', '基地', { emptyLabel: '全部基地' }),
                            filterSelect('ftFilterVehicle', '项目', { emptyLabel: '全部项目' }),
                            filterSelect('ftFilterCategory', '分类', { emptyLabel: '全部分类' }),
                            filterSelect('ftFilterCreator', '上传人', { emptyLabel: '全部上传人' }),
                            filterInput('ftFilterFilename', '文件名', '模糊搜索原件名', { widthClass: 'w-full sm:w-44' }),
                            filterInput('ftFilterFrom', '上传时间起', '', { type: 'date', widthClass: 'w-full sm:w-36' }),
                            filterInput('ftFilterTo', '上传时间止', '', { type: 'date', widthClass: 'w-full sm:w-36' }),
                            `<button id="ftBtnReset" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                <div id="ftNoCategoryHint" class="hidden px-5 py-16 text-center border-b border-line-subtle">
                    <div class="text-ink-muted text-sm mb-2">当前账号没有可查看的文件分类。</div>
                    <div class="text-ink-faint text-xs">由管理员开通对应菜单后可查看。</div>
                </div>

                ${hudTableHtml({
                    prefix: 'ft',
                    wrapId: 'ftTableWrap',
                    minWidth: '980px',
                    colgroupHtml: `
                            <col style="width: 4px;">
                            <col style="width: 110px;">
                            <col style="width: 220px;">
                            <col style="width: 240px;">
                            <col style="width: 80px;">
                            <col style="width: 90px;">
                            <col style="width: 140px;">
                            <col style="width: 90px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">分类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">原件名</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">范围</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">大小</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">上传人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">上传时间</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                })}
            </div>
        </div>

        <div id="ftDrawerBackdrop" class="hidden ${DRAWER_BACKDROP}"></div>
        <aside id="ftDrawer" class="fixed top-0 right-0 h-full w-full max-w-md bg-app-main border-l border-line z-[85] translate-x-full transition-transform duration-200 overflow-y-auto">
            <div class="flex items-center justify-between px-5 py-4 border-b border-line-subtle">
                <div>
                    <h3 class="text-sm font-semibold text-ink">文件详情</h3>
                </div>
                <button id="ftDrawerClose" type="button" class="w-8 h-8 inline-flex items-center justify-center text-ink-muted hover:text-ink border border-line rounded">×</button>
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
        return `<tr><td colspan="8" class="px-4 py-16 text-center text-ink-faint text-xs">暂无溯源文件</td></tr>`;
    }

    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
    return items.map((item) => hudRowHtml({
        attrs: `data-id="${item.id}"`,
        cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <span class="${CATEGORY_BADGE}">${esc(item.file_category_label || item.file_category)}</span>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-ink font-semibold truncate" title="${esc(item.original_filename)}">${esc(item.original_filename)}</div>
                <div class="text-[9px] text-ink-faint truncate">${esc(item.extension || '')}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-ink-muted truncate" title="${esc(item.scope_text || '')}">${esc(item.scope_text || '-')}</td>
            <td class="${numCell}">${esc(item.file_size_text || fmtNum(item.file_size, 0))}</td>
            <td class="px-2 py-2 text-[10px] text-ink-muted truncate">${esc(item.created_by)}</td>
            <td class="px-2 py-2 text-[10px] text-ink-muted">${esc(formatDateTime(item.created_at))}</td>`,
        opsHtml: `${opsIconButtonHtml({
            action: 'detail',
            title: '详情',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
            attrs: `data-id="${item.id}"`,
        })}${opsIconButtonHtml({
            action: 'download',
            title: '下载',
            icon: window.svgIcon('download', 'w-3.5 h-3.5'),
            attrs: `data-id="${item.id}"`,
        })}`,
    })).join('');
}


export function renderDrawerDetail(item) {
    const rows = [
        ['分类', item.file_category_label || item.file_category],
        ['原件名', item.original_filename],
        ['范围', item.scope_text || '-'],
        ['校验码', item.file_hash],
        ['大小', item.file_size_text || `${item.file_size} B`],
        ['扩展名', item.extension],
        ['上传人', item.created_by],
        ['上传时间', formatDateTime(item.created_at)],
        ['状态', FILE_STATUS_LABEL[item.status] || item.status || '-'],
    ];
    const canDownload = typeof can === 'function' && can('op:file-trace:download');
    return `
        <dl class="space-y-3">
            ${rows.map(([label, value]) => `
                <div>
                    <dt class="text-[9px] text-ink-faint tracking-[0.08em] mb-1">${esc(label)}</dt>
                    <dd class="text-[11px] text-ink font-mono break-all">${esc(value)}</dd>
                </div>
            `).join('')}
        </dl>
        ${canDownload ? `
            <button id="ftDrawerDownload" type="button" data-id="${item.id}"
                    class="w-full inline-flex items-center justify-center gap-2 bg-brand-hud text-ink-onbrand px-4 py-2 text-xs font-semibold rounded hover:bg-brand-hover transition-all mt-4">
                ${window.svgIcon('download', 'w-3.5 h-3.5')}
                下载原件
            </button>
        ` : ''}
    `;
}
