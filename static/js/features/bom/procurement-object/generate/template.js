/**
 * 采购对象清单 — 生成页（对齐冲压零件价格计算壳 + 焊接拆解历史）
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { SECTION_LABELS } from '../labels.js?v=2';

export function procurementObjectGenerateTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-[#bbb]">

            <div class="flex items-center justify-between pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">生成采购对象清单</h1>
                <a href="#/bom-procurement-object-list"
                   class="text-[10px] text-[#616161] hover:text-[#FF1E27] transition-colors">
                    前往采购对象清单 →
                </a>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-[#1e1e1e]"
                 style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('poGenLocation', '基地', true)}
                    ${filterSelect('poGenModel', '项目', true)}
                    ${filterSelect('poGenVersion', '版本', true)}
                    <button id="poGenResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-[#222] py-2.5">
                <div class="flex items-center gap-6 flex-wrap">
                    <div>
                        <span class="text-[9px] text-[#666] block">BOM 节点</span>
                        <span id="poCntNodes" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">将列入采购对象</span>
                        <span id="poCntObjects" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">${SECTION_LABELS.other_leaf}</span>
                        <span id="poCntOther" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">${SECTION_LABELS.anomaly}</span>
                        <span id="poCntAnomaly" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">已审锁定</span>
                        <span id="poCntApproved" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="poGenNotice" class="text-[9px] text-[#666]">
                        从材料清单树生成采购对象；同一版本再生成带回确认，已审须先反审核
                    </span>
                    <button id="poGenSubmitBtn"
                            class="h-7 px-4 text-[10px] bg-[#b71c1c] hover:bg-[#c62828] text-white font-medium rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                        开始生成
                    </button>
                </div>
            </div>

            <p class="text-[9px] text-[#484848] leading-relaxed px-1 -mt-1">
                供货总成无子件，或全部一级件都没有内部号，按退化供货件列入。一级件有内部号才进采购对象。
            </p>

            <div id="poGenProgressPanel" class="hidden border border-[#2c2c2c] bg-[#1a1a1a] px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="poGenProgressSpinner" class="w-3.5 h-3.5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin shrink-0"></div>
                        <h5 id="poGenProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在生成采购对象清单...</h5>
                    </div>
                    <span id="poGenProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-2">
                    <div id="poGenProgressBar"
                         class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="poGenProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">正在读取材料清单树</p>
            </div>

            <div id="poGenReadyBanner" class="hidden text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]"></div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-[#666] font-medium">生成历史</div>
                    <button id="poGenHistoryRefreshBtn" type="button"
                            class="text-[9px] text-[#616161] hover:text-[#9e9e9e] transition-colors">
                        刷新
                    </button>
                </div>
                <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden">
                    <div class="overflow-x-auto">
                        <table id="poGenHistoryTable" class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c] text-[9px] text-[#555] uppercase tracking-[0.08em]">
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">生成时间</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">创建人</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">项目</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">版本</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">节点</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">采购对象</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="poGenHistoryBody" class="text-[10px] divide-y divide-[#222222]">
                                <tr>
                                    <td colspan="9" class="py-8 text-center text-[#555]">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'poGenHistoryTotal', selectId: 'poGenHistoryPageSize', buttonsId: 'poGenHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-[#1e1e1e] bg-[#141414]' })}
                </div>
            </div>
        </div>
    `;
}

function filterSelect(id, label, required = false) {
    const mark = required ? '<span class="text-[#d32f2f]">*</span>' : '';
    const emptyLabel = required ? '请选择' : '全部';
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}${mark}</span>
        <select id="${id}" class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">${emptyLabel}</option>
        </select>
    </label>`;
}

