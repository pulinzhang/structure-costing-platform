/**
 * Steel Base Price Download Template
 * 基准价格列表页面
 */

import { filterSelect, filterInputWithDatalist, HUD_LED, BTN_GHOST, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=15';
import { filterBarHtml } from '../../../../ui/filter-bar.js?v=6';
import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    paginationBarHtml,
} from '../../../../ui/page-size.js?v=11';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=7';

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

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    ${filterBarHtml({
                        prefix: 'basePriceDownload',
                        searchId: 'btnPreviewBasePrice',
                        capsules: [
                            { capsuleId: 'basePriceCapsulePeriod', idleLabel: '全部期间' },
                            { capsuleId: 'basePriceCapsuleLocation', idleLabel: '全部基地' },
                            { capsuleId: 'basePriceCapsuleMill', idleLabel: '全部钢厂' },
                            { capsuleId: 'basePriceCapsuleCategory', idleLabel: '全部钢种大类' },
                            { capsuleId: 'basePriceCapsuleGrade', idleLabel: '全部牌号' },
                        ],
                        alwaysHintHtml: '打开默认当年。年度、月份、基地、钢厂、钢种大类、牌号都可以不选。这里记每个基地、每个钢厂、每个牌号、每个月的到厂原卷承兑价。导出必须先选年度和月份。',
                        fieldsHtml: [
                            filterSelect('basePriceDownloadYear', '年度'),
                            filterSelect('basePriceDownloadMonth', '月份'),
                            filterSelect('basePriceDownloadLocation', '基地'),
                            filterSelect('basePriceDownloadMill', '钢厂'),
                            filterSelect('basePriceDownloadCategory', '钢种大类'),
                            filterInputWithDatalist('basePriceDownloadGrade', '牌号', 'basePriceGradeOptions'),
                            `<button id="basePriceDownloadResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
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
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">溯源钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">钢种大类</th>
                                        <th class="record-key px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">牌号</th>
                                        <th class="record-spec px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">规格</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">厚度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">宽度</th>
                                        <th class="record-focus px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">基准价格</th>
                                        <th class="record-aux px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">加工费</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">文件名</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">表页</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">行号</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold font-medium tracking-[0.08em] text-ink-faint whitespace-nowrap">列号</th>
                                    </tr>
                                </thead>
                                <tbody id="basePricePreviewBody" class="divide-y divide-line-subtle">
                                    <tr>
                                        <td colspan="17" class="px-4 py-8 text-center text-ink-dim text-xs">
                                            当前筛选下暂无数据；打开默认当年，筛选项用来缩小范围
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

