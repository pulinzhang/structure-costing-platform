/**
 * 采购对象清单 — 对人展示的文案（内部码仍用 other_leaf / l0_degenerate）。
 */

export const KIND_LABELS = {
    l0_degenerate: '退化供货件',
    l1_subassembly: '分总成',
    l1_stamping: '冲压件',
};

export const SECTION_LABELS = {
    object: '采购对象',
    other_leaf: '标准件/胶等',
    anomaly: '异常',
};

export const CONFIRM_LABELS = {
    pending: '待定',
    outsourced: '外发',
    in_house: '自制',
};

export const AUDIT_LABELS = {
    pending: '待审',
    approved: '已审',
};
