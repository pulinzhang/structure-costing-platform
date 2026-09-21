/**
 * 包装运输费列表 — Brabus HUD
 * 批量操作范围 = 基地 + 年度 + 项目
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_GHOST, BTN_SOLID, BTN_SOLID_DANGER } from '../../../../ui/classes.js?v=11';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

export function formatFee4(value) {
    return formatDecimalFixed(value, 4) ?? '-';
}

export function feeInputValue(value) {
    return formatDecimalFixed(value, 4) ?? '';
}

export function parseFeeInput(raw) {
    return parseDecimalInput(raw, 4);
}


export function pkgTransportFeeTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({ title: '记录条数', valueHtml: '<span id="pkgHudTotal">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '待审', valueHtml: '<span id="pkgHudPending">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '已审', valueHtml: '<span id="pkgHudApproved">—</span>', unit: '条' })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'pkgMoreWrap',
                                btnId: 'pkgMoreBtn',
                                menuId: 'pkgMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'btnBatchApprovePkg', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchReversePkg', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchDeletePkg', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="btnExportPkg" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-ink-dim border border-line-hud px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-brand-hud/50 hover:text-brand-hud transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')} Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'pkg',
                        searchId: 'btnFilterPkg',
                        capsules: [
                            { capsuleId: 'pkgCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'pkgCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'pkgCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'pkgCapsuleAudit', idleLabel: '全部审核' },
                            { capsuleId: 'pkgCapsuleKeyword', idleLabel: '零件号/名称' },
                        ],
                        fieldsHtml: [
                            filterSelect('pkgYearFilter', '年度'),
                            filterSelect('pkgLocationFilter', '基地'),
                            filterSelect('pkgVehicleFilter', '项目'),
                            filterSelect('pkgAuditStatusFilter', '审核状态'),
                            filterInput('pkgKeywordFilter', '零件号/名称', '模糊搜索', { widthClass: 'w-40' }),
                            `<button id="pkgResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量删除 / 审核 / 反审核须同时选定基地、年度和项目。已审核不可删除、不可修改。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'pkg',
                    bodyId: 'pkgTransportFeeTableBody',
                    minWidth: '1400px',
                    colgroupHtml: `
                            <col style="width:2px">
                            <col style="width:7%">
                            <col style="width:5%">
                            <col style="width:6%">
                            <col style="width:6%">
                            <col style="width:12%">
                            <col style="width:8%">
                            <col style="width:6%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:8%">
                            <col style="width:6%">
                            <col style="width:5%">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">年份</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">包装类型</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">包装费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">运输费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">维护费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">其它</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">合计</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">创建人</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        showIcon: false,
                        title: '暂无包装运输费数据',
                        hint: '请先在「包装运输费上传」中导入 Excel',
                    },
                    loading: true,
                })}
            </div>
        </div>

        ${batchAuditDrawerHtml()}
        ${detailDrawerHtml()}
        ${editDrawerHtml()}
        ${deleteDrawerHtml()}
    `;
}

function batchAuditDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="pkgBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="pkgBatchAuditDrawer" style="display:none; max-height:100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    <span id="pkgBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closePkgBatchAuditDrawer" class="w-8 h-8 text-ink-dim hover:text-ink hover:bg-brand rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="pkgBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="pkgBatchAuditFilterSummary"></div>
                <p id="pkgBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">操作人</label>
                    <div id="pkgBatchAuditOperatorDisplay" class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">—</div>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="pkgBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="pkgBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink rounded resize-none focus:outline-none focus:border-brand-active"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgBatchAuditBtn" class="px-4 py-2 text-[11px] text-ink-muted border border-line rounded">取消</button>
                <button type="button" id="confirmPkgBatchAuditBtn" class="${BTN_SOLID}">确认提交</button>
            </div>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="pkgDetailDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[520px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="pkgDetailDrawer" style="display:none; max-height:100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    包装运输费明细
                </h5>
                <button type="button" id="closePkgDetailDrawer" class="w-8 h-8 text-ink-dim hover:text-ink hover:bg-brand rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6" id="pkgDetailDrawerBody"></div>
        </div>
    `;
}

function editDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="pkgEditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[520px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="pkgEditDrawer" style="display:none; max-height:100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    编辑包装运输费
                </h5>
                <button type="button" id="closePkgEditDrawer" class="w-8 h-8 text-ink-dim hover:text-ink hover:bg-brand rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-3">
                <input type="hidden" id="pkgEditId">
                <div class="text-[11px] text-ink-muted" id="pkgEditScopeHint"></div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">产品名称</label>
                    <input id="pkgEditPartName" type="text" maxlength="200" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active">
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">包装类型</label>
                    <input id="pkgEditPackagingType" type="text" maxlength="50" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">单件包装费 *</label>
                        <input id="pkgEditPackagingFee" type="text" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded font-mono focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">单件运输费 *</label>
                        <input id="pkgEditTransportFee" type="text" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded font-mono focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">器具维护费 *</label>
                        <input id="pkgEditMaintFee" type="text" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded font-mono focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">其它费用 *</label>
                        <input id="pkgEditOtherFee" type="text" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded font-mono focus:outline-none focus:border-brand-active">
                    </div>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">包装运输费合计 *</label>
                    <input id="pkgEditTotal" type="text" class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-brand-hud rounded font-mono font-semibold focus:outline-none focus:border-brand-active">
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                    <textarea id="pkgEditRemark" rows="3" class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink rounded resize-none focus:outline-none focus:border-brand-active"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgEditBtn" class="px-4 py-2 text-[11px] text-ink-muted border border-line rounded">取消</button>
                <button type="button" id="confirmPkgEditBtn" class="${BTN_SOLID}">保存</button>
            </div>
        </div>
    `;
}

function deleteDrawerHtml() {
    return `
        <div class="${DRAWER_BACKDROP}" id="pkgDeleteDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="pkgDeleteDrawer" style="display:none; max-height:100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;display:inline-block"></span>
                    删除确认
                </h5>
                <button type="button" id="closePkgDeleteDrawer" class="w-8 h-8 text-ink-dim hover:text-ink hover:bg-brand rounded-md">×</button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="pkgDeleteId">
                <p class="text-xs text-ink-muted" id="pkgDeleteHint">确定删除该条包装运输费吗？此操作不可恢复。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgDeleteBtn" class="px-4 py-2 text-[11px] text-ink-muted border border-line rounded">取消</button>
                <button type="button" id="confirmPkgDeleteBtn" class="${BTN_SOLID_DANGER}">确认删除</button>
            </div>
        </div>
    `;
}

export function updatePkgHud(summary = {}) {
    const set = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = v == null ? '—' : String(v);
    };
    set('pkgHudTotal', summary.total_count);
    set('pkgHudPending', summary.pending_count);
    set('pkgHudApproved', summary.approved_count);
}

function auditBadge(status) {
    if (status === 'approved') {
        return '<span class="inline-flex px-1.5 py-0.5 text-[9px] font-medium rounded bg-ok/20 text-ok">已通过</span>';
    }
    return '<span class="inline-flex px-1.5 py-0.5 text-[9px] font-medium rounded bg-warn/20 text-warn">待审</span>';
}

const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';

export function renderTableRows(records) {
    const canUpdate = typeof can === 'function' ? can('op:bom-packaging-transport-fee:update') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-packaging-transport-fee:delete') : true;

    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const editBtn = canUpdate && !approved
            ? opsIconButtonHtml({
                action: 'edit',
                extraClass: 'pkg-edit-btn',
                title: '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                attrs: `data-id="${record.id}"`,
            })
            : '';
        const delBtn = canDelete && !approved
            ? opsIconButtonHtml({
                action: 'delete',
                extraClass: 'pkg-delete-btn',
                danger: true,
                title: '删除',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                attrs: `data-id="${record.id}"`,
            })
            : '';
        const detailBtn = opsIconButtonHtml({
            action: 'detail',
            extraClass: 'pkg-detail-btn',
            title: '明细',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
            attrs: `data-id="${record.id}"`,
        });

        return hudRowHtml({
            cellsHtml: `
            <td class="px-2 py-2 text-ink overflow-hidden truncate">${esc(record.location)}</td>
            <td class="px-2 py-2 text-ink-muted">${esc(fmtYear(record.year))}</td>
            <td class="px-2 py-2 text-ink overflow-hidden truncate">${esc(record.vehicle_model)}</td>
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                ${partShortCodeCellHtml(record.part_number)}
            </td>
            <td class="px-2 py-2 overflow-hidden">
                ${partNumberNameCellHtml(record.part_number, record.part_name)}
            </td>
            <td class="px-2 py-2 text-ink-muted overflow-hidden truncate">${esc(record.packaging_type || '—')}</td>
            <td class="${numCell}">${esc(formatFee4(record.unit_packaging_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.unit_transport_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.fixture_maint_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.other_fee))}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                ${esc(formatFee4(record.packaging_transport_total))}
            </td>
            <td class="px-1 py-2 text-center">${auditBadge(record.audit_status)}</td>
            <td class="px-2 py-2 text-[9px] text-ink-faint truncate">${esc(record.created_by || '—')}</td>`,
            opsHtml: `${detailBtn}${editBtn}${delBtn}`,
        });
    }).join('');
}


export function renderDetailBody(record) {
    const row = (label, value) => `
        <div class="flex justify-between gap-3 border-b border-line-subtle py-2">
            <span class="text-[10px] text-ink-dim shrink-0">${label}</span>
            <span class="text-[11px] text-ink text-right font-mono break-all">${esc(value ?? '—')}</span>
        </div>`;
    return `
        <div class="space-y-1">
            ${row('基地', record.location)}
            ${row('年度', fmtYear(record.year))}
            ${row('项目', record.vehicle_model)}
            ${row('零件号', record.part_number)}
            ${row('产品', record.part_name)}
            ${row('包装类型', record.packaging_type)}
            ${row('单包装数', record.pieces_per_pack)}
            ${row('器具 L×W×H', [record.fixture_length_mm, record.fixture_width_mm, record.fixture_height_mm].every((v) => v == null) ? null : `${record.fixture_length_mm ?? '-'}×${record.fixture_width_mm ?? '-'}×${record.fixture_height_mm ?? '-'}`)}
            ${row('器具总投入', record.total_fixture_qty)}
            ${row('器具单价', formatFee4(record.fixture_unit_price))}
            ${row('投入总金额', formatFee4(record.fixture_invest_amount))}
            ${row('往返运输价', formatFee4(record.round_trip_transport_price))}
            ${row('单件包装费', formatFee4(record.unit_packaging_fee))}
            ${row('单件运输费', formatFee4(record.unit_transport_fee))}
            ${row('器具维护费', formatFee4(record.fixture_maint_fee))}
            ${row('其它费用', formatFee4(record.other_fee))}
            ${row('包装运输费合计', formatFee4(record.packaging_transport_total))}
            ${row('审核状态', record.audit_status === 'approved' ? '已通过' : '待审')}
            ${row('来源文件', record.excel_filename)}
            ${row('工作表', record.sheet_name)}
            ${row('Excel 行号', record.excel_row)}
            ${row('备注', record.remark)}
        </div>`;
}
