/**
 * Settings Template
 * 系统设置 — Brabus Carbon & Precision Dark
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
                        <input id="settingsAppName" type="text"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-all"
                               placeholder="汽车冲压件自动核价平台">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">版本</label>
                        <input id="settingsVersion" type="text" readonly
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a]/50 border border-[#222222] rounded-sm text-[#616161] cursor-not-allowed">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">
                            钢材密度
                            <span class="ml-1 font-normal normal-case tracking-normal text-[#484848]">g/cm³</span>
                        </label>
                        <input id="settingsSteelDensity" type="number" step="0.01" min="0.01" max="20"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] font-mono tabular-nums focus:outline-none focus:border-[#ff5252] transition-all"
                               placeholder="7.85">
                        <p class="mt-1.5 text-[10px] text-[#555555]">毛坯重量公式使用；未配置时默认 7.85</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">
                            冲压材料损耗率
                            <span class="ml-1 font-normal normal-case tracking-normal text-[#484848]">‰</span>
                        </label>
                        <input id="settingsMaterialLossPermille" type="number" step="0.1" min="0" max="200"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] font-mono tabular-nums focus:outline-none focus:border-[#ff5252] transition-all"
                               placeholder="3">
                        <p class="mt-1.5 text-[10px] text-[#555555]">采购按 (1+损耗率) 买料；默认 3‰</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1 block">
                            废料回收率
                            <span class="ml-1 font-normal normal-case tracking-normal text-[#484848]">%</span>
                        </label>
                        <input id="settingsScrapRecoveryPercent" type="number" step="0.1" min="0.1" max="100"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] font-mono tabular-nums focus:outline-none focus:border-[#ff5252] transition-all"
                               placeholder="97">
                        <p class="mt-1.5 text-[10px] text-[#555555]">废料扣除 × 回收率（含损耗废料）；默认 97%</p>
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-[#222222]">
                    <button id="btnSaveSettings" type="button"
                            class="inline-flex items-center gap-2 bg-[#262626] text-white border border-[#2c2c2c] rounded-sm px-4 py-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 hover:bg-[#d32f2f] hover:border-[#b71c1c]">
                        ${window.svgIcon('check', 'w-3.5 h-3.5')}
                        保存设置
                    </button>
                </div>
            </div>
        </div>
    `;
}
