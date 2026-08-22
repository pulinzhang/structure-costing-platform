/**
 * 常见提问（纯自然语言；条件由后端 LLM 抽取）
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
