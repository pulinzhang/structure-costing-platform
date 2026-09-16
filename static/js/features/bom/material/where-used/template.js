/**
 * 零件用在哪 — HUD 密表 + 胶囊筛选（对齐材料清单列表）
 */

import { can } from '../../../../permissions.js?v=12';

export function bomWhereUsedTemplate() {
    const canExport = can('op:bom-where-used:export');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4">
                        <div class="grid grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            ${hudCard('wuHudHits', '命中节点', '条', true)}
                            ${hudCard('wuHudSnapshots', '材料清单', '份')}
                            ${hudCard('wuHudModels', '项目', '个')}
                        </div>
                        ${canExport ? `
                        <div class="flex items-center shrink-0 pt-1">
                            <button id="wuExportBtn" type="button" title="按当前查询导出"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>` : ''}
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap min-w-0">
                                <input id="wuQuery" type="text"
                                       placeholder="零件号 / 短码 / 名称"
                                       class="h-7 w-[180px] px-2.5 bg-[#1A1A22] border border-[#2A2A35] text-[#F0F0F2] rounded-md outline-none focus:border-[#FF1E27]/50">
                                <span id="wuCapsuleLocation" class="hidden bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md"></span>
                                <span id="wuCapsuleModel" class="hidden bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md"></span>
                                <span id="wuCapsuleVersion" class="hidden bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md"></span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="wuToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="wuAdvancedFilterLabel">展开高级筛选</span>
                            </button>
                            <button type="button" id="wuSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>
                    <div id="wuAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('wuLocation', '基地')}
                            ${filterSelect('wuVehicle', '项目')}
                            ${filterSelect('wuVersion', '版本')}
                            <button id="wuResetFilterBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                    </div>
                </div>

                <div id="wuPathsPanel" class="p-5 space-y-4 min-h-[240px] brabus-bg-grid"></div>
            </div>
        </div>
        <div id="wuHover" class="hidden fixed z-[82] w-64 pointer-events-none bg-[#121218] border border-[#2c2c2c] p-3 text-[11px]"></div>
    `;
}

function hudCard(id, label, unit, focus = false) {
    const box = focus
        ? 'bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50'
        : 'bg-[#0D0D11]/80 border border-[#1E1E26]';
    const valueCls = focus ? 'text-[22px] font-black text-[#FF1E27]' : 'text-[18px] font-bold text-[#FFFFFF]';
    return `
        <div class="${box} p-3 backdrop-blur-sm"
             style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
            <div class="text-[#555555] text-[10px] tracking-wider">${label}</div>
            <div class="${valueCls} mt-1 tabular-nums leading-none">
                <span id="${id}">—</span>
                <span class="text-[10px] text-[#555555] ml-1 font-bold">${unit}</span>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-[#555555]" for="${id}">${label}</label>
            <select id="${id}"
                    class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all min-w-[7rem]">
                <option value="">全部</option>
            </select>
        </div>
    `;
}
