export function steelPriceUploadTemplate() {
    const headers = ['年度', '月份', '钢种', '牌号', '参考规格', '钢厂', '中标价', '厚度', '厚度加减价', '加工费', '最终价/吨', '备注'];
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-3">
            <section class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                    ${window.svgIcon('upload', 'w-4 h-4 text-[#d32f2f]')}
                    <h3 class="text-xs font-semibold text-[#9e9e9e]">上传钢材价格文件</h3>
                </div>
                <form id="steelPriceUploadForm" class="p-5">
                    <div id="steelPriceUploadZone" class="border-2 border-dashed border-[#2c2c2c] bg-[rgba(255,255,255,0.01)] rounded p-12 text-center transition-all cursor-pointer hover:border-[#d32f2f] hover:bg-[rgba(211,47,47,0.02)]">
                        ${window.svgIcon('file-earmark-excel', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                        <p id="steelPriceUploadTitle" class="text-xs text-[#9e9e9e]">拖拽文件到此处，或<span class="text-[#d32f2f]">点击选择</span></p>
                        <p class="text-[11px] text-[#616161] mt-2">仅支持 .xlsx，最大 50MB</p>
                        <input id="steelPriceFileInput" type="file" accept=".xlsx" class="hidden">
                    </div>
                    <div id="steelPriceFilePreview" class="hidden mt-4"></div>
                    <div class="flex justify-end gap-2 mt-5">
                        <button id="steelPriceResetButton" type="button" class="px-4 py-2 text-xs text-[#9e9e9e] border border-[#2c2c2c] rounded hover:text-[#ffffff] hover:border-[#9e9e9e] transition-all">重置</button>
                        <button id="steelPriceSubmitButton" type="submit" class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-[#ffffff] bg-[#d32f2f] rounded hover:bg-[#b71c1c] disabled:opacity-40 disabled:pointer-events-none transition-all">${window.svgIcon('upload', 'w-3.5 h-3.5')}上传并导入</button>
                    </div>
                </form>
            </section>
            <aside class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222]"><h3 class="text-xs font-semibold text-[#9e9e9e]">文件格式要求</h3></div>
                <div class="p-5">
                    <p class="text-[11px] text-[#616161] leading-5 mb-3">首行必须严格按照以下 12 列排列。导入会按文件中的年度、月份覆盖该期间已有数据。</p>
                    <div class="flex flex-wrap gap-1.5">${headers.map((header, index) => `<span class="px-2 py-1 text-[10px] border border-[#2c2c2c] bg-[#121212] text-[#9e9e9e]"><span class="text-[#d32f2f] mr-1">${index + 1}</span>${header}</span>`).join('')}</div>
                </div>
            </aside>
        </div>`;
}
