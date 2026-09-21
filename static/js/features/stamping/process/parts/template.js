/**
 * Parts Template
 * 零件列表页面 —Brabus Carbon & Precision Dark
 * 布局对齐加工费列表：HUD + 胶囊筛选（默认收起） 级联查询
 *
 * 明细抽屉 / renderDetailContent 保持不变
 */

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';
import { BRABUS_PANEL, BRABUS_PANEL_HEADER, BRABUS_SECTION_HEADER, BRABUS_TABLE_WRAPPER, BTN_SAVE_DEFAULT, DIE_TYPE_SELECT, filterSelect, filterInput, HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, DRAWER_CLOSE, HUD_BAND, BTN_GHOST, OPS_TH, TH_KEY, TH_TEXT, TH_NUM, HUD_LED } from '../../../../ui/classes.js?v=11';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

export function partsTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <!-- HUD + 操作 -->
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                title: '基地',
                                valueHtml: '<span id="partsHudLocation">—</span>',
                                unit: '个',
                            })}
                            ${hudKpiCardHtml({
                                title: '项目',
                                valueHtml: '<span id="partsHudVehicle">—</span>',
                                unit: '种',
                            })}
                            ${hudKpiCardHtml({
                                title: '版本',
                                valueHtml: '<span id="partsHudVersion">—</span>',
                                unit: '个',
                            })}
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: '零件号',
                                pulse: true,
                                valueHtml: '<span id="partsHudPartNumber">—</span>',
                                meta: '去重后件数',
                            })}
                            ${hudKpiCardHtml({
                                title: '冲压工厂',
                                valueHtml: '<span id="partsHudSupplier">—</span>',
                                unit: '个',
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'partsMoreWrap',
                                btnId: 'partsMoreBtn',
                                menuId: 'partsMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'partsBatchDeleteBtn', label: '批量删除', danger: true }),
                            })}
                            <button id="partsExportBtn" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                            <button id="partsSteelPurchaseExportBtn" type="button"
                                    class="${BTN_GHOST}">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                钢材测算
                            </button>
                        </div>
                    </div>
                    <div class="text-[11px] font-mono text-ink-faint truncate">
                        查询范围：<span id="partsHudScope" class="text-ink-muted">全部范围</span>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'parts',
                        capsules: [
                            { capsuleId: 'partsCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'partsCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'partsCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'partsCapsuleSupplier', idleLabel: '全部工厂' },
                        ],
                        fieldsHtml: [
                            filterSelect('locationFilter', '基地'),
                            filterSelect('vehicleModelFilter', '项目'),
                            filterSelect('versionFilter', '版本'),
                            filterSelect('supplierFilter', '冲压工厂'),
                            filterInput('searchInput', '零件号', '短号或完整零件号'),
                            `<button id="partsResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        hintHtml: '筛选均可选；级联为基地 → 项目 → 版本 → 冲压工厂。批量删除须基地、项目、版本；冲压工厂可选。导出工艺表或钢材测算须选定基地。',
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'parts',
                    tableId: 'partsTable',
                    minWidth: '1460px',
                    headHtml: `
                                <th class="p-0 w-0"></th>
                                <th class="${TH_TEXT} whitespace-nowrap w-14">图纸</th>
                                <th class="${TH_KEY} whitespace-nowrap">短代码</th>
                                <th class="${TH_TEXT} whitespace-nowrap">零件</th>
                                <th class="${TH_TEXT} whitespace-nowrap">基地</th>
                                <th class="${TH_TEXT} whitespace-nowrap">项目</th>
                                <th class="${TH_TEXT} whitespace-nowrap">版本</th>
                                <th class="${TH_TEXT} whitespace-nowrap border-r border-line-hud">冲压工厂</th>
                                <th class="${TH_TEXT} whitespace-nowrap">材料</th>
                                <th class="${TH_TEXT} whitespace-nowrap">利废</th>
                                <th class="${TH_TEXT} whitespace-nowrap">废料副产品</th>
                                <th class="${TH_TEXT} whitespace-nowrap">摆剪</th>
                                <th class="${TH_NUM} whitespace-nowrap">厚度</th>
                                <th class="${TH_NUM} whitespace-nowrap">重量</th>
                                <th class="${TH_NUM} whitespace-nowrap">工序</th>
                                <th class="${TH_TEXT} whitespace-nowrap">生失效</th>
                                <th class="${TH_TEXT} whitespace-nowrap">来源文件</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无零件数据', hint: '请先上传工艺文件' },
                    loading: true,
                })}
            </div>
        </div>

        <!-- 零件详情抽屉（图级+ 信息 + 工序，表格保持可见） -->
        <div class="${DRAWER_BACKDROP} transition-opacity duration-300"
             id="partDrawerBackdrop" style="display:none"></div>

        <div class="${DRAWER_SHELL} w-[640px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="partDrawer" style="display:none; max-height: 100vh">
            <!-- 拖拽条-->
            <div class="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-brand/50 transition-colors z-10"></div>

            <!-- 头部（固定不滚动）-->
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted flex items-center gap-2.5 uppercase" id="partDrawerTitle">
                    <span class="${HUD_LED}"></span>
                    零件详情
                </h5>
                <button type="button" id="closePartDrawer"
                        class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <!-- 可滚动内容区 -->
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="partDrawerContent">
                <div class="flex items-center justify-center py-16">
                    <div class="w-7 h-7 border-2 border-line border-brand rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
    `;
}



export function updatePartsHudScope() {
    const scopeEl = document.getElementById('partsHudScope');
    if (!scopeEl) return;
    const parts = [
        document.getElementById('locationFilter')?.value || '',
        document.getElementById('vehicleModelFilter')?.value || '',
        document.getElementById('versionFilter')?.value || '',
        document.getElementById('supplierFilter')?.value || '',
    ].filter(Boolean);
    scopeEl.textContent = parts.length ? parts.join(' · ') : '全部范围';
}

export function updatePartsHud(summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const fmt = (value) => Number(value || 0).toLocaleString('zh-CN');
    setText('partsHudLocation', fmt(data.location_count));
    setText('partsHudSupplier', fmt(data.stamping_supplier_count));
    setText('partsHudVehicle', fmt(data.vehicle_model_count));
    setText('partsHudPartNumber', fmt(data.part_number_count));
    setText('partsHudVersion', fmt(data.version_count));
}


// CORE_COST_FIELDS 决定详情表强调样开
const CORE_COST_FIELDS = new Set(['材料', '重量', '可制件数', '模具类型']);

const DIE_TYPE_OPTIONS = [
    { value: 'progressive', label: '级进模（80%）' },
    { value: 'single', label: '单干模具（100%）' },
    { value: 'shared', label: '共模（50%）' },
    { value: 'progressive_shared', label: '级进共模（40%）' },
];

/**
 * 详情表格表—用CORE_COST_FIELDS 决定强调样式
 */
function detailTableRow([label, value]) {
    const isCore = CORE_COST_FIELDS.has(label);
    const tdClass = isCore
        ? 'text-[11px] font-mono font-semibold text-brand tracking-[0.05em]'
        : 'text-[11px] text-ink-dim tracking-wider';
    const tdStyle = isCore ? '' : '';
    return `
            <tr class="border-b border-line-subtle last:border-b-0">
                <th class="${TH_TEXT} w-28">${label}</th>
                <td class="px-4 py-3 ${tdClass}"${tdStyle}>${value}</td>
            </tr>`;
}

function renderOffalRows(part, canUpdate) {
    const isOn = Boolean(part.is_offal_nested);
    const source = part.offal_source || '';
    if (!canUpdate) {
        return [
            detailTableRow(['是否利废', isOn ? '是' : '否']),
            detailTableRow(['利用哪类废料', esc(source)]),
            detailTableRow(['废料副产品', part.is_scrap_byproduct ? '是' : '否']),
            detailTableRow(['摆剪工序', part.has_swing_shear ? '是' : '否']),
        ].join('');
    }
    const knobX = isOn ? '16px' : '2px';
    const trackBg = isOn ? 'rgb(var(--brabus-red))' : 'rgb(var(--bg-hud))';
    const trackBorder = isOn ? 'rgb(var(--brabus-red))' : 'rgb(var(--border-color))';
    return `
            <tr class="border-b border-line-subtle">
                <th class="${TH_TEXT} w-28">是否利废</th>
                <td class="px-4 py-3">
                    <div class="flex items-center gap-2.5 flex-wrap">
                        <button type="button" id="offalNestedToggle" role="switch"
                                aria-checked="${isOn ? 'true' : 'false'}"
                                data-on="${isOn ? '1' : '0'}"
                                class="relative h-5 w-9 shrink-0 rounded-full border focus:outline-none focus:border-brand-active"
                                style="background:${trackBg}; border-color:${trackBorder};">
                            <span id="offalNestedKnob"
                                  class="absolute top-0.5 h-3.5 w-3.5 rounded-full bg-ink pointer-events-none"
                                  style="left:0; transform:translateX(${knobX}); transition:transform 150ms ease;"></span>
                        </button>
                        <span id="offalNestedLabel" class="text-[11px] text-ink-muted tracking-wide">${isOn ? '是' : '否'}</span>
                        <button type="button" id="saveOffalBtn" data-active="false"
                                class="h-7 px-3 text-[10px] text-ink-faint border border-line bg-transparent rounded-sm hover:text-brand hover:border-brand/50 transition-all tracking-wide">
                            保存利废
                        </button>
                    </div>
                    <p class="mt-1.5 text-[9px] text-ink-faint leading-relaxed">从废料里捡成品；材料按成品净重 × 废料单价。改后须重算零件价格才生效。</p>
                </td>
            </tr>
            <tr id="offalSourceRow" class="border-b border-line-subtle ${isOn ? '' : 'hidden'}">
                <th class="${TH_TEXT} w-28">利用哪类废料</th>
                <td class="px-4 py-3">
                    <input type="text" id="offalSourceInput" maxlength="50"
                           value="${esc(source)}"
                           placeholder="如：侧围（可空）"
                           class="w-full h-8 px-2 text-[11px] bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all rounded-sm">
                </td>
            </tr>
            <tr class="border-b border-line-subtle">
                <th class="${TH_TEXT} w-28">废料副产品</th>
                <td class="px-4 py-3 text-[11px] text-ink-dim tracking-wider">${part.is_scrap_byproduct ? '是' : '否'}</td>
            </tr>
            <tr class="border-b border-line-subtle">
                <th class="${TH_TEXT} w-28">摆剪工序</th>
                <td class="px-4 py-3 text-[11px] text-ink-dim tracking-wider">${part.has_swing_shear ? '是' : '否'}</td>
            </tr>`;
}

/**
 * Excel 单元格溯源：文件 + 表页 + 表+ 零件号列（与 BOM 防扯皮对齐）
 */
function renderExcelProvenance(part) {
    const filename = part?.excel_filename || '';
    const sheet = part?.excel_sheet_name || '';
    const row = part?.excel_row;
    const col = part?.excel_part_col;
    const hasCell = Boolean(sheet) || row != null || col != null;
    if (!filename && !hasCell) {
        return `
            <div class="mx-4 mb-4 border border-app-elevated bg-app-main p-3">
                <p class="text-[10px] uppercase tracking-[0.14em] text-brand mb-1.5 flex items-center gap-2">
                    <span class="${HUD_LED}"></span>
                    Excel 溯源
                </p>
                <p class="text-[12px] text-ink-dim">无单元格溯源（请重新上传工艺文件生成）</p>
            </div>
        `;
    }
    const colHint = col != null ? `第${col} 列（零件号）` : null;
    const rowHint = row != null ? `第${row} 行` : null;
    const locator = [
        sheet ? `表「${sheet}」` : null,
        rowHint,
        colHint,
    ].filter(Boolean).join(' · ');
    const cellHint = hasCell
        ? `<p class="text-[11px] text-ink-muted">${esc(locator || '—')}</p>`
        : `<p class="text-[11px] text-ink-dim">仅有文件名（该批数据上传时尚未落表页/行列；请再上传一次工艺文件，或已由运维回填）</p>`;
    return `
        <div class="mx-4 mb-4 border border-brand/25 bg-app-main p-3">
            <p class="text-[10px] uppercase tracking-[0.14em] text-brand mb-2 flex items-center gap-2">
                <span class="${HUD_LED}"></span>
                Excel 溯源
            </p>
            <p class="text-[12px] text-ink font-mono break-all mb-1">${esc(filename || '—')}</p>
            ${cellHint}
        </div>
    `;
}

function renderProcessRow(p, idx) {
    const processId = p.id ?? idx;
    const ratioMap = { 0.8: 'progressive', 1: 'single', 0.5: 'shared', 0.4: 'progressive_shared' };
    const ratioKey = Number(p.cost_ratio);
    const currentDieType = p.die_type || ratioMap[ratioKey] || 'single';

    return `
                <tr class="border-b border-line-subtle last:border-b-0 group hover:bg-app-deep transition-colors duration-200 process-row" data-process-id="${processId}">
                    <td class="px-4 py-4 text-[10px] text-ink-faint font-mono tracking-[0.06em]">${p.process_order ?? '—'}</td>
                    <td class="px-4 py-4 text-[11px] text-ink-muted font-mono tracking-[0.06em]">${esc(p.process_seq)}</td>
                    <td class="px-4 py-4 text-[11px] text-ink-muted font-medium tracking-[0.05em]">${esc(p.process_code)}</td>
                    <td class="px-4 py-4 text-[11px] text-ink-muted font-mono tracking-[0.04em]">${esc(p.die_number)}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-ink-dim tracking-[0.06em]">${p.die_sets ?? '—'}</td>
                    <td class="px-4 py-4 text-right text-[11px] font-mono text-ink-dim tracking-[0.06em]">${p.tonnage ? `${p.tonnage}T` : '—'}</td>
                    <td class="px-4 py-4">
                        <div class="flex items-center gap-2">
                            <select class="${DIE_TYPE_SELECT} hud-filter" data-original-die-type="${currentDieType}">
                                ${DIE_TYPE_OPTIONS.map(o => `<option value="${o.value}" ${o.value === currentDieType ? 'selected' : ''}>${o.label}</option>`).join('')}
                            </select>
                            <span class="text-[9px] font-mono text-ink-faint tracking-[0.05em]" title="模具成本比例">${p.cost_ratio != null ? `${(p.cost_ratio * 100).toFixed(0)}%` : '—'}</span>
                        </div>
                    </td>
                </tr>`;
}

export function renderDetailContent(part, options = {}) {
    const canUpdate = options.canUpdate !== false;
    const sketchUrl = part.sketch_url || '';

    const rows = [
        ['零件号', esc(part.part_number)],
        ['零件名称', esc(part.part_name)],
        ['采购基地', esc(part.location)],
        ['冲压供应商', esc(part.stamping_supplier)],
        ['项目', esc(part.vehicle_model)],
        ['版本', esc(part.version)],
        ['生失效', esc(options.periodLabel || '—')],
        ['材料', esc(part.material)],
        ['工艺方法', esc(part.process_method ?? '-')],
        ['自动化', esc(part.automation ?? '-')],
    ];
    const rowsRightTop = [
        ['厚度', part.thickness != null ? `${part.thickness} mm` : '-'],
        ['重量', part.part_weight != null ? `${part.part_weight} kg` : '-'],
        ['板材尺寸', (part.sheet_length && part.sheet_width) ? `${part.sheet_length}x${part.sheet_width}` : '-'],
        ['可制件数', esc(part.parts_per_sheet)],
        ['板材类型', esc(part.sheet_type)],
    ];
    const rowsRightBottom = [
        ['模具类型', part.cost_ratio != null ? `${(part.cost_ratio * 100).toFixed(0)}%` : esc(part.die_type)],
        ['备注', esc(part.remark ?? '-')],
    ];

    const processes = part.processes || [];
    const processRows = processes.length
        ? processes.map((p, idx) => renderProcessRow(p, idx)).join('')
        : `<tr><td colspan="7" class="px-4 py-12 text-center text-[11px] text-ink-faint tracking-[0.15em]">暂无工序数据</td></tr>`;

    return `
        <div class="h-full min-h-full flex flex-col">
            <!-- 顶部信息区域 -->
            <div class="flex gap-3 p-4">
                <!-- 左侧：基本信息-->
                <div class="flex-1 ${BRABUS_PANEL}">
                    <div class="${BRABUS_PANEL_HEADER} flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-ink-faint">${svgIcon('info-circle')}</span>
                            <span class="text-[9px] font-semibold text-ink-faint uppercase tracking-[0.22em]">基本信息</span>
                        </div>
                        ${sketchUrl ? `
                        <button type="button" id="openSketchModal" class="flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[9px] text-ink-faint hover:text-ink-muted border border-line-subtle hover:border-line transition-all duration-200 tracking-wide group">
                            ${svgIcon('arrows-fullscreen', 'w-3.5 h-3.5 text-ink-faint group-hover:text-ink-muted transition-colors duration-200')}
                            <span class="group-hover:text-ink-faint transition-colors duration-200">查看图纸</span>
                        </button>` : ''}
                    </div>
                    <table class="w-full">${rows.map(detailTableRow).join('')}</table>
                </div>
                <!-- 右侧：尺寸参数-->
                <div class="flex-1 ${BRABUS_PANEL}">
                    <div class="${BRABUS_PANEL_HEADER} flex items-center gap-2">
                        <span class="text-ink-faint">${svgIcon('ruler')}</span>
                        <span class="text-[9px] font-semibold text-ink-faint uppercase tracking-[0.22em]">尺寸参数</span>
                    </div>
                    <table class="w-full">${rowsRightTop.map(detailTableRow).join('')}${renderOffalRows(part, canUpdate)}${rowsRightBottom.map(detailTableRow).join('')}</table>
                </div>
            </div>

            ${renderExcelProvenance(part)}

            <!-- 工序列表 -->
            <div class="mx-4 mb-4 flex flex-col shrink-0">
                <div class="${BRABUS_SECTION_HEADER} flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-ink-faint">${svgIcon('list-ol')}</span>
                        <span class="text-[9px] font-semibold text-ink-faint uppercase tracking-[0.22em]">工序列表</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <select id="batchDieTypeSelect" class="${DIE_TYPE_SELECT} hud-filter" style="width:148px;">
                            <option value="">批量修改模具类型</option>
                            ${DIE_TYPE_OPTIONS.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
                        </select>
                        <button type="button" id="applyBatchDieType" class="h-9 px-4 text-[10px] bg-app-main text-ink-faint border-none focus:outline-none rounded-sm transition-all duration-200 hover:text-brand tracking-wide">
                            批量应用
                        </button>
                    </div>
                </div>
                <div class="${BRABUS_TABLE_WRAPPER}">
                    <table class="w-full">
                        <thead class="shrink-0">
                            <tr>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">序</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">工序号</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">代号</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">模具编号</th>
                                <th class="px-4 py-2.5 text-right text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">模数</th>
                                <th class="px-4 py-2.5 text-right text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">吨位</th>
                                <th class="px-4 py-2.5 text-left text-[8px] font-semibold uppercase tracking-[0.22em] text-ink-faint">模具类型</th>
                            </tr>
                        </thead>
                        <tbody id="processTableBody">${processRows}</tbody>
                    </table>
                </div>
            </div>

            <!-- 保存按钮与规则栏 -->
            ${processes.length > 0 ? `
            <div class="mx-4 mb-6 mt-4">
                <!-- 成本规则 -->
                <div class="flex items-center justify-center gap-4 py-2 mb-3 bg-app-deep border border-line-subtle rounded-sm">
                    <span class="text-[7px] text-ink-faint tracking-[0.15em] uppercase">成本规则</span>
                    <span class="text-[7px] text-ink-faint">·</span>
                    <span class="text-[9px] text-ink-faint"><span class="text-ink-faint">级进模</span> <span class="text-brand-hud font-medium">80%</span></span>
                    <span class="text-[7px] text-ink-faint">·</span>
                    <span class="text-[9px] text-ink-faint"><span class="text-ink-faint">单干模具</span> <span class="text-brand-hud font-medium">100%</span></span>
                    <span class="text-[7px] text-ink-faint">·</span>
                    <span class="text-[9px] text-ink-faint"><span class="text-ink-faint">共模</span> <span class="text-brand-hud font-medium">50%</span></span>
                    <span class="text-[7px] text-ink-faint">·</span>
                    <span class="text-[9px] text-ink-faint"><span class="text-ink-faint">级进共模</span> <span class="text-brand-hud font-medium">40%</span></span>
                </div>
                <!-- 保存按钮 -->
                <div class="flex justify-center">
                    <button type="button" id="saveProcessBtn"
                            data-active="false"
                            class="${BTN_SAVE_DEFAULT}">
                        <span class="tracking-[0.2em]">保存</span>
                    </button>
                </div>
            </div>` : ''}
        </div>
    `;
}
