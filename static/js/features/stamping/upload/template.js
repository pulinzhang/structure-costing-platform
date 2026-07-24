/**
 * Upload Template
 * 上传页面 — Brabus Carbon & Precision Dark
 * - 双栏布局：左侧表单 + 右侧信息面板
 * - 主按钮 Brabus 红 / 次按钮 Ghost 文字型
 * - 拖拽区加大垂直留白
 */

export function uploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- ===== 左栏：表单卡片 ===== -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                    ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-[#616161]')}
                    <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">上传车型冲压工艺文件</h5>
                </div>
                <div class="p-5">
                    <form id="uploadForm">
                        <!-- 车型 + 版本 -->
                        <div class="grid grid-cols-2 gap-3 mb-5">
                            <div class="space-y-1">
                                <label for="vehicleModel" class="upload-label">
                                    车型 <span class="text-[#d32f2f]">*</span>
                                </label>
                                <input type="text"
                                       id="vehicleModel"
                                       name="vehicle_model"
                                       placeholder="例如：H61"
                                       required
                                       class="upload-input">
                            </div>
                            <div class="space-y-1">
                                <label for="version" class="upload-label">
                                    版本 <span class="text-[#d32f2f]">*</span>
                                </label>
                                <input type="text"
                                       id="version"
                                       name="version"
                                       placeholder="例如：V1.0"
                                       required
                                       class="upload-input">
                            </div>
                        </div>

                        <!-- 拖拽上传区：加大垂直留白 -->
                        <div id="uploadZone" class="upload-dropzone mb-5">
                            ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                            <h5 id="uploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                            <p id="uploadHint" class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                            <input type="file" id="fileInput" class="hidden" accept=".xlsx,.xls">
                            <button type="button"
                                    onclick="document.getElementById('fileInput').click()"
                                    class="btn-file-select">
                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                选择文件
                            </button>
                            <p class="text-[10px] text-[#616161] mt-5 mb-0">支持 .xlsx, .xls（最大 50MB）</p>
                        </div>

                        <!-- 文件预览 -->
                        <div id="filePreview" class="hidden mb-5"></div>

                        <!-- 操作按钮行 -->
                        <div class="flex items-center justify-end gap-3">
                            <button type="button"
                                    onclick="window.resetUploadForm()"
                                    class="btn-ghost">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                重置
                            </button>
                            <button type="submit"
                                    id="submitBtn"
                                    class="btn-upload-submit disabled:opacity-30 disabled:pointer-events-none">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                上传
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
                        <h5 class="text-xs font-semibold text-[#616161] mb-0">上传说明</h5>
                    </div>
                    <div class="p-5">
                        <h6 class="upload-label mb-2.5">Excel 文件格式要求</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>文件应包含冲压工艺相关信息</li>
                            <li>支持多工作表导入</li>
                            <li>数据从第一行开始，不要有空行</li>
                        </ul>
                        <h6 class="upload-label mb-2.5">支持的字段</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                            <li>零件号 (Part Number)</li>
                            <li>零件名称 (Part Name)</li>
                            <li>材料 (Material)</li>
                            <li>料厚 (Thickness)</li>
                            <li>工序数量 (Process Count)</li>
                            <li>模具数量 (Die Count)</li>
                        </ul>
                    </div>
                </div>

                <!-- 最近上传记录 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-[#616161] mb-0">最近上传</h5>
                    </div>
                    <div class="p-5" id="recentUploads">
                        <div class="text-center py-6">
                            <div class="w-8 h-8 bg-[#262626] flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[11px] text-[#616161]">暂无上传记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
