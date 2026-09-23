/**
 * 冲压模具费列表—对齐冲压加工费列表：HUD + 胶囊筛选 + 查看/编辑抽屉 + 批量审核/反审核/删除 + Excel 导出
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, BTN_GHOST, OPS_TH, TH_KEY, TH_TEXT, TH_NUM, TH_FOCUS, HUD_LED, BTN_SOLID } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=4';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml, paintHudKpiAlert } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=6';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

export function dieFeeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                title: '整体模具费',
                                valueHtml: '¥ <span id="dieFeeHudTotalFee">—</span>',
                                footer: [{ label: '件均', valueHtml: '¥ <span id="dieFeeHudAvgFee">—</span> / 件' }],
                            })}
                            ${hudKpiCardHtml({
                                title: '零件总条数',
                                valueHtml: '<span id="dieFeeHudTotal">—</span>',
                                unit: '条',
                                footer: [{ label: '当前项目', valueHtml: '<span id="dieFeeHudScope" class="text-ink-muted tabular-nums truncate" title="">—</span>' }],
                            })}
                            ${hudKpiCardHtml({
                                as: 'button',
                                id: 'dieFeeHudZeroCard',
                                title: '最终为零待办',
                                titleId: 'dieFeeHudZeroLabel',
                                titleAttr: '点击筛选最终模具费为 0 的行',
                                valueWrapId: 'dieFeeHudZeroValue',
                                valueHtml: '<span id="dieFeeHudZero">—</span>',
                                unit: '条',
                                glowId: 'dieFeeHudZeroGlow',
                                pulseId: 'dieFeeHudZeroDot',
                                meta: '无零价行',
                                metaId: 'dieFeeHudZeroHint',
                            })}
                            ${hudKpiCardHtml({
                                title: '审核进度',
                                valueHtml: '<span id="dieFeeHudPending">—</span>',
                                unit: '条待审',
                                footer: [{ label: '已审核', valueHtml: '<span id="dieFeeHudApproved">—</span> 条' }],
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'dieFeeMoreWrap',
                                btnId: 'dieFeeMoreBtn',
                                menuId: 'dieFeeMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'dieFeeBatchApproveBtn', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'dieFeeBatchReverseBtn', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'dieFeeBatchDeleteBtn', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="dieFeeExportBtn" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'dieFee',
                        searchId: 'dieFeeSearchBtn',
                        capsules: [
                            { capsuleId: 'dieFeeCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'dieFeeCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'dieFeeCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'dieFeeCapsuleSupplier', idleLabel: '全部供应商' },
                            { capsuleId: 'dieFeeCapsuleVersion', idleLabel: '全部版本' },
                        ],
                        extraCapsulesHtml: '<span id="dieFeeCapsuleZero" class="hidden bg-brand-hud/15 border border-brand-hud/40 text-brand-hud px-2.5 py-1 rounded-md font-bold">零价筛选中</span>',
                        fieldsHtml: [
                            filterSelect('dieFeeYearFilter', '年度'),
                            filterSelect('dieFeeLocationFilter', '基地'),
                            filterSelect('dieFeeVehicleFilter', '项目'),
                            filterSelect('dieFeeSupplierFilter', '供应商'),
                            filterSelect('dieFeeVersionFilter', '版本'),
                            filterSelect('dieFeeAuditStatusFilter', '审核状态'),
                            filterInput('dieFeePartNumberFilter', '零件号', '短号或完整零件号'),
                            `<button id="dieFeeResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '打开即查全量；年 / 基地 / 项目等为可选筛。导出须至少一筛。批量删除 / 审核 / 反审核须选定年度、基地、项目。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'dieFee',
                    minWidth: '1960px',
                    headHtml: `
                                <th class="p-0 w-0"></th>
                                <th class="${TH_TEXT} whitespace-nowrap">核价维度</th>
                                <th class="${TH_TEXT} whitespace-nowrap">供应商</th>
                                <th class="${TH_TEXT} whitespace-nowrap">版本</th>
                                <th class="${TH_KEY} whitespace-nowrap">短代码</th>
                                <th class="${TH_TEXT} whitespace-nowrap">零件</th>
                                <th class="${TH_TEXT} whitespace-nowrap border-r border-line-hud">生产方式</th>
                                <th class="${TH_NUM} whitespace-nowrap">单价</th>
                                <th class="${TH_NUM} whitespace-nowrap">分摊万台</th>
                                <th class="${TH_NUM} whitespace-nowrap">系统模具费</th>
                                <th class="${TH_NUM} whitespace-nowrap border-r border-line-hud">调整金额</th>
                                <th class="${TH_FOCUS} whitespace-nowrap">最终模具费</th>
                                <th class="${TH_TEXT} whitespace-nowrap">材质</th>
                                <th class="${TH_NUM} whitespace-nowrap">料厚</th>
                                <th class="${TH_NUM} whitespace-nowrap">重量</th>
                                <th class="${TH_TEXT} whitespace-nowrap">模具类型</th>
                                <th class="${TH_TEXT} whitespace-nowrap">备注</th>
                                <th class="${TH_TEXT} whitespace-nowrap">审核</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建时间</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改时间</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无模具费数据',
                        hint: '当前筛选下暂无模具费数据；可到「冲压模具费计算」手算，或由自动核价引擎补算',
                    },
                    loading: true,
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="dieFeeBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dieFeeBatchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="dieFeeBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeDieFeeBatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="dieFeeBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="dieFeeBatchAuditFilterSummary"></div>
                <p id="dieFeeBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="dieFeeBatchAuditOperatorLabel">操作人</label>
                    <div id="dieFeeBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">
                        —
                    </div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="dieFeeBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="dieFeeBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDieFeeBatchAuditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmDieFeeBatchAuditBtn" class="${BTN_SOLID}">
                    确认提交
                </button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="dieFeeEditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[560px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dieFeeEditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="dieFeeEditDrawerTitle">编辑模具费</span>
                </h5>
                <button type="button" id="closeDieFeeEditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="dieFeeEditDrawerContent">
                <form id="dieFeeEditForm" class="p-6 space-y-5">
                    <input type="hidden" id="dieFeeEditRecordId" value="">
                    <div class="bg-app-main border border-brand/30 p-4">
                        <label class="text-[10px] font-semibold text-brand uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            费用构成
                        </label>
                        <div class="grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 items-end mb-4">
                            <div class="bg-app-deep border border-line px-3 py-2.5">
                                <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">系统模具费</div>
                                <div id="die-fee-edit-die-fee" class="text-[15px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="pb-3 text-ink-faint font-mono text-lg font-bold">+</div>
                            <div>
                                <label class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1 block">
                                    调整金额
                                    <span class="text-ink-dim normal-case">（可正可负）</span>
                                </label>
                                <input type="text" id="dieFeeEditAdjustment" inputmode="decimal"
                                       class="w-full h-10 px-3 text-sm font-mono bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded tabular-nums text-right"
                                       placeholder="0.0000">
                            </div>
                            <div class="pb-3 text-ink-faint font-mono text-lg font-bold">=</div>
                            <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">最终模具费</div>
                                <div id="die-fee-edit-final-fee" class="text-[16px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                            </div>
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                            <textarea id="dieFeeEditRemark" rows="3" maxlength="1000"
                                      class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                                      placeholder="调整理由 / 原因"></textarea>
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-2 block">零件基本信息（只读）</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${viewRow('年度', 'die-fee-edit-year')}
                            ${viewRow('基地', 'die-fee-edit-location')}
                            ${partNumberViewBlock('die-fee-edit')}
                            ${viewRow('项目', 'die-fee-edit-vehicle')}
                            ${viewRow('供应商', 'die-fee-edit-supplier')}
                            ${viewRow('版本', 'die-fee-edit-version')}
                            ${viewRow('生产方式', 'die-fee-edit-production-mode')}
                            ${viewRow('取价档', 'die-fee-edit-price-kind')}
                        </div>
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDieFeeEditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitDieFeeEditBtn" class="${BTN_SOLID}">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="dieFeeViewDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[640px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dieFeeViewDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    模具费详情
                </h5>
                <button type="button" id="closeDieFeeViewDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="dieFeeViewDrawerContent">
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">零件基本信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'die-fee-view-year')}
                        ${viewRow('基地', 'die-fee-view-location')}
                        ${partNumberViewBlock('die-fee-view')}
                        ${viewRow('零件名称', 'die-fee-view-part-name')}
                        ${viewRow('项目', 'die-fee-view-vehicle')}
                        ${viewRow('供应商', 'die-fee-view-supplier')}
                        ${viewRow('版本', 'die-fee-view-version')}
                        ${viewRow('序号', 'die-fee-view-seq-no')}
                        ${viewRow('生产方式', 'die-fee-view-production-mode')}
                        ${viewRow('取价档', 'die-fee-view-price-kind')}
                    </div>
                </div>
                <div class="bg-app-main border border-brand/30">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                        <span class="${HUD_LED}"></span>
                        <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">费用构成</h6>
                    </div>
                    <div class="p-4">
                        <div class="grid grid-cols-3 gap-3 mb-4">
                            <div class="bg-app-deep border border-line px-3 py-2.5">
                                <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">系统模具费</div>
                                <div id="die-fee-view-die-fee" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="bg-app-deep border border-line px-3 py-2.5">
                                <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">调整金额</div>
                                <div id="die-fee-view-adjustment" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">最终模具费</div>
                                <div id="die-fee-view-final-fee" class="text-[15px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('单价(万元/吨)', 'die-fee-view-unit-price')}
                            ${viewRow('分摊(万台)', 'die-fee-view-allocation-qty')}
                            ${viewRow('备注', 'die-fee-view-remark')}
                        </div>
                    </div>
                </div>
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                        <span class="${HUD_LED}"></span>
                        <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">各序模具费溯源</h6>
                    </div>
                    <div class="overflow-x-auto" id="dieFeeViewProcessItems">
                        <div class="px-4 py-6 text-[11px] text-ink-dim">加载中..</div>
                    </div>
                </div>
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">材料 / 工艺快照</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('材质', 'die-fee-view-material')}
                        ${viewRow('料厚', 'die-fee-view-thickness')}
                        ${viewRow('零件重量', 'die-fee-view-part-weight')}
                        ${viewRow('模具类型', 'die-fee-view-die-type')}
                        ${viewRow('模具方法', 'die-fee-view-die-method')}
                        ${viewRow('来源文件', 'die-fee-view-excel-filename')}
                    </div>
                </div>
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">审核 / 元数据</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('审核状态', 'die-fee-view-audit-status')}
                        ${viewRow('审核人', 'die-fee-view-audited-by')}
                        ${viewRow('审核时间', 'die-fee-view-audited-at')}
                        ${viewRow('审核意见', 'die-fee-view-audit-remark')}
                        ${viewRow('反审核人', 'die-fee-view-reverse-by')}
                        ${viewRow('反审核时间', 'die-fee-view-reverse-at')}
                        ${viewRow('反审核意见', 'die-fee-view-reverse-remark')}
                        ${viewRow('创建人', 'die-fee-view-created-by')}
                        ${viewRow('创建时间', 'die-fee-view-created-at')}
                        ${viewRow('修改人', 'die-fee-view-updated-by')}
                        ${viewRow('修改时间', 'die-fee-view-updated-at')}
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0 flex-wrap">
                <button type="button" id="dieFeeViewDrawerEditBtn" class="${BTN_SOLID}">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>
    `;
}

export function renderDieFeeRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((row) => {
        const approved = row.audit_status === 'approved';
        const cell = 'p-3 border-b border-line-subtle font-mono text-[11px]';
        const muted = 'text-ink-muted';
        const mutedDeep = 'text-ink-dim';
        const zoneEnd = 'border-r border-line-hud';
        const finalCell = [
            'p-3 text-right font-mono font-black tabular-nums text-[13px]',
            'text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20',
            'border-b border-line-subtle',
        ].join(' ');
        const canUpdate = typeof can === 'function' ? can('op:stamping-die-fee:update') : true;
        const adj = row.adjustment_amount != null && Number(row.adjustment_amount) !== 0
            ? formatNum(row.adjustment_amount, 4)
            : '-';
        const priceKind = row.price_kind === 'progressive' ? '级进模' : '钢板模';

        const viewBtn = opsIconButtonHtml({
            extraClass: 'view-btn',
            title: '查看详情',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
        });
        const editBtn = canUpdate
            ? opsIconButtonHtml({
                extraClass: `edit-btn${approved ? ' opacity-30 pointer-events-none' : ''}`,
                title: approved ? '已审核，不可编辑' : '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            })
            : '';
        return hudRowHtml({
            attrs: `data-id="${esc(row.id)}"`,
            cellsHtml: `
            <td class="${cell} font-sans whitespace-nowrap">
                <div class="font-bold text-ink text-[12px] group-hover:text-brand-hud transition-colors">${esc(fmtYear(row.year))}</div>
                <div class="text-ink-faint text-[10px] mt-0.5">${esc(row.location)} · ${esc(row.vehicle_model)}</div>
            </td>
            <td class="${cell} ${muted} font-sans whitespace-nowrap">${esc(row.stamping_supplier)}</td>
            <td class="${cell} ${muted} font-mono whitespace-nowrap">${esc(row.version)}</td>
            <td class="${cell} font-sans whitespace-nowrap">
                ${partShortCodeCellHtml(row.part_number)}
            </td>
            <td class="${cell} font-sans overflow-hidden">
                ${partNumberNameCellHtml(row.part_number, row.part_name)}
            </td>
            <td class="${cell} ${muted} font-sans ${zoneEnd}">
                <div>${esc(row.production_mode || '—')}</div>
                <div class="text-[10px] text-ink-faint mt-0.5">${esc(priceKind)}</div>
            </td>
            <td class="${cell} text-right ${muted} tabular-nums">${formatNum(row.unit_price, 4)}</td>
            <td class="${cell} text-right ${muted} tabular-nums">${formatNum(row.allocation_qty, 0)}</td>
            <td class="${cell} text-right tabular-nums ${muted}">${formatNum(row.die_fee, 4)}</td>
            <td class="${cell} text-right ${muted} tabular-nums ${zoneEnd}">${adj}</td>
            <td class="${finalCell}">${formatNum(row.final_die_fee, 4)}</td>
            <td class="${cell} ${muted} font-sans">${esc(row.material)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.thickness, 4)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.part_weight, 4)}</td>
            <td class="${cell} ${muted} font-sans">${esc(row.die_type)}</td>
            <td class="${cell} text-[10px] text-ink-faint max-w-[160px] truncate" title="${esc(row.remark || '')}">${esc(row.remark)}</td>
            <td class="${cell}">${auditBadge(row.audit_status)}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(row.created_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.created_at))}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(row.updated_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.updated_at))}</td>`,
            opsHtml: `${viewBtn}${editBtn}`,
        });
    }).join('');
}

export function updateDieFeeHud(total, summary, onlyZeroActive = false, scopeLabel = '—') {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const totalCount = Number(data.total_count ?? total ?? 0);
    const zeroCount = Number(data.zero_count ?? 0);
    const hasZeroTodo = zeroCount > 0;

    const fmtMoney = (value) => {
        const fixed = formatDecimalFixed(value, 4, { allowNegative: true });
        return fixed == null ? '—' : withThousandsSep(fixed);
    };

    setText('dieFeeHudTotalFee', fmtMoney(data.total_fee));
    setText('dieFeeHudAvgFee', fmtMoney(data.avg_fee));
    setText('dieFeeHudTotal', totalCount.toLocaleString('zh-CN'));
    const scopeEl = document.getElementById('dieFeeHudScope');
    if (scopeEl) {
        scopeEl.textContent = scopeLabel || '—';
        scopeEl.title = scopeLabel || '';
    }
    setText('dieFeeHudZero', zeroCount.toLocaleString('zh-CN'));
    setText('dieFeeHudPending', Number(data.pending_count ?? 0).toLocaleString('zh-CN'));
    setText('dieFeeHudApproved', Number(data.approved_count ?? 0).toLocaleString('zh-CN'));

    paintHudKpiAlert('dieFeeHudZeroCard', {
        mode: hasZeroTodo ? 'alert' : 'ok',
        pressed: onlyZeroActive,
        glowId: 'dieFeeHudZeroGlow',
        pulseId: 'dieFeeHudZeroDot',
        titleId: 'dieFeeHudZeroLabel',
        valueWrapId: 'dieFeeHudZeroValue',
        hintId: 'dieFeeHudZeroHint',
    });
    const hint = document.getElementById('dieFeeHudZeroHint');
    if (hint) {
        hint.textContent = hasZeroTodo
            ? (onlyZeroActive ? '已定位零价行 · 再点取消' : '点击一键定位')
            : '无零价行';
    }

    const zeroCapsule = document.getElementById('dieFeeCapsuleZero');
    if (zeroCapsule) {
        zeroCapsule.classList.toggle('hidden', !onlyZeroActive);
    }
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-brand font-mono' : 'text-ink'} truncate"></span>
    </div>`;
}

function partNumberViewBlock(prefix) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">零件号</span>
        <span id="${prefix}-part-short"
              class="block text-xl font-mono font-bold tabular-nums text-ink tracking-[0.14em] hud-kpi-num-glow"></span>
        <span id="${prefix}-part-number" class="block text-[11px] font-mono text-ink-dim tracking-wider mt-0.5 truncate"></span>
    </div>`;
}

function auditBadge(status) {
    const label = { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '-';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm bg-app-surface text-ink-muted border border-line">${esc(label)}</span>`;
}

function formatAuditDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

function formatNum(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    return fixed == null ? '-' : withThousandsSep(fixed);
}
