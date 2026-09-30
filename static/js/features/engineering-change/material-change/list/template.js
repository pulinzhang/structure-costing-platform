/**
 * 材料变更列表 — 按变更单行；删除即整本回滚并物理删除
 */

import { filterSelect, HUD_SHELL, DRAWER_CLOSE, DRAWER_BACKDROP, DRAWER_SHELL, HUD_FILTER, FILTER_LABEL, HUD_BAND, OPS_TH, BTN_GHOST } from '../../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';


export function materialChangeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="grid grid-cols-2 gap-3 font-mono">
                        ${hudKpiCardHtml({
                            title: '查询范围',
                            valueKind: 'text',
                            valueId: 'ecmListHudScope',
                            valueHtml: '全部范围',
                        })}
                        ${hudKpiCardHtml({
                            title: '零件',
                            valueId: 'ecmListHudTotal',
                            valueHtml: '—',
                            meta: '每个零件一行，不是上传了几本',
                        })}
                    </div>
                    <p class="mt-3 text-[10px] text-ink-dim leading-snug tracking-wide">
                        一本 Excel 里每个零件一行。删除会撤销这一整本，同一文件里的零件一起去掉。
                    </p>
                </div>
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'ecm',
                        searchId: 'ecmListSearchBtn',
                        capsules: [
                            { capsuleId: 'ecmCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'ecmCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'ecmCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'ecmCapsuleStatus', idleLabel: '全部状态' },
                        ],
                        fieldsHtml: [
                            filterSelect('ecmListYearFilter', '年度'),
                            filterSelect('ecmListMonthFilter', '月份'),
                            filterSelect('ecmListLocationFilter', '基地'),
                            filterSelect('ecmListVehicleFilter', '项目'),
                            `<label class="space-y-1">
                                <span class="${FILTER_LABEL}">状态</span>
                                <select id="ecmListStatusFilter" class="w-36 ${HUD_FILTER}">
                                    <option value="">全部</option>
                                    <option value="pending">进行中</option>
                                    <option value="success">成功</option>
                                    <option value="failed">失败</option>
                                </select>
                            </label>`,
                            `<button id="ecmListResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '点删除会撤销这一整本材料变更，并删掉这条记录。同一文件里的零件一起去掉。',
                    })}
                </div>
                ${hudTableHtml({
                    prefix: 'ecm',
                    minWidth: '1480px',
                    colgroupHtml: `
                            <col style="width: 8px">
                            <col style="width: 72px">
                            <col style="width: 108px">
                            <col style="width: 160px">
                            <col style="width: 96px">
                            <col style="width: 120px">
                            <col style="width: 120px">
                            <col style="width: 88px">
                            <col style="width: 88px">
                            <col style="width: 88px">
                            <col style="width: 140px">
                            <col style="width: 72px">
                            <col style="width: 132px">
                            <col style="width: 56px">
                            <col style="width: 80px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目 / 生效</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">冲压工厂</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">版本</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">变更前 / 后材料</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">变更前 / 后料厚</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">互换性</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">源文件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">上传人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">上传时间</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无记录', hint: '请先上传材料变更，或调整筛选条件' },
                    loading: true,
                })}
            </div>
        </div>
        ${detailDrawerHtml()}
    `;
}

function periodText(row) {
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

function thicknessText(value) {
    if (value == null || value === '') return '';
    const text = String(value);
    if (!text.includes('.')) return text;
    return text.replace(/\.?0+$/, '');
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

export function renderEcmListRows(records, { canDelete }) {
    if (!records.length) return '';
    return records.map((row) => {
        const logId = Number(row.upload_log_id);
        const canDeleteRow = canDelete && logId && row.status !== 'pending';
        const project = row.vehicle_model || '—';
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
                title: '删除（撤销这一整本）',
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
                <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.stamping_supplier || '')}">${esc(row.stamping_supplier || '—')}</td>
                <td class="px-2 py-2 text-ink-muted truncate font-mono">${esc(row.change_version || '—')}</td>
                <td class="px-2 py-2 text-ink truncate font-mono" title="${esc(row.part_number || '')}">${esc(row.part_number || '—')}</td>
                <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(row.after_material, row.before_material)}</td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(thicknessText(row.after_thickness), thicknessText(row.before_thickness))}</td>
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.interchangeability || '—')}</td>
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
        <div class="hidden ${DRAWER_BACKDROP}" id="ecmDetailDrawerBackdrop"></div>
        <div class="hidden ${DRAWER_SHELL} w-[480px]" id="ecmDetailDrawer">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-app-elevated">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    材料变更详情
                </h5>
                <button type="button" id="ecmDetailCloseBtn" class="${DRAWER_CLOSE}">
                    ${window.svgIcon('x-lg', 'w-4 h-4')}
                </button>
            </div>
            <div id="ecmDetailBody" class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4 font-mono"></div>
        </div>
    `;
}

function operatorMessage(message) {
    const text = String(message || '').trim();
    const legacy = text.match(/^材料变更成功：(\d+) 行切点$/);
    if (legacy) return `材料变更成功，改了 ${legacy[1]} 个零件。`;
    return text;
}

export function renderEcmDetailBody(row) {
    const status = row.status || '';
    const isFailed = status === 'failed';
    const reasonTitle = isFailed ? '失败原因' : '说明';
    const message = operatorMessage(row.message);
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
