/**
 * Quotation Template
 * 报价页面 — Brabus Carbon & Precision Dark
 */

export function quotationTemplate() {
    return `
        <div class="max-w-sm">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] p-10 text-center">
                <div class="flex justify-center mb-4">${window.svgIcon('file-earmark-text', 'w-6 h-6 text-[#616161]')}</div>
                <h3 class="text-sm font-semibold text-[#9e9e9e] mb-2">报价功能开发中</h3>
                <p class="text-xs text-[#616161] leading-relaxed">报价单生成功能正在开发中，敬请期待...</p>
            </div>
        </div>
    `;
}
