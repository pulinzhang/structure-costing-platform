/**
 * Settings Template
 * 设置页面 — Brabus Carbon & Precision Dark
 */

export function settingsTemplate() {
    return `
        <div class="max-w-xl">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                    <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.25)]"></div>
                    <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">系统设置</h3>
                </div>
                <div class="p-5 space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">应用名称</label>
                        <input type="text" value="汽车冲压件自动核价平台"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-all">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">版本</label>
                        <input type="text" value="1.0.0" readonly
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a]/50 border border-[#222222] rounded-sm text-[#616161] cursor-not-allowed">
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-[#222222]">
                    <button id="btnSaveSettings" class="inline-flex items-center gap-2 bg-[#262626] text-white border border-[#2c2c2c] rounded-sm px-4 py-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 hover:bg-[#d32f2f] hover:border-[#b71c1c]">
                        ${window.svgIcon('check', 'w-3.5 h-3.5')}
                        保存设置
                    </button>
                </div>
            </div>
        </div>
    `;
}
