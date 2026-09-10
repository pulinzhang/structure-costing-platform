/**
 * 常见提问（纯自然语言；条件由后端 LLM 抽取）
 * 操作员场景靠前，主管总览靠后。
 */

/** @typedef {{ id: string, label: string, audience?: string, needs_part_number?: boolean }} PromptItem */

/** @type {PromptItem[]} */
export const PROMPT_CATALOG = [
    {
        id: 'O01',
        label: '{part_number}的价格多少？',
        audience: 'buyer',
        needs_part_number: true,
    },
    {
        id: 'O02',
        label: '{part_number}最近一次核价多少钱？',
        audience: 'buyer',
        needs_part_number: true,
    },
    {
        id: 'O03',
        label: '{part_number}在不在库里？',
        audience: 'buyer',
        needs_part_number: true,
    },
    {
        id: 'O04',
        label: '成品核价计算卡住怎么办？',
        audience: 'buyer',
    },
    {
        id: 'O05',
        label: '采购对象怎么确认外发？',
        audience: 'buyer',
    },
    {
        id: 'O06',
        label: '自动核价引擎一直运行中怎么办？',
        audience: 'buyer',
    },
    {
        id: 'O07',
        label: '怎么用简码问某个件的价？',
        audience: 'buyer',
    },
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
        id: 'Q06',
        label: '总成核价怎么审核？',
        audience: 'buyer',
    },
    {
        id: 'Q07',
        label: '冲压零件价格计算页在哪？',
        audience: 'buyer',
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
