/**
 * Annual Part Price List Template
 * 年度零件价列表 — Brabus HUD（对齐焊接单价列表）
 * 数据来自上传，无「新增」入口；批量操作范围 = 上传条件（基地 + 年度）
 *
 * 单价一律按十进制字符串处理（不经 Number/parseFloat）。
 */

import { filterSelect, filterInput, HUD_SHELL, DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_GHOST, HUD_LED, BTN_SOLID, BTN_SOLID_DANGER, HUD_FILTER } from '../../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=7';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../domain/part-identity.js?v=5';

/** 格式化为固定 4 位小数字符串；非法值返回 '-'。 */
export function formatUnitPrice4(value) {
    return formatDecimalFixed(value, 4) ?? '-';
}

export function unitPriceInputValue(value) {
    return formatDecimalFixed(value, 4) ?? '';
}

/** 校验并规范输入为 4 位小数字符串；失败返回 null。 */
export function parseUnitPriceInput(raw) {
    return parseDecimalInput(raw, 4);
}

export function stripConversionFactorDisplay(value) {
    const fixed = formatDecimalFixed(value, 6);
    if (!fixed) return null;
    if (!fixed.includes('.')) return fixed;
    return fixed.replace(/0+$/, '').replace(/\.$/, '');
}

export function formatConversionFactor(value) {
    return stripConversionFactorDisplay(value) ?? '-';
}

export function conversionFactorInputValue(value) {
    return stripConversionFactorDisplay(value) ?? '1';
}

export function parseConversionFactorInput(raw) {
    const text = String(raw ?? '').trim();
    if (!text) return '1';
    if (text.includes('/')) return null;
    const parsed = parseDecimalInput(text, 6);
    if (!parsed) return null;
    const display = stripConversionFactorDisplay(parsed);
    if (!display || display === '0') return null;
    return display;
}

export function annualPartPriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({ title: '记录条数', valueHtml: '<span id="annualHudTotal">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '待审', valueHtml: '<span id="annualHudPending">—</span>', unit: '条' })}
                            ${hudKpiCardHtml({ title: '已审', valueHtml: '<span id="annualHudApproved">—</span>', unit: '条' })}
                        </div>
                        <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
                            ${moreMenuShellHtml({
                                wrapId: 'annualMoreWrap',
                                btnId: 'annualMoreBtn',
                                menuId: 'annualMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'btnBatchApproveAnnual', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchReverseAnnual', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchDeleteAnnualPartPrice', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="btnExportAnnualPartPrice" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'annual',
                        searchId: 'btnFilter',
                        capsules: [
                            { capsuleId: 'annualCapsuleYear', idleLabel: '全部年度' },
                            { capsuleId: 'annualCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'annualCapsuleAudit', idleLabel: '全部审核' },
                            { capsuleId: 'annualCapsuleKeyword', idleLabel: '零件号/名称' },
                        ],
                        fieldsHtml: [
                            filterSelect('annualYearFilter', '年度'),
                            filterSelect('annualLocationFilter', '基地'),
                            filterSelect('annualAuditStatusFilter', '审核状态'),
                            filterInput('annualKeywordFilter', '零件号/名称', '模糊匹配零件号或名称'),
                            `<button id="annualResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '批量删除、审核、反审核要同时选基地和年度。已经审核的不能删、不能改。核价单价不能为负；填 0 时，成品核价不算这件。转换系数必须大于 0，默认 1，最多 6 位小数。核价单价 = 采购单价 ÷ 转换系数。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'annual',
                    bodyId: 'annualPartPriceTableBody',
                    minWidth: '1960px',
                    colgroupHtml: `
                            <col style="width:2px">
                            <col style="width:6%">
                            <col style="width:5%">
                            <col style="width:6%">
                            <col style="width:10%">
                            <col style="width:7%">
                            <col style="width:6%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:5%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:6%">
                            <col style="width:5%">
                            <col style="width:5%">
                            <col style="width:6%">
                            <col style="width:8%">
                            <col style="width:5%">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">年份</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">规格</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">采购单位</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">采购单价</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint" title="1采购单位=N核价单位；可小数如25.4；核价单价=采购单价÷N">转换系数</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">单位</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10"
                                    title="核价单价；≥0；填 0 表示成品核价不计入该件">单价</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">原供货类型</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">供应商</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">备注</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">审核</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">创建人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">创建时间</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-ink-faint">修改人</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无年度零件价数据', hint: '请先在「年度零件价上传」中导入 Excel' },
                    loading: true,
                })}
            </div>
        </div>

        ${batchAuditDrawerHtml('annual')}
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
             id="annualEditDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[560px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="annualEditDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase" id="annualEditDrawerTitle">
                    <span class="${HUD_LED}"></span>
                    编辑零件价
                </h5>
                <button type="button" id="closeAnnualEditDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto" id="annualEditDrawerContent">
                <form id="annualEditForm" class="p-6 space-y-5">
                    <input type="hidden" id="annualEditRecordId" value="">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">基地</label>
                            <input type="text" id="annualEditLocation" disabled
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">年份</label>
                            <input type="number" id="annualEditYear" disabled
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">零件号</label>
                        <input type="text" id="annualEditPartNumber" disabled
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink-muted rounded">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">零件名称</label>
                        <input type="text" id="annualEditPartName" maxlength="200"
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                               placeholder="可选" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">规格</label>
                        <input type="text" id="annualEditSpecification" maxlength="100"
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                               placeholder="展示用，不参与取价" autocomplete="off">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">采购单位</label>
                            <input type="text" id="annualEditPurchaseUnit" maxlength="20"
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                                   placeholder="如 打、瓶；同核价可空" autocomplete="off">
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">采购单价</label>
                            <input type="text" id="annualEditPurchaseUnitPrice" inputmode="decimal"
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink font-mono rounded focus:outline-none focus:border-brand-active"
                                   placeholder="空=未报采购价" autocomplete="off">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">转换系数</label>
                            <input type="text" id="annualEditConversionFactor" inputmode="decimal"
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink font-mono rounded focus:outline-none focus:border-brand-active"
                                   placeholder="默认 1；1打=12，1英寸=25.4" autocomplete="off">
                            <p class="mt-1.5 text-[10px] text-ink-faint leading-relaxed">1 采购单位 = N 核价单位。核价单价 = 采购单价 ÷ N。可小数（如 25.4），最多 6 位，不补零。</p>
                        </div>
                        <div>
                            <label class="text-[10px] text-ink-dim mb-1 block">单位 <span class="text-brand">*</span></label>
                            <input type="text" id="annualEditUnit" required maxlength="20"
                                   class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                                   placeholder="核价单位，如 pcs / mm" autocomplete="off">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">单价 <span class="text-brand">*</span></label>
                        <input type="text" id="annualEditUnitPrice" inputmode="decimal" required
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink font-mono rounded focus:outline-none focus:border-brand-active"
                               placeholder="≥0，核价单价，保留4位小数" autocomplete="off">
                        <p class="mt-1.5 text-[10px] text-ink-faint leading-relaxed">
                            须 <span class="text-ink-muted">≥ 0</span>。填了采购单价时，单价 0 会按公式覆盖。
                            <span class="text-ink-muted">填 0</span> 且无采购单价时，成品核价<span class="text-ink-muted">不计入</span>该件。
                        </p>
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">原供货类型</label>
                        <input type="text" id="annualEditSupplyType" maxlength="50"
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                               placeholder="如 标准件 / 沿用 / 胶块" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">供应商</label>
                        <select id="annualEditSupplierName"
                               class="w-full ${HUD_FILTER}">
                            <option value="">（空）</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[10px] text-ink-dim mb-1 block">备注</label>
                        <input type="text" id="annualEditRemark" maxlength="500"
                               class="w-full h-9 px-3 text-xs bg-app-deep border border-line text-ink rounded focus:outline-none focus:border-brand-active"
                               placeholder="可选" autocomplete="off">
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelAnnualEditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitAnnualEditBtn" class="${BTN_SOLID}">
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
             id="annualDeleteDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[380px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="annualDeleteDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase">
                    <span class="${HUD_LED}"></span>
                    确认删除
                </h5>
                <button type="button" id="closeAnnualDeleteDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="annualDeleteRecordId" value="">
                <p class="text-[12px] text-ink-muted mb-3">确定删除这条未审核记录吗？</p>
                <p class="text-[11px] text-ink-dim">已审核记录不可删除。此操作不可撤销。</p>
            </div>
            <div class="px-6 py-4 border-t border-app-elevated flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelAnnualDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmAnnualDeleteBtn" class="${BTN_SOLID_DANGER}">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}



export function updateAnnualHud(summary) {
    const data = summary && typeof summary === 'object' ? summary : {};
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    setText('annualHudTotal', String(data.total_count ?? '—'));
    setText('annualHudPending', String(data.pending_count ?? '—'));
    setText('annualHudApproved', String(data.approved_count ?? '—'));
}

export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const canUpdate = typeof can === 'function' ? can('op:bom-annual-part-price:update') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-annual-part-price:delete') : true;

    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const editBtn = canUpdate
            ? opsIconButtonHtml({
                extraClass: `annual-edit-btn${approved ? ' opacity-30 pointer-events-none' : ''}`,
                title: approved ? '已审核，不可编辑' : '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            })
            : '';
        const deleteBtn = canDelete && !approved
            ? opsIconButtonHtml({
                extraClass: 'annual-delete-btn',
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
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                ${partShortCodeCellHtml(record.part_number)}
            </td>
            <td class="px-2 py-2 overflow-hidden">
                ${partNumberNameCellHtml(record.part_number, record.part_name)}
            </td>
            <td class="px-2 py-2 text-ink-muted overflow-hidden truncate" title="${esc(record.specification || '')}">${esc(record.specification || '—')}</td>
            <td class="px-2 py-2 text-ink-muted overflow-hidden truncate">${esc(record.purchase_unit || '—')}</td>
            <td class="px-2 py-2 text-right font-mono tabular-nums text-ink-muted">${record.purchase_unit_price == null || record.purchase_unit_price === '' ? '—' : esc(formatUnitPrice4(record.purchase_unit_price))}</td>
            <td class="px-2 py-2 text-right font-mono tabular-nums text-ink-muted">${esc(formatConversionFactor(record.conversion_factor))}</td>
            <td class="px-2 py-2 text-ink-muted overflow-hidden truncate">${esc(record.unit)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20">
                ${esc(formatUnitPrice4(record.unit_price))}
            </td>
            <td class="px-2 py-2 text-ink-muted overflow-hidden truncate" title="${esc(record.supply_type || '')}">${esc(record.supply_type || '—')}</td>
            <td class="px-2 py-2 text-[10px] text-ink-faint overflow-hidden truncate" title="${esc(record.supplier_name || '')}">${esc(record.supplier_name || '—')}</td>
            <td class="px-2 py-2 text-[10px] text-ink-faint overflow-hidden truncate" title="${esc(record.remark || '')}">${esc(record.remark || '—')}</td>
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
