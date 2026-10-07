/**
 * 零件用在哪
 */

import { can } from '../../../../core/permissions.js?v=14';
import { shortPartNumber } from '../../../../domain/part-identity.js?v=5';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=6';
import { bomWhereUsedTemplate } from './template.js?v=21';

const API_BASE = '/api/bom/where-used';
const CASCADE_API = '/api/bom/filters/cascade';

/** @type {{ paint: () => void, setOpen: (isOpen: boolean) => void, unbind: () => void } | null} */
let filterBar = null;

const LEVEL_LABEL = {
    0: '供货总成',
    1: '一级',
    2: '二级',
};

const wuState = {
    canExport: false,
};

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
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

function sketchThumbHtml(src, alt) {
    if (!src) {
        return `<span class="wu-sketch-thumb inline-flex items-center justify-center text-[9px] text-ink-faint">暂无图</span>`;
    }
    return `<img src="${esc(src)}" alt="${esc(alt || '')}" width="40" height="32"
             class="wu-sketch-thumb" loading="lazy" draggable="false">`;
}

function queryParams() {
    const params = { query: val('wuQuery') };
    const location = val('wuLocation');
    const vehicleModel = val('wuVehicle');
    const bomVersion = val('wuVersion');
    if (location) params.location = location;
    if (vehicleModel) params.vehicle_model = vehicleModel;
    if (bomVersion) params.bom_version = bomVersion;
    return params;
}

async function loadCascade(changed) {
    const location = val('wuLocation');
    const vehicleModel = val('wuVehicle');
    const params = {};
    if (location) params.location = location;
    if (vehicleModel) params.vehicle_model = vehicleModel;
    const res = await HttpClient.get(CASCADE_API, { params });
    if (!res.ok) return;
    const data = res.data || {};
    if (changed !== 'vehicle' && changed !== 'version') {
        fillSelect('wuLocation', data.locations || [], location, '全部');
    }
    if (changed !== 'version') {
        fillSelect('wuVehicle', data.vehicle_models || [], vehicleModel, '全部');
    }
    fillSelect('wuVersion', data.bom_versions || [], val('wuVersion'), '全部');
    filterBar?.paint();
}

function fillSelect(id, values, selected, emptyLabel) {
    const el = document.getElementById(id);
    if (!el) return;
    const current = selected || '';
    let html = `<option value="">${esc(emptyLabel)}</option>`;
    (values || []).forEach((item) => {
        const mark = item === current ? ' selected' : '';
        html += `<option value="${esc(item)}"${mark}>${esc(item)}</option>`;
    });
    el.innerHTML = html;
}

function bindEvents() {
    filterBar = bindFilterBar({
        prefix: 'wu',
        searchId: 'wuSearchBtn',
        capsules: [
            { capsuleId: 'wuCapsuleLocation', fieldId: 'wuLocation', idleLabel: '全部基地', hideWhenIdle: true },
            { capsuleId: 'wuCapsuleModel', fieldId: 'wuVehicle', idleLabel: '全部项目', hideWhenIdle: true },
            { capsuleId: 'wuCapsuleVersion', fieldId: 'wuVersion', idleLabel: '全部版本', hideWhenIdle: true },
        ],
        countFieldIds: ['wuLocation', 'wuVehicle', 'wuVersion'],
        resetId: 'wuResetFilterBtn',
        enterFieldIds: ['wuQuery'],
        startOpen: false,
        onSearch: () => runSearch(),
        onReset: () => resetFilters(),
    });
    document.getElementById('wuExportBtn')?.addEventListener('click', () => exportExcel());
    document.getElementById('wuLocation')?.addEventListener('change', () => loadCascade('location'));
    document.getElementById('wuVehicle')?.addEventListener('change', () => loadCascade('vehicle'));
}

function updateHud(summary) {
    const set = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = String(value ?? 0);
    };
    set('wuHudHits', summary?.hit_count);
    set('wuHudSnapshots', summary?.snapshot_count);
    set('wuHudModels', summary?.vehicle_model_count);
}

function emptyHtml(message) {
    return `
        <div class="flex flex-col items-center justify-center py-14">
            <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-app-main border border-line-hud">
                ${window.svgIcon('clipboard-list', 'w-4 h-4 text-ink-faint')}
            </div>
            <p class="text-[11px] text-ink-muted">${esc(message)}</p>
        </div>
    `;
}

function renderPaths(paths) {
    const panel = document.getElementById('wuPathsPanel');
    if (!panel) return;
    if (!paths || !paths.length) {
        panel.innerHTML = emptyHtml('没有挂载。换个零件号、短码或名称再查。');
        return;
    }
    panel.innerHTML = paths.map((path) => {
        const head = `${esc(path.location)} · ${esc(path.vehicle_model)} · ${esc(path.bom_version)}`;
        const cards = (path.nodes || []).map((node, nodeIndex) => nodeCardHtml(path, node, nodeIndex === 0)).join(
            '<div class="text-ink-faint text-lg px-1">→</div>',
        );
        return `
            <div class="wu-open-path border border-line-hud bg-app-main p-3 cursor-pointer hover:border-brand-hud/40"
                 data-snapshot-id="${esc(String(path.snapshot_id))}"
                 data-node-id="${esc(String(path.l0_node_id))}"
                 title="打开该供货总成">
                <div class="text-[10px] text-ink-faint mb-3 font-mono">${head}</div>
                <div class="flex flex-wrap items-stretch gap-2">${cards}</div>
            </div>
        `;
    }).join('');
    bindCardEvents(panel);
    panel.querySelectorAll('.wu-open-path').forEach((row) => {
        row.addEventListener('click', () => openAssembly(row));
    });
}

function openAssembly(el) {
    const snapshotId = el.getAttribute('data-snapshot-id');
    const nodeId = el.getAttribute('data-node-id');
    if (!snapshotId || !nodeId) return;
    hideHover();
    const url =
        `${window.location.pathname}${window.location.search}` +
        `#/bom-viz?snapshot_id=${encodeURIComponent(snapshotId)}&node_id=${encodeURIComponent(nodeId)}`;
    const opened = window.open(url, '_blank', 'noopener,noreferrer');
    if (opened) opened.opener = null;
}

function nodeCardHtml(path, node, isHit) {
    const src = sketchSrc(node.sketch_url);
    const shortNo = shortPartNumber(node.part_number) || node.part_number;
    const levelText = LEVEL_LABEL[node.level] || `L${node.level}`;
    const payload = encodeURIComponent(JSON.stringify({
        node,
        pathQty: path.path_qty,
        isHit,
    }));
    return `
        <div class="wu-node-card w-32 shrink-0 bg-app-main border border-line text-left"
             data-payload="${payload}">
            <div class="flex items-center gap-1 px-2 pt-1.5">
                <span class="text-[9px] text-ink-faint shrink-0">${esc(levelText)}</span>
                ${sketchThumbHtml(src, node.part_name || node.part_number)}
            </div>
            <div class="px-2 py-1.5 border-t border-line-hud">
                <div class="text-[13px] font-mono font-bold text-ink truncate">${esc(shortNo)}</div>
                <div class="text-[9px] text-ink-faint truncate">${esc(node.part_name || '')}</div>
                <div class="text-[9px] font-mono text-ink-dim mt-1">
                    ${esc(isHit ? `单车 ${path.path_qty}` : (node.qty_text || node.qty || ''))}
                </div>
            </div>
        </div>
    `;
}

function bindCardEvents(root) {
    root.querySelectorAll('.wu-node-card').forEach((card) => {
        card.addEventListener('mouseenter', (event) => showHover(card, event));
        card.addEventListener('mousemove', (event) => moveHover(event));
        card.addEventListener('mouseleave', hideHover);
    });
}

function parsePayload(card) {
    try {
        return JSON.parse(decodeURIComponent(card.getAttribute('data-payload') || ''));
    } catch {
        return null;
    }
}

function showHover(card, event) {
    const payload = parsePayload(card);
    const panel = document.getElementById('wuHover');
    if (!payload || !panel) return;
    const node = payload.node || {};
    const lines = [];
    const push = (label, value) => {
        if (value === null || value === undefined || value === '') return;
        lines.push(`<div class="mb-1"><span class="text-ink-faint">${esc(label)}</span> ${esc(String(value))}</div>`);
    };
    push('层级', LEVEL_LABEL[node.level] || node.level);
    push('短码', shortPartNumber(node.part_number));
    push('零件号', node.part_number);
    push('名称', node.part_name);
    push('内部号', node.internal_number);
    push('相对父件用量', node.qty_text || node.qty);
    if (payload.isHit) push('本路径单车用量', payload.pathQty);
    push('材料', node.material);
    push('料厚', node.thickness_text);
    push('厂家', node.material_mill);
    push('单件重量', node.part_weight);
    push('焊接信息', node.weld_info);
    push('备注', node.remark);
    const excelBits = [node.excel_filename, node.excel_sheet_name, node.excel_row]
        .filter((item) => item !== null && item !== undefined && item !== '');
    if (excelBits.length) push('材料清单位置', excelBits.join(' · '));
    const src = sketchSrc(node.sketch_url);
    const thumb = src
        ? `<img src="${esc(src)}" alt="" width="240" height="160" class="wu-sketch-preview mb-2">`
        : '';
    panel.innerHTML = thumb + lines.join('');
    panel.classList.remove('hidden');
    moveHover(event);
}

function moveHover(event) {
    placeHover(event.clientX + 14, event.clientY + 14);
}

function placeHover(x, y) {
    const panel = document.getElementById('wuHover');
    if (!panel || panel.classList.contains('hidden')) return;
    const panelW = panel.offsetWidth || 256;
    const panelH = panel.offsetHeight || 200;
    let left = x;
    let top = y;
    if (left + panelW > window.innerWidth - 12) left = x - panelW - 14;
    if (top + panelH > window.innerHeight - 12) top = y - panelH - 14;
    if (left < 12) left = 12;
    if (top < 12) top = 12;
    panel.style.left = `${Math.round(left)}px`;
    panel.style.top = `${Math.round(top)}px`;
}

function hideHover() {
    document.getElementById('wuHover')?.classList.add('hidden');
}

async function runSearch() {
    const params = queryParams();
    if (!params.query) {
        showToast('请输入零件号、4 位短码或名称', 'warning');
        return;
    }
    const res = await HttpClient.get(API_BASE, { params });
    if (!res.ok) {
        showToast(res.message || '查询失败', res.status === 409 ? 'warning' : 'error');
        return;
    }
    updateHud(res.data?.summary);
    renderPaths(res.data?.paths || []);
    if (!(res.data?.paths || []).length) {
        showToast(res.message || '没有挂载', 'warning');
    }
}

async function exportExcel() {
    if (!wuState.canExport) return;
    const params = queryParams();
    if (!params.query) {
        showToast('请输入零件号、4 位短码或名称', 'warning');
        return;
    }
    try {
        const { blob, filename } = await HttpClient.download(API_BASE + '/export', { params });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || '零件用在哪.xlsx';
        link.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        if (error?.wechatGuide) return;
        showToast(error?.message || '导出失败', 'error');
    }
}

function resetFilters() {
    ['wuLocation', 'wuVehicle', 'wuVersion'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    loadCascade();
}

function init() {
    if (!can('op:bom-where-used:view')) {
        const root = document.getElementById('pageContent');
        if (root) {
            root.innerHTML = `<div class="py-16 text-center text-[11px] text-ink-dim">需要权限 op:bom-where-used:view</div>`;
        }
        return;
    }
    wuState.canExport = can('op:bom-where-used:export');
    updateHud({ hit_count: 0, snapshot_count: 0, vehicle_model_count: 0 });
    renderPaths([]);
    bindEvents();
    loadCascade();
}

function destroy() {
    hideHover();
    filterBar?.unbind();
    filterBar = null;
}

export const pageConfig = {
    render: bomWhereUsedTemplate,
    init,
    destroy,
};
