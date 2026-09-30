/**
 * Tonnage Price List Template
 * 冲次单价列表 — Brabus HUD（与钢材联动价 / 加工费列表对齐）
 * 数据来自上传，无「新增」入口；批量操作范围 = 上传条件（基地 + 年度）
 */

import { HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_GHOST, filterSelect, HUD_LED, BTN_SOLID, BTN_SOLID_DANGER } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=7';

/** 格式化为固定 3 位小数字符串；非法值返回 '-'。 */
export function formatPricePerStroke3(value) {
    return formatDecimalFixed(value, 3) ?? '-';
}

export function pricePerStrokeInputValue(value) {
    return formatDecimalFixed(value, 3) ?? '';
}

/** 校验并规范输入为 3 位小数字符串；失败返回 null。 */
export function parsePricePerStrokeInput(raw) {
    return parseDecimalInput(raw, 3);
}

export function tonnagePriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({ title: '记录条数', valueHtml: '<span id="tonnageHudTotal">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '待审', valueHtml: '<span id="tonnageHudPending">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '已审', valueHtml: '<span id="tonnageHudApproved">—</span>', unit: '条' })}
                        </div>
                        <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
                            ${moreMenuShellHtml({
                                wrapId: 'tonnageMoreWrap',
                                btnId: 'tonnageMoreBtn',
                                menuId: 'tonnageMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'btnBatchApproveTonnage', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchReverseTonnage', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchDeleteTonnagePrice', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="btnExportTonnagePrice" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'tonnage',
                        searchId: 'btnFilter',
                        capsules: [
                            { capsuleId: 'tonnageCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'tonnageCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'tonnageCapsuleAudit', idleLabel: '全部审核' },
                        ],
                        fieldsHtml: [
                            filterSelect('yearFilter', '年度'),
                            filterSelect('locationFilter', '基地'),
                            filterSelect('auditStatusFilter', '审核状态'),
                            `<button id="tonnageResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量删除、审核、反审核要同时选基地和年度。已经审核的不能删、不能改。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'tonnage',
                    bodyId: 'tonnagePriceTableBody',
                    minWidth: '1100px',
                    colgroupHtml: `
                            <col style="width:2px">
                            <col style="width:16%">
                            <col style="width:10%">
                            <col style="width:14%">
                            <col style="width:14%">
                            <col style="width:10%">
                            <col style="width:8%">
                            <col style="width:8%">
                            <col style="width:10%">
                            <col style="width:10%">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">年份</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">压机吨位 (T)</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">单冲次价格</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">创建人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">创建时间</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">修改人</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无冲次单价数据', hint: '请先在「冲次单价上传」中导入 Excel' },
                    loading: true,
                })}
            </div>
        </div>

        ${batchAuditDrawerHtml('tonnage')}
        ${editDrawerHtml()}
        ${deleteDrawerHtml()}
    `;
}

function batchAuditDrawerHtml(prefix) {
    return `
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="${prefix}BatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="${prefix}BatchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="${prefix}BatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="close${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="${prefix}BatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="${prefix}BatchAuditFilterSummary"></div>
                <p id="${prefix}BatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="${prefix}BatchAuditOperatorLabel">操作人</label>
                    <div id="${prefix}BatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">—</div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="${prefix}BatchAuditRemarkLabel">审核意见</label>
                    <textarea id="${prefix}BatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancel${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirm${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditBtn" class="${BTN_SOLID}">确认提交</button>
            </div>
        </div>
    `;
}

function editDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[560px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="editDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase" id="editDrawerTitle">
                    <span class="${HUD_LED}"></span>
                    编辑价格
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto" id="editDrawerContent">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">基地</label>
                            <input type="text" id="editLocation" disabled
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">年份</label>
                            <input type="number" id="editYear" disabled
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">压机吨位 (T)</label>
                        <input type="number" id="editTonnage" disabled
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">单冲次价格 <span class="text-brand">*</span></label>
                        <input type="text" id="editPrice" inputmode="decimal" required
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink font-mono rounded focus:outline-none focus:border-brand-active"
                               placeholder="保留3位小数，如 0.564" autocomplete="off">
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelEditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitEditBtn" class="${BTN_SOLID}">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>
    `;
}

function deleteDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[380px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="deleteDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    确认删除
                </h5>
                <button type="button" id="closeDeleteDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="deleteRecordId" value="">
                <p class="text-[12px] text-ink-muted mb-3">确定删除这条未审核记录吗？</p>
                <p class="text-[11px] text-ink-dim">已审核记录不可删除。此操作不可撤销。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmDeleteBtn" class="${BTN_SOLID_DANGER}">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}


export function updateTonnageHud(summary) {
    const data = summary && typeof summary === 'object' ? summary : {};
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    setText('tonnageHudTotal', String(data.total_count ?? '—'));
    setText('tonnageHudPending', String(data.pending_count ?? '—'));
    setText('tonnageHudApproved', String(data.approved_count ?? '—'));
}

export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const canUpdate = typeof can === 'function' ? can('op:stamping-tonnage:update') : true;
    const canDelete = typeof can === 'function' ? can('op:stamping-tonnage:delete') : true;
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';

    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const editBtn = canUpdate
            ? opsIconButtonHtml({
                extraClass: `edit-btn${approved ? ' opacity-30 pointer-events-none' : ''}`,
                title: approved ? '已审核，不可编辑' : '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            })
            : '';
        const deleteBtn = canDelete && !approved
            ? opsIconButtonHtml({
                extraClass: 'delete-btn',
                danger: true,
                title: '删除',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            })
            : '';
        return hudRowHtml({
            attrs: `data-id="${esc(record.id)}"`,
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-semibold text-ink">${esc(record.location)}</div>
            </td>
            <td class="px-2 py-2 text-ink-muted tabular-nums">${esc(fmtYear(record.year))}</td>
            <td class="${numCell} text-ink-muted font-semibold">${esc(record.tonnage)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                ${esc(formatPricePerStroke3(record.price_per_stroke))}
            </td>
            <td class="px-2 py-2 text-center">${auditBadge(record.audit_status)}</td>
            <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">${esc(record.created_by)}</td>
            <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">${esc(formatAuditDateTime(record.created_at))}</td>
            <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">${esc(record.updated_by)}</td>`,
            opsHtml: `${editBtn}${deleteBtn}`,
        });
    }).join('');
}


function auditBadge(status) {
    const label = { pending: '待审', approved: '已通过' }[status] || status || '-';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm bg-app-surface text-ink-muted border border-line">${esc(label)}</span>`;
}

function formatAuditDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}
