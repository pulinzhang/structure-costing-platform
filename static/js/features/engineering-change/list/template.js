/**
 * 工程变更单列表 — HUD 密表；按变更单行；删除即整本回滚并物理删除
 */

import { filterSelect, HUD_SHELL, DRAWER_CLOSE, DRAWER_BACKDROP, DRAWER_SHELL, HUD_FILTER, FILTER_LABEL, HUD_BAND, OPS_TH, BTN_GHOST } from '../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../ui/filter-bar.js?v=4';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../ui/hud-kpi.js?v=1';


const STATUS_LABELS = {
    pending: '进行中',
    success: '成功',
    failed: '失败',
};

export function engineeringChangeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="grid grid-cols-2 gap-3 font-mono">
                        ${hudKpiCardHtml({
                            title: '查询范围',
                            valueKind: 'text',
                            valueId: 'ecListHudScope',
                            valueHtml: '全部范围',
                        })}
                        ${hudKpiCardHtml({
                            title: '变更单行',
                            valueId: 'ecListHudTotal',
                            valueHtml: '—',
                            meta: '变化记录条数，不是换树数量，也不是采购件数量',
                        })}
                    </div>
                    <p class="mt-3 text-[10px] text-ink-dim leading-snug tracking-wide">
                        变更单 → 树坑 → 树 → 换树 → 盖章 → 数采购件（分总成和冲压件以新版本号存在了新树上）
                    </p>
                </div>
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'ec',
                        searchId: 'ecListSearchBtn',
                        capsules: [
                            { capsuleId: 'ecCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'ecCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'ecCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'ecCapsuleStatus', idleLabel: '全部状态' },
                            { capsuleId: 'ecCapsuleChangeType', idleLabel: '全部变更类型' },
                        ],
                        fieldsHtml: [
                            filterSelect('ecListYearFilter', '年度'),
                            filterSelect('ecListMonthFilter', '月份'),
                            filterSelect('ecListLocationFilter', '基地'),
                            filterSelect('ecListVehicleFilter', '项目'),
                            `<label class="space-y-1">
                                <span class="${FILTER_LABEL}">状态</span>
                                <select id="ecListStatusFilter" class="w-36 ${HUD_FILTER}">
                                    <option value="">全部</option>
                                    <option value="pending">进行中</option>
                                    <option value="success">成功</option>
                                    <option value="failed">失败</option>
                                </select>
                            </label>`,
                            `<label class="space-y-1">
                                <span class="${FILTER_LABEL}">变更类型</span>
                                <select id="ecListChangeTypeFilter" class="w-36 ${HUD_FILTER}">
                                    <option value="">全部</option>
                                    <option value="完成停止">完成停止</option>
                                    <option value="改图">改图</option>
                                    <option value="增加零件">增加零件</option>
                                    <option value="此件不装">此件不装</option>
                                </select>
                            </label>`,
                            `<button id="ecListResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '删除即回滚：撤销本次上传的全部变更，并物理删除本记录。同一文件的全部变更单行一起去掉。',
                    })}
                </div>
                ${hudTableHtml({
                    prefix: 'ec',
                    minWidth: '1420px',
                    colgroupHtml: `
                            <col style="width: 8px">
                            <col style="width: 72px">
                            <col style="width: 120px">
                            <col style="width: 148px">
                            <col style="width: 52px">
                            <col style="width: 120px">
                            <col style="width: 88px">
                            <col style="width: 64px">
                            <col style="width: 148px">
                            <col style="width: 120px">
                            <col style="width: 140px">
                            <col style="width: 80px">
                            <col style="width: 132px">
                            <col style="width: 72px">
                            <col style="width: 80px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目 / 生效</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">变更前 / 后总成</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">序号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">总成名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">变更类型</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">层级</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">变更前 / 后零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">源文件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">上传人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">上传时间</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无记录', hint: '请先上传工程变更，或调整筛选条件' },
                    loading: true,
                })}
            </div>
        </div>
        ${detailDrawerHtml()}
    `;
}

function periodText(row) {
    if (row.effective_period_text) {
        return esc(row.effective_period_text);
    }
    if (typeof fmtPeriod === 'function') {
        return fmtPeriod(row.effective_year, row.effective_month);
    }
    return `${esc(row.effective_year)}年${String(row.effective_month).padStart(2, '0')}月`;
}

function statusBadge(status) {
    const map = {
        pending: { text: '进行中', cls: 'text-warn' },
        success: { text: '成功', cls: 'text-ink-muted' },
        failed: { text: '失败', cls: 'text-brand-hud font-bold' },
    };
    const item = map[status] || { text: status || '—', cls: 'text-ink-faint' };
    return `<span class="text-[9px] ${item.cls}">${esc(item.text)}</span>`;
}

function formatUploadTime(value) {
    if (!value) return '—';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

function stackedPair(afterValue, beforeValue) {
    const afterText = afterValue || '';
    const beforeText = beforeValue || '';
    if (afterText && beforeText) {
        return `
        <div class="text-ink truncate" title="${esc(afterText)}">${esc(afterText)}</div>
        <div class="text-[9px] text-ink-faint mt-0.5 truncate" title="${esc(beforeText)}">前 ${esc(beforeText)}</div>`;
    }
    const only = afterText || beforeText || '—';
    return `<div class="text-ink truncate" title="${esc(only)}">${esc(only)}</div>`;
}

export function renderEcListRows(records, { canDelete }) {
    if (!records.length) {
        return '';
    }
    return records.map((row) => {
        const logId = Number(row.upload_log_id);
        const canDeleteRow = canDelete && logId && row.status !== 'pending';
        const project = row.project_code || row.vehicle_model || '—';
        const filename = row.original_filename || '—';
        const viewBtn = logId
            ? opsIconButtonHtml({
                action: 'view',
                title: '查看',
                icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
                attrs: `data-upload-log-id="${logId}"`,
            })
            : '';
        const deleteBtn = canDeleteRow
            ? opsIconButtonHtml({
                action: 'delete',
                title: '删除（整次回滚）',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                danger: true,
                attrs: `data-upload-log-id="${logId}"`,
            })
            : '';
        return hudRowHtml({
            cellsHtml: `
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.location || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="font-semibold text-ink truncate" title="${esc(project)}">${esc(project)}</div>
                    <div class="text-[9px] text-ink-faint mt-0.5 tabular-nums">${periodText(row)}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(row.after_assembly_part_number, row.before_assembly_part_number)}</td>
                <td class="px-2 py-2 text-center text-ink-muted">${row.seq_no != null ? esc(row.seq_no) : '—'}</td>
                <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.assembly_name || '')}">${esc(row.assembly_name || '—')}</td>
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.change_type || '—')}</td>
                <td class="px-2 py-2 text-center text-ink-muted">${esc(row.part_level || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(row.after_part_number, row.before_part_number)}</td>
                <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[9px] text-ink-faint truncate" title="${esc(filename)}">${esc(filename)}</div>
                </td>
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.created_by || '—')}</td>
                <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">${esc(formatUploadTime(row.created_at))}</td>
                <td class="px-2 py-2 text-center">${statusBadge(row.status)}</td>`,
            opsHtml: `${viewBtn}${deleteBtn}`,
        });
    }).join('');
}


function detailDrawerHtml() {
    return `
        <div class="hidden ${DRAWER_BACKDROP}" id="ecDetailDrawerBackdrop"></div>
        <div class="hidden ${DRAWER_SHELL} w-[480px]"
             id="ecDetailDrawer">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-app-elevated">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    工程变更详情
                </h5>
                <button type="button" id="ecDetailCloseBtn"
                        class="${DRAWER_CLOSE}">
                    ${window.svgIcon('x-lg', 'w-4 h-4')}
                </button>
            </div>
            <div id="ecDetailBody" class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4 font-mono"></div>
        </div>
    `;
}

export function renderEcDetailBody(row) {
    const status = row.status || '';
    const isFailed = status === 'failed';
    const reasonTitle = isFailed ? '失败原因' : '说明';
    const message = String(row.message || '').trim();
    const reasonSection = message
        ? `<div>
                <div class="text-[9px] tracking-wider mb-2 ${isFailed ? 'text-brand-hud' : 'text-ink-faint'}">${reasonTitle}</div>
                <div class="text-[13px] text-ink whitespace-pre-wrap leading-relaxed">${esc(message)}</div>
           </div>`
        : '';
    const filename = row.original_filename || '—';
    const logId = Number(row.upload_log_id) || 0;
    const createdBy = row.created_by || '—';
    const createdAt = formatUploadTime(row.created_at);
    return `
        ${reasonSection}
        <div class="flex items-center justify-between gap-3 ${message ? 'pt-2' : ''}">
            <div class="min-w-0">
                <div class="text-[9px] text-ink-faint tracking-wider mb-1">当时 Excel</div>
                <div class="text-[11px] text-ink-muted truncate" title="${esc(filename)}">${esc(filename)}</div>
            </div>
            <button type="button" data-action="download" data-upload-log-id="${logId}" data-filename="${esc(filename)}"
                    class="inline-flex items-center gap-1 h-8 px-2.5 text-[11px] rounded-md text-ink-faint hover:text-ink hover:bg-brand transition-all shrink-0"
                    title="下载" aria-label="下载">
                ${window.svgIcon('download', 'w-3.5 h-3.5')}
                下载
            </button>
        </div>
        <div class="pt-3 space-y-1">
            <div class="text-[9px] text-ink-faint truncate">上传人 ${esc(createdBy)}</div>
            <div class="text-[9px] text-ink-faint tabular-nums">上传时间 ${esc(createdAt)}</div>
        </div>
    `;
}

