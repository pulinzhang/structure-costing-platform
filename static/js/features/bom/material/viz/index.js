/**
 * Multi-Level BOM — 产品结构可视化
 *
 * 业务域：汽车冲焊件供应商。制造类别不含电子/电气件。
 * 自上而下层级树：父子关系 + 用量 + 制造类别。
 */

import { can } from '../../../../core/permissions.js?v=10';
import { HUD_LED } from '../../../../ui/classes.js?v=15';
import { bindMoreMenu } from '../../../../ui/more-menu.js?v=7';
import { bomVizTemplate } from './template.js?v=11';
import { fmtPeriodRange, hasClosedPeriod } from '../../../common/period-ui.js?v=5';

/** 布局常量（保证同层不重叠、标签不挤） */
const LAYOUT = {
    padX: 48,
    padY: 40,
    levelGapY: 56,
    siblingGapX: 28,
    node: {
        0: { w: 168, h: 196, img: 88 },
        1: { w: 148, h: 172, img: 72 },
        2: { w: 128, h: 100, img: 0 },
        deep: { w: 120, h: 100, img: 0 },
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
        token: '--viz-assembly',
        knowledge: '供货总成 —— 交付客户的冲焊装配单元',
    },
    sub_assembly: {
        key: 'sub_assembly',
        label: '分总成',
        token: '--viz-sub-assembly',
        knowledge: '分总成（焊接件）—— 有下级子件的焊接结构',
    },
    stamping: {
        key: 'stamping',
        label: '冲压件',
        token: '--viz-stamping',
        knowledge: '自制冲压成形零件（含安装支架、加强板等）',
    },
    standard: {
        key: 'standard',
        label: '标准件',
        token: '--viz-standard',
        knowledge: '标准件 —— 螺栓、螺母等',
    },
    plastic: {
        key: 'plastic',
        label: '塑料件',
        token: '--viz-plastic',
        knowledge: '外购塑料件',
    },
    rubber: {
        key: 'rubber',
        label: '橡胶件',
        token: '--viz-rubber',
        knowledge: '橡胶 / 密封件',
    },
    consumable: {
        key: 'consumable',
        label: '辅料',
        token: '--viz-consumable',
        knowledge: '胶、焊丝等冲焊辅料',
    },
    other: {
        key: 'other',
        label: '其他',
        token: '--viz-other',
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
    isExporting: false,
};

function categoryInk(token, alpha) {
    if (alpha == null) return `rgb(var(${token}))`;
    return `rgb(var(${token}) / ${alpha})`;
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
    return isRoot ? '本页供货总成' : '零件';
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
            <div class="border border-app-elevated bg-app-main p-3">
                <p class="text-[10px] uppercase tracking-[0.14em] text-brand mb-1.5">Excel 溯源</p>
                <p class="text-[12px] text-ink-dim">无单元格溯源（请重新上传材料清单生成）</p>
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
        <div class="border border-brand/25 bg-app-main p-3">
            <p class="text-[10px] uppercase tracking-[0.14em] text-brand mb-2 flex items-center gap-2">
                <span class="${HUD_LED}"></span>
                Excel 溯源
            </p>
            <p class="text-[12px] text-ink font-mono break-all mb-1">${esc(filename || '—')}</p>
            <p class="text-[11px] text-ink-muted">${esc(locator || '—')}</p>
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
function layoutTree(root, viewportW = 800, viewportH = 600, expandAll = false) {
    const placements = [];
    const edges = [];

    function measure(node, depth) {
        const size = nodeSize(depth);
        const kids = node.children || [];
        const open = kids.length > 0 && (expandAll || isExpanded(node.id));

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
            isExpanded: expandAll || isExpanded(node.id),
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

const EXPORT_FONT_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const EXPORT_FONT_SANS = "Inter, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif";

function themeRgba(varName, alpha = 1) {
    const [red, green, blue] = getComputedStyle(document.documentElement)
        .getPropertyValue(varName)
        .trim()
        .split(/\s+/);
    if (alpha >= 1) return `rgb(${red}, ${green}, ${blue})`;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function svgText(x, y, fill, font, size, content, weight, spacing) {
    const weightAttr = weight ? ` font-weight="${weight}"` : '';
    const spacingAttr = spacing ? ` letter-spacing="${spacing}"` : '';
    return `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="central" fill="${fill}" font-family="${font}" font-size="${size}"${weightAttr}${spacingAttr}>${content}</text>`;
}

function monoLines(text, fontSize, maxWidth) {
    const source = String(text || '—');
    const maxChars = Math.max(4, Math.floor(maxWidth / (fontSize * 0.62)));
    const lines = [];
    for (let index = 0; index < source.length && lines.length < 3; index += maxChars) {
        lines.push(source.slice(index, index + maxChars));
    }
    if (source.length > maxChars * 3 && lines[2]) {
        lines[2] = `${lines[2].slice(0, Math.max(1, lines[2].length - 1))}…`;
    }
    return lines.length ? lines : ['—'];
}

function exportFilename(extension) {
    const assembly = bomVizState.assembly;
    const base = String(assembly?.part_number || assembly?.part_name || '结构图').trim() || '结构图';
    const safe = base.replace(/[\\/:*?"<>|]/g, '_').slice(0, 80);
    return `${safe}-结构图.${extension}`;
}

let exportMenu = null;

function setExportMenuEnabled(enabled) {
    const button = document.getElementById('bomVizExportMore');
    if (!button) return;
    button.disabled = !enabled;
    button.classList.toggle('opacity-40', !enabled);
    button.classList.toggle('pointer-events-none', !enabled);
}

function snapshotPathLabel() {
    const snapshot = bomVizState.snapshot;
    if (!snapshot) return '';
    return [snapshot.location, snapshot.customer_name, snapshot.vehicle_model, snapshot.bom_version]
        .filter(Boolean)
        .join(' / ');
}

async function sketchDataUrl(url) {
    try {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) return null;
        const blob = await response.blob();
        const blobType = String(blob.type || '');
        if (blobType && !blobType.startsWith('image/')) return null;
        return await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(blob);
        });
    } catch (error) {
        console.warn('结构图简图未能写入 SVG:', url, error);
        return null;
    }
}

async function loadExportImages(placements) {
    const urls = [
        ...new Set(
            placements
                .map((placement) => (placement.showImage ? sketchSrc(placement.node.sketch_url) : null))
                .filter(Boolean)
        ),
    ];
    const entries = await Promise.all(urls.map(async (url) => [url, await sketchDataUrl(url)]));
    return new Map(entries);
}

function exportNodeMarkup(placement, imageHref) {
    const token = placement.category.token;
    const left = placement.x - placement.w / 2;
    const top = placement.y - placement.h / 2;
    const isShortPartNo = placement.partNoLabel !== (placement.node.part_number || '—');
    const partSize = isShortPartNo
        ? placement.depth === 0
            ? 24
            : placement.depth === 1
              ? 20
              : 18
        : placement.depth === 0
          ? 14
          : 12;
    const qtySize = placement.depth === 0 ? 18 : 16;
    const nameSize = 10;
    const innerW = Math.max(24, placement.w - 16);
    const partLines = monoLines(placement.partNoLabel, partSize, innerW);
    const lineGap = 2;
    const blockGap = 6;
    const partBlock = partLines.length * partSize + Math.max(0, partLines.length - 1) * lineGap;
    const hasImageSlot = placement.depth <= 1 && placement.imgSize > 0;
    const imageH = hasImageSlot ? placement.imgSize : 0;
    const textBlock = partBlock + blockGap + qtySize + blockGap + nameSize;
    const contentH = (hasImageSlot ? imageH + 4 : 0) + textBlock;
    const topPad = Math.max(8, (placement.h - contentH) / 2);
    const parts = [
        `<g>`,
        `<rect x="${left}" y="${top}" width="${placement.w}" height="${placement.h}" fill="${themeRgba(token, placement.depth === 0 ? 0.22 : 0.12)}" stroke="${themeRgba(token, 0.55)}" stroke-width="1"/>`,
    ];

    let textTop = top + topPad;
    if (hasImageSlot) {
        if (imageHref) {
            parts.push(
                `<image href="${imageHref}" x="${left + 8}" y="${textTop}" width="${innerW}" height="${imageH}" preserveAspectRatio="xMidYMid meet"/>`
            );
        } else {
            parts.push(svgText(placement.x, textTop + imageH / 2, themeRgba('--text-faint'), EXPORT_FONT_SANS, 9, '暂无图'));
        }
        textTop += imageH + 4;
    }

    partLines.forEach((line, index) => {
        const y = textTop + partSize / 2 + index * (partSize + lineGap);
        parts.push(svgText(placement.x, y, themeRgba('--text-main'), EXPORT_FONT_MONO, partSize, esc(line), 600, '0.06em'));
    });
    textTop += partBlock + blockGap;
    parts.push(svgText(placement.x, textTop + qtySize / 2, themeRgba(token, 0.72), EXPORT_FONT_MONO, qtySize, esc(placement.qtyLabel), 600));
    textTop += qtySize + blockGap;
    parts.push(svgText(placement.x, textTop + nameSize / 2, themeRgba('--text-faint'), EXPORT_FONT_SANS, nameSize, esc(placement.displayName)));
    parts.push('</g>');
    return parts.join('');
}

function buildStructureSvg(placements, edges, canvasW, canvasH, images) {
    const legend = LEGEND_ORDER.filter((key) => placements.some((placement) => placement.category.key === key)).map(
        (key) => PART_CATEGORY[key]
    );
    const headerH = 76;
    const title = bomVizState.assembly?.part_name || bomVizState.assembly?.part_number || '产品结构';
    const pathLabel = snapshotPathLabel();
    let legendX = 24;
    const legendMarkup = legend
        .map((category) => {
            const mark = `<circle cx="${legendX + 4}" cy="58" r="3" fill="${themeRgba(category.token)}"/><text x="${legendX + 12}" y="58" dominant-baseline="central" fill="${themeRgba('--text-dim')}" font-family="${EXPORT_FONT_SANS}" font-size="10">${esc(category.label)}</text>`;
            legendX += 14 + [...category.label].length * 11 + 14;
            return mark;
        })
        .join('');
    const svgW = Math.max(canvasW, legendX + 24, 24 + [...title].length * 13, 24 + [...pathLabel].length * 10);
    const svgH = canvasH + headerH;
    const treeOffsetX = (svgW - canvasW) / 2;

    const edgeMarkup = edges
        .map((edge) => {
            const child = placements.find((placement) => placement.node.id === edge.childId);
            const token = child?.category?.token || PART_CATEGORY.other.token;
            return `<path d="${orthogonalPath(edge.x1, edge.y1, edge.x2, edge.y2)}" fill="none" stroke="${themeRgba(token, 0.35)}" stroke-width="1.25"/>`;
        })
        .join('');

    const nodeMarkup = placements
        .map((placement) => {
            const src = placement.showImage ? sketchSrc(placement.node.sketch_url) : null;
            const imageHref = src ? images.get(src) : null;
            return exportNodeMarkup(placement, imageHref);
        })
        .join('');

    return {
        width: svgW,
        height: svgH,
        markup: `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${svgW}" height="${svgH}" viewBox="0 0 ${svgW} ${svgH}">
  <rect width="100%" height="100%" fill="${themeRgba('--bg-deep')}"/>
  <text x="24" y="22" dominant-baseline="central" fill="${themeRgba('--text-main')}" font-family="${EXPORT_FONT_SANS}" font-size="13" font-weight="600">${esc(title)}</text>
  <text x="24" y="40" dominant-baseline="central" fill="${themeRgba('--text-faint')}" font-family="${EXPORT_FONT_SANS}" font-size="10">${esc(pathLabel)}</text>
  ${legendMarkup}
  <g transform="translate(${treeOffsetX}, ${headerH})">
    ${edgeMarkup}
    ${nodeMarkup}
  </g>
</svg>`,
    };
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

async function svgToPngBlob(markup, width, height) {
    const maxEdge = 8192;
    const maxPixels = 16_000_000;
    let scale = Math.min(2, window.devicePixelRatio || 1);
    scale = Math.min(scale, maxEdge / width, maxEdge / height);
    if (width * height * scale * scale > maxPixels) {
        scale = Math.sqrt(maxPixels / (width * height));
    }
    const canvasW = Math.max(1, Math.round(width * scale));
    const canvasH = Math.max(1, Math.round(height * scale));
    const blob = new Blob([markup], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
        const image = new Image();
        await new Promise((resolve, reject) => {
            image.onload = () => resolve();
            image.onerror = () => reject(new Error('无法生成 PNG'));
            image.src = url;
        });
        const canvas = document.createElement('canvas');
        canvas.width = canvasW;
        canvas.height = canvasH;
        const context = canvas.getContext('2d');
        if (!context) throw new Error('无法生成 PNG');
        context.drawImage(image, 0, 0, canvasW, canvasH);
        const png = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
        if (!png) throw new Error('无法生成 PNG');
        return png;
    } finally {
        URL.revokeObjectURL(url);
    }
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

        document.getElementById('bomVizBackAssemblies')?.addEventListener('click', () => {
            window.location.hash = snapshotId
                ? `/bom-structure?snapshot_id=${encodeURIComponent(snapshotId)}`
                : '/bom-structure';
        });
        exportMenu = bindMoreMenu({
            wrapId: 'bomVizExportWrap',
            btnId: 'bomVizExportMore',
            menuId: 'bomVizExportMenu',
        });
        document.getElementById('bomVizExportSvg')?.addEventListener('click', () => {
            this.exportStructure('svg');
        });
        document.getElementById('bomVizExportPng')?.addEventListener('click', () => {
            this.exportStructure('png');
        });
        setExportMenuEnabled(false);

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
            this.renderFatal('无法打开结构图', '链接不完整，请从总成列表重新打开');
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
                    params: { include_expired: true },
                }),
            ]);
            const snapshot = snapResp.data || null;
            const tree = Array.isArray(treeResp.data) ? treeResp.data : [];
            const assembly = findNodeById(tree, nodeId);
            if (!assembly) {
                this.renderFatal('未找到总成', '这张清单里没有这个总成，请回到列表重选');
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

    renderHeader() {
        const assembly = bomVizState.assembly;
        const pathEl = document.getElementById('bomVizPath');
        const nameEl = document.getElementById('bomVizAssemblyName');
        const legendEl = document.getElementById('bomVizCategoryLegend');

        if (pathEl) pathEl.textContent = snapshotPathLabel() || '—';
        if (nameEl) {
            nameEl.textContent = assembly?.part_name || assembly?.part_number || '—';
        }

        setExportMenuEnabled(!bomVizState.isExporting);

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
                                  style="background:${categoryInk(cat.token)}"></span>
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
            <div class="flex flex-col items-center justify-center py-24 border border-line bg-app-main">
                <p class="text-xs text-ink-muted mb-1">${esc(title)}</p>
                <p class="text-[11px] text-ink-dim mb-5">${esc(desc || '')}</p>
                <button type="button" id="bomVizFatalBack"
                        class="text-[11px] text-ink-muted hover:text-ink transition-colors">
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
                const token = child?.category?.token || PART_CATEGORY.other.token;
                return `<path d="${orthogonalPath(e.x1, e.y1, e.x2, e.y2)}"
                            fill="none"
                            stroke="${categoryInk(token)}"
                            stroke-opacity="0.35"
                            stroke-width="1.25"
                            class="bom-edge"
                            data-parent-id="${e.parentId}"
                            data-child-id="${e.childId}" />`;
            })
            .join('');

        const nodesHtml = placements
            .map((p) => {
                const token = p.category.token;
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
                        ? `<span class="absolute -bottom-2 left-1/2 -translate-x-1/2 inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono font-semibold tabular-nums bg-app-surface border text-ink"
                                 style="border-color:${categoryInk(token, 0.55)}">+${p.childCount}</span>`
                        : hasKids && p.isExpanded
                          ? `<span class="absolute -bottom-2 left-1/2 -translate-x-1/2 inline-flex items-center px-1.5 py-0.5 text-[9px] font-mono text-ink-dim bg-app-main border border-line">−</span>`
                          : '';

                const imgBlock =
                    p.showImage && src
                        ? `<div class="flex shrink-0 items-center justify-center mb-1" style="height:${p.imgSize}px">
                               <img src="${esc(src)}" alt="" class="max-h-full max-w-full object-contain" draggable="false" loading="lazy">
                           </div>`
                        : p.depth <= 1 && !src
                          ? `<div class="flex shrink-0 items-center justify-center mb-1 text-[9px] text-ink-faint" style="height:${Math.max(p.imgSize, 28)}px">暂无图</div>`
                          : '';

                return `
                  <div class="bom-node absolute flex flex-col items-center justify-center px-2 py-2 border cursor-pointer transition-colors"
                       data-node-id="${p.node.id}"
                       data-depth="${p.depth}"
                       data-has-children="${hasKids ? '1' : '0'}"
                       style="left:${left}px;top:${top}px;width:${p.w}px;height:${p.h}px;
                              background:${categoryInk(token, p.depth === 0 ? 0.22 : 0.12)};
                              border-color:${categoryInk(token, 0.55)};
">
                    ${imgBlock}
                    <p class="${shortSize} shrink-0 font-mono font-semibold tabular-nums tracking-[0.06em] text-ink leading-tight text-center break-all px-0.5
                               drop-shadow-[0_0_12px_rgb(var(--text-main)/0.06)]">${esc(p.partNoLabel)}</p>
                    <p class="${qtySize} shrink-0 font-mono font-semibold tabular-nums tracking-wide mt-1.5 leading-snug"
                       style="color:${categoryInk(token, 0.72)}">${esc(p.qtyLabel)}</p>
                    <p class="shrink-0 text-[10px] text-ink-faint mt-1.5 leading-normal text-center truncate w-full">${esc(p.displayName)}</p>
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

    async exportStructure(format) {
        const assembly = bomVizState.assembly;
        if (!assembly || bomVizState.isExporting) return;
        exportMenu?.close();
        if (typeof window.refuseWeChatDownload === 'function' && window.refuseWeChatDownload()) return;

        bomVizState.isExporting = true;
        setExportMenuEnabled(false);

        try {
            await new Promise((resolve) => {
                window.setTimeout(resolve, 0);
            });
            const { placements, edges, canvasW, canvasH } = layoutTree(assembly, 0, 0, true);
            const images = await loadExportImages(placements);
            const picture = buildStructureSvg(placements, edges, canvasW, canvasH, images);
            if (format === 'png') {
                const png = await svgToPngBlob(picture.markup, picture.width, picture.height);
                downloadBlob(png, exportFilename('png'));
                showToast(`已导出 PNG，共 ${placements.length} 个节点`, 'success');
            } else {
                const svg = new Blob([picture.markup], { type: 'image/svg+xml;charset=utf-8' });
                downloadBlob(svg, exportFilename('svg'));
                showToast(`已导出 SVG，共 ${placements.length} 个节点`, 'success');
            }
        } catch (error) {
            console.error('导出结构图失败:', error);
            showToast(error?.message || '导出失败', 'error');
        } finally {
            bomVizState.isExporting = false;
            setExportMenuEnabled(Boolean(bomVizState.assembly));
        }
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
                        ? 'drop-shadow(0 0 10px rgb(var(--text-main) / 0.12))'
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
                : `<div class="w-full h-full flex items-center justify-center"><span class="text-[10px] text-ink-faint">暂无图</span></div>`;
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
        const periodEl = document.getElementById('bomVizPreviewPeriod');
        if (periodEl) {
            const isChanged = hasClosedPeriod(
                node.effective_year,
                node.effective_month,
                node.expiry_year,
                node.expiry_month,
            );
            periodEl.textContent = fmtPeriodRange(
                node.effective_year,
                node.effective_month,
                node.expiry_year,
                node.expiry_month,
            );
            periodEl.classList.toggle('text-brand', isChanged);
            periodEl.classList.toggle('text-ink-faint', !isChanged);
            periodEl.title = isChanged ? '已变更' : '';
        }

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
                <span class="inline-block w-1.5 h-1.5 rounded-full" style="background:${categoryInk(category.token)}"></span>
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
                       style="color:${categoryInk(category.token)}">
                        <span class="inline-block w-1.5 h-1.5 rounded-full" style="background:${categoryInk(category.token)}"></span>
                        ${esc(category.label)}
                    </p>
                    <h3 class="text-xl font-mono font-semibold tabular-nums tracking-[0.06em] text-ink leading-snug mb-2 break-all">${esc(
                        resolvePartNumberLabel(node, category)
                    )}</h3>
                    <p class="text-xl font-mono font-semibold tabular-nums tracking-wide mb-2"
                       style="color:${categoryInk(category.token, 0.72)}">${esc(qtyLabel)}</p>
                    <p class="text-[12px] text-ink-dim mb-1">${esc(displayName)}</p>
                    <p class="text-[13px] text-ink-muted mb-2">${esc(fullName)}</p>
                    ${
                        node.part_number
                            ? `<p class="text-[11px] font-mono text-ink-faint">${esc(node.part_number)}</p>`
                            : ''
                    }
                    <p class="text-[11px] text-ink-faint mt-2">
                        ${esc(node.location || '')} · ${esc(node.vehicle_model || '')} · ${esc(node.bom_version || '')}
                    </p>
                </div>

                ${
                    src
                        ? `
                    <button type="button" id="bomVizKnowledgeSketch"
                            class="mx-auto flex w-fit max-w-full items-center justify-center bg-app-deep border overflow-hidden hover:border-line transition-colors p-0"
                            style="border-color:${categoryInk(category.token, 0.45)}">
                        <img src="${esc(src)}" alt="${esc(fullName)}" class="block max-h-40 max-w-[200px] w-auto h-auto object-contain" loading="lazy" draggable="false">
                    </button>
                    <p class="text-[10px] text-ink-faint -mt-3">点击在新窗口打开图纸</p>
                `
                        : `
                    <div class="h-56 bg-app-deep border border-line-subtle flex items-center justify-center">
                        <span class="text-[10px] text-ink-faint">暂无图</span>
                    </div>
                `
                }

                <div class="space-y-4">
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-ink-dim mb-1.5">完整名称</p>
                        <p class="text-[13px] text-ink leading-relaxed">${esc(fullName)}</p>
                    </div>
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-ink-dim mb-1.5">结构位置</p>
                        <p class="text-[13px] text-ink">第 ${esc(String(node.level ?? placement?.depth ?? '—'))} 层</p>
                        ${
                            parent
                                ? `<p class="text-[12px] text-ink-muted mt-1">所属：${esc(
                                      resolveDisplayName(parent, Math.max(0, (placement?.depth ?? 1) - 1))
                                  )} · ${esc(parent.part_number || '')}</p>`
                                : '<p class="text-[12px] text-ink-muted mt-1">本页供货总成</p>'
                        }
                        ${
                            childCount(node) > 0
                                ? `<p class="text-[12px] text-ink-muted mt-0.5">子件：${childCount(node)} 件</p>`
                                : ''
                        }
                    </div>
                    <div>
                        <p class="text-[10px] uppercase tracking-[0.14em] text-ink-dim mb-1.5">制造类别</p>
                        <p class="text-[13px] leading-relaxed" style="color:${categoryInk(category.token, 0.72)}">${esc(roleText)}</p>
                    </div>
                    ${
                        node.material
                            ? `
                        <div>
                            <p class="text-[10px] uppercase tracking-[0.14em] text-ink-dim mb-1.5">材料</p>
                            <p class="text-[13px] font-mono text-ink">${esc(node.material)}${
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
                            <p class="text-[10px] uppercase tracking-[0.14em] text-ink-dim mb-1.5">连接 / 焊接</p>
                            <p class="text-[13px] text-ink-muted leading-relaxed">${esc(node.weld_info)}</p>
                        </div>
                    `
                            : ''
                    }
                    ${renderExcelProvenance(node)}
                </div>
            `;

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

};

export const pageConfig = {
    render: bomVizTemplate,
    init: () => BomVizPage.init(),
    destroy() {
        exportMenu?.unbind();
        exportMenu = null;
    },
};
