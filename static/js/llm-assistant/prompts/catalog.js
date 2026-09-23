/**
 * 常见提问（纯自然语言；条件由后端 LLM 抽取）
 * 只留核算、进度、异常这类核价提问。操作说明不进胶囊。
 */

/** @typedef {{ id: string, label: string, audience?: string, needs_part_number?: boolean }} PromptItem */

/** @type {PromptItem[]} */
export const PROMPT_CATALOG = [
    {
        id: 'Q01',
        label: '当月核算情况怎么样？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q02',
        label: '当月一事一议价格怎么样？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q03',
        label: '当月核价进度怎么样？待审核还有多少？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q04',
        label: '采购对象还有多少没确认外发？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q05',
        label: '今年模具费待审核有多少？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q08',
        label: '检具费情况怎么样？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q09',
        label: '当月核价有无异常？',
        audience: 'buyer_lead',
    },
    {
        id: 'Q10',
        label: '芜湖今年年度零件价有无异常？',
        audience: 'buyer_lead',
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
