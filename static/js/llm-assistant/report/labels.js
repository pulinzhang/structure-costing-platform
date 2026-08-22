/**
 * 报告类型 / 受众中文标签（与后端 prompts/labels.py 对齐）
 */

/** @type {Record<string, string>} */
export const ANALYSIS_KIND_LABEL = {
    summary: '概览分析',
    trend: '趋势分析',
    drivers: '动因分析',
    comparison: '对比分析',
    risk: '风险分析',
    drilldown: '核价详情',
};

/** composite.result.parts 分区标题（与后端 runner 键名对齐） */
/** @type {Record<string, string>} */
export const ANALYSIS_SECTION_LABEL = {
    existence: '数据覆盖',
    l0_drilldown: '成品核价详情',
    stamping_cost_drilldown: '冲压核价详情',
    stamping_process_drilldown: '冲压工艺详情',
    part_existence: '零件数据概览',
};

/** @type {Record<string, string>} */
export const AUDIENCE_LABEL = {
    buyer: '采购员',
    buyer_lead: '采购主管',
    costing: '核价工程师',
    sales_quote: '销售报价',
    exec: '管理层',
};

/**
 * @param {string|null|undefined} analysesKey
 * @returns {string}
 */
export function analysesKeyLabelZh(analysesKey) {
    const text = String(analysesKey || '').trim();
    if (!text) return ANALYSIS_KIND_LABEL.summary;
    return text
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean)
        .map((part) => ANALYSIS_KIND_LABEL[part] || part)
        .join('、');
}

/**
 * @param {string|null|undefined} audience
 * @returns {string}
 */
export function audienceLabelZh(audience) {
    const text = String(audience || '').trim();
    return AUDIENCE_LABEL[text] || text;
}

/**
 * Snapshot composite 分区 / 分析类型 → 中文标题
 * @param {string} key
 * @returns {string}
 */
export function analysisSectionLabelZh(key) {
    const text = String(key || '').trim();
    if (!text) return '分析结果';
    return ANALYSIS_KIND_LABEL[text]
        || ANALYSIS_SECTION_LABEL[text]
        || text.replace(/_/g, ' ');
}
