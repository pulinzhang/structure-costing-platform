/**
 * BOM 焊接费列表模板 — HUD 密表
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_BACKDROP, DRAWER_SHELL, HUD_BAND, BTN_GHOST, TH_ROW, OPS_TH, HUD_LED, BTN_SOLID } from '../../../../ui/classes.js?v=11';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml, paintHudKpiAlert } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';
import {
    partShortCodeCellHtml,
    partNumberNameCellHtml,
    resolveBomNodeShortCode,
} from '../../../../domain/part-identity.js?v=5';

const AUDIT_LABEL = {
    pending: { text: '待审', cls: 'bg-warn/15 text-warn' },
    approved: { text: '已审', cls: 'bg-ok/15 text-ok' },
    rejected: { text: '已驳回', cls: 'bg-danger/15 text-danger' },
};

const CALC_LABEL = {
    ok: { text: '正常', cls: 'text-ink-muted' },
    partial: { text: '缺单价', cls: 'text-warn' },
    failed: { text: '失败', cls: 'text-danger' },
};

export function l0WeldingFeeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                title: '焊接费合计',
                                valueHtml: '¥ <span id="l0wfHudTotalFee">—</span>',
                                meta: '系统计算 + 其它费用',
                            })}
                            ${hudKpiCardHtml({
                                title: '结果条数',
                                valueHtml: '<span id="l0wfHudTotal">—</span>',
                                unit: '条',
                                footer: [{ label: '版本', valueHtml: '<span id="l0wfHudVersion" class="text-ink-muted">—</span>' }],
                            })}
                            ${hudKpiCardHtml({
                                as: 'button',
                                id: 'l0wfHudPartialCard',
                                title: '缺单价待办',
                                titleAttr: '点击筛选缺单价（partial）',
                                valueWrapId: 'l0wfHudPartialValue',
                                valueHtml: '<span id="l0wfHudPartial">—</span>',
                                unit: '条',
                                glowId: 'l0wfHudPartialGlow',
                                pulseId: 'l0wfHudPartialDot',
                                meta: '工艺行缺分年单价',
                            })}
                            ${hudKpiCardHtml({
                                title: '审核进度',
                                valueHtml: '<span id="l0wfHudPending">—</span>',
                                unit: '条待审',
                                footer: [{ label: '已审核', valueHtml: '<span id="l0wfHudApproved">—</span> 条' }],
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'l0wfMoreWrap',
                                btnId: 'l0wfMoreBtn',
                                menuId: 'l0wfMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'l0wfBatchApproveBtn', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'l0wfBatchReverseBtn', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'l0wfBatchDeleteBtn', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="l0wfExportBtn" type="button" title="按当前筛选导出"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-ink-dim border border-line-hud px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-brand-hud/50 hover:text-brand-hud transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'l0wf',
                        searchId: 'l0wfSearchBtn',
                        capsules: [
                            { capsuleId: 'l0wfCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'l0wfCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'l0wfCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'l0wfCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'l0wfCapsuleLevel', idleLabel: '全部层级' },
                        ],
                        extraCapsulesHtml: '<span id="l0wfCapsulePartial" class="hidden bg-brand-hud/15 border border-brand-hud/40 text-brand-hud px-2.5 py-1 rounded-md font-bold">缺单价筛选中</span>',
                        fieldsHtml: [
                            filterSelect('l0wfYearFilter', '年度'),
                            filterSelect('l0wfLocationFilter', '基地'),
                            filterSelect('l0wfVehicleModelFilter', '项目'),
                            filterSelect('l0wfBomVersionFilter', '版本'),
                            filterSelect('l0wfLevelFilter', '层级'),
                            filterSelect('l0wfAuditStatusFilter', '审核状态'),
                            filterInput('l0wfPartNumberFilter', '零件号', '短号或完整零件号'),
                            `<button id="l0wfResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量审核 / 反审核 / 删除须选定年度 + 基地 + 项目。版本可选，选了只处理该版本。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'l0wf',
                    bodyClass: '',
                    minWidth: '1580px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 100px;">
                            <col style="width: 110px;">
                            <col style="width: 48px;">
                            <col style="width: 72px;">
                            <col style="width: 140px;">
                            <col style="width: 200px;">
                            <col style="width: 52px;">
                            <col style="width: 52px;">
                            <col style="width: 52px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">
                            <col style="width: 96px;">
                            <col style="width: 64px;">
                            <col style="width: 64px;">
                            <col style="width: 72px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地 / 年</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目 / 版本</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">层级</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">焊接信息原文</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">工艺数</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">命中</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">缺单价</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">系统计算</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">其它费用</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">确认单价</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">计算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无焊接费数据', hint: '请先在计算页按年 / 基地 / 项目生成' },
                })}
            </div>

            <!-- 查看详情抽屉 -->
            <div id="l0wfViewBackdrop" class="${DRAWER_BACKDROP} transition-opacity duration-300" style="display:none;"></div>
            <div id="l0wfViewDrawer"
                 class="${DRAWER_SHELL} w-[640px] translate-x-full transition-transform duration-300"
                 style="display:none; max-height: 100vh">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                    <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                        <span class="${HUD_LED}"></span>
                        焊接费详情
                    </h5>
                    <button type="button" id="l0wfViewClose"
                            class="${DRAWER_CLOSE}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="l0wfViewDrawerContent">
                    <div class="bg-app-main border border-app-elevated">
                        <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                            <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">基本信息</h6>
                        </div>
                        <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('年度', 'l0wf-view-year')}
                            ${viewRow('基地', 'l0wf-view-location')}
                            ${viewRow('项目', 'l0wf-view-vehicle')}
                            ${viewRow('版本', 'l0wf-view-version')}
                            ${partNumberViewBlock('l0wf-view')}
                            ${viewRow('零件名称', 'l0wf-view-part-name')}
                            ${viewRow('顾客名称', 'l0wf-view-customer')}
                        </div>
                    </div>

                    <div class="bg-app-main border border-brand/30">
                        <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">单价构成</h6>
                        </div>
                        <div class="p-4">
                            <div class="grid grid-cols-3 gap-3 mb-4">
                                <div class="bg-app-deep border border-line px-3 py-2.5">
                                    <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">系统计算</div>
                                    <div id="l0wf-view-system-fee" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                                </div>
                                <div class="bg-app-deep border border-line px-3 py-2.5">
                                    <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">其它费用</div>
                                    <div id="l0wf-view-other-fee" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                                </div>
                                <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                    <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                    <div id="l0wf-view-final-fee" class="text-[15px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${viewRow('工艺数', 'l0wf-view-process-count')}
                                ${viewRow('命中 / 缺单价', 'l0wf-view-match-stats')}
                                ${viewRow('计算状态', 'l0wf-view-calc-status')}
                                ${viewRow('备注', 'l0wf-view-remark')}
                                <div class="col-span-2 min-w-0">
                                    <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">计算说明</span>
                                    <span id="l0wf-view-calc-message" class="block text-xs text-ink whitespace-pre-wrap break-words">—</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="bg-app-main border border-app-elevated">
                        <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">焊接信息原文</h6>
                        </div>
                        <div class="px-4 py-3">
                            <p id="l0wf-view-weld-info" class="text-[11px] text-ink-dim leading-relaxed whitespace-pre-wrap break-words mb-0">—</p>
                        </div>
                    </div>

                    <div class="bg-app-main border border-app-elevated">
                        <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">工艺明细</h6>
                        </div>
                        <div class="overflow-x-auto" id="l0wfViewProcessItems">
                            <div class="px-4 py-6 text-[11px] text-ink-dim">加载中..</div>
                        </div>
                    </div>

                    <div class="bg-app-main border border-app-elevated">
                        <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                            <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">审核 / 元数据</h6>
                        </div>
                        <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('审核状态', 'l0wf-view-audit-status')}
                            ${viewRow('审核人', 'l0wf-view-audited-by')}
                            ${viewRow('审核时间', 'l0wf-view-audited-at')}
                            ${viewRow('审核意见', 'l0wf-view-audit-remark')}
                            ${viewRow('反审核人', 'l0wf-view-reverse-by')}
                            ${viewRow('反审核时间', 'l0wf-view-reverse-at')}
                            ${viewRow('反审核意见', 'l0wf-view-reverse-remark')}
                            ${viewRow('创建人', 'l0wf-view-created-by')}
                            ${viewRow('创建时间', 'l0wf-view-created-at')}
                            ${viewRow('修改人', 'l0wf-view-updated-by')}
                            ${viewRow('修改时间', 'l0wf-view-updated-at')}
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0 flex-wrap">
                    <button type="button" id="l0wfViewEditBtn"
                            class="${BTN_SOLID}">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                        编辑
                    </button>
                </div>
            </div>

            <!-- 编辑抽屉：其它费用 / 确认单价 -->
            <div id="l0wfEditBackdrop" class="${DRAWER_BACKDROP}" style="display:none;"></div>
            <div id="l0wfEditDrawer"
                 class="${DRAWER_SHELL} w-[560px] translate-x-full transition-transform duration-300"
                 style="display:none; max-height: 100vh">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-app-surface border-b border-line">
                    <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                        <span class="${HUD_LED}"></span>
                        编辑焊接费
                    </h5>
                    <button type="button" id="l0wfEditClose"
                            class="${DRAWER_CLOSE}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6">
                    <form id="l0wfEditForm" class="space-y-5">
                        <input type="hidden" id="l0wfEditRecordId" value="">
                        <div class="bg-app-main border border-brand/30 p-4">
                            <label class="text-[10px] font-semibold text-brand uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                                <span class="${HUD_LED}"></span>
                                单价构成
                            </label>
                            <div class="grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 items-end mb-4">
                                <div class="bg-app-deep border border-line px-3 py-2.5">
                                    <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">系统计算</div>
                                    <div id="l0wf-edit-system-fee" class="text-[15px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                                </div>
                                <div class="pb-3 text-ink-faint font-mono text-lg font-bold">+</div>
                                <div>
                                    <label class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1 block">
                                        其它费用 <span class="text-ink-dim normal-case">（可正可负）</span>
                                    </label>
                                    <input type="number" id="l0wfEditOtherFee" step="0.0001"
                                           class="w-full h-10 px-3 text-sm font-mono bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded tabular-nums text-right"
                                           placeholder="0.0000">
                                </div>
                                <div class="pb-3 text-ink-faint font-mono text-lg font-bold">=</div>
                                <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                    <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                    <div id="l0wf-edit-final-fee" class="text-[16px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                                <textarea id="l0wfEditRemark" rows="3" maxlength="1000"
                                          class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded resize-none"
                                          placeholder="调整理由 / 原因"></textarea>
                            </div>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-2 block">基本信息（只读）</label>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${partNumberViewBlock('l0wf-edit')}
                                ${viewRow('零件名称', 'l0wf-edit-part-name')}
                                ${viewRow('年度', 'l0wf-edit-year')}
                                ${viewRow('基地', 'l0wf-edit-location')}
                                ${viewRow('项目', 'l0wf-edit-vehicle')}
                                ${viewRow('版本', 'l0wf-edit-version')}
                            </div>
                        </div>
                    </form>
                </div>
                <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                    <button type="button" id="l0wfEditCancel"
                            class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded hover:border-ink-muted hover:text-ink transition-all">取消</button>
                    <button type="button" id="l0wfEditSubmit"
                            class="${BTN_SOLID}">
                        ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                        保存
                    </button>
                </div>
            </div>

            <!-- 批量审核抽屉 -->
            <div id="l0wfBatchAuditBackdrop" class="${DRAWER_BACKDROP}" style="display:none;"></div>
            <div id="l0wfBatchAuditDrawer"
                 class="${DRAWER_SHELL} w-[420px] translate-x-full transition-transform duration-300"
                 style="display:none;">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-app-surface border-b border-line">
                    <h5 id="l0wfBatchAuditTitle" class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">批量审核</h5>
                    <button type="button" id="l0wfBatchAuditClose"
                            class="${DRAWER_CLOSE}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-5 space-y-4">
                    <p id="l0wfBatchAuditScope" class="text-[11px] text-ink-muted"></p>
                    <label class="block space-y-1.5">
                        <span id="l0wfBatchAuditRemarkLabel" class="text-[10px] text-ink-dim">审核意见</span>
                        <textarea id="l0wfBatchAuditRemark" rows="4"
                                  class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded-sm"
                                  placeholder="请填写审核意见（必填）"></textarea>
                    </label>
                </div>
                <div class="px-5 py-3 border-t border-line-subtle flex justify-end gap-2 shrink-0">
                    <button type="button" id="l0wfBatchAuditCancel"
                            class="h-8 px-4 text-[11px] text-ink-muted border border-line rounded hover:text-ink hover:border-ink-muted">取消</button>
                    <button type="button" id="l0wfBatchAuditSubmit"
                            class="${BTN_SOLID}">确认</button>
                </div>
            </div>
        </div>
    `;
}



function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-brand font-mono' : 'text-ink'} truncate">—</span>
    </div>`;
}

function partNumberViewBlock(prefix) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">零件号</span>
        <span id="${prefix}-part-short"
              class="hud-kpi-num-glow block text-xl font-mono font-bold tabular-nums text-ink tracking-[0.14em]">—</span>
        <span id="${prefix}-part-number" class="block text-[11px] font-mono text-ink-dim tracking-wider mt-0.5 truncate"></span>
    </div>`;
}

/** HUD 只用 API filters.summary（筛选全量），禁止用本页 items 加总。 */
export function updateL0WeldingFeeHud(summary = {}, versionLabel = '—') {
    const set = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const totalFee = data.total_fee != null ? fmtNum(data.total_fee, 4) : '—';
    set('l0wfHudTotalFee', totalFee);
    set('l0wfHudTotal', data.total_count != null ? String(data.total_count) : '—');
    set('l0wfHudPending', data.pending_count != null ? String(data.pending_count) : '—');
    set('l0wfHudApproved', data.approved_count != null ? String(data.approved_count) : '—');
    set('l0wfHudVersion', versionLabel || '—');

    const partial = Number(data.partial_count) || 0;
    set('l0wfHudPartial', String(partial));
    paintHudKpiAlert('l0wfHudPartialCard', {
        mode: partial > 0 ? 'alert' : 'aux',
        shell: false,
        glowId: 'l0wfHudPartialGlow',
        pulseId: 'l0wfHudPartialDot',
        valueWrapId: 'l0wfHudPartialValue',
    });
}

export function updateL0WeldingFeeFilterCapsules(state) {
    document.getElementById('l0wfCapsulePartial')?.classList.toggle('hidden', !state.onlyPartial);
    const countEl = document.getElementById('l0wfAdvancedFilterCount');
    if (!countEl || !state.onlyPartial) return;
    const match = /^\((\d+)\)$/.exec((countEl.textContent || '').trim());
    const counted = match ? Number(match[1]) : 0;
    countEl.textContent = `(${counted + 1})`;
}

export function renderL0WeldingFeeRows(records) {
    if (!records.length) return '';
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
    const canUpdate = typeof can === 'function' ? can('op:bom-welding-fee-list:update') : true;
    return records.map((row) => {
        const audit = AUDIT_LABEL[row.audit_status] || { text: row.audit_status || '-', cls: 'text-ink-muted' };
        const calc = CALC_LABEL[row.calc_status] || { text: row.calc_status || '-', cls: 'text-ink-muted' };
        const shortNo = resolveBomNodeShortCode(row.part_number, { level: row.level });
        const systemFee = row.total_welding_fee != null ? fmtNum(row.total_welding_fee, 4) : '-';
        const otherFee = row.other_fee != null && Number(row.other_fee) !== 0
            ? fmtNum(row.other_fee, 4)
            : '-';
        const finalFee = row.final_welding_fee != null
            ? fmtNum(row.final_welding_fee, 4)
            : systemFee;
        const approved = row.audit_status === 'approved';
        const weld = (row.weld_info_raw || '').trim();
        const detailBtn = opsIconButtonHtml({
            action: 'detail',
            title: '明细',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
            attrs: `data-id="${esc(row.id)}"`,
        });
        const editBtn = canUpdate
            ? opsIconButtonHtml({
                action: 'edit',
                extraClass: approved ? 'opacity-30 pointer-events-none' : '',
                title: approved ? '已审核，不可编辑' : '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                attrs: `data-id="${esc(row.id)}"`,
            })
            : '';
        return hudRowHtml({
            cellsHtml: `
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-ink font-semibold truncate">${esc(row.location || '-')}</div>
                    <div class="text-[9px] text-ink-faint">${esc(fmtYear(row.year))}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-ink-muted truncate">${esc(row.vehicle_model || '-')}</div>
                    <div class="text-[9px] text-ink-faint">${esc(row.bom_version || '-')}</div>
                </td>
                <td class="px-1 py-2 text-center font-mono text-[10px] text-ink-muted">L${esc(row.level ?? 0)}</td>
                <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                    ${partShortCodeCellHtml(row.part_number, shortNo)}
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    ${partNumberNameCellHtml(row.part_number, row.part_name)}
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-ink-faint truncate" title="${esc(weld || '')}">${esc(weld || '—')}</div>
                </td>
                <td class="${numCell}">${esc(row.process_line_count ?? 0)}</td>
                <td class="${numCell}">${esc(row.matched_line_count ?? 0)}</td>
                <td class="${numCell} ${Number(row.missing_price_count) > 0 ? 'text-warn' : ''}">${esc(row.missing_price_count ?? 0)}</td>
                <td class="${numCell}">${esc(systemFee)}</td>
                <td class="${numCell}">${esc(otherFee)}</td>
                <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">${esc(finalFee)}</td>
                <td class="px-1 py-2 text-center text-[9px] ${calc.cls}">${calc.text}</td>
                <td class="px-1 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${audit.cls}">${audit.text}</span>
                </td>`,
            opsHtml: `${detailBtn}${editBtn}`,
        });
    }).join('');
}


export function renderFeeDetailItems(items) {
    if (!items?.length) {
        return `<div class="px-4 py-8 text-center text-[11px] text-ink-faint">无工艺明细</div>`;
    }
    const matchMap = {
        matched: { text: '已匹配', cls: 'text-ok' },
        missing_price: { text: '缺单价', cls: 'text-warn' },
        unmapped: { text: '未映射', cls: 'text-ink-muted' },
    };
    const rows = items.map((item) => {
        const m = matchMap[item.match_status] || { text: item.match_status || '-', cls: 'text-ink-muted' };
        return `
            <tr class="border-b border-line-subtle hover:bg-app-rowhover transition-colors">
                <td class="px-3 py-2 text-[10px] text-ink-muted">${esc(item.standard_process_name || item.process_token || '-')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-ink-muted">${esc(fmtNum(item.process_qty, 4))} ${esc(item.process_qty_unit || '')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-ink-muted">${item.unit_price != null ? esc(fmtNum(item.unit_price, 4)) : '-'}</td>
                <td class="px-3 py-2 text-[10px] text-ink-faint">${esc(item.unit || '-')}</td>
                <td class="px-3 py-2 text-right font-mono text-[10px] tabular-nums text-brand-hud">${item.line_fee != null ? esc(fmtNum(item.line_fee, 4)) : '-'}</td>
                <td class="px-3 py-2 text-center text-[9px] ${m.cls}">${m.text}</td>
            </tr>
        `;
    }).join('');
    return `
        <table class="w-full border-collapse">
            <thead>
                <tr class="${TH_ROW}">
                    <th class="px-3 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">标准工艺</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">过程量</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">单价</th>
                    <th class="px-3 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">单位</th>
                    <th class="px-3 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">行费</th>
                    <th class="px-3 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">匹配</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}
