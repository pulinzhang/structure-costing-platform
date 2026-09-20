/**
 * 工程变更单列表 — HUD 密表；按变更单行；删除即整本回滚并物理删除
 */

import { paginationBarHtml } from '../../../page-size.js?v=3';

const STATUS_LABELS = {
    pending: '进行中',
    success: '成功',
    failed: '失败',
};

export function engineeringChangeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="grid grid-cols-2 gap-3 font-mono">
                        <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                            <div class="text-[#555555] text-[10px] tracking-wider">查询范围</div>
                            <div class="text-[14px] font-bold text-[#FFFFFF] mt-1 truncate" id="ecListHudScope">全部范围</div>
                        </div>
                        <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">变更单行</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums" id="ecListHudTotal">—</div>
                                <div class="text-[9px] text-[#6E6E73] mt-2 leading-snug">变化记录条数，不是换树数量，也不是采购件数量</div>
                        </div>
                    </div>
                    <p class="mt-3 text-[10px] text-[#6E6E73] leading-snug tracking-wide">
                        变更单 → 树坑 → 树 → 换树 → 盖章 → 数采购件（本页只数变更单）
                    </p>
                </div>
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="ecCapsulePeriod" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部期间</span>
                                <span id="ecCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="ecCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="ecCapsuleStatus" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部状态</span>
                                <span id="ecCapsuleChangeType" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部变更类型</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="ecToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="ecAdvancedFilterLabel">展开高级筛选</span>
                                <span id="ecAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="ecListSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>
                    <div id="ecAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('ecListYearFilter', '年度')}
                            ${filterSelect('ecListMonthFilter', '月份')}
                            ${filterSelect('ecListLocationFilter', '基地')}
                            ${filterSelect('ecListVehicleFilter', '项目')}
                            <label class="space-y-1">
                                <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">状态</span>
                                <select id="ecListStatusFilter" class="w-36 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
                                    <option value="">全部</option>
                                    <option value="pending">进行中</option>
                                    <option value="success">成功</option>
                                    <option value="failed">失败</option>
                                </select>
                            </label>
                            <label class="space-y-1">
                                <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">变更类型</span>
                                <select id="ecListChangeTypeFilter" class="w-36 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
                                    <option value="">全部</option>
                                    <option value="完成停止">完成停止</option>
                                    <option value="改图">改图</option>
                                    <option value="增加零件">增加零件</option>
                                    <option value="此件不装">此件不装</option>
                                </select>
                            </label>
                            <button id="ecListResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">删除即回滚：撤销本次上传的全部变更，并物理删除本记录。同一文件的全部变更单行一起去掉。</p>
                    </div>
                </div>
                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-separate border-spacing-0" style="min-width: 1420px;">
                        <colgroup>
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
                            <col style="width: 80px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目 / 生效</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">变更前 / 后总成</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">序号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">总成名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">变更类型</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">层级</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">变更前 / 后零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#3a3a3a]">源文件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">上传人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">上传时间</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555] sticky right-0 z-[3] bg-[#0B0B0D] shadow-[-8px_0_12px_rgba(0,0,0,0.55)]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="ecListTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>
                ${paginationBarHtml({ infoId: 'ecListTotalLabel', selectId: 'ecListPageSize', buttonsId: 'ecListPagination' })}
                <div id="ecListEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 id="ecListEmptyTitle" class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无记录</h5>
                    <p id="ecListEmptyHint" class="text-[10px] text-[#555555]">请先上传工程变更，或调整筛选条件</p>
                </div>
                <div id="ecListLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
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
        pending: { text: '进行中', cls: 'text-[#ffb74d]' },
        success: { text: '成功', cls: 'text-[#8E8E93]' },
        failed: { text: '失败', cls: 'text-[#FF1E27] font-bold' },
    };
    const item = map[status] || { text: status || '—', cls: 'text-[#555555]' };
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
        <div class="text-[#F0F0F2] truncate" title="${esc(afterText)}">${esc(afterText)}</div>
        <div class="text-[9px] text-[#555555] mt-0.5 truncate" title="${esc(beforeText)}">前 ${esc(beforeText)}</div>`;
    }
    const only = afterText || beforeText || '—';
    return `<div class="text-[#F0F0F2] truncate" title="${esc(only)}">${esc(only)}</div>`;
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
            ? `<button type="button"
                    class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                    data-action="view" data-upload-log-id="${logId}" title="查看" aria-label="查看">
                    ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                </button>`
            : '';
        const deleteBtn = canDeleteRow
            ? `<button type="button"
                    class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                    data-action="delete" data-upload-log-id="${logId}" title="删除（整次回滚）" aria-label="删除">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                </button>`
            : '';
        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.location || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="font-semibold text-[#F0F0F2] truncate" title="${esc(project)}">${esc(project)}</div>
                    <div class="text-[9px] text-[#555555] mt-0.5 tabular-nums">${periodText(row)}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(row.after_assembly_part_number, row.before_assembly_part_number)}</td>
                <td class="px-2 py-2 text-center text-[#8E8E93]">${row.seq_no != null ? esc(row.seq_no) : '—'}</td>
                <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.assembly_name || '')}">${esc(row.assembly_name || '—')}</td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.change_type || '—')}</td>
                <td class="px-2 py-2 text-center text-[#8E8E93]">${esc(row.part_level || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">${stackedPair(row.after_part_number, row.before_part_number)}</td>
                <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[9px] text-[#3a3a3a] truncate" title="${esc(filename)}">${esc(filename)}</div>
                </td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.created_by || '—')}</td>
                <td class="px-2 py-2 text-[9px] text-[#3a3a3a] whitespace-nowrap overflow-hidden">${esc(formatUploadTime(row.created_at))}</td>
                <td class="px-2 py-2 text-center">${statusBadge(row.status)}</td>
                <td class="px-1 py-2 text-center whitespace-nowrap sticky right-0 z-[2] bg-[#0A0A0C] group-hover:bg-[#161620] shadow-[-8px_0_12px_rgba(0,0,0,0.45)]">${viewBtn}${deleteBtn}</td>
            </tr>
        `;
    }).join('');
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" class="w-36 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">全部</option>
        </select>
    </label>`;
}

export function updateEcFilterCapsules() {
    const year = document.getElementById('ecListYearFilter')?.value || '';
    const month = document.getElementById('ecListMonthFilter')?.value || '';
    const location = document.getElementById('ecListLocationFilter')?.value || '';
    const vehicle = document.getElementById('ecListVehicleFilter')?.value || '';
    const status = document.getElementById('ecListStatusFilter')?.value || '';
    const changeType = document.getElementById('ecListChangeTypeFilter')?.value || '';
    const active = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idle = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const periodEl = document.getElementById('ecCapsulePeriod');
    const locationEl = document.getElementById('ecCapsuleLocation');
    const vehicleEl = document.getElementById('ecCapsuleVehicle');
    const statusEl = document.getElementById('ecCapsuleStatus');
    const changeTypeEl = document.getElementById('ecCapsuleChangeType');
    const countEl = document.getElementById('ecAdvancedFilterCount');

    if (periodEl) {
        const periodText = year && month && typeof fmtPeriod === 'function'
            ? fmtPeriod(year, month)
            : (year && typeof fmtYear === 'function' ? fmtYear(year) : (year || ''));
        if (periodText) {
            periodEl.textContent = periodText;
            periodEl.className = active;
        } else {
            periodEl.textContent = '全部期间';
            periodEl.className = idle;
        }
    }
    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? active : idle;
    }
    if (vehicleEl) {
        vehicleEl.textContent = vehicle || '全部项目';
        vehicleEl.className = vehicle ? active : idle;
    }
    if (statusEl) {
        statusEl.textContent = STATUS_LABELS[status] || '全部状态';
        statusEl.className = status ? active : idle;
    }
    if (changeTypeEl) {
        changeTypeEl.textContent = changeType || '全部变更类型';
        changeTypeEl.className = changeType ? active : idle;
    }
    if (countEl) {
        countEl.textContent = `(${[year, month, location, vehicle, status, changeType].filter(Boolean).length})`;
    }
}

function detailDrawerHtml() {
    return `
        <div class="hidden fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="ecDetailDrawerBackdrop"></div>
        <div class="hidden fixed inset-y-0 right-0 z-[85] w-[480px] max-w-full bg-[#121212] border-l border-[#1A1A22] flex flex-col"
             id="ecDetailDrawer" style="box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#262626]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#FF1E27;display:inline-block;"></span>
                    工程变更详情
                </h5>
                <button type="button" id="ecDetailCloseBtn"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
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
                <div class="text-[9px] tracking-wider mb-2 ${isFailed ? 'text-[#FF1E27]' : 'text-[#555555]'}">${reasonTitle}</div>
                <div class="text-[13px] text-[#F0F0F2] whitespace-pre-wrap leading-relaxed">${esc(message)}</div>
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
                <div class="text-[9px] text-[#555555] tracking-wider mb-1">当时 Excel</div>
                <div class="text-[11px] text-[#8E8E93] truncate" title="${esc(filename)}">${esc(filename)}</div>
            </div>
            <button type="button" data-action="download" data-upload-log-id="${logId}" data-filename="${esc(filename)}"
                    class="inline-flex items-center gap-1 h-8 px-2.5 text-[11px] rounded-md text-[#555555] hover:text-white hover:bg-[#d32f2f] transition-all shrink-0"
                    title="下载" aria-label="下载">
                ${window.svgIcon('download', 'w-3.5 h-3.5')}
                下载
            </button>
        </div>
        <div class="pt-3 space-y-1">
            <div class="text-[9px] text-[#3a3a3a] truncate">上传人 ${esc(createdBy)}</div>
            <div class="text-[9px] text-[#3a3a3a] tabular-nums">上传时间 ${esc(createdAt)}</div>
        </div>
    `;
}

