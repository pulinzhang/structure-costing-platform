/**
 * Steel Base Price Download Template
 * 基准价格列表页面
 */

import { filterSelect, filterInputWithDatalist, HUD_LED, BTN_GHOST, BTN_FILTER_SEARCH, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    paginationBarHtml,
} from '../../../../ui/page-size.js?v=6';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=6';

export function basePriceDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <!-- 页面主面板 -->
            <div class="bg-app-surface border border-line overflow-hidden w-full max-w-full">

                <!-- 面板头部：标题 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-line-subtle">
                    <div class="flex items-center gap-3">
                        <div class="${HUD_LED}"></div>
                        <h2 class="text-[12px] font-semibold text-ink-muted tracking-wide">基准价格列表</h2>
                    </div>
                    <div class="flex items-center gap-1.5">
                        ${moreMenuShellHtml({
                            wrapId: 'basePriceMoreWrap',
                            btnId: 'basePriceMoreBtn',
                            menuId: 'basePriceMoreMenu',
                            itemsHtml: moreMenuItemHtml({ id: 'btnDeleteBasePrice', label: '删除', danger: true }),
                        })}
                        <button id="btnExportBasePrice"
                                class="${BTN_GHOST}">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            Excel
                        </button>
                    </div>
                </div>

                <!-- 筛选工具栏 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-app-surface">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('basePriceDownloadYear', '年度')}
                        ${filterSelect('basePriceDownloadMonth', '月份')}
                        ${filterSelect('basePriceDownloadLocation', '基地')}
                        ${filterSelect('basePriceDownloadMill', '钢厂')}
                        ${filterSelect('basePriceDownloadCategory', '钢种大类')}
                        ${filterInputWithDatalist('basePriceDownloadGrade', '牌号', 'basePriceGradeOptions')}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreviewBasePrice"
                                class="${BTN_FILTER_SEARCH} h-7">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <!-- 提示信息 -->
                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="bg-app-deep border border-line-subtle rounded p-3">
                        <p class="text-[11px] text-ink-muted leading-5">
                            <span class="text-ink-muted font-medium">说明：</span>
                            打开默认当年；年度、月份、基地、钢厂、钢种大类、牌号为可选筛（一事一议按月定价）。基准价格表记录每个基地、每个钢厂、每个牌号在每个月的到厂原卷承兑价格。导出须选定年度和月份。
                        </p>
                    </div>
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
                    <!-- 已选条件 -->
                    <div class="mb-3 px-3 py-2 rounded-sm relative">
                        <div class="absolute top-0 left-0 right-0 h-px"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-ink-faint">已选条件：</span>
                            <span id="selectedBasePriceConditions" class="text-ink-muted ml-2 font-medium tracking-wide">全部</span>
                        </div>
                        <div class="absolute bottom-0 left-0 right-0 h-px"></div>
                    </div>

                    <!-- 预览表格 -->
                    <div class="bg-app-main border border-line-subtle rounded-sm overflow-hidden">
                        <div class="overflow-x-auto max-h-[400px] brabus-bg-grid">
                            <table class="w-full min-w-[1200px]">
                                <thead>
                                    <tr class="border-b border-app-surface">
                                        <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">ID</th>
                                        <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint whitespace-nowrap">年度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">月份</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基地</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢种大类</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">牌号</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">规格</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">厚度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">宽度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基准价格</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">加工费</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">文件名</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">表页</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">行号</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">列号</th>
                                    </tr>
                                </thead>
                                <tbody id="basePricePreviewBody" class="divide-y divide-line-subtle">
                                    <tr>
                                        <td colspan="16" class="px-4 py-8 text-center text-ink-dim text-xs">
                                            当前筛选下暂无数据；打开默认当年，筛选项只作收窄
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- 分页 -->
                    ${paginationBarHtml({ infoHtml: `<div class="text-[11px] text-ink-dim">共 <span id="basePriceRecordCount" class="text-ink-muted font-mono">0</span> 条记录</div>`, selectId: 'basePricePageSize', buttonsId: 'basePricePagination', currentSize: DEFAULT_PREVIEW_PAGE_SIZE, options: PREVIEW_PAGE_SIZE_OPTIONS, wrapperClass: 'flex items-center justify-between mt-4 gap-3' })}
                </div>
            </div>
        </div>

        <!-- 加载遮罩 -->
        <div id="basePriceDownloadLoading" class="hidden ${DRAWER_BACKDROP} flex items-center justify-center">
            <div class="bg-app-surface border border-line rounded p-6 flex flex-col items-center gap-3">
                <div class="w-6 h-6 border-2 border-line border-brand rounded-full animate-spin"></div>
                <span class="text-[11px] text-ink-muted">正在生成 Excel...</span>
            </div>
        </div>
    `;
}

// ===== 辅助函数 =====

