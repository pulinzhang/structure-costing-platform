/**
 * 报告类型中文标签（与后端 prompts/labels.py 对齐）
 */

/** @type {Record<string, string>} */
export const ANALYSIS_KIND_LABEL = {
    summary: '概览分析',
    trend: '趋势分析',
    drivers: '动因分析',
    comparison: '对比分析',
    risk: '风险分析',
    drilldown: '核价详情',
    usage_help: '操作说明',
    engine_readiness: '核价条件检查',
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
        .map((part) => ANALYSIS_KIND_LABEL[part] || '分析')
        .join('、');
}
