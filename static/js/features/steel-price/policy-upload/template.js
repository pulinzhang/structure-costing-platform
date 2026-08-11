/**
 * Policy Upload Template
 * 政策导入页面 — 异步上传 + 任务进度轮询
 * - 双栏布局：左侧表单 + 右侧信息面板
 * - 拖拽区原位显示解析进度条与日志
 */

export function policyUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- ===== 左栏：表单卡片 ===== -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                    ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                    <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">厚度加减价导入</h5>
                </div>
                <div class="p-5">
                    <form id="policyUploadForm">
                        <!-- 生效期间：年度 + 月份（手工录入） -->
                        <div class="grid grid-cols-2 gap-3 mb-5">
                            <div class="space-y-1">
                                <label for="policyYear" class="upload-label">
                                    生效年度 <span class="text-[#d32f2f]">*</span>
                                </label>
                                <input type="text"
                                       id="policyYear"
                                       name="year"
                                       placeholder="例如：2026"
                                       required
                                       pattern="[0-9]{4}"
                                       class="upload-input">
                            </div>
                            <div class="space-y-1">
                                <label for="policyMonth" class="upload-label">
                                    生效月份 <span class="text-[#d32f2f]">*</span>
                                </label>
                                <input type="text"
                                       id="policyMonth"
                                       name="month"
                                       placeholder="例如：7"
                                       required
                                       pattern="[0-9]{1,2}"
                                       class="upload-input">
                            </div>
                        </div>

                        <!-- 拖拽上传区（解析中切换为进度面板） -->
                        <div id="policyUploadZone" class="upload-dropzone mb-5">
                            <div id="policyDropIdle">
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="policyUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                                <p class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                                <input type="file" id="policyFileInput" class="hidden" accept=".xlsx,.xls,.xlsm">
                                <button type="button"
                                        id="policySelectFileBtn"
                                        class="btn-file-select">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#616161] mt-5 mb-0">支持 .xlsx, .xls, .xlsm（最大 50MB）</p>
                            </div>

                            <!-- 解析进度（运行中显示在拖拽区原位置） -->
                            <div id="policyProgressPanel" class="hidden text-left">
                                <div class="flex items-center justify-between gap-3 mb-3">
                                    <div class="flex items-center gap-2 min-w-0">
                                        ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                        <h5 id="policyProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在解析政策文件...</h5>
                                    </div>
                                    <span id="policyProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div id="policyProgressBar"
                                         class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                                         style="width: 0%"></div>
                                </div>
                                <p id="policyProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">已提交解析队列</p>
                            </div>
                        </div>

                        <!-- 文件预览 -->
                        <div id="policyFilePreview" class="hidden mb-5"></div>

                        <!-- 操作按钮行 -->
                        <div class="flex items-center justify-end gap-3">
                            <button type="button"
                                    onclick="window.resetPolicyUploadForm()"
                                    id="policyResetButton"
                                    class="btn-ghost">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                重置
                            </button>
                            <button type="submit"
                                    id="policySubmitButton"
                                    disabled
                                    class="btn-upload-submit disabled:opacity-30 disabled:pointer-events-none">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                导入政策
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- ===== 右栏：信息面板 ===== -->
            <div class="space-y-3">
                <!-- 上传说明 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-[#616161] mb-0">导入说明</h5>
                    </div>
                    <div class="p-5">
                        <h6 class="upload-label mb-2.5">Excel 文件格式要求</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>文件应包含钢价政策相关信息</li>
                            <li>支持马钢、宝钢、首钢、鞍钢等钢厂</li>
                            <li>数据从第一行开始，不要有空行</li>
                        </ul>
                        <h6 class="upload-label mb-2.5">upsert 规则</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>按 (年度, 月份, 钢厂, 钢种, 类型, 牌号, 基准厚度) 匹配</li>
                            <li>已存在的政策会被覆盖替换</li>
                            <li>支持新增和更新</li>
                        </ul>
                        <h6 class="upload-label mb-2.5">支持的政策文件</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                            <li>马钢政策</li>
                            <li>宝钢政策</li>
                            <li>首钢政策</li>
                            <li>鞍钢政策</li>
                            <li>唐钢、邯钢、VAMA、山钢、涟钢等</li>
                        </ul>
                    </div>
                </div>

                <!-- 最近导入记录 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-[#616161] mb-0">最近导入</h5>
                    </div>
                    <div class="p-5" id="recentPolicyUploads">
                        <div class="text-center py-6">
                            <div class="w-8 h-8 bg-[#262626] flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[11px] text-[#616161]">暂无导入记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
