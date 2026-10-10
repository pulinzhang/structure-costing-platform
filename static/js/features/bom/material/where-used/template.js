/**
 * 零件用在哪 — HUD 密表 + 胶囊筛选（对齐材料清单列表）
 */

import { can } from '../../../../core/permissions.js?v=14';
import { filterSelect, HUD_SHELL, HUD_INPUT, HUD_BAND, BTN_GHOST } from '../../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';


export function bomWhereUsedTemplate() {
    const canExport = can('op:bom-where-used:export');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="grid grid-cols-1 gap-3 font-mono flex-1 min-w-0 sm:grid-cols-3">
                            ${hudKpiCardHtml({
                                variant: 'focus',
                                title: '命中零件',
                                pulse: true,
                                valueHtml: '<span id="wuHudHits">—</span>',
                                unit: '条',
                            })}
                            ${hudKpiCardHtml({
                                title: '材料清单',
                                valueHtml: '<span id="wuHudSnapshots">—</span>',
                                unit: '份',
                            })}
                            ${hudKpiCardHtml({
                                title: '项目',
                                valueHtml: '<span id="wuHudModels">—</span>',
                                unit: '个',
                            })}
                        </div>
                        ${canExport ? `
                        <div class="flex items-center justify-end shrink-0 pt-1 w-full sm:w-auto">
                            <button id="wuExportBtn" type="button" title="按当前查询导出"
                                    class="${BTN_GHOST}">
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
                        leadHtml: `<input id="wuQuery" type="text" placeholder="零件号 / 短码 / 名称" class="h-7 w-full sm:w-[180px] px-2.5 ${HUD_INPUT}">`,
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

