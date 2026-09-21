/**
 * 零件用在哪 — HUD 密表 + 胶囊筛选（对齐材料清单列表）
 */

import { can } from '../../../../core/permissions.js?v=14';
import { filterSelect, HUD_SHELL, HUD_INPUT, HUD_BAND, BTN_GHOST } from '../../../../ui/classes.js?v=8';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=2';


export function bomWhereUsedTemplate() {
    const canExport = can('op:bom-where-used:export');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4">
                        <div class="grid grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            ${hudCard('wuHudHits', '命中节点', '条', true)}
                            ${hudCard('wuHudSnapshots', '材料清单', '份')}
                            ${hudCard('wuHudModels', '项目', '个')}
                        </div>
                        ${canExport ? `
                        <div class="flex items-center shrink-0 pt-1">
                            <button id="wuExportBtn" type="button" title="按当前查询导出"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-ink-dim border border-line-hud px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-brand-hud/50 hover:text-brand-hud transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>` : ''}
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'wu',
                        searchId: 'wuSearchBtn',
                        leadHtml: `<input id="wuQuery" type="text" placeholder="零件号 / 短码 / 名称" class="h-7 w-[180px] px-2.5 ${HUD_INPUT}">`,
                        capsules: [
                            { capsuleId: 'wuCapsuleLocation', idleLabel: '全部基地', hideWhenIdle: true },
                            { capsuleId: 'wuCapsuleModel', idleLabel: '全部项目', hideWhenIdle: true },
                            { capsuleId: 'wuCapsuleVersion', idleLabel: '全部版本', hideWhenIdle: true },
                        ],
                        fieldsHtml: [
                            filterSelect('wuLocation', '基地'),
                            filterSelect('wuVehicle', '项目'),
                            filterSelect('wuVersion', '版本'),
                            `<button id="wuResetFilterBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                <div id="wuPathsPanel" class="p-5 space-y-4 min-h-[240px] brabus-bg-grid"></div>
            </div>
        </div>
        <div id="wuHover" class="hidden fixed z-[82] w-64 pointer-events-none bg-app-main border border-line p-3 text-[11px]"></div>
    `;
}

function hudCard(id, label, unit, focus = false) {
    const box = focus
        ? 'hud-kpi-card-glow bg-gradient-to-b from-brand-hud/15 to-app-deep border border-brand-hud/50'
        : 'bg-app-main/80 border border-line-hud';
    const valueCls = focus ? 'text-[22px] font-black text-brand-hud' : 'text-[18px] font-bold text-ink';
    return `
        <div class="${box} p-3 backdrop-blur-sm">
            <div class="text-ink-faint text-[10px] tracking-wider">${label}</div>
            <div class="${valueCls} mt-1 tabular-nums leading-none">
                <span id="${id}">—</span>
                <span class="text-[10px] text-ink-faint ml-1 font-bold">${unit}</span>
            </div>
        </div>
    `;
}

