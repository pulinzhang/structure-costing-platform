/**
 * 常见提问（纯自然语言；条件由后端 LLM 抽取）
 */

/** @typedef {{ id: string, label: string, audience?: string, needs_part_number?: boolean }} PromptItem */

/** @type {PromptItem[]} */
export const PROMPT_CATALOG = [
    {
        id: 'Q01',
        label: '今年青岛采购成本总体怎么样？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q03',
        label: '哪些供货总成最贵？优先跟哪些件议价？',
        audience: 'buyer',
    },
    {
        id: 'Q11',
        label: '还有哪些零件缺价或算不全（partial）？',
        audience: 'buyer',
    },
    {
        id: 'Q12',
        label: '为什么这个月核价跑不起来？主数据还缺什么？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q21',
        label: '本月钢材联动价哪些规格在涨？',
        audience: 'buyer',
    },
    {
        id: 'Q31',
        label: '哪些冲压件材料净成本异常偏高？',
        audience: 'buyer',
    },
    {
        id: 'Q41',
        label: '交给主机厂的总成里，总费用 Top 有哪些？',
        audience: 'sales_quote',
    },
    {
        id: 'Q51',
        label: '帮我解读零件号 {part_number}，我怎么跟供应商谈？',
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
 * @param {{ part_number?: string|null }} [vars]
 * @returns {string}
 */
export function fillPromptTemplate(template, vars) {
    const partNumber = vars?.part_number ?? '';
    return String(template || '').replace(/\{part_number\}/g, String(partNumber));
}
