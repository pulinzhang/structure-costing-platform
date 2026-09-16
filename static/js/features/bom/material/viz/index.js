/**
 * Multi-Level BOM — 产品结构可视化
 *
 * 业务域：汽车冲焊件供应商。制造类别不含电子/电气件。
 * 自上而下层级树：父子关系 + 用量 + 制造类别。
 */

import { can } from '../../../../permissions.js?v=8';
import { bomVizTemplate } from './template.js?v=4';
import {
    asOfFilterHtml,
    fillAsOfSelects,
    fillYearMonthSelects,
    fmtPeriodRange,
    periodEditorHtml,
    readAsOf,
    readPeriod,
    wallClockYearMonth,
} from '../../../common/period-ui.js?v=2';

/** 布局常量（保证同层不重叠、标签不挤） */
const LAYOUT = {
    padX: 48,
    padY: 40,
    levelGapY: 56,
    siblingGapX: 28,
    node: {
        0: { w: 168, h: 168, img: 88 },
        1: { w: 148, h: 156, img: 72 },
        2: { w: 128, h: 78, img: 0 },
        deep: { w: 120, h: 74, img: 0 },
    },
};

/**
 * 制造类别（与后端 app.common.bom.manufacturing_category 对齐）
 * 刻意不含 electronic / machining
 */
const PART_CATEGORY = {
    assembly: {
        key: 'assembly',
        label: '总成',
        color: '#30343A',
        knowledge: '供货总成 —— 交付客户的冲焊装配单元',
    },
    sub_assembly: {
        key: 'sub_assembly',
        label: '分总成',
        color: '#8B6A45',
        knowledge: '分总成（焊接件）—— 有下级子件的焊接结构',
    },
    stamping: {
        key: 'stamping',
        label: '冲压件',
        color: '#54758C',
        knowledge: '自制冲压成形零件（含安装支架、加强板等）',
    },
    standard: {
        key: 'standard',
        label: '标准件',
        color: '#9A948A',
        knowledge: '标准件 —— 螺栓、螺母等',
    },
    plastic: {
        key: 'plastic',
        label: '塑料件',
        color: '#A98256',
        knowledge: '外购塑料件',
    },
    rubber: {
        key: 'rubber',
        label: '橡胶件',
        color: '#665D57',
        knowledge: '橡胶 / 密封件',
    },
    consumable: {
        key: 'consumable',
        label: '辅料',
        color: '#5A534C',
        knowledge: '胶、焊丝等冲焊辅料',
    },
    other: {
        key: 'other',
        label: '其他',
        color: '#70777D',
        knowledge: '其他外购件（非电器）',
    },
};

const LEGEND_ORDER = [
    'assembly',
    'sub_assembly',
    'stamping',
    'standard',
    'plastic',
    'rubber',
    'consumable',
    'other',
];

const ROLE_KNOWLEDGE = {
    supply: '供货总成 —— 我方向客户交付的冲焊装配单元',
    structure: '分总成 —— 焊接结构，由若干子件组成',
    make: '自制件 —— 我方冲压成形零件',
    buy: '采购件 —— 外购标准件或外协件（非电器）',
    consumable: '辅料 —— 胶、焊丝等消耗材料',
};

const STEEL_MATERIAL_RE =
    /DC\d|HC\d|CR\d|SPCC|SPCD|SPCE|\+Z|镀锌|冷轧|热轧|钢板|B340|B410|SAPH|QSTE/i;
const STAMPING_NAME_RE =
    /支架|加强板|连接板|内板|外板|梁|纵梁|横梁|安装板|固定板|底板|盖板|罩板|翼子板|门槛/;
const STANDARD_NAME_RE = /螺母|螺栓|螺钉|垫圈|垫片|卡扣|卡箍|铆钉|销/;
const PLASTIC_RE = /塑料|注塑|\bPP\b|\bABS\b|\bPC\b|尼龙|PA6|PA66/i;
const RUBBER_RE = /橡胶|密封|胶套|减震|EPDM|衬套/;
const CONSUMABLE_RE = /TEROSON|结构胶|密封胶|焊丝|涂料/i;

const bomVizState = {
    snapshotId: null,
    nodeId: null,
    snapshot: null,
    assembly: null,
    /** @type {Map<number, object>} */
    nodeMap: new Map(),
    /** 展开中的节点 id */
    expandedIds: new Set(),
    /** @type {Array<object>} */
    placements: [],
    hoverId: null,
    selectedId: null,
    isLoading: false,
    asOf: wallClockYearMonth(),
    includeExpired: false,
    canUpdatePeriod: false,
};

function parseHex(hex) {
    const h = String(hex || '').replace('#', '');
    if (h.length !== 6) return { r: 120, g: 120, b: 120 };
    return {
        r: Number.parseInt(h.slice(0, 2), 16),
        g: Number.parseInt(h.slice(2, 4), 16),
        b: Number.parseInt(h.slice(4, 6), 16),
    };
}

function hexToRgba(hex, alpha) {
    const { r, g, b } = parseHex(hex);
    return `rgba(${r},${g},${b},${alpha})`;
}

function lightenHex(hex, amount = 0.28) {
    const { r, g, b } = parseHex(hex);
    const mix = (c) => Math.round(c + (255 - c) * amount);
    const to = (n) => n.toString(16).padStart(2, '0');
    return `#${to(mix(r))}${to(mix(g))}${to(mix(b))}`;
}

/**
 * 制造类别：优先用后端 manufacturing_category；无字段时本地兜底（与后端规则对齐）
 */
function classifyPart(node, isRoot = false) {
    const fromApi = node?.manufacturing_category;
    if (fromApi && PART_CATEGORY[fromApi]) {
        return PART_CATEGORY[fromApi];
    }

    const hasChildren =
        Array.isArray(node?.children) && node.children.length > 0;

    if (isRoot || node?.node_role === 'supply' || node?.is_supply_unit) {
        return PART_CATEGORY.assembly;
    }
    if (
        node?.node_role === 'structure' ||
        hasChildren ||
        /分总成/.test(String(node?.part_name || ''))
    ) {
        return PART_CATEGORY.sub_assembly;
    }

    const partName = String(node?.part_name || '');
    const material = String(node?.material || '');
    const partNumber = String(node?.part_number || '');
    const qtyUnit = String(node?.qty_unit || '').toLowerCase();

    if (node?.node_role === 'consumable' || qtyUnit === 'mm') {
        return PART_CATEGORY.consumable;
    }
    if (node?.node_role === 'make') {
        return PART_CATEGORY.stamping;
    }
    if (node?.thickness_mm != null && node.thickness_mm !== '') {
        return PART_CATEGORY.stamping;
    }
    if (STEEL_MATERIAL_RE.test(material)) {
        return PART_CATEGORY.stamping;
    }
    if (STAMPING_NAME_RE.test(partName) && node?.node_role !== 'buy') {
        return PART_CATEGORY.stamping;
    }
    if (CONSUMABLE_RE.test(material) || CONSUMABLE_RE.test(partName)) {
        return PART_CATEGORY.consumable;
    }
    if (STANDARD_NAME_RE.test(partName) || /^N/i.test(partNumber)) {
        return PART_CATEGORY.standard;
    }
    if (PLASTIC_RE.test(partName) || PLASTIC_RE.test(material)) {
        return PART_CATEGORY.plastic;
    }
    if (RUBBER_RE.test(partName) || RUBBER_RE.test(material)) {
        return PART_CATEGORY.rubber;
    }
    if (node?.node_role === 'buy') {
        return PART_CATEGORY.other;
    }
    if (material && node?.node_role !== 'buy' && node?.node_role !== 'consumable') {
        return PART_CATEGORY.stamping;
    }
    return PART_CATEGORY.other;
}

function categoryKnowledge(node, isRoot, category) {
    if (node?.weld_info) return `备注：${node.weld_info}`;
    if (category?.knowledge) return category.knowledge;
    if (node?.node_role && ROLE_KNOWLEDGE[node.node_role]) {
        return ROLE_KNOWLEDGE[node.node_role];
    }
    return isRoot ? '本页供货总成' : '零件节点';
}

function readHashParams() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return { snapshotId: null, nodeId: null };
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    const snapshotId = Number.parseInt(qs.get('snapshot_id') || '', 10);
    const nodeId = Number.parseInt(qs.get('node_id') || '', 10);
    return {
        snapshotId: Number.isFinite(snapshotId) && snapshotId > 0 ? snapshotId : null,
        nodeId: Number.isFinite(nodeId) && nodeId > 0 ? nodeId : null,
    };
}

function sketchSrc(sketchUrl) {
    if (!sketchUrl) return null;
    if (
        sketchUrl.startsWith('http://') ||
        sketchUrl.startsWith('https://') ||
        sketchUrl.startsWith('/')
    ) {
        return sketchUrl;
    }
    return `/uploads/${sketchUrl}`;
}

function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/**
 * 分总成（焊接件）短号：
 * - 无 -N → 数字末四位（501005123AA → 5123）
 * - 有 -N → 末四位 + 字母尾 + -N（501005123AA-1 → 5123AA-1）
 */
function shortWeldPartNumber(partNumber) {
    if (!partNumber) return null;
    const raw = String(partNumber).trim();
    if (!raw) return null;
    const match = raw.match(/(\d{4,})([A-Za-z]*)(-\d+)\s*$/);
    if (match) {
        const digitsTail = match[1].slice(-4);
        const letters = match[2] || '';
        const dashSuffix = match[3];
        return `${digitsTail}${letters}${dashSuffix}`;
    }
    return shortPartNumber(raw);
}

/**
 * 零件号展示：
 * - 交付客户（供货总成）→ 数字末四位
 * - 分总成 / 焊接件 → 无 -N 取末四位；有 -N 取 5123AA-1 形式
 * - 冲压件 → 数字末四位
 * - 其余 → 完整零件号
 */
function resolvePartNumberLabel(node, category) {
    const full = node?.part_number || '—';
    const isCustomerDelivery =
        Boolean(node?.is_supply_unit) || node?.node_role === 'supply';
    if (category?.key === 'sub_assembly') {
        return shortWeldPartNumber(full) || full;
    }
    if (isCustomerDelivery || category?.key === 'stamping') {
        return shortPartNumber(full) || full;
    }
    return full;
}

/**
 * 培训用缩写 display_name（API 无独立字段时由 part_name 推导）
 * 节点上默认只显示缩写，完整名称仅 hover / detail
 */
function resolveDisplayName(node, depth = 0) {
    const raw = String(node?.part_name || '').trim();
    if (!raw) {
        return shortPartNumber(node?.part_number) || node?.part_number || '—';
    }

    let name = raw;
    if (depth > 0) {
        name = name.replace(/分总成$/, '').replace(/总成$/, '');
    }
    name = name.trim() || raw;

    const maxLen = depth === 0 ? 8 : depth === 1 ? 7 : 6;
    if (name.length > maxLen) {
        return `${name.slice(0, maxLen)}…`;
    }
    return name;
}

/** 突出显示用量：×1 / ×2 / ×1550mm */
function formatQtyLabel(node) {
    const text = String(node?.qty_text || '').trim();
    if (text && /mm|kg|g|m\b/i.test(text)) {
        return text.startsWith('×') ? text : `×${text}`;
    }
    if (node?.qty != null && node.qty !== '') {
        const n = Number(node.qty);
        if (Number.isFinite(n)) {
            const shown = Number.isInteger(n) ? String(n) : String(n);
            return `×${shown}`;
        }
    }
    if (text) {
        return text.startsWith('×') ? text : `×${text}`;
    }
    return '×1';
}

/** Excel 单元格溯源：文件 + 表页 + 行 + 零件号列 */
function renderExcelProvenance(node) {
    const filename = node?.excel_filename || '';
    const sheet = node?.excel_sheet_name || '';
    const row = node?.excel_row;
    const col = node?.excel_part_col;
    if (!filename && !sheet && row == null && col == null) {
        return `
            <div class="border border-[#262626] bg-[#111111] p-3">
                <p class="text-[10px] uppercase tracking-[0.14em] text-[#d32f2f] mb-1.5">Excel 溯源</p>
                <p class="text-[12px] text-[#616161]">无单元格溯源（请重新上传材料清单生成）</p>
            </div>
        `;
    }
    const colHint = col != null ? `第 ${col} 列（零件号）` : '—';
    const rowHint = row != null ? `第 ${row} 行` : '—';
    const locator = [
        sheet ? `表「${sheet}」` : null,
        row != null ? rowHint : null,
        col != null ? colHint : null,
    ]
        .filter(Boolean)
        .join(' · ');
    return `
        <div class="border border-[#d32f2f]/25 bg-[#111111] p-3"
             style="box-shadow: 0 0 20px rgba(211,47,47,0.06), inset 0 1px 0 rgba(211,47,47,0.05);">
            <p class="text-[10px] uppercase tracking-[0.14em] text-[#d32f2f] mb-2 flex items-center gap-2">
                <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                Excel 溯源
            </p>
            <p class="text-[12px] text-[#cfcfcf] font-mono break-all mb-1">${esc(filename || '—')}</p>
            <p class="text-[11px] text-[#888888]">${esc(locator || '—')}</p>
        </div>
    `;
}

function findNodeById(nodes, id) {
    const list = Array.isArray(nodes) ? nodes : [];
    for (const node of list) {
        if (node.id === id) return node;
        const found = findNodeById(node.children || [], id);
        if (found) return found;
    }
    return null;
}

function indexTree(node, map = bomVizState.nodeMap) {
    if (!node) return;
    map.set(node.id, node);
    (node.children || []).forEach((child) => indexTree(child, map));
}

function childCount(node) {
    return Array.isArray(node?.children) ? node.children.length : 0;
}

function nodeSize(depth) {
    if (depth <= 0) return LAYOUT.node[0];
    if (depth === 1) return LAYOUT.node[1];
    if (depth === 2) return LAYOUT.node[2];
    return LAYOUT.node.deep;
}

function isExpanded(nodeId) {
    return bomVizState.expandedIds.has(nodeId);
}

/**
 * 自底向上测量子树宽度 → 自上而下摆放
 * 保证同层不重叠；连接线走节点底部到子节点顶部
 * 最终将整棵树平移到画布中心（相对视口至少铺满舞台）
 */
function layoutTree(root, viewportW = 800, viewportH = 600) {
    const placements = [];
    const edges = [];

    function measure(node, depth) {
        const size = nodeSize(depth);
        const kids = node.children || [];
        const open = isExpanded(node.id) && kids.length > 0;

        if (!open) {
            return { width: size.w, node, depth, size, children: [] };
        }

        const measuredKids = kids.map((c) => measure(c, depth + 1));
        const kidsWidth =
            measuredKids.reduce((sum, m) => sum + m.width, 0) +
            LAYOUT.siblingGapX * Math.max(0, measuredKids.length - 1);
        return {
            width: Math.max(size.w, kidsWidth),
            node,
            depth,
            size,
            children: measuredKids,
        };
    }

    function place(measured, leftX, topY) {
        const { node, depth, size, children: measuredKids, width } = measured;
        const x = leftX + width / 2;
        const y = topY + size.h / 2;
        const category = classifyPart(node, depth === 0);
        const kids = node.children || [];

        placements.push({
            node,
            depth,
            x,
            y,
            w: size.w,
            h: size.h,
            imgSize: size.img,
            category,
            displayName: resolveDisplayName(node, depth),
            partNoLabel: resolvePartNumberLabel(node, category),
            qtyLabel: formatQtyLabel(node),
            childCount: kids.length,
            isExpanded: isExpanded(node.id),
            showImage: depth <= 1 && size.img > 0 && !!node.sketch_url,
        });

        if (!measuredKids.length) return;

        const kidsWidth =
            measuredKids.reduce((sum, m) => sum + m.width, 0) +
            LAYOUT.siblingGapX * Math.max(0, measuredKids.length - 1);
        let cursor = leftX + (width - kidsWidth) / 2;
        const childTop = topY + size.h + LAYOUT.levelGapY;

        measuredKids.forEach((m) => {
            const childCenterX = cursor + m.width / 2;
            edges.push({
                parentId: node.id,
                childId: m.node.id,
                x1: x,
                y1: y + size.h / 2,
                x2: childCenterX,
                y2: childTop,
            });
            place(m, cursor, childTop);
            cursor += m.width + LAYOUT.siblingGapX;
        });
    }

    const measured = measure(root, 0);
    // 先按原点排布，再整体平移居中
    place(measured, LAYOUT.padX, LAYOUT.padY);

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    placements.forEach((p) => {
        minX = Math.min(minX, p.x - p.w / 2);
        minY = Math.min(minY, p.y - p.h / 2);
        maxX = Math.max(maxX, p.x + p.w / 2);
        maxY = Math.max(maxY, p.y + p.h / 2 + 8);
    });
    if (!Number.isFinite(minX)) {
        minX = 0;
        minY = 0;
        maxX = 0;
        maxY = 0;
    }

    const contentW = maxX - minX + LAYOUT.padX * 2;
    const contentH = maxY - minY + LAYOUT.padY * 2;
    const canvasW = Math.max(contentW, viewportW);
    const canvasH = Math.max(contentH, viewportH);
    const offsetX = (canvasW - (maxX - minX)) / 2 - minX;
    const offsetY = (canvasH - (maxY - minY)) / 2 - minY;

    placements.forEach((p) => {
        p.x += offsetX;
        p.y += offsetY;
    });
    edges.forEach((e) => {
        e.x1 += offsetX;
        e.y1 += offsetY;
        e.x2 += offsetX;
        e.y2 += offsetY;
    });

    return {
        placements,
        edges,
        canvasW,
        canvasH,
    };
}

function orthogonalPath(x1, y1, x2, y2) {
    const midY = (y1 + y2) / 2;
    return `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`;
}

const BomVizPage = {
    init() {
        if (!can('op:bom-structure:view')) {
            this.renderFatal('无权查看', '需要权限 op:bom-structure:view');
            return;
        }

        const { snapshotId, nodeId } = readHashParams();
        bomVizState.snapshotId = snapshotId;
        bomVizState.nodeId = nodeId;
        bomVizState.hoverId = null;
        bomVizState.selectedId = null;
        bomVizState.expandedIds = new Set();
        bomVizState.canUpdatePeriod = can('op:bom-structure:update');
        const asOfHost = document.getElementById('bomVizAsOfFilters');
        if (asOfHost && !document.getElementById('bomVizYear')) {
            asOfHost.innerHTML = asOfFilterHtml('bomViz', { includeExpired: true });
            fillAsOfSelects('bomViz', bomVizState.asOf.year, bomVizState.asOf.month);
            document.getElementById('bomVizYear')?.addEventListener('change', () => this.reloadAsOf());
            document.getElementById('bomVizMonth')?.addEventListener('change', () => this.reloadAsOf());
            document.getElementById('bomVizIncludeExpired')?.addEventListener('change', () => this.reloadAsOf());
        }

        document.getElementById('bomVizBackAssemblies')?.addEventListener('click', () => {
            window.location.hash = snapshotId
                ? `/bom-structure?snapshot_id=${encodeURIComponent(snapshotId)}`
                : '/bom-structure';
        });

        document.getElementById('bomVizKnowledgeClose')?.addEventListener('click', () => {
            this.closeKnowledge();
        });
        document.getElementById('bomVizKnowledgeBackdrop')?.addEventListener('click', () => {
            this.closeKnowledge();
        });

        const shell = document.getElementById('bomVizStageShell');
        shell?.addEventListener('mousemove', (e) => this.onStageMouseMove(e));
        shell?.addEventListener('mouseleave', () => this.clearHover());

        if (!snapshotId || !nodeId) {
            this.renderFatal('无法打开结构视图', '缺少 snapshot_id 或 node_id');
            return;
        }

        this.load(snapshotId, nodeId);
    },

    async load(snapshotId, nodeId) {
        if (bomVizState.isLoading) return;
        bomVizState.isLoading = true;
        this.showStageMessage('加载中…', '正在生成产品结构图');

        try {
            const [snapResp, treeResp] = await Promise.all([
                HttpClient.get(`/api/bom/snapshots/${snapshotId}`),
                HttpClient.get(`/api/bom/snapshots/${snapshotId}/tree`, {
                    params: this.treeQueryParams(),
                }),
            ]);
            const snapshot = snapResp.data || null;
            const tree = Array.isArray(treeResp.data) ? treeResp.data : [];
            const assembly = findNodeById(tree, nodeId);
            if (!assembly) {
                this.renderFatal('未找到总成', `node_id=${nodeId}`);
                return;
            }

            bomVizState.snapshot = snapshot;
            bomVizState.assembly = assembly;
            bomVizState.nodeMap = new Map();
            indexTree(assembly);

            // 默认展开根节点，露出全部一级子件；更深层级折叠（显示 +N）
            bomVizState.expandedIds = new Set([assembly.id]);

            this.renderHeader();
            this.renderTree();
            this.hideStageMessage();
        } catch (error) {
            console.error('加载 Multi-Level BOM 失败:', error);
            this.renderFatal('加载失败', error.message || '请稍后重试');
        } finally {
            bomVizState.isLoading = false;
        }
    },

    treeQueryParams() {
        const asOf = readAsOf('bomViz') || {
            year: bomVizState.asOf.year,
            month: bomVizState.asOf.month,
            include_expired: bomVizState.includeExpired,
        };
        bomVizState.asOf = { year: asOf.year, month: asOf.month };
        bomVizState.includeExpired = asOf.include_expired;
        return {
            year: asOf.year,
            month: asOf.month,
            include_expired: asOf.include_expired,
        };
    },

    reloadAsOf() {
        if (!bomVizState.snapshotId || !bomVizState.nodeId) return;
        this.load(bomVizState.snapshotId, bomVizState.nodeId);
    },

    renderHeader() {
        const snapshot = bomVizState.snapshot;
        const assembly = bomVizState.assembly;
        const pathEl = document.getElementById('bomVizPath');
        const nameEl = document.getElementById('bomVizAssemblyName');
        const legendEl = document.getElementById('bomVizCategoryLegend');

        if (pathEl) {
            pathEl.textContent = snapshot
                ? [snapshot.location, snapshot.customer_name, snapshot.vehicle_model, snapshot.bom_version]
                      .filter(Boolean)
                      .join(' / ')
                : '—';
        }
        if (nameEl) {
            nameEl.textContent = assembly?.part_name || assembly?.part_number || '—';
        }

        if (legendEl) {
            const present = new Set();
            const walk = (n, d = 0) => {
                present.add(classifyPart(n, d === 0).key);
                (n.children || []).forEach((c) => walk(c, d + 1));
            };
            if (assembly) walk(assembly);
            legendEl.innerHTML = LEGEND_ORDER.filter((k) => present.has(k))
                .map((key) => {
                    const cat = PART_CATEGORY[key];
                    return `
                        <span class="inline-flex items-center gap-1.5 whitespace-nowrap">
                            <span class="inline-block w-1.5 h-1.5 rounded-full"
                                  style="background:${cat.color};box-shadow:0 0 0 1px ${hexToRgba(cat.color, 0.35)}"></span>
                            ${esc(cat.label)}
                        </span>
                    `;
                })
                .join('');
        }
    },

    showStageMessage(title, desc) {
        const box = document.getElementById('bomVizStageEmpty');
        const t = document.getElementById('bomVizStageEmptyTitle');
        const d = document.getElementById('bomVizStageEmptyDesc');
        if (t) t.textContent = title;
        if (d) d.textContent = desc || '';
        box?.classList.remove('hidden');
    },

    hideStageMessage() {
        document.getElementById('bomVizStageEmpty')?.classList.add('hidden');
    },

    renderFatal(title, desc) {
        const root = document.getElementById('bomVizRoot');
        if (!root) return;
        root.innerHTML = `
            <div class="flex flex-col items-center justify-center py-24 border border-[#2c2c2c] bg-[#121212]">
                <p class="text-xs text-[#9e9e9e] mb-1">${esc(title)}</p>
                <p class="text-[11px] text-[#616161] mb-5">${esc(desc || '')}</p>
                <button type="button" id="bomVizFatalBack"
                        class="text-[11px] text-[#9e9e9e] hover:text-white transition-colors">
                    ← 返回总成列表
                </button>
            </div>
        `;
        document.getElementById('bomVizFatalBack')?.addEventListener('click', () => {
            const sid = bomVizState.snapshotId;
            window.location.hash = sid
                ? `/bom-structure?snapshot_id=${encodeURIComponent(sid)}`
                : '/bom-structure';
        });
    },

    renderTree() {
        const stage = document.getElementById('bomVizStage');
        const shell = document.getElementById('bomVizStageShell');
        const assembly = bomVizState.assembly;
        if (!stage || !assembly) return;

        const viewportW = shell?.clientWidth || 800;
        const viewportH = shell?.clientHeight || 600;
        const { placements, edges, canvasW, canvasH } = layoutTree(
            assembly,
            viewportW,
            viewportH
        );
        bomVizState.placements = placements;

        const edgeSvg = edges
            .map((e) => {
                const child = placements.find((p) => p.node.id === e.childId);
                const color = child?.category?.color || PART_CATEGORY.other.color;
                return `<path d="${orthogonalPath(e.x1, e.y1, e.x2, e.y2)}"
                            fill="none"
                            stroke="${hexToRgba(color, 0.35)}"
                            stroke-width="1.25"
                            class="bom-edge"
                            data-parent-id="${e.parentId}"
                            data-child-id="${e.childId}" />`;
            })
            .join('');

        const nodesHtml = placements
            .map((p) => {
                const color = p.category.color;
                const src = sketchSrc(p.node.sketch_url);
                const left = p.x - p.w / 2;
                const top = p.y - p.h / 2;
                const hasKids = p.childCount > 0;
                const isShortPartNo =
                    p.partNoLabel !== (p.node.part_number || '—');
                const shortSize = isShortPartNo
                    ? p.depth === 0
                        ? 'text-2xl'
                        : p.depth === 1
                          ? 'text-xl'
                          : 'text-lg'
                    : p.depth === 0
                      ? 'text-sm'
                      : 'text-xs';
                const qtySize = p.depth === 0 ? 'text-lg' : 'text-base';
                const badge =
                    hasKids && !p.isExpanded
                        ? `<span class="absolute -bottom-2 left-1/2 -translate-x-1/2 inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono font-semibold tabular-nums bg-[#1a1a1a] border text-[#cfcfcf]"
                                 style="border-color:${hexToRgba(color, 0.55)}">+${p.childCount}</span>`
                        : hasKids && p.isExpanded
                          ? `<span class="absolute -bottom-2 left-1/2 -translate-x-1/2 inline-flex items-center px-1.5 py-0.5 text-[9px] font-mono text-[#616161] bg-[#121212] border border-[#2c2c2c]">−</span>`
                          : '';

                const imgBlock =
                    p.showImage && src
                        ? `<div class="flex items-center justify-center mb-1" style="height:${p.imgSize}px">
                               <img src="${esc(src)}" alt="" class="max-h-full max-w-full object-contain" draggable="false" loading="lazy">
                           </div>`
                        : p.depth <= 1 && !src
                          ? `<div class="flex items-center justify-center mb-1 text-[9px] text-[#3a3a3a]" style="height:${Math.max(p.imgSize, 28)}px">暂无图</div>`
                          : '';

                return `
                  <div class="bom-node absolute flex flex-col items-center justify-center px-2 py-2 border cursor-pointer transition-colors"
                       data-node-id="${p.node.id}"
                       data-depth="${p.depth}"
                       data-has-children="${hasKids ? '1' : '0'}"
                       style="left:${left}px;top:${top}px;width:${p.w}px;height:${p.h}px;
                              background:${hexToRgba(color, p.depth === 0 ? 0.22 : 0.12)};
                              border-color:${hexToRgba(color, 0.55)};
                              box-shadow:inset 0 1px 0 rgba(255,255,255,0.03)">
                    ${imgBlock}
                    <p class="${shortSize} font-mono font-semibold tabular-nums tracking-[0.06em] text-[#ffffff] leading-tight text-center break-all px-0.5
                               drop-shadow-[0_0_12px_rgba(255,255,255,0.06)]">${esc(p.partNoLabel)}</p>
                    <p class="${qtySize} font-mono font-semibold tabular-nums tracking-wide mt-1.5 leading-none"
                       style="color:${lightenHex(color, 0.45)}">${esc(p.qtyLabel)}</p>
                    <p class="text-[10px] text-[#555555] mt-1.5 leading-tight text-center truncate w-full">${esc(p.displayName)}</p>
                    ${badge}
                  </div>
                `;
            })
            .join('');

        stage.style.width = `${canvasW}px`;
        stage.style.height = `${canvasH}px`;
        stage.innerHTML = `
            <svg class="absolute inset-0 pointer-events-none" width="${canvasW}" height="${canvasH}"
                 aria-hidden="true">
              <g class="bom-edges">${edgeSvg}</g>
            </svg>
            <div class="absolute inset-0">${nodesHtml}</div>
        `;

        // 溢出时滚到内容几何中心，保证图落在视口正中
        if (shell) {
            requestAnimationFrame(() => {
                shell.scrollLeft = Math.max(0, (canvasW - shell.clientWidth) / 2);
                shell.scrollTop = Math.max(0, (canvasH - shell.clientHeight) / 2);
            });
        }

        stage.querySelectorAll('.bom-node').forEach((el) => {
            const nodeId = Number.parseInt(el.getAttribute('data-node-id') || '', 10);
            el.addEventListener('mouseenter', () => this.setHover(nodeId));
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                this.onNodeClick(nodeId);
            });
        });

        this.applyHighlightState();
    },

    onNodeClick(nodeId) {
        const node = bomVizState.nodeMap.get(nodeId);
        if (!node) return;

        if (childCount(node) > 0) {
            if (bomVizState.expandedIds.has(nodeId)) {
                this.collapseSubtree(nodeId);
            } else {
                bomVizState.expandedIds.add(nodeId);
            }
            this.renderTree();
            this.renderHeader();
            return;
        }

        this.openKnowledge(nodeId);
    },

    collapseSubtree(nodeId) {
        const node = bomVizState.nodeMap.get(nodeId);
        if (!node) return;
        const remove = (n) => {
            bomVizState.expandedIds.delete(n.id);
            (n.children || []).forEach(remove);
        };
        remove(node);
    },

    setHover(nodeId) {
        bomVizState.hoverId = nodeId;
        this.applyHighlightState();
        this.showPreview(nodeId);
    },

    clearHover() {
        bomVizState.hoverId = null;
        this.applyHighlightState();
        this.hidePreview();
    },

    applyHighlightState() {
        const hoverId = bomVizState.hoverId;
        const selectedId = bomVizState.selectedId;
        const activeId = hoverId ?? selectedId;

        const related = new Set();
        if (activeId != null) {
            related.add(activeId);
            let cur = bomVizState.nodeMap.get(activeId);
            while (cur?.parent_id != null) {
                related.add(cur.parent_id);
                cur = bomVizState.nodeMap.get(cur.parent_id);
            }
            // 可见子孙：若展开则包含直接子
            const focus = bomVizState.nodeMap.get(activeId);
            (focus?.children || []).forEach((c) => related.add(c.id));
        }

        document.querySelectorAll('#bomVizStage .bom-node').forEach((el) => {
            const id = Number.parseInt(el.getAttribute('data-node-id') || '', 10);
            if (activeId == null) {
                el.style.opacity = '1';
                el.style.filter = 'none';
                return;
            }
            if (related.has(id)) {
                el.style.opacity = '1';
                el.style.filter =
                    id === activeId
                        ? 'drop-shadow(0 0 10px rgba(255,255,255,0.12))'
                        : 'none';
            } else {
                el.style.opacity = '0.28';
                el.style.filter = 'none';
            }
        });

        document.querySelectorAll('#bomVizStage .bom-edge').forEach((path) => {
            const parentId = Number.parseInt(path.getAttribute('data-parent-id') || '', 10);
            const childId = Number.parseInt(path.getAttribute('data-child-id') || '', 10);
            if (activeId == null) {
                path.style.opacity = '1';
                return;
            }
            path.style.opacity =
                related.has(parentId) && related.has(childId) ? '1' : '0.12';
        });
    },

    findPlacement(nodeId) {
        return bomVizState.placements.find((p) => p.node.id === nodeId) || null;
    },

    showPreview(nodeId) {
        const panel = document.getElementById('bomVizPreview');
        const placement = this.findPlacement(nodeId);
        if (!panel || !placement) return;

        const node = placement.node;
        const category = placement.category;
        const src = sketchSrc(node.sketch_url);
        const fullName = node.part_name || '—';

        const imgBox = document.getElementById('bomVizPreviewImage');
        if (imgBox) {
            imgBox.innerHTML = src
                ? `<img src="${esc(src)}" alt="${esc(fullName)}" class="w-full h-full object-fill" draggable="false">`
                : `<div class="w-full h-full flex items-center justify-center"><span class="text-[10px] text-[#3a3a3a]">暂无图</span></div>`;
        }

        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text || '';
        };

        setText('bomVizPreviewQty', placement.qtyLabel);
        setText('bomVizPreviewDisplay', placement.partNoLabel || placement.displayName);
        setText('bomVizPreviewName', fullName);
        setText('bomVizPreviewNo', node.part_number || '');

        const parent = node.parent_id != null ? bomVizState.nodeMap.get(node.parent_id) : null;
        setText(
            'bomVizPreviewParent',
            parent
                ? `所属：${resolveDisplayName(parent, Math.max(0, placement.depth - 1))} · ${parent.part_number || ''}`
                : placement.depth === 0
                  ? '本页供货总成'
                  : ''
        );

        const directChildCount = placement.childCount;
        const knowledge = categoryKnowledge(node, placement.depth === 0, category);
        if (directChildCount > 0) {
            const expandHint = placement.isExpanded ? '点击折叠' : '点击展开';
            setText(
                'bomVizPreviewHint',
                `直接子件 ${directChildCount} 个 · ${knowledge} · ${expandHint}`
            );
        } else {
            setText('bomVizPreviewHint', knowledge);
        }

        const catEl = document.getElementById('bomVizPreviewCategory');
        if (catEl) {
            catEl.innerHTML = `
                <span class="inline-block w-1.5 h-1.5 rounded-full" style="background:${category.color}"></span>
                ${esc(category.label)}
            `;
        }

        panel.classList.remove('opacity-0', 'scale-[0.98]');
        panel.classList.add('opacity-100', 'scale-100');
        panel.setAttribute('aria-hidden', 'false');
    },

    hidePreview() {
        const panel = document.getElementById('bomVizPreview');
        if (!panel) return;
        panel.classList.add('opacity-0', 'scale-[0.98]');
        panel.classList.remove('opacity-100', 'scale-100');
        panel.setAttribute('aria-hidden', 'true');
    },

    onStageMouseMove(event) {
        const nodeEl = event.target.closest?.('.bom-node');
        if (nodeEl) {
            const nodeId = Number.parseInt(nodeEl.getAttribute('data-node-id') || '', 10);
            if (Number.isFinite(nodeId) && nodeId !== bomVizState.hoverId) {
                this.setHover(nodeId);
            }
        } else if (bomVizState.hoverId != null) {
            this.clearHover();
        }

        const panel = document.getElementById('bomVizPreview');
        if (!panel || bomVizState.hoverId == null) return;

        // fixed：相对视口贴鼠标，不受画布居中 / scroll 影响
        const gap = 14;
        const panelW = panel.offsetWidth || 300;
        const panelH = panel.offsetHeight || 320;
        const viewW = window.innerWidth;
        const viewH = window.innerHeight;

        let left = event.clientX + gap;
        let top = event.clientY + gap;

        if (left + panelW > viewW - 12) {
            left = event.clientX - panelW - gap;
        }
        if (top + panelH > viewH - 12) {
            top = event.clientY - panelH - gap;
        }
        if (left < 12) left = 12;
        if (top < 12) top = 12;

        panel.style.left = `${Math.round(left)}px`;
        panel.style.top = `${Math.round(top)}px`;
    },

    openKnowledge(nodeId) {
        const placement = this.findPlacement(nodeId);
        const node = bomVizState.nodeMap.get(nodeId);
        if (!node) return;

        bomVizState.selectedId = nodeId;
        this.applyHighlightState();

        const category = placement?.category || classifyPart(node, false);
        const src = sketchSrc(node.sketch_url);
        const displayName = resolveDisplayName(node, placement?.depth ?? node.level ?? 1);
        const fullName = node.part_name || '—';
        const qtyLabel = formatQtyLabel(node);
        const parent = node.parent_id != null ? bomVizState.nodeMap.get(node.parent_id) : null;
        const roleText = categoryKnowledge(node, !node.parent_id, category);

        const body = document.getElementById('bomVizKnowledgeBody');
        if (body) {
            body.innerHTML = `
                <div>
                    <p class="inline-flex items-center gap-1.5 text-[10px] tracking-wide mb-2"
                       style="color:${category.color}">
                        <span class="inline-block w-1.5 h-1.5 rounded-full" style="background:${category.color}"></span>
                        ${esc(category.label)}
                    </p>
                    <h3 class="text-xl font-mono font-semibold tabular-nums tracking-[0.06em] text-[#ffffff] leading-snug mb-2 break-all">${esc(
                        resolvePartNumberLabel(node, category)
                    )}</h3>
                    <p class="text-xl font-mono font-semibold tabular-nums tracking-wide mb-2"
                       style="color:${lightenHex(category.color, 0.35)}">${esc(qtyLabel)}</p>
                    <p class="text-[12px] text-[#777777] mb-1">${esc(displayName)}</p>
                    <p class="text-[13px] text-[#9e9e9e] mb-2">${esc(fullName)}</p>
                    ${
                        node.part_number
                            ? `<p class="text-[11px] font-mono text-[#555555]">${esc(node.part_number)}</p>`
                            : ''
                    }
                    <p class="text-[11px] text-[#888888] mt-2">
                        ${esc(node.location || '')} · ${esc(node.vehicle_model || '')} · ${esc(node.bom_version || '')}
                    </p>
                    <p class="text-[11px] text-[#9e9e9e] mt-1">
                        ${esc(fmtPeriodRange(node.effective_year, node.effective_month, node.expiry_year, node.expiry_month))}
                    </p>
                </div>

                ${
                    src
                        ? `
                    <button type="button" id="bomVizKnowledgeSketch"
                            class="w-full h-56 bg-[#0a0a0a] border overflow-hidden hover:border-[#3a3a3a] transition-colors p-0"
                            style="border-color:${hexToRgba(category.color, 0.45)}">
                        <img src="${esc(src)}" alt="${esc(fullName)}" class="w-full h-full object-fill" loading="lazy" draggable="false">
                    </button>
                    <p class="text-[10px] text-[#484848] -mt-3">点击在新窗口打开图纸</p>
                `
                        : `
                    <div class="h-56 bg-[#0a0a0a] border border-[#222222] flex items-center justify-center">
                        <span class="text-[10px] text-[#3a3a3a]">暂无图</span>
                    </div>
                `
                }

                <div class="space-y-4">
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">完整名称</p>
                        <p class="text-[13px] text-[#cfcfcf] leading-relaxed">${esc(fullName)}</p>
                    </div>
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">结构位置</p>
                        <p class="text-[13px] text-[#cfcfcf]">第 ${esc(String(node.level ?? placement?.depth ?? '—'))} 层</p>
                        ${
                            parent
                                ? `<p class="text-[12px] text-[#888888] mt-1">所属：${esc(
                                      resolveDisplayName(parent, Math.max(0, (placement?.depth ?? 1) - 1))
                                  )} · ${esc(parent.part_number || '')}</p>`
                                : '<p class="text-[12px] text-[#888888] mt-1">本页供货总成</p>'
                        }
                        ${
                            childCount(node) > 0
                                ? `<p class="text-[12px] text-[#888888] mt-0.5">子件：${childCount(node)} 件</p>`
                                : ''
                        }
                    </div>
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">制造类别</p>
                        <p class="text-[13px] leading-relaxed" style="color:${lightenHex(category.color, 0.35)}">${esc(roleText)}</p>
                    </div>
                    ${
                        node.material
                            ? `
                        <div>
                            <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">材料</p>
                            <p class="text-[13px] font-mono text-[#cfcfcf]">${esc(node.material)}${
                                  node.thickness_mm != null
                                      ? ` · ${esc(String(node.thickness_mm))} mm`
                                      : ''
                              }</p>
                        </div>
                    `
                            : ''
                    }
                    ${
                        node.weld_info
                            ? `
                        <div>
                            <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">连接 / 焊接</p>
                            <p class="text-[13px] text-[#9e9e9e] leading-relaxed">${esc(node.weld_info)}</p>
                        </div>
                    `
                            : ''
                    }
                    ${
                        !node.parent_id && bomVizState.canUpdatePeriod
                            ? `
                        <div>
                            <p class="text-[10px] uppercase tracking-[0.14em] text-[#616161] mb-1.5">生失效</p>
                            ${periodEditorHtml('bomVizL0')}
                            <button type="button" id="bomVizSavePeriod"
                                    class="mt-2 inline-flex items-center h-7 px-3 text-[10px] text-[#c8c8c8] border border-[#8a2020] hover:text-white">
                                保存生失效
                            </button>
                        </div>
                    `
                            : ''
                    }
                    ${renderExcelProvenance(node)}
                </div>
            `;

            if (!node.parent_id && bomVizState.canUpdatePeriod) {
                fillYearMonthSelects(
                    'bomVizL0',
                    node.effective_year,
                    node.effective_month,
                    node.expiry_year,
                    node.expiry_month,
                );
                document.getElementById('bomVizSavePeriod')?.addEventListener('click', () => {
                    this.saveRootPeriod(node.id);
                });
            }

            document.getElementById('bomVizKnowledgeSketch')?.addEventListener('click', () => {
                if (!src) return;
                window.open(src, '_blank', 'noopener,noreferrer');
            });
        }

        const panel = document.getElementById('bomVizKnowledge');
        const backdrop = document.getElementById('bomVizKnowledgeBackdrop');
        panel?.classList.remove('translate-x-full');
        panel?.setAttribute('aria-hidden', 'false');
        if (backdrop) {
            backdrop.classList.remove('pointer-events-none', 'opacity-0');
            backdrop.classList.add('opacity-100');
        }
    },

    closeKnowledge() {
        bomVizState.selectedId = null;
        this.applyHighlightState();
        const panel = document.getElementById('bomVizKnowledge');
        const backdrop = document.getElementById('bomVizKnowledgeBackdrop');
        panel?.classList.add('translate-x-full');
        panel?.setAttribute('aria-hidden', 'true');
        if (backdrop) {
            backdrop.classList.add('pointer-events-none', 'opacity-0');
            backdrop.classList.remove('opacity-100');
        }
    },

    async saveRootPeriod(nodeId) {
        const period = readPeriod('bomVizL0');
        if (!period) return;
        try {
            await HttpClient.patch(`/api/bom/nodes/${nodeId}`, period);
            showToast('已保存生失效', 'success');
            this.reloadAsOf();
        } catch (error) {
            showToast(error.message || '保存失败', 'error');
        }
    },
};

export const pageConfig = {
    render: bomVizTemplate,
    init: () => BomVizPage.init(),
};
