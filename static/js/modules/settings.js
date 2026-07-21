/**
 * Settings Template
 * 设置页面模板
 */

export function settingsTemplate() {
    return `
        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
            <h3 class="text-base font-semibold text-slate-900 mb-4">系统设置</h3>
            <div class="space-y-4">
                <div>
                    <label class="text-sm font-medium text-slate-700 mb-1 block">应用名称</label>
                    <input type="text" value="汽车冲压件自动核价平台"
                           class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-300 transition-colors">
                </div>
                <div>
                    <label class="text-sm font-medium text-slate-700 mb-1 block">版本</label>
                    <input type="text" value="1.0.0" readonly
                           class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-slate-100 text-slate-500 cursor-not-allowed">
                </div>
            </div>
            <div class="mt-6 pt-4 border-t border-slate-100">
                <button class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    保存设置
                </button>
            </div>
        </div>
    `;
}
