/**
 * BOM 材料清单列表 — HUD 密表
 */

import { filterSelect, HUD_SHELL, HUD_BAND, OPS_TH, BTN_GHOST } from '../../../../ui/classes.js?v=11';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';


const STATUS_LABEL = {
    draft: { text: '草稿', cls: 'text-warn bg-warn/15' },
    active: { text: '生效', cls: 'text-ok bg-ok/15' },
    archived: { text: '归档', cls: 'text-ink-muted bg-ink-faint/15' },
};

const STAGE_LABEL = {
    initial: '初始',
    mass: '批量',
};

export function bomMaterialListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono mb-3">
                        ${hudKpiCardHtml({ title: '清单', valueHtml: '<span id="bomMatHudTotal">—</span>', unit: '份' })}
                        ${hudKpiCardHtml({ title: '生效', valueHtml: '<span id="bomMatHudActive">—</span>', unit: '份' })}
                        ${hudKpiCardHtml({ title: '草稿', valueHtml: '<span id="bomMatHudDraft">—</span>', unit: '份' })}
                        ${hudKpiCardHtml({ title: '归档', valueHtml: '<span id="bomMatHudArchived">—</span>', unit: '份' })}
                        ${hudKpiCardHtml({
                            title: '节点合计',
                            tone: 'warn',
                            valueHtml: '<span id="bomMatHudNodes">—</span>',
                            unit: '个',
                        })}
                    </div>
                    <p class="text-[10px] text-ink-muted leading-relaxed">
                        材料清单按<strong class="font-semibold text-ink">基地 + 项目 + 版本</strong>唯一。
                        操作列可打开产品结构；删除仅针对该行清单（含全部树节点），不可恢复。
                    </p>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'bomMat',
                        searchId: 'btnBomMatFilter',
                        capsules: [
                            { capsuleId: 'bomMatCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'bomMatCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'bomMatCapsuleVersion', idleLabel: '全部版本' },
                            { capsuleId: 'bomMatCapsuleStatus', idleLabel: '全部状态' },
                        ],
                        fieldsHtml: [
                            filterSelect('bomMatLocationFilter', '基地'),
                            filterSelect('bomMatModelFilter', '项目'),
                            filterSelect('bomMatVersionFilter', '版本'),
                            filterSelect('bomMatStatusFilter', '状态'),
                            `<button id="bomMatResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                ${hudTableHtml({
                    prefix: 'bomMat',
                    minWidth: '1100px',
                    colgroupHtml: `
                            <col style="width:2px">
                            <col style="width:8%">
                            <col style="width:8%">
                            <col style="width:7%">
                            <col style="width:18%">
                            <col style="width:8%">
                            <col style="width:7%">
                            <col style="width:8%">
                            <col style="width:16%">
                            <col style="width:10%">
                            <col style="width:10%">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">版本</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-dim">标题 / 顾客</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">阶段</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-brand-hud/90 bg-brand-hud/10">节点数</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">源文件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">更新</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无材料清单', hint: '请先在「上传材料清单」页导入 Excel' },
                    loading: true,
                })}
            </div>
        </div>
    `;
}

export function updateBomMatHud(summary) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val == null ? '—' : String(val);
    };
    set('bomMatHudTotal', summary?.total_count);
    set('bomMatHudActive', summary?.active_count);
    set('bomMatHudDraft', summary?.draft_count);
    set('bomMatHudArchived', summary?.archived_count);
    set('bomMatHudNodes', summary?.total_node_count);
}

export function renderBomMatTableRows(records, options = {}) {
    if (!records.length) return '';
    const canViewStructure = !!options.canViewStructure;
    const canDelete = !!options.canDelete;
    const nodeCell =
        'px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-brand-hud bg-brand-hud/10 border-x border-brand-hud/20';

    return records.map((row) => {
        const status = STATUS_LABEL[row.status] || { text: row.status || '-', cls: 'text-ink-muted' };
        const stage = STAGE_LABEL[row.stage] || row.stage || '—';
        const nodeCount = Number(row.node_count) || 0;
        const title = row.title || '—';
        const customer = row.customer_name || '';
        const source = row.source_filename || '—';
        const updated = formatUpdatedAt(row.updated_at) || '—';
        const updatedBy = row.updated_by || '';

        const structureBtn = canViewStructure
            ? opsIconButtonHtml({
                action: 'open-structure',
                title: '产品结构',
                icon: window.svgIcon('eye', 'w-3.5 h-3.5'),
                attrs: `data-snapshot-id="${row.id}"`,
            })
            : '';
        const deleteBtn = canDelete
            ? opsIconButtonHtml({
                action: 'delete-one',
                danger: true,
                title: '删除本清单',
                icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                attrs: `data-snapshot-id="${row.id}" data-location="${esc(row.location)}" data-vehicle-model="${esc(row.vehicle_model)}" data-bom-version="${esc(row.bom_version)}"`,
            })
            : '';
        const opsHtml = (structureBtn || deleteBtn) ? `${structureBtn}${deleteBtn}` : '—';

        return hudRowHtml({
            attrs: `data-snapshot-id="${row.id}"`,
            cellsHtml: `
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.location)}</td>
                <td class="px-2 py-2 text-ink font-semibold truncate">${esc(row.vehicle_model)}</td>
                <td class="px-2 py-2 text-ink-muted truncate">${esc(row.bom_version)}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[11px] text-ink font-semibold truncate" title="${esc(title)}">${esc(title)}</div>
                    ${customer ? `<div class="text-[9px] text-ink-faint mt-0.5 truncate" title="${esc(customer)}">${esc(customer)}</div>` : ''}
                </td>
                <td class="px-2 py-2 text-center text-[10px] text-ink-muted">${esc(stage)}</td>
                <td class="px-2 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${status.cls}">${esc(status.text)}</span>
                </td>
                <td class="${nodeCell}" title="节点数 ${nodeCount}">
                    <span>${nodeCount}</span>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-ink-muted truncate" title="${esc(source)}">${esc(source)}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-ink-muted truncate">${esc(updated)}</div>
                    ${updatedBy ? `<div class="text-[9px] text-ink-faint mt-0.5 truncate">${esc(updatedBy)}</div>` : ''}
                </td>`,
            opsHtml,
        });
    }).join('');
}

function formatUpdatedAt(value) {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value).slice(0, 16).replace('T', ' ');
    }
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d} ${hh}:${mm}`;
}

