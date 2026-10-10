/**
 * Dashboard Template
 * 管理者看板 — 本期产出 / 待办决策 / 核价闭环就绪
 */

import { filterSelect, BTN_GHOST } from '../../ui/classes.js?v=14';
import { filterBarHtml } from '../../ui/filter-bar.js?v=6';
import { hudKpiCardHtml } from '../../ui/hud-kpi.js?v=1';

function actionLink({ page, label, sub }) {
    return `
        <a href="#/${page}" data-page="${page}" class="dash-action">
            <span class="dash-action-label">${label}</span>
            <span class="dash-action-sub">${sub}</span>
        </a>
    `;
}

export function dashboardTemplate() {
    return `
        <div class="dash-board">
            ${filterBarHtml({
                prefix: 'dash',
                searchId: 'dashBtnSearch',
                capsules: [
                    { capsuleId: 'dashCapsulePeriod', idleLabel: '全部期间' },
                    { capsuleId: 'dashCapsuleLocation', idleLabel: '全部基地' },
                    { capsuleId: 'dashCapsuleVehicle', idleLabel: '全部项目' },
                ],
                fieldsHtml: [
                    filterSelect('dashYear', '核价年度', { emptyLabel: '全部年度', widthClass: 'w-full sm:w-28' }),
                    filterSelect('dashMonth', '核价月份', { emptyLabel: '全部月份', widthClass: 'w-full sm:w-28' }),
                    filterSelect('dashLocation', '生产基地', { emptyLabel: '全部基地', widthClass: 'w-full sm:w-36' }),
                    filterSelect('dashVehicle', '项目', { emptyLabel: '全部项目', widthClass: 'w-full sm:w-36' }),
                    `<button id="dashResetBtn" type="button" class="${BTN_GHOST}">
                        ${window.svgIcon('refresh', 'w-3 h-3')}
                        重置
                    </button>`,
                ].join(''),
            })}

            <section class="dash-panel">
                <div class="dash-panel-head">
                    <h3 class="dash-kicker">本期核价产出</h3>
                </div>
                <div class="dash-panel-body">
                    <div class="dash-kpi font-mono grid grid-cols-2 lg:grid-cols-4">
                        ${hudKpiCardHtml({
                            variant: 'focus',
                            title: '冲压件均单价',
                            pulse: true,
                            valueHtml: '¥<span id="dashPartAvg">—</span>',
                            footer: [
                                { label: '已审', valueHtml: '<span id="dashPartApproved">—</span>' },
                                { label: '待审', valueHtml: '<span id="dashPartPending">—</span><span id="dashPartMix" class="hidden"> · 各厂混合</span>' },
                            ],
                        })}
                        ${hudKpiCardHtml({
                            title: '待办合计',
                            valueHtml: '<span id="dashPendingTotal" class="text-warn">—</span>',
                            unit: '条',
                            rows: [
                                { label: '加工费', valueHtml: '<span id="dashFeePending">—</span>' },
                                { label: '钢价', valueHtml: '<span id="dashSteelPricePending">—</span>' },
                                { label: '冲压件', valueHtml: '<span id="dashPartCostPending">—</span>' },
                            ],
                        })}
                        ${hudKpiCardHtml({
                            title: '加工费待补价',
                            valueHtml: '<span id="dashFeeZero">—</span>',
                            unit: '条',
                            footer: [
                                { label: '件均', valueHtml: '<span id="dashFeeAvg">—</span>' },
                            ],
                        })}
                        ${hudKpiCardHtml({
                            title: '钢材联动均价',
                            valueHtml: '¥<span id="dashSteelAvg">—</span>',
                            footer: [
                                { label: '已审', valueHtml: '<span id="dashSteelApproved">—</span>' },
                                { label: '待审', valueHtml: '<span id="dashSteelPendingCount">—</span>' },
                            ],
                        })}
                    </div>
                </div>
            </section>

            <div class="dash-split">
                <section class="dash-surface">
                    <div class="dash-surface-head">
                        <h3 class="dash-kicker">待办与风险</h3>
                        <span class="dash-count" id="dashAttentionCount">—</span>
                    </div>
                    <div id="dashAttentionList" class="dash-attention-list">
                        <div class="dash-attention-empty">加载中…</div>
                    </div>
                </section>

                <section class="dash-surface">
                    <div class="dash-surface-head">
                        <h3 class="dash-kicker">核价闭环就绪</h3>
                        <span class="dash-count" id="dashReadyScore">—/6</span>
                    </div>
                    <div id="dashReadiness" class="dash-readiness"></div>
                    <p class="dash-ready-hint" id="dashReadyHint">
                        基价 · 政策 · 废料 · 加工费 · 钢价 · 冲压零件价，六项齐备方可闭环本期冲压核价。
                    </p>
                </section>
            </div>

            <div class="dash-bottom">
                <section class="dash-surface dash-context">
                    <h3 class="dash-kicker">主数据</h3>
                    <div id="dashMasterEmpty" class="dash-master-empty hidden">—</div>
                    <div id="dashMasterStats" class="dash-master-stats">
                        <div class="dash-master-stat">
                            <strong id="dashMasterParts">—</strong>
                            <span>零件</span>
                        </div>
                        <div class="dash-master-stat">
                            <strong id="dashMasterProcesses">—</strong>
                            <span>工序</span>
                        </div>
                        <div class="dash-master-stat">
                            <strong id="dashMasterModels">—</strong>
                            <span>项目</span>
                        </div>
                    </div>
                    <p class="dash-bom-line" id="dashBomBlock">材料清单 —</p>
                </section>
                <section class="dash-surface dash-context">
                    <h3 class="dash-kicker">决策入口</h3>
                    <div class="dash-actions" id="dashActions">
                        ${actionLink({ page: 'stamping-process-fee', label: '审核加工费', sub: '待审 / 待补价清单' })}
                        ${actionLink({ page: 'steel-price-list', label: '审核钢材联动价', sub: '本期联动价列表' })}
                        ${actionLink({ page: 'stamping-part-cost', label: '审核冲压零件价格', sub: '本期冲压件核价确认' })}
                        ${actionLink({ page: 'steel-price-calc', label: '发起钢材联动计算', sub: '基价 + 政策 → 联动价' })}
                        ${actionLink({ page: 'stamping-part-cost-calc', label: '发起冲压零件价格计算', sub: '材料 + 加工费 + 模具/检具' })}
                        ${actionLink({ page: 'scrap-price', label: '维护废料月度价', sub: '核价扣减依据' })}
                    </div>
                </section>
            </div>
        </div>
    `;
}
