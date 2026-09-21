import { HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, filterSelect, filterInput, BTN_GHOST } from '../../../../ui/classes.js?v=12';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=3';
import { hudTableHtml } from '../../../../ui/hud-table.js?v=2';
import { hudKpiCardHtml } from '../../../../ui/hud-kpi.js?v=1';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=5';

export function dieListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 gap-3 font-mono flex-1 min-w-0">
                            ${hudKpiCardHtml({
                                title: '查询范围',
                                valueKind: 'text',
                                valueId: 'dieHudScope',
                                valueHtml: '全部',
                            })}
                            ${hudKpiCardHtml({
                                title: '零件',
                                valueId: 'dieHudTotal',
                                valueHtml: '—',
                            })}
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'dieMoreWrap',
                                btnId: 'dieMoreBtn',
                                menuId: 'dieMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'dieBatchDeleteBtn', label: '删除本范围', danger: true }),
                            })}
                            <button id="dieExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-ink-dim border border-line-hud px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-brand-hud/50 hover:text-brand-hud hover:bg-brand-hud/10 transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>
                        </div>
                    </div>
                </div>
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'dieList',
                        capsules: [
                            { capsuleId: 'dieListCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'dieListCapsuleModel', idleLabel: '全部项目' },
                            { capsuleId: 'dieListCapsulePart', idleLabel: '全部零件' },
                        ],
                        fieldsHtml: [
                            filterSelect('dieListLocation', '基地'),
                            filterSelect('dieListVehicle', '项目'),
                            filterInput('dieListPartNumber', '零件号', '可选'),
                            `<button id="dieListResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                        alwaysHintHtml: '进入即显示全部；基地/项目/零件号可选收窄。删除本范围、导出须选定基地+项目。',
                    })}
                </div>
                ${hudTableHtml({
                    prefix: 'dieList',
                    minWidth: '880px',
                    colgroupHtml: `
                            <col style="width: 8px">
                            <col style="width: 56px">
                            <col style="width: 72px">
                            <col style="width: 180px">
                            <col style="width: 90px">
                            <col style="width: 90px">
                            <col style="width: 90px">
                            <col style="width: 140px">
                            <col style="width: 72px">
                            <col style="width: 56px">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">序号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-muted">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">模具类型</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">模具方式</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">生产方式</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">生失效</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">工序</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: { title: '暂无模具数据', hint: '请先上传模具布点清单', hidden: false },
                    loading: true,
                })}
            </div>
        </div>
        <div class="${DRAWER_BACKDROP}" id="dieDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[860px] max-w-[96vw] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="dieDrawer" style="display:none; max-height: 100vh">
            <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between">
                <div>
                    <p class="text-[9px] tracking-[0.12em] text-ink-faint mb-0.5">DIE LAYOUT</p>
                    <h5 class="text-xs font-semibold text-ink-muted mb-0">模具详情</h5>
                </div>
                <button type="button" id="dieDrawerCloseBtn" class="w-7 h-7 text-ink-dim hover:text-ink">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 overflow-y-auto p-5" id="dieDrawerContent"></div>
        </div>
    `;
}
