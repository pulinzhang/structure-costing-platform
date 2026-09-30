/**
 * Steel Price List Template
 * 钢材价格计算结果浏览 —Brabus Carbon & Precision Dark
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, TH_KEY, TH_TEXT, TH_NUM, TH_FOCUS, BTN_GHOST, HUD_LED, BTN_SOLID, BTN_SOLID_DANGER } from '../../../../ui/classes.js?v=13';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=7';

export function steelPriceListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <!-- HUD 战术数据看板 + 操作 -->
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                title: '核价条数',
                                valueHtml: '<span id="steelPriceHudTotal">—</span>',
                                unit: '条',
                            })}
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: '本期均价',
                                pulse: true,
                                valueHtml: '￥<span id="steelPriceHudAvg">—</span>',
                                footer: [{
                                    label: '系统自动计算',
                                    valueHtml: '<span id="steelPriceHudSkuCount">— 条</span>',
                                }],
                            })}
                            ${hudKpiCardHtml({
                                title: '待审',
                                valueHtml: '<span id="steelPriceHudPending">—</span>',
                                unit: '条',
                            })}
                            ${hudKpiCardHtml({
                                title: '已审',
                                valueHtml: '<span id="steelPriceHudApproved">—</span>',
                                unit: '条',
                            })}
                        </div>
                        <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
                            ${moreMenuShellHtml({
                                wrapId: 'steelPriceMoreWrap',
                                btnId: 'steelPriceMoreBtn',
                                menuId: 'steelPriceMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'steelPriceBatchApproveButton', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'steelPriceBatchReverseButton', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'steelPriceBatchDeleteButton', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="steelPriceExportButton"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'steelPrice',
                        searchId: 'steelPriceSearchButton',
                        capsules: [
                            { capsuleId: 'steelCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'steelCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'steelCapsuleMill', idleLabel: '全部钢厂' },
                        ],
                        alwaysHintHtml: '批量审核、反审核、删除要先选年度、月份、基地。不用勾选行；打开单条也不能审核。',
                        fieldsHtml: [
                            filterSelect('steelPriceYear', '年度'),
                            filterSelect('steelPriceMonth', '月份'),
                            filterSelect('steelPriceLocation', '基地'),
                            filterSelect('steelPriceCategory', '钢种'),
                            filterInput('steelPriceGrade', '牌号', '输入牌号（模糊）'),
                            filterSelect('steelPriceMill', '钢厂'),
                            `<button id="steelPriceResetFilterButton" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'steelPrice',
                    minWidth: '2900px',
                    headHtml: `
                                <th class="p-0 w-0"></th>
                                <th class="${TH_TEXT} whitespace-nowrap">核价维度</th>
                                <th class="${TH_TEXT} whitespace-nowrap">钢厂</th>
                                <th class="${TH_TEXT} whitespace-nowrap">钢种</th>
                                <th class="${TH_KEY} whitespace-nowrap">牌号</th>
                                <th class="${TH_NUM} whitespace-nowrap">厚度</th>
                                <th class="${TH_NUM} whitespace-nowrap border-r border-line-hud">宽度</th>
                                <th class="${TH_NUM} whitespace-nowrap">基础价</th>
                                <th class="${TH_NUM} whitespace-nowrap">厚度加价</th>
                                <th class="${TH_NUM} whitespace-nowrap">宽度加价</th>
                                <th class="${TH_NUM} whitespace-nowrap border-r border-line-hud">加工费</th>
                                <th class="${TH_FOCUS} whitespace-nowrap">最终价/启</th>
                                <th class="${TH_TEXT} whitespace-nowrap">基价溯源</th>
                                <th class="${TH_TEXT} whitespace-nowrap">厚度溯源</th>
                                <th class="${TH_TEXT} whitespace-nowrap">宽度溯源</th>
                                <th class="${TH_TEXT} whitespace-nowrap">匹配</th>
                                <th class="${TH_TEXT} whitespace-nowrap">审核</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">创建时间</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改人</th>
                                <th class="${TH_TEXT} whitespace-nowrap">最后修改时间</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无钢材价格数据', hint: '数据由系统计算写入，或通过 Excel 导入' },
                    loading: true,
                })}
            </div>
        </div>

        <!-- 新增 / 编辑抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[760px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="editDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="editDrawerTitle">编辑钢材价格</span>
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="editDrawerContent">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">

                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-2 block">业务主键</label>
                        <div class="grid grid-cols-4 gap-3">
                            ${editNumber('editYear', '年度', '2000', '2100', '2026')}
                            ${editNumber('editMonth', '月份', '1', '12', '1')}
                            ${editText('editLocation', '基地', '如 芜湖基地')}
                            ${editText('editSteelMill', '钢厂', '如 马钢')}
                            ${editText('editCategoryName', '钢种', '如 冷轧')}
                            ${editText('editGrade', '牌号', '如 DC01')}
                            ${editNumber('editThickness', '厚度', '0', null, '0.8', '0.0001')}
                            ${editNumber('editWidth', '宽度', '0', null, '1250', '0.0001')}
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-2 block">价格分项</label>
                        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
                            ${editNumber('editBasePrice', '基础价base_price', '0', null, '全', '0.0001')}
                            ${editNumber('editThicknessAdjustment', '厚度加价 thickness_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editWidthAdjustment', '宽度加价 width_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editZincAdjustment', '锌层加价 zinc_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editProcessingFee', '加工费processing_fee', '0', null, '全', '0.0001')}
                            ${editNumber('editOtherAdjustment', '其他调整 other_adjustment', null, null, '全', '0.0001')}
                        </div>
                        <p class="text-[10px] text-ink-dim mt-2">最终价由服务端按分项自动汇总，无需手工填写。</p>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim uppercase tracking-[0.1em] mb-1.5 block">规格 / 备注</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${editText('editSpec', '规格（可选）', '如 1.00*1250.00', false)}
                            <div>
                                <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                                <textarea id="editRemark" rows="2" maxlength="500"
                                          class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                                          placeholder="人工备注"></textarea>
                            </div>
                        </div>
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

        <!-- 查看详情抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="viewDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[560px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="viewDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    价格详情
                </h5>
                <button type="button" id="closeViewDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="viewDrawerContent">
                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">业务主键</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'view-year')}
                        ${viewRow('月份', 'view-month')}
                        ${viewRow('基地', 'view-location')}
                        ${viewRow('钢厂', 'view-steel-mill')}
                        ${viewRow('钢种', 'view-category-name')}
                        ${viewRow('牌号', 'view-grade')}
                        ${viewRow('厚度', 'view-thickness')}
                        ${viewRow('宽度', 'view-width')}
                        ${viewRow('规格', 'view-spec')}
                    </div>
                </div>

                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">价格分项（对齐VO）</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('基础价base_price', 'view-base-price')}
                        ${viewRow('厚度加价 thickness_adjustment', 'view-thickness-adjustment')}
                        ${viewRow('宽度加价 width_adjustment', 'view-width-adjustment')}
                        ${viewRow('锌层加价 zinc_adjustment', 'view-zinc-adjustment')}
                        ${viewRow('加工费processing_fee', 'view-processing-fee')}
                        ${viewRow('其他调整 other_adjustment', 'view-other-adjustment')}
                        ${viewRow('最终价 final_price_per_ton', 'view-final-price', true)}
                    </div>
                </div>

                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">溯源信息（Excel / 政策 ID）</h6>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-ink-muted">
                        <div id="view-trace-base" class="leading-relaxed"></div>
                        <div id="view-trace-thickness" class="leading-relaxed"></div>
                        <div id="view-trace-width" class="leading-relaxed"></div>
                        <div id="view-trace-zinc" class="leading-relaxed"></div>
                    </div>
                </div>

                <div class="bg-app-main border border-app-elevated">
                    <div class="px-4 py-3 bg-app-deep border-b border-line-subtle">
                        <h6 class="text-[10px] font-semibold text-ink-muted tracking-wider uppercase">审核 / 计算</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('审核状态', 'view-audit-status')}
                        ${viewRow('审核人', 'view-audited-by')}
                        ${viewRow('审核时间', 'view-audited-at')}
                        ${viewRow('审核意见', 'view-audit-remark')}
                        ${viewRow('反审核人', 'view-reverse-audited-by')}
                        ${viewRow('反审核时间', 'view-reverse-audited-at')}
                        ${viewRow('反审核原因', 'view-reverse-audit-remark')}
                        ${viewRow('匹配状态', 'view-match-status')}
                        ${viewRow('计算批次', 'view-calc-batch-id')}
                        ${viewRow('计算时间', 'view-calculated-at')}
                    </div>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0 flex-wrap">
                <button type="button" id="viewDrawerEditBtn" class="${BTN_SOLID}">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
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
            <div class="flex-1 min-h-0 overflow-y-auto p-6">
                <input type="hidden" id="deleteRecordId" value="">
                <p class="text-[12px] text-ink-muted mb-3">确定要删除这条价格记录吗（</p>
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-dim" id="deleteSummary"></div>
                <p class="text-[11px] text-danger mt-3">已审核通过的记录不可删除，须先反审核。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmDeleteBtn" class="${BTN_SOLID_DANGER}">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>

        <!-- 批量审核 / 反审核抽屉-->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="batchAuditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="batchAuditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    <span id="batchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeBatchAuditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="batchAuditMode" value="approve">
                <div class="bg-app-deep border border-line-subtle rounded p-3 text-[11px] text-ink-muted" id="batchAuditFilterSummary"></div>
                <p id="batchAuditHint" class="text-[11px] text-ink-dim">仅按年度、月份、基地批量处理；三者必须同时选择。</p>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="batchAuditOperatorLabel">操作人</label>
                    <div id="batchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-app-deep border border-line text-ink-muted rounded">
                        —                    </div>
                    <p class="text-[10px] text-ink-faint mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-ink-dim mb-1 block" id="batchAuditRemarkLabel">审核意见</label>
                    <textarea id="batchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelBatchAuditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmBatchAuditBtn" class="${BTN_SOLID}">
                    确认提交
                </button>
            </div>
        </div>
    `;
}

export function millLabel(record) {
    return (record && record.steel_mill_abbreviation) || '';
}

export function renderSteelPriceRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const period = esc(fmtPeriod(record.year, record.month));
        const mill = esc(millLabel(record)) || '—';
        const location = esc(record.location) || '—';
        const cell = 'p-3 border-b border-line-subtle font-mono text-[11px]';
        const muted = 'text-ink-muted';
        const mutedDeep = 'text-ink-dim';
        const zoneEnd = 'border-r border-line-hud';
        const finalCell = [
            'p-3 text-right font-mono font-black tabular-nums text-[13px]',
            'text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20',
            'border-b border-line-subtle',
        ].join(' ');
        const viewBtn = opsIconButtonHtml({
            extraClass: 'view-btn',
            title: '查看详情',
            icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
        });
        const editBtn = (typeof can === 'function' ? can('op:steel-price-list:update') : true)
            ? opsIconButtonHtml({
                extraClass: `edit-btn${approved ? ' opacity-30 pointer-events-none' : ''}`,
                title: approved ? '已审核，不可编辑' : '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            })
            : '';
        const deleteBtn = (typeof can === 'function' ? can('op:steel-price-list:delete') : true)
            ? opsIconButtonHtml({
                extraClass: `delete-btn${approved ? ' opacity-30 pointer-events-none' : ''}`,
                danger: true,
                title: approved ? '已审核，不可删除' : '删除',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            })
            : '';
        return hudRowHtml({
            attrs: `data-id="${esc(record.id)}"`,
            cellsHtml: `
            <td class="${cell} font-sans whitespace-nowrap">
                <div class="font-bold text-ink text-[12px] group-hover:text-brand-hud transition-colors">${period}</div>
                <div class="text-ink-faint text-[10px] mt-0.5">${location} · ${mill}</div>
            </td>
            <td class="${cell} ${muted} font-sans text-[11px]">${mill}</td>
            <td class="${cell} ${muted} font-sans text-[11px]">${esc(record.category_name)}</td>
            <td class="${cell} font-sans">
                <span class="inline-block bg-app-hud text-ink font-bold border border-line px-2 py-1 rounded text-[11px]">${esc(record.grade)}</span>
            </td>
            <td class="${cell} text-right font-bold text-ink text-[13px] tabular-nums">${formatPrice(record.thickness, 2)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums ${zoneEnd}">${formatWidth(record.width)}</td>
            <td class="${cell} text-right ${muted} tabular-nums">${formatPrice(record.base_price, 2)}</td>
            <td class="${cell} text-right tabular-nums">${formatAdjustment(record.thickness_adjustment)}</td>
            <td class="${cell} text-right tabular-nums">${formatAdjustment(record.width_adjustment)}</td>
            <td class="${cell} text-right ${muted} tabular-nums ${zoneEnd}">${formatPriceOrDash(record.processing_fee)}</td>
            <td class="${finalCell}">${formatPrice(record.final_price_per_ton, 2)}</td>
            <td class="${cell} text-[10px] text-ink-faint max-w-[220px]">${formatTraceCell('base', record)}</td>
            <td class="${cell} text-[10px] text-ink-faint max-w-[220px]">${formatTraceCell('thickness', record)}</td>
            <td class="${cell} text-[10px] text-ink-faint max-w-[220px]">${formatTraceCell('width', record)}</td>
            <td class="${cell} ${muted} text-[11px]">${esc(record.match_status)}</td>
            <td class="${cell}">${auditBadge(record.audit_status)}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(record.created_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(record.created_at))}</td>
            <td class="${cell} text-[9px] text-ink-faint whitespace-nowrap">${esc(record.updated_by)}</td>
            <td class="${cell} text-[9px] text-ink-faint font-mono whitespace-nowrap">${esc(formatAuditDateTime(record.updated_at))}</td>`,
            opsHtml: `${viewBtn}${editBtn}${deleteBtn}`,
        });
    }).join('');
}

/** 用筛选汇总刷新HUD（均价/ 待审 / 已审均为全量筛选结果，非本页） */
export function updateSteelPriceHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const avg = data.avg_final_price;
    const avgFixed = formatDecimalFixed(avg, 2, { allowNegative: true });

    setText('steelPriceHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText(
        'steelPriceHudAvg',
        avgFixed == null ? '—' : withThousandsSep(avgFixed),
    );
    setText('steelPriceHudSkuCount', `${Number(total || 0).toLocaleString('zh-CN')} 条`);
    setText('steelPriceHudPending', String(data.pending_count ?? 0));
    setText('steelPriceHudApproved', String(data.approved_count ?? 0));
}

/**
 * 列表溯源摘要，字段对齐SteelPriceResponse VO。 * base: base_price_id / base_excel_filename / base_sheet_name / base_excel_row / base_excel_col
 * thickness|width|zinc: *_policy_id / *_ladder_item_id / *_steel_mill / *_excel_filename / *_sheet_name / *_excel_row / *_excel_col
 */
function formatTraceCell(prefix, record) {
    const mill = prefix === 'base' ? record.steel_mill : record[`${prefix}_steel_mill`];
    const filename = record[`${prefix}_excel_filename`];
    const sheet = record[`${prefix}_sheet_name`];
    const row = record[`${prefix}_excel_row`];
    const col = record[`${prefix}_excel_col`];
    const refId = prefix === 'base'
        ? record.base_price_id
        : record[`${prefix}_policy_id`];
    const ladderId = prefix === 'base' ? null : record[`${prefix}_ladder_item_id`];

    if (filename == null && refId == null && ladderId == null && row == null && col == null) {
        return '<span class="text-ink-faint">—</span>';
    }

    const idPart = prefix === 'base'
        ? (refId != null ? `id=${esc(refId)}` : '')
        : [
            refId != null ? `policy=${esc(refId)}` : '',
            ladderId != null ? `item=${esc(ladderId)}` : '',
        ].filter(Boolean).join(' ');

    const excelPart = [
        mill || '',
        filename || '',
        sheet || '',
        row != null || col != null ? `R${row ?? '-'}C${col ?? '-'}` : '',
    ].filter(Boolean).join(' / ');

    const text = [idPart, excelPart].filter(Boolean).join(' · ') || '—';
    return `<span class="block truncate" title="${esc(text)}">${text}</span>`;
}




function editText(id, label, placeholder, required = true) {
    return `<div>
        <label class="text-[10px] text-ink-dim mb-1 block">${label}${required ? ' <span class="text-brand">*</span>' : ''}</label>
        <input type="text" id="${id}" ${required ? 'required' : ''} maxlength="100"
               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded"
               placeholder="${placeholder}">
    </div>`;
}

function editNumber(id, label, min, max, placeholder, step = '1') {
    const minAttr = min != null ? `min="${min}"` : '';
    const maxAttr = max != null ? `max="${max}"` : '';
    return `<div>
        <label class="text-[10px] text-ink-dim mb-1 block">${label} <span class="text-brand">*</span></label>
        <input type="number" id="${id}" ${minAttr} ${maxAttr} step="${step}" required
               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active rounded"
               placeholder="${placeholder || ''}">
    </div>`;
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-ink-faint uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-brand font-mono' : 'text-ink'} truncate"></span>
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

function formatPrice(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    return fixed == null ? '-' : withThousandsSep(fixed);
}

/** 加工费：为 0 时显示 -- */
function formatPriceOrDash(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    if (fixed == null || compareDecimalStrings(fixed, '0', digits) === 0) {
        return '--';
    }
    return withThousandsSep(fixed);
}

/**
 * 厚度/宽度加价（单色冷灰）
 * 有值→text-ink-muted 带正负号；无值→text-ink-dim -
 */
function formatAdjustment(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    if (fixed == null || compareDecimalStrings(fixed, '0', digits) === 0) {
        return '<span class="text-ink-dim">-</span>';
    }
    const absText = withThousandsSep(fixed.startsWith('-') ? fixed.slice(1) : fixed);
    const signed = fixed.startsWith('-') ? `-${absText}` : `+${absText}`;
    return `<span class="text-ink-muted">${signed}</span>`;
}

/** 宽度：整数、无千分位 */
function formatWidth(value) {
    return formatDecimalFixed(value, 0) ?? '-';
}
