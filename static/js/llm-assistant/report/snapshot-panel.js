/**
 * Snapshot 结构化证据（数字以 Snapshot 为准，LLM Markdown 为解释层）
 */

import { ANALYSIS_KIND_LABEL, analysisSectionLabelZh } from './labels.js';

const COMPARABILITY_LABEL = {
    tight: '同口径可比',
    loose: '口径可能漂移',
    unknown: '口径未校验',
};

/**
 * @param {object|null|undefined} snapshot
 * @param {object|null|undefined} scope
 * @param {string|null|undefined} resolvedReportType
 * @returns {string}
 */
export function renderSnapshotPanel(snapshot, scope, resolvedReportType) {
    const meta = snapshot?.meta || {};
    const summary = snapshot?.summary;
    const result = snapshot?.result;
    const query = snapshot?.query;

    const badges = buildBadges(meta, scope, query, resolvedReportType);
    const warnings = buildWarnings(meta);
    const drilldownFocused = isDrilldownFocused(query, resolvedReportType);
    const kpiBlock = drilldownFocused ? '' : renderSummaryKpis(summary);
    const resultBlock = renderResultBlock(result, query, resolvedReportType);

    if (!badges && !warnings && !kpiBlock && !resultBlock) {
        if (meta.data_message) {
            return `<div class="mb-2 text-[10px] text-[#757575]">${esc(meta.data_message)}</div>`;
        }
        return '';
    }

    return `
<div class="mb-2 rounded-sm border border-[#222222] bg-[#0c0c0c] overflow-hidden">
  ${badges ? `<div class="px-2 py-1.5 border-b border-[#1a1a1a] flex flex-wrap gap-1">${badges}</div>` : ''}
  ${warnings}
  <div class="px-2 py-2 space-y-2">
    ${kpiBlock}
    ${resultBlock}
  </div>
</div>`;
}

/**
 * @param {object} meta
 * @param {object|null|undefined} scope
 * @param {object|null|undefined} query
 * @param {string|null|undefined} resolvedReportType
 * @returns {string}
 */
function buildBadges(meta, scope, query, resolvedReportType) {
    const parts = [];

    const comparability = meta.comparability || 'unknown';
    const compClass = comparability === 'tight'
        ? 'text-[#4caf50] border-[#2e7d32]/40 bg-[#1b2e1b]'
        : comparability === 'loose'
            ? 'text-[#ffb74d] border-[#f57f17]/40 bg-[#2a2210]'
            : 'text-[#9e9e9e] border-[#2c2c2c] bg-[#141414]';
    parts.push(`<span class="inline-flex px-1.5 py-0.5 text-[9px] border rounded-sm ${compClass}">${esc(COMPARABILITY_LABEL[comparability] || comparability)}</span>`);

    const timeRange = query?.time_range;
    if (timeRange?.start && timeRange?.end) {
        const label = timeRange.start === timeRange.end
            ? timeRange.start
            : `${timeRange.start} ~ ${timeRange.end}`;
        parts.push(chip(label, 'font-mono'));
    }

    const filters = query?.filters || {};
    const location = filters.location || scope?.location;
    if (location) parts.push(chip(location));
    if (filters.vehicle_model || scope?.vehicle_model) {
        const vehicleModel = filters.vehicle_model || scope?.vehicle_model;
        if (vehicleModel && vehicleModel !== '未指定') {
            parts.push(chip(vehicleModel));
        }
    }
    if (filters.part_number || scope?.part_number) {
        parts.push(chip(filters.part_number || scope?.part_number, 'font-mono'));
    }

    const analyses = parseAnalyses(resolvedReportType, query?.analyses)
        .filter((kind) => !(isDrilldownFocused(query, resolvedReportType) && kind === 'summary'));
    analyses.forEach((kind) => {
        parts.push(chip(ANALYSIS_KIND_LABEL[kind] || kind, 'text-[#ff8a80]'));
    });

    if (meta.comparison_basis_label) {
        parts.push(chip(meta.comparison_basis_label, 'text-[#757575]'));
    }

    return parts.join('');
}

/**
 * @param {object} meta
 * @returns {string}
 */
function buildWarnings(meta) {
    const lines = [];
    if (meta.comparability === 'loose') {
        lines.push('趋势可能含 BOM/工艺变更，不单是价格变动');
    }
    if (Array.isArray(meta.unresolved_mentions) && meta.unresolved_mentions.length) {
        lines.push(`未识别实体：${meta.unresolved_mentions.join('、')}`);
    }
    if (meta.has_data === false && meta.data_message) {
        lines.push(meta.data_message);
    }
    if (!lines.length) return '';
    return `<div class="px-2 py-1.5 border-b border-[#1a1a1a] bg-[#1A080A]/40 text-[10px] text-[#ffb74d]">${lines.map((line) => esc(line)).join('<br>')}</div>`;
}

/**
 * @param {object|null|undefined} summary
 * @returns {string}
 */
function renderSummaryKpis(summary) {
    if (!summary || typeof summary !== 'object') return '';

    const rows = [];

    if (summary.grand_total_sum != null) {
        rows.push(kpi('采购合计', summary.grand_total_sum, true));
    }
    if (summary.final_processing_fee_avg != null) {
        rows.push(kpi('加工费均值', summary.final_processing_fee_avg, true));
    }
    if (summary.final_l0_welding_fee != null || summary.total_l0_welding_fee != null) {
        rows.push(kpi('焊接费', summary.final_l0_welding_fee || summary.total_l0_welding_fee, true));
    }
    if (summary.row_count != null) {
        rows.push(kpi('记录数', summary.row_count));
    }
    if (summary.part_count != null) {
        rows.push(kpi('零件数', summary.part_count));
    }
    if (summary.l0_count != null) {
        rows.push(kpi('总成件数', summary.l0_count));
    }
    if (summary.partial_count != null && Number(summary.partial_count) > 0) {
        rows.push(kpi('核算不全', summary.partial_count, false, 'text-[#ffb74d]'));
    }
    if (summary.ok_count != null) {
        rows.push(kpi('已算清', summary.ok_count));
    }

    if (!rows.length) return '';

    return `<div class="grid grid-cols-2 gap-1.5">${rows.join('')}</div>`;
}

/**
 * @param {object|null|undefined} result
 * @param {object|null|undefined} query
 * @param {string|null|undefined} resolvedReportType
 * @returns {string}
 */
function renderResultBlock(result, query, resolvedReportType) {
    if (!result || typeof result !== 'object') return '';

    const kind = result.kind;
    if (kind === 'composite') {
        const parts = result.parts || {};
        return Object.entries(parts)
            .map(([key, part]) => {
                if (!shouldRenderCompositePart(key, part, query, resolvedReportType)) return '';
                return `<div class="border-t border-[#1a1a1a] pt-2 first:border-0 first:pt-0">
                  <div class="text-[9px] text-[#555555] mb-1">${esc(analysisSectionLabelZh(key))}</div>
                  ${renderResultBlock(part, query, resolvedReportType)}
                </div>`;
            })
            .join('');
    }

    if (kind === 'trend') {
        return renderTrendBlock(result);
    }
    if (kind === 'drilldown') {
        return renderDrilldownBlock(result);
    }
    if (kind === 'drivers') {
        return renderDriversBlock(result);
    }
    if (kind === 'comparison') {
        return renderComparisonBlock(result);
    }
    if (kind === 'risk') {
        return renderRiskBlock(result);
    }

    return '';
}

/**
 * @param {object} trend
 * @returns {string}
 */
function renderTrendBlock(trend) {
    const stats = [];
    if (trend.start != null && trend.end != null) {
        stats.push(`起止 ${trend.start} → ${trend.end}`);
    }
    if (trend.cumulative_rate != null) {
        stats.push(`累计 ${formatRate(trend.cumulative_rate)}`);
    }
    if (trend.cumulative_delta != null) {
        stats.push(`Δ ${trend.cumulative_delta}`);
    }
    if (Array.isArray(trend.anomaly_months) && trend.anomaly_months.length) {
        stats.push(`异常月 ${trend.anomaly_months.join('、')}`);
    }

    const points = Array.isArray(trend.points) ? trend.points.slice(-6) : [];
    const table = points.length
        ? `<table class="w-full text-[9px] font-mono mt-1.5 border-collapse">
            <thead><tr class="text-[#555555]">
              <th class="text-left py-0.5">月</th>
              <th class="text-right py-0.5">值</th>
              <th class="text-right py-0.5">环比</th>
            </tr></thead>
            <tbody>${points.map((point) => {
            const value = point.grand_total_sum
                || point.avg_final_price
                || point.unit_cost_sum
                || point.value
                || '-';
            return `<tr class="border-t border-[#141418] text-[#8E8E93]">
                <td class="py-0.5">${esc(point.month)}</td>
                <td class="py-0.5 text-right tabular-nums">${esc(value)}</td>
                <td class="py-0.5 text-right tabular-nums">${esc(formatRate(point.mom_rate))}</td>
              </tr>`;
        }).join('')}</tbody>
          </table>`
        : '';

    return `
<div>
  ${stats.length ? `<div class="text-[10px] text-[#9e9e9e]">${stats.map((s) => esc(s)).join(' · ')}</div>` : ''}
  ${table}
</div>`;
}

/**
 * @param {object} drill
 * @returns {string}
 */
function renderDrilldownBlock(drill) {
    if (drill.found === false) {
        if (drill.applicable === false || drill.expected_absence) return '';
        return `<div class="text-[10px] text-[#757575]">${esc(drill.message || '未找到匹配记录')}</div>`;
    }

    const latest = drill.latest && typeof drill.latest === 'object' ? drill.latest : null;
    const fields = latest
        ? [
            ['零件号', drill.part_number],
            ['零件名', drill.part_name],
            ['月份', latest.month],
            ['总费用', latest.grand_total],
            ['月总账', latest.total_amount],
            ['间接费用', latest.indirect_amount],
            ['冲压费用', latest.stamping_amount],
            ['外购费用', latest.purchased_amount],
            ['焊接费用', latest.welding_amount],
            ['核算状态', latest.calc_status],
            ['BOM版本', latest.bom_version],
        ]
        : [
            ['零件号', drill.part_number],
            ['零件名', drill.part_name],
            ['加工费', drill.final_processing_fee || drill.processing_fee],
            ['焊接费', drill.final_l0_welding_fee || drill.total_l0_welding_fee],
            ['单价', drill.unit_cost || drill.final_unit_cost],
            ['年度价', drill.annual_price || drill.final_annual_price],
            ['年份', drill.year],
            ['基地', drill.location || drill.stamping_supplier],
            ['月份', drill.month],
        ].filter(([, value]) => value != null && value !== '');

    if (!fields.length) {
        if (drill.message) {
            return `<div class="text-[10px] text-[#757575]">${esc(drill.message)}</div>`;
        }
        return '';
    }

    return `<dl class="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px]">
    ${fields.map(([label, value]) => `
      <dt class="text-[#555555]">${esc(label)}</dt>
      <dd class="text-[#C8C8D0] font-mono tabular-nums truncate" title="${escAttr(value)}">${esc(value)}</dd>
    `).join('')}
  </dl>`;
}

/**
 * @param {object} drivers
 * @returns {string}
 */
function renderDriversBlock(drivers) {
    const items = Array.isArray(drivers.items)
        ? drivers.items
        : (Array.isArray(drivers.top) ? drivers.top : []);
    if (!items.length) return '';

    const rows = items.slice(0, 5).map((item) => {
        const name = item.part_number || item.part_name || item.label || '-';
        const change = item.change_rate != null
            ? formatRate(item.change_rate)
            : (item.change != null ? item.change : '-');
        return `<tr class="border-t border-[#141418]">
          <td class="py-0.5 text-[#C8C8D0] truncate max-w-[120px]" title="${escAttr(name)}">${esc(name)}</td>
          <td class="py-0.5 text-right font-mono tabular-nums text-[#ff8a80]">${esc(change)}</td>
        </tr>`;
    }).join('');

    return `<table class="w-full text-[9px] border-collapse">
    <thead><tr class="text-[#555555]"><th class="text-left py-0.5">对象</th><th class="text-right py-0.5">变化</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

/**
 * @param {object} comparison
 * @returns {string}
 */
function renderComparisonBlock(comparison) {
    const items = Array.isArray(comparison.items)
        ? comparison.items
        : (Array.isArray(comparison.locations) ? comparison.locations : []);
    if (!items.length) return '';

    const rows = items.slice(0, 4).map((item) => {
        const label = item.location || item.label || '-';
        const rate = item.change_rate != null ? formatRate(item.change_rate) : (item.rate || '-');
        return `<tr class="border-t border-[#141418]">
          <td class="py-0.5 text-[#C8C8D0]">${esc(label)}</td>
          <td class="py-0.5 text-right font-mono tabular-nums">${esc(rate)}</td>
        </tr>`;
    }).join('');

    return `<table class="w-full text-[9px] border-collapse">
    <thead><tr class="text-[#555555]"><th class="text-left py-0.5">维度</th><th class="text-right py-0.5">涨幅</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

/**
 * @param {object} risk
 * @returns {string}
 */
function renderRiskBlock(risk) {
    const count = risk.partial_count ?? risk.missing_count;
    const risks = Array.isArray(risk.risks) ? risk.risks : [];
    const head = count != null
        ? `<div class="text-[10px] text-[#ffb74d]">缺价 / partial：${esc(count)} 件</div>`
        : '';
    const list = risks.slice(0, 3).map((item) => {
        const label = item.part_number || item.message || JSON.stringify(item);
        return `<li class="truncate">${esc(label)}</li>`;
    }).join('');
    return `${head}${list ? `<ul class="mt-1 text-[9px] text-[#757575] list-disc pl-4">${list}</ul>` : ''}`;
}

/**
 * @param {string|null|undefined} resolvedReportType
 * @param {string[]|undefined} queryAnalyses
 * @returns {string[]}
 */
function parseAnalyses(resolvedReportType, queryAnalyses) {
    if (Array.isArray(queryAnalyses) && queryAnalyses.length) {
        return queryAnalyses;
    }
    if (!resolvedReportType) return [];
    return String(resolvedReportType)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
}

/**
 * 单件核价/价格详情：不展示仪表盘式 KPI / 概览标签
 * @param {object|null|undefined} query
 * @param {string|null|undefined} resolvedReportType
 * @returns {boolean}
 */
function isDrilldownFocused(query, resolvedReportType) {
    const analyses = parseAnalyses(resolvedReportType, query?.analyses);
    if (analyses.length === 1 && analyses[0] === 'drilldown') return true;
    if (analyses.includes('drilldown') && !analyses.includes('summary')) return true;
    const question = String(query?.user_question || '');
    return /价格详情|核价详情|价格详细|核价详细|价格明细|核价明细/.test(question);
}

/**
 * @param {string} key
 * @param {object} part
 * @param {object|null|undefined} query
 * @param {string|null|undefined} resolvedReportType
 * @returns {boolean}
 */
function shouldRenderCompositePart(key, part, query, resolvedReportType) {
    if (!part || typeof part !== 'object') return false;
    if (key === 'existence' || part.kind === 'part_existence') return false;
    if (part.kind === 'drilldown') {
        if (part.found === false) return false;
        if (part.applicable === false || part.expected_absence) return false;
        if (part.message && !part.latest && !part.part_number) return false;
    }
    if (isDrilldownFocused(query, resolvedReportType)) {
        if (key === 'stamping_cost_drilldown' || key === 'stamping_process_drilldown') {
            return false;
        }
    }
    return true;
}

/**
 * @param {string} label
 * @param {string|number} value
 * @param {boolean} [emphasis]
 * @param {string} [valueClass]
 * @returns {string}
 */
function kpi(label, value, emphasis = false, valueClass = '') {
    const valCls = valueClass || (emphasis ? 'text-[#FF1E27] font-semibold' : 'text-[#C8C8D0]');
    return `<div class="px-1.5 py-1 bg-[#111111] border border-[#1a1a1a] rounded-sm">
    <div class="text-[9px] text-[#555555]">${esc(label)}</div>
    <div class="text-[11px] font-mono tabular-nums ${valCls}">${esc(value)}</div>
  </div>`;
}

/**
 * @param {string} text
 * @param {string} [extraClass]
 * @returns {string}
 */
function chip(text, extraClass = '') {
    return `<span class="inline-flex px-1.5 py-0.5 text-[9px] border border-[#2c2c2c] bg-[#141414] text-[#9e9e9e] rounded-sm ${extraClass}">${esc(text)}</span>`;
}

/**
 * @param {string|number|null|undefined} rate
 * @returns {string}
 */
function formatRate(rate) {
    if (rate == null || rate === '') return '-';
    const num = Number(rate);
    if (Number.isFinite(num)) {
        const pct = Math.abs(num) <= 1 ? num * 100 : num;
        const sign = pct > 0 ? '+' : '';
        return `${sign}${pct.toFixed(1)}%`;
    }
    return String(rate);
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '-');
}

function escAttr(value) {
    return esc(value).replace(/'/g, '&#39;');
}
