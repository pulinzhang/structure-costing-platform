/**
 * Stamping Process Fee List Template
 * 冲压加工费计算结果浏览—Brabus Carbon & Precision Dark
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, BTN_GHOST, OPS_TH, HUD_KPI_AUX, TH_KEY, TH_TEXT, TH_NUM, TH_FOCUS, HUD_LED } from '../../../../ui/classes.js?v=8';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=2';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=3';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

export function processFeeListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <!-- HUD 战术数据看板 + 操作 -->
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            <!-- 1. 整体加工费：管理者成本大盘 -->
                            <div class="${HUD_KPI_AUX} backdrop-blur-sm">
                                <div class="text-ink-faint text-[10px] tracking-wider">整体加工费</div>
                                <div class="text-[22px] font-black text-ink mt-1 tracking-tight tabular-nums leading-none">
                                    ¥ <span id="feeHudTotalFee">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-ink-dim mt-2 flex items-center justify-between gap-2">
                                    <span>件均</span>
                                    <span class="text-ink-muted tabular-nums">¥ <span id="feeHudAvgFee">—</span> / 件</span>
                                </div>
                            </div>
                            <!-- 2. 零件总条数：批次规模 -->
                            <div class="${HUD_KPI_AUX} backdrop-blur-sm">
                                <div class="text-ink-faint text-[10px] tracking-wider">零件总条数</div>
                                <div class="text-[22px] font-black text-ink mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="feeHudTotal">—</span>
                                    <span class="text-[10px] text-ink-faint ml-1 font-bold">条</span>
                                </div>
                                <div class="text-[9px] font-mono text-ink-dim mt-2 flex items-center justify-between gap-2">
                                    <span>当前版本</span>
                                    <span id="feeHudVersion" class="text-ink-muted tabular-nums">—</span>
                                </div>
                            </div>
                            <!-- 3. 算费失败待办：操作员核心工作台（有待办才红晕） -->
                            <button type="button" id="feeHudZeroCard"
                                    class="text-left w-full p-3.5 relative overflow-hidden group transition-all duration-200 cursor-pointer
                                           bg-app-main/80 border border-line-hud backdrop-blur-sm
                                           hover:border-line-hud focus:outline-none focus-visible:border-brand-hud/60"
                                    title="点击筛选算费失败 / 零价待补价行"
                                    aria-pressed="false">
                                <div id="feeHudZeroGlow" class="hidden absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-brand-hud to-transparent hud-kpi-line-glow"></div>
                                <div class="flex justify-between items-start">
                                    <span id="feeHudZeroLabel" class="text-ink-faint text-[10px] font-bold tracking-widest">算费失败待办</span>
                                    <span id="feeHudZeroDot" class="hidden w-2 h-2 rounded-full bg-brand-hud animate-pulse hud-kpi-dot-glow"></span>
                                </div>
                                <div id="feeHudZeroValue" class="text-[26px] font-black text-ink-dim font-mono mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="feeHudZero">—</span>
                                    <span class="text-[10px] ml-1 font-bold opacity-70">条</span>
                                </div>
                                <div id="feeHudZeroHint" class="text-[9px] font-mono text-ink-faint mt-2">
                                    规则运行完备
                                </div>
                            </button>
                            <!-- 4. 审核进度：出账 / 封盘条件 -->
                            <div class="${HUD_KPI_AUX} backdrop-blur-sm">
                                <div class="text-ink-faint text-[10px] tracking-wider">审核进度</div>
                                <div class="text-[22px] font-black text-ink mt-1 tracking-tight tabular-nums leading-none">
                                    <span id="feeHudPending">—</span>
                                    <span class="text-[10px] text-ink-faint ml-1 font-bold">条待审</span>
                                </div>
                                <div class="text-[9px] font-mono text-ink-dim mt-2 flex items-center justify-between gap-2">
                                    <span>已审核</span>
                                    <span class="text-ink-muted tabular-nums"><span id="feeHudApproved">—</span> 条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'feeMoreWrap',
                                btnId: 'feeMoreBtn',
                                menuId: 'feeMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'feeBatchApproveBtn', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'feeBatchReverseBtn', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'feeBatchDeleteBtn', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="feeExportBtn" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 战术胶囊筛选栏：默认收起，抹平 ERP 模版意-->
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'fee',
                        searchId: 'feeSearchBtn',
                        capsules: [
                            { capsuleId: 'feeCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'feeCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'feeCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'feeCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'feeCapsuleSupplier', idleLabel: '全部工厂' },
                        ],
                        extraCapsulesHtml: '<span id="feeCapsuleFailTodo" class="hidden bg-brand-hud/15 border border-brand-hud/40 text-brand-hud px-2.5 py-1 rounded-md font-bold">待补价筛选中</span>',
                        fieldsHtml: [
                            filterSelect('feeYearFilter', '年度'),
                            filterSelect('feeLocationFilter', '基地'),
                            filterSelect('feeVehicleFilter', '项目'),
                            filterSelect('feeVersionFilter', '版本'),
                            filterSelect('feeSupplierFilter', '冲压工厂'),
                            filterSelect('feeAuditStatusFilter', '审核状态'),
                            filterInput('feePartNumberFilter', '零件号', '短号或完整零件号'),
                            `<button id="feeResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '筛选均可选；级联为年度 → 基地 → 项目 → 版本 → 冲压工厂。批量审核 / 反审核按整车签字。批量删除可按工厂收窄。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'fee',
                    minWidth: '2100px',
                    headHtml: `
                                <th class="p-0 w-0"></th>
                                <th class="${TH_TEXT} whitespace-nowrap">核价维度</th>
                                <th class="${TH_KEY} whitespace-nowrap">短代码</th>
                                <th class="${TH_TEXT} whitespace-nowrap">零件</th>
                                <th class="${TH_TEXT} whitespace-nowrap border-r border-line-hud">项目/版本</th>
                                <th class="${TH_NUM} whitespace-nowrap">工序数</th>
                                <th class="${TH_NUM} whitespace-nowrap">系统计算</th>
                                <th class="${TH_NUM} whitespace-nowrap border-r border-line-hud">其它费用</th>
                                <th class="${TH_FOCUS} whitespace-nowrap">确认单价</th>
                                <th class="${TH_TEXT} whitespace-nowrap">材质</th>
                                <th class="${TH_NUM} whitespace-nowrap">料厚</th>
                                <th class="${TH_NUM} whitespace-nowrap">重量</th>
                                <th class="${TH_NUM} whitespace-nowrap">料片长</th>
                                <th class="${TH_NUM} whitespace-nowrap">料片审</th>
                                <th class="${TH_TEXT} whitespace-nowrap">模具/工艺</th>
                                <th class="${TH_TEXT} whitespace-nowrap">备注</th>
                                <th class="${TH_TEXT} whitespace-nowrap">审核</th>
                                <th class="${TH_TEXT} whitespace-nowrap">说明</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建时间</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改时间</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无加工费数据', hint: '请先在「冲压加工费计算」中执行计算' },
                    loading: true,
                })}
            </div>
        </div>

        <!-- 批量审核 / 反审核抽屉-->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="feeBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="feeBatchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="hud-led"></span>
                    <span id="feeBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeFeeBatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="feeBatchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="feeBatchAuditFilterSummary"></div>
                <p id="feeBatchAuditHint" class="text-[11px] text-ink-dim"></p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="feeBatchAuditOperatorLabel">操作人</label>
                    <div id="feeBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">
                        —
                    </div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="feeBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="feeBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelFeeBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded hover:border-ink-muted hover:text-ink transition-all">取消</button>
                <button type="button" id="confirmFeeBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-brand text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-brand-hover transition-all">
                    确认提交
                </button>
            </div>
        </div>

        <!-- 编辑抽屉：其它费用 / 确认单价 -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="feeEditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[560px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="feeEditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="hud-led"></span>
                    <span id="feeEditDrawerTitle">编辑加工费</span>
                </h5>
                <button type="button" id="closeFeeEditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="feeEditDrawerContent">
                <form id="feeEditForm" class="p-6 space-y-5">
                    <input type="hidden" id="feeEditRecordId" value="">
                    <!-- 关注区：系统计算 + 其它费用 = 确认单价 -->
                    <div class="bg-app-main border border-brand/30 p-4">
                        <label class="text-[10px] font-semibold text-brand uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            单价构成
                        </label>
                        <div id="feeEditTailorWeldHint"
                             class="hidden mb-3 px-3 py-2 border border-brand-hud/30 bg-brand-hud/10">
                            <div class="text-[10px] font-semibold tracking-[0.08em] text-brand-hud">拼焊件</div>
                            <div class="text-[10px] text-ink-muted mt-1 leading-relaxed">
                                系统计算不含拼焊费，请在「其它费用」录入拼焊费（可正可负）。
                            </div>
                        </div>
                        <div class="grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 items-end mb-4">
                            <div class="bg-app-deep border border-line px-3 py-2.5">
                                <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">系统计算</div>
                                <div id="fee-edit-processing-fee" class="text-[15px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="pb-3 text-ink-faint font-mono text-lg font-bold">+</div>
                            <div>
                                <label class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1 block">
                                    其它费用
                                    <span id="feeEditOtherFeeHint" class="text-ink-dim normal-case">（可正可负）</span>
                                </label>
                                <input type="number" id="feeEditOtherFee" step="0.001"
                                       class="w-full h-10 px-3 text-sm font-mono bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded tabular-nums text-right"
                                       placeholder="0.000">
                            </div>
                            <div class="pb-3 text-ink-faint font-mono text-lg font-bold">=</div>
                            <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                <div id="fee-edit-final-fee" class="text-[16px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                            </div>
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                            <textarea id="feeEditRemark" rows="3" maxlength="1000"
                                      class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                                      placeholder="调整理由 / 原因"></textarea>
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-2 block">零件基本信息（只读）</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${viewRow('年度', 'fee-edit-year')}
                            ${viewRow('基地', 'fee-edit-location')}
                            ${viewRow('冲压工厂', 'fee-edit-supplier')}
                            ${partNumberViewBlock('fee-edit')}
                            ${viewRow('零件类型', 'fee-edit-part-type')}
                            ${viewRow('项目', 'fee-edit-vehicle')}
                            ${viewRow('版本', 'fee-edit-version')}
                        </div>
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelFeeEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-4 py-2 text-[11px] font-medium rounded hover:border-ink-muted hover:text-ink transition-all">取消</button>
                <button type="button" id="submitFeeEditBtn" class="inline-flex items-center gap-1.5 bg-brand text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-brand-hover transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <!-- 查看详情抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="feeViewDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[640px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="feeViewDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="hud-led"></span>
                    加工费详情
                </h5>
                <button type="button" id="closeFeeViewDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="feeViewDrawerContent">
                <!-- 关注区：零件标识 + 加工费结果-->
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">零件基本信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'fee-view-year')}
                        ${viewRow('基地', 'fee-view-location')}
                        ${viewRow('冲压工厂', 'fee-view-supplier')}
                        ${partNumberViewBlock('fee-view')}
                        ${viewRow('零件名称', 'fee-view-part-name')}
                        ${viewRow('零件类型', 'fee-view-part-type')}
                        ${viewRow('项目', 'fee-view-vehicle')}
                        ${viewRow('版本', 'fee-view-version')}
                        ${viewRow('序号', 'fee-view-seq-no')}
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
                                <div id="fee-view-processing-fee" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="bg-app-deep border border-line px-3 py-2.5">
                                <div class="text-[9px] text-ink-faint tracking-[0.08em] uppercase mb-1">其它费用</div>
                                <div id="fee-view-other-fee" class="text-[14px] font-mono font-bold tabular-nums text-ink-muted text-right">—</div>
                            </div>
                            <div class="bg-brand-hud/10 border border-brand-hud/30 px-3 py-2.5">
                                <div class="text-[9px] text-brand-hud/90 tracking-[0.08em] uppercase mb-1">确认单价</div>
                                <div id="fee-view-final-fee" class="text-[15px] font-mono font-black tabular-nums text-brand-hud text-right">—</div>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('工序数', 'fee-view-process-count')}
                        ${viewRow('计算失败原因', 'fee-view-fail-reason')}
                        ${viewRow('备注', 'fee-view-remark')}
                        </div>
                    </div>
                </div>
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle flex items-center gap-2">
                        <span class="${HUD_LED}"></span>
                        <h6 class="text-[10px] font-semibold text-brand tracking-wider uppercase">工序单价溯源</h6>
                    </div>
                    <div class="overflow-x-auto" id="feeViewProcessItems">
                        <div class="px-4 py-6 text-[11px] text-ink-dim">加载中..</div>
                    </div>
                </div>
                <!-- 材料 / 工艺快照：自动化着重显示-->
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">材料 / 工艺快照</h6>
                    </div>
                    <div class="p-4 space-y-4">
                        <div class="border border-brand/35 bg-app-deep p-3">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="${HUD_LED}"></span>
                                <span class="text-[9px] font-semibold text-brand uppercase tracking-[0.12em]">关键工艺</span>
                            </div>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${viewRow('工艺方法', 'fee-view-process-method')}
                                ${viewRow('自动匹', 'fee-view-automation', true)}
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('材质', 'fee-view-material')}
                            ${viewRow('料厚', 'fee-view-thickness')}
                            ${viewRow('零件重量', 'fee-view-part-weight')}
                            ${viewRow('料片长', 'fee-view-sheet-length')}
                            ${viewRow('料片审', 'fee-view-sheet-width')}
                            ${viewRow('可制件数', 'fee-view-parts-per-sheet')}
                            ${viewRow('板料类型', 'fee-view-sheet-type')}
                            ${viewRow('模具类型', 'fee-view-die-type')}
                            ${viewRow('来源文件', 'fee-view-excel-filename')}
                            ${viewRow('零件备注', 'fee-view-part-remark')}
                        </div>
                    </div>
                </div>
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">审核 / 元数据</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('审核状态', 'fee-view-audit-status')}
                        ${viewRow('审核人', 'fee-view-audited-by')}
                        ${viewRow('审核时间', 'fee-view-audited-at')}
                        ${viewRow('审核意见', 'fee-view-audit-remark')}
                        ${viewRow('反审核人', 'fee-view-reverse-by')}
                        ${viewRow('反审核时间', 'fee-view-reverse-at')}
                        ${viewRow('反审核意见', 'fee-view-reverse-remark')}
                        ${viewRow('创建人', 'fee-view-created-by')}
                        ${viewRow('创建时间', 'fee-view-created-at')}
                        ${viewRow('修改交', 'fee-view-updated-by')}
                        ${viewRow('修改时间', 'fee-view-updated-at')}
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0 flex-wrap">
                <button type="button" id="feeViewDrawerEditBtn" class="inline-flex items-center gap-1.5 bg-brand text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-brand-hover transition-all">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>
    `;
}

export function renderFeeRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((row) => {
        const approved = row.audit_status === 'approved';
        const feeText = typeof formatDecimalFixed === 'function'
            ? formatDecimalFixed(row.processing_fee, 3)
            : null;
        const isZero = feeText == null || feeText === '0.000';
        const isTailor = Boolean(row.is_tailor_welded);
        const failHint = row.calc_fail_reason
            ? `<span class="text-brand-hud" title="${esc(row.calc_fail_reason)}">计算失败</span>`
            : (isTailor && (row.other_fee == null || row.other_fee === '')
                ? '<span class="text-brand-hud">拼焊件待补价</span>'
                : (isZero
                    ? '<span class="text-brand-hud">计算价为 0</span>'
                    : '<span class="text-ink-faint">—</span>'));
        const cell = 'p-3 border-b border-line-subtle font-mono text-[11px]';
        const muted = 'text-ink-muted';
        const mutedDeep = 'text-ink-dim';
        const zoneEnd = 'border-r border-line-hud';
        const finalCell = [
            'p-3 text-right font-mono font-bold tabular-nums text-[13px]',
            'text-ink bg-app-hud',
            'border-b border-line-subtle border-l border-r border-line-subtle',
            'group-hover:bg-app-surface transition-colors',
        ].join(' ');
        const canUpdate = typeof can === 'function' ? can('op:stamping-process-fee:update') : true;
        const otherFee = row.other_fee != null && Number(row.other_fee) !== 0
            ? formatNum(row.other_fee, 3)
            : '-';

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
                <div class="font-bold text-white text-[12px] group-hover:text-brand-hud transition-colors">${esc(fmtYear(row.year))}</div>
                <div class="text-ink-faint text-[10px] mt-0.5">${esc(row.location)} · ${esc(row.stamping_supplier)}</div>
            </td>
            <td class="${cell} font-sans whitespace-nowrap">
                ${partShortCodeCellHtml(row.part_number)}
            </td>
            <td class="${cell} font-sans overflow-hidden">
                ${partNumberNameCellHtml(row.part_number, row.part_name, tailorBadge(row.is_tailor_welded))}
            </td>
            <td class="${cell} ${muted} font-sans ${zoneEnd}">${esc(row.vehicle_model)} / ${esc(row.version)}</td>
            <td class="${cell} text-right ${muted} tabular-nums">${esc(row.process_count)}</td>
            <td class="${cell} text-right tabular-nums ${isZero ? 'text-brand-hud' : muted}">${formatNum(row.processing_fee, 3)}</td>
            <td class="${cell} text-right ${muted} tabular-nums ${zoneEnd}">${otherFee}</td>
            <td class="${finalCell}">${formatNum(row.final_processing_fee, 3)}</td>
            <td class="${cell} ${muted} font-sans">${esc(row.material)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.thickness, 4)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.part_weight, 4)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.sheet_length, 2)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.sheet_width, 2)}</td>
            <td class="${cell} ${muted} font-sans">
                <div>${esc(row.die_type)}</div>
                <div class="text-[10px] text-ink-faint mt-0.5">${esc(row.process_method)}</div>
            </td>
            <td class="${cell} text-[10px] text-ink-faint max-w-[160px] truncate" title="${esc(row.remark || '')}">${esc(row.remark)}</td>
            <td class="${cell}">${auditBadge(row.audit_status)}</td>
            <td class="${cell}">${failHint}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(row.created_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.created_at))}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(row.updated_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.updated_at))}</td>`,
            opsHtml: `${viewBtn}${editBtn}`,
        });
    }).join('');
}

/**
 * 用筛选汇总刷新 HUD（总金额 / 件均 / 条数 / 待补价 / 待审 / 已审均为全量筛选结果，非本页）
 * @param {number} total 当前列表匹配条数（仅作兜底；条数优先用 summary.total_count）
 * @param {object|null} summary API filters.summary
 * @param {boolean} [onlyZeroActive=false] 是否已激活「算费失败待办」筛选
 */
export function updateFeeHud(total, summary, onlyZeroActive = false) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const totalCount = Number(data.total_count ?? total ?? 0);
    const zeroCount = Number(data.zero_count ?? 0);
    const hasFailTodo = zeroCount > 0;

    const fmtMoney = (value) => {
        const fixed = formatDecimalFixed(value, 2, { allowNegative: true });
        return fixed == null ? '—' : withThousandsSep(fixed);
    };

    setText('feeHudTotalFee', fmtMoney(data.total_fee));
    setText('feeHudAvgFee', fmtMoney(data.avg_fee));
    setText('feeHudTotal', totalCount.toLocaleString('zh-CN'));
    setText('feeHudVersion', data.version_label || '—');
    setText('feeHudZero', zeroCount.toLocaleString('zh-CN'));
    setText('feeHudPending', Number(data.pending_count ?? 0).toLocaleString('zh-CN'));
    setText('feeHudApproved', Number(data.approved_count ?? 0).toLocaleString('zh-CN'));

    const card = document.getElementById('feeHudZeroCard');
    const glow = document.getElementById('feeHudZeroGlow');
    const dot = document.getElementById('feeHudZeroDot');
    const label = document.getElementById('feeHudZeroLabel');
    const valueEl = document.getElementById('feeHudZeroValue');
    const hint = document.getElementById('feeHudZeroHint');

    if (card) {
        card.setAttribute('aria-pressed', onlyZeroActive ? 'true' : 'false');
        if (hasFailTodo) {
            card.className = [
                'text-left w-full p-3.5 relative overflow-hidden group transition-all duration-200 cursor-pointer',
                'hud-kpi-card-glow bg-gradient-to-b from-brand-hud/15 to-app-deep border border-brand-hud/50',
                onlyZeroActive ? 'ring-1 border-brand-hud/40' : '',
                'hover:border-brand-hud/80 focus:outline-none focus-visible:border-brand-hud',
            ].filter(Boolean).join(' ');
        } else {
            card.className = [
                'text-left w-full p-3.5 relative overflow-hidden group transition-all duration-200 cursor-pointer',
                'hud-kpi-aux-inset bg-app-main/80 border border-line-hud backdrop-blur-sm',
                'hover:border-line-hud focus:outline-none focus-visible:border-ok/40/50',
            ].join(' ');
        }
    }

    glow?.classList.toggle('hidden', !hasFailTodo);
    dot?.classList.toggle('hidden', !hasFailTodo);

    if (label) {
        label.className = hasFailTodo
            ? 'text-brand-hud text-[10px] font-bold tracking-widest'
            : 'text-ok text-[10px] font-bold tracking-widest';
        label.textContent = '算费失败待办';
    }
    if (valueEl) {
        valueEl.className = hasFailTodo
            ? 'hud-kpi-num-glow text-[26px] font-black text-brand-hud font-mono mt-1 tracking-tight tabular-nums leading-none'
            : 'text-[26px] font-black text-ok font-mono mt-1 tracking-tight tabular-nums leading-none';
    }
    if (hint) {
        if (hasFailTodo) {
            hint.className = 'text-[9px] font-mono text-brand-hud/60 mt-2';
            hint.textContent = onlyZeroActive ? '已定位异常行 · 再点取消' : '点击一键定位';
        } else {
            hint.className = 'text-[9px] font-mono text-ok/70 mt-2';
            hint.textContent = '规则运行完备';
        }
    }

    const failCapsule = document.getElementById('feeCapsuleFailTodo');
    if (failCapsule) {
        failCapsule.classList.toggle('hidden', !onlyZeroActive);
    }
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-brand font-mono' : 'text-ink'} truncate"></span>
    </div>`;
}

function tailorBadge(isTailorWelded) {
    return isTailorWelded
        ? `<span class="mt-1 inline-block text-[9px] font-sans tracking-[0.08em] text-brand-hud border border-brand-hud/30 bg-brand-hud/10 px-1.5 py-0.5">拼焊件</span>`
        : '';
}

/** 抽屉：短史+ 完整零件号*/
function partNumberViewBlock(prefix) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">零件号</span>
        <span id="${prefix}-part-short"
              class="block text-xl font-mono font-bold tabular-nums text-white tracking-[0.14em] hud-kpi-num-glow"></span>
        <span id="${prefix}-part-number" class="block text-[11px] font-mono text-ink-dim tracking-wider mt-0.5 truncate"></span>
    </div>`;
}

function auditBadge(status) {
    const map = {
        pending: 'bg-app-surface text-ink-muted border border-line',
        approved: 'bg-app-surface text-ink-muted border border-line',
        rejected: 'bg-app-surface text-ink-muted border border-line',
    };
    const label = { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '-';
    const cls = map[status] || 'bg-app-surface text-ink-muted border border-line';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm ${cls}">${esc(label)}</span>`;
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
