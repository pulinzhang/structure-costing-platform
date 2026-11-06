/**
 * 成本还原 — 采购对象。一行一条明细，分页按采购对象。
 */

import { HUD_SHELL, BTN_GHOST, filterSelect } from '../../../../ui/classes.js?v=15';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudTableHtml, hudRowHtml } from '../../../../ui/hud-table.js?v=3';

const COLUMNS = [
    ['supplier_name', '供应商'],
    ['vehicle_model', '项目'],
    ['object_kind', '分类'],
    ['internal_number', '物料编码'],
    ['object_part_number', '对象零件号'],
    ['object_part_name', '对象名称'],
    ['vehicle_qty', '单车用量'],
    ['settlement_price', '结算价'],
    ['row_type', '行类型'],
    ['leaf_part_number', '叶子零件号'],
    ['priced_part_number', '取价零件号'],
    ['material', '材质'],
    ['thickness', '厚'],
    ['sheet_length', '长'],
    ['sheet_width', '宽'],
    ['parts_per_sheet', '可制件数'],
    ['blank_weight_kg', '毛坯定额'],
    ['finished_weight_kg', '产品净重'],
    ['utilization_pct', '利用率'],
    ['scrap_weight_kg', '废料重量'],
    ['scrap_price_per_kg', '废料价格'],
    ['swing_shear_fee_per_ton', '摆剪'],
    ['steel_price_per_kg', '钢板单价'],
    ['material_amount_sheet', '原材料金额'],
    ['loss_scrap_deduction', '损耗扣除'],
    ['process_scrap_deduction', '边角扣除'],
    ['material_net', '原材料净成本'],
    ['automation', '冲压模式'],
    ['process_code', '工序'],
    ['tonnage', '吨位'],
    ['stroke_fee', '单冲费用'],
    ['die_length', '模具长'],
    ['die_width', '模具宽'],
    ['die_height', '模具高'],
    ['hollow_factor', '掏空系数'],
    ['die_sets', '套数'],
    ['die_weight_t', '模具重量'],
    ['material_cost', '原材料成本'],
    ['process_cost', '费用总计'],
    ['material_plus_process', '原材料加加工费'],
    ['die_fee', '模具费'],
    ['gauge_fee', '检具费'],
    ['finance_fee', '财务费'],
    ['management_fee', '管理费'],
    ['warehouse_fee', '仓储包装费'],
    ['profit_fee', '税前利润'],
    ['direct_cost', '直接成本'],
    ['unit_cost', '零件标准成本'],
    ['line_amount', '行金额'],
    ['outsourced_amount', '外购费用'],
    ['weld_name', '焊接名称'],
    ['weld_qty', '焊接数量'],
    ['weld_unit_price', '焊接单价'],
    ['weld_amount', '焊接费用'],
    ['ecoat_amount', '电泳费用'],
    ['part_cost_id', '零件价id'],
    ['process_fee_id', '加工费id'],
    ['die_fee_id', '模具费id'],
    ['gauge_fee_id', '检具费id'],
    ['steel_price_id', '钢价id'],
    ['scrap_price_id', '废料价id'],
    ['welding_fee_id', '焊接费id'],
    ['source_filename', '来源文件'],
    ['source_row', '来源行号'],
    ['calc_status', '核算状态'],
    ['remark', '备注'],
];

const NUMBER_KEYS = new Set([
    'vehicle_qty', 'settlement_price', 'thickness', 'sheet_length', 'sheet_width',
    'parts_per_sheet', 'blank_weight_kg', 'finished_weight_kg', 'utilization_pct',
    'scrap_weight_kg', 'scrap_price_per_kg', 'swing_shear_fee_per_ton', 'steel_price_per_kg',
    'material_amount_sheet', 'loss_scrap_deduction', 'process_scrap_deduction', 'material_net',
    'tonnage', 'stroke_fee', 'die_length', 'die_width', 'die_height', 'hollow_factor',
    'die_sets', 'die_weight_t', 'material_cost', 'process_cost', 'material_plus_process',
    'die_fee', 'gauge_fee', 'finance_fee', 'management_fee', 'warehouse_fee', 'profit_fee',
    'direct_cost', 'unit_cost', 'line_amount', 'outsourced_amount', 'weld_qty',
    'weld_unit_price', 'weld_amount', 'ecoat_amount', 'part_cost_id', 'process_fee_id',
    'die_fee_id', 'gauge_fee_id', 'steel_price_id', 'scrap_price_id', 'welding_fee_id',
    'source_row',
]);

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function procurementObjectTemplate() {
    const head = COLUMNS.map(([, label]) => (
        `<th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint whitespace-nowrap">${label}</th>`
    )).join('');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'crpo',
                        searchId: 'crpoBtnSearch',
                        capsules: [
                            { capsuleId: 'crpoCapsuleLocation', idleLabel: '基地' },
                            { capsuleId: 'crpoCapsulePeriod', idleLabel: '年月' },
                            { capsuleId: 'crpoCapsuleVehicle', idleLabel: '全部项目' },
                            { capsuleId: 'crpoCapsuleSupplier', idleLabel: '全部供应商' },
                        ],
                        fieldsHtml: [
                            filterSelect('crpoFilterLocation', '基地', { required: true, emptyLabel: '请选择基地' }),
                            filterSelect('crpoFilterYear', '年', { required: true, emptyLabel: '年' }),
                            filterSelect('crpoFilterMonth', '月', { required: true, emptyLabel: '月' }),
                            filterSelect('crpoFilterVehicle', '项目', { emptyLabel: '全部项目' }),
                            filterSelect('crpoFilterSupplier', '供应商', { emptyLabel: '全部供应商' }),
                            `<button id="crpoExportBtn" type="button" class="${BTN_GHOST}">导出</button>`,
                        ].join(''),
                        alwaysHintHtml: '分页按采购对象。一个对象的材料、工序、小计和合计都在同一页。',
                    })}
                    <p id="crpoScope" class="mt-2 text-[11px] text-ink-muted"></p>
                </div>
                ${hudTableHtml({
                    prefix: 'crpo',
                    minWidth: '3600px',
                    headHtml: head,
                    empty: {
                        title: '没有命中的采购对象',
                        hint: '该月没有落在生效期内的对象，或还没有总成核价。',
                    },
                    loading: true,
                })}
            </div>
        </div>`;
}

export function renderProcurementObjectRows(items) {
    let previousId = null;
    return items.map((item) => {
        const broken = (item.remark || '').includes('还原不符');
        const isTotal = item.row_type === '合计';
        const split = previousId !== null && previousId !== item.object_id;
        previousId = item.object_id;
        const cells = COLUMNS.map(([key]) => {
            const raw = item[key];
            const text = raw == null || raw === '' ? '' : escapeHtml(raw);
            const align = NUMBER_KEYS.has(key) ? 'text-right tabular-nums' : 'text-left';
            const warn = key === 'remark' && broken ? ' text-danger' : '';
            return `<td class="px-2 py-1.5 ${align}${warn} whitespace-nowrap text-[11px] text-ink">${text}</td>`;
        }).join('');
        const extra = [
            split ? 'border-t border-line-strong' : '',
            isTotal ? 'font-medium' : '',
        ].filter(Boolean).join(' ');
        return hudRowHtml({ cellsHtml: cells, extraClass: extra });
    }).join('');
}
