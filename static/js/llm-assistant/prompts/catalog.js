/**
 * 常见提问目录（对齐设计 §9.3 P0）
 */

/** @typedef {{ id: string, label: string, report_type: string, audience?: string, needs_part_number?: boolean }} PromptItem */

/** @type {PromptItem[]} */
export const PROMPT_CATALOG = [
    {
        id: 'Q01',
        label: '{location} {year}年{month}月的采购成本总体怎么样？',
        report_type: 'dashboard',
        audience: 'buyer_lead',
    },
    {
        id: 'Q03',
        label: '哪些供货总成最贵？优先跟哪些件议价？',
        report_type: 'l0',
        audience: 'buyer',
    },
    {
        id: 'Q11',
        label: '还有哪些零件缺价或算不全（partial）？',
        report_type: 'dashboard',
        audience: 'buyer',
    },
    {
        id: 'Q12',
        label: '为什么这个月核价跑不起来？主数据还缺什么？',
        report_type: 'gate',
        audience: 'buyer_lead',
    },
    {
        id: 'Q21',
        label: '本月钢材联动价哪些规格在涨？',
        report_type: 'steel',
        audience: 'buyer',
    },
    {
        id: 'Q31',
        label: '哪些冲压件材料净成本异常偏高？',
        report_type: 'stamping_part',
        audience: 'buyer',
    },
    {
        id: 'Q41',
        label: '交给主机厂的总成里，总费用 Top 有哪些？',
        report_type: 'l0',
        audience: 'sales_quote',
    },
    {
        id: 'Q51',
        label: '帮我解读零件号 {part_number}，我怎么跟供应商谈？',
        report_type: 'part_drilldown',
        audience: 'buyer',
        needs_part_number: true,
    },
];

/**
 * @param {string} promptId
 * @returns {PromptItem|null}
 */
export function findPrompt(promptId) {
    if (!promptId) return null;
    return PROMPT_CATALOG.find((item) => item.id === promptId) || null;
}

/**
 * @param {string} template
 * @param {Record<string, string|number|null|undefined>} scope
 * @returns {string}
 */
export function fillPromptTemplate(template, scope) {
    const map = {
        location: scope.location ?? '',
        year: scope.year ?? '',
        month: scope.month ?? '',
        vehicle_model: scope.vehicle_model ?? '',
        bom_version: scope.bom_version ?? '',
        part_number: scope.part_number ?? '',
    };
    return String(template || '').replace(/\{(\w+)\}/g, (_, key) => {
        const value = map[key];
        return value == null ? '' : String(value);
    });
}
