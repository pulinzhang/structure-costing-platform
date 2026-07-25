import { steelPriceUploadTemplate } from './template.js';

const SteelPriceUploadPage = {
    selectedFile: null,
    init() {
        this.selectedFile = null;
        const zone = document.getElementById('steelPriceUploadZone');
        const input = document.getElementById('steelPriceFileInput');
        const form = document.getElementById('steelPriceUploadForm');
        const resetButton = document.getElementById('steelPriceResetButton');
        zone?.addEventListener('click', () => input?.click());
        input?.addEventListener('change', () => this.selectFile(input.files?.[0]));
        zone?.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('border-[#d32f2f]'); });
        zone?.addEventListener('dragleave', () => zone.classList.remove('border-[#d32f2f]'));
        zone?.addEventListener('drop', event => { event.preventDefault(); zone.classList.remove('border-[#d32f2f]'); this.selectFile(event.dataTransfer.files?.[0]); });
        resetButton?.addEventListener('click', () => this.reset());
        form?.addEventListener('submit', event => { event.preventDefault(); this.submit(); });
    },
    selectFile(file) {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.xlsx')) { showToast('仅支持 .xlsx 文件', 'warning'); return; }
        if (file.size > 50 * 1024 * 1024) { showToast('文件过大，最大支持 50MB', 'warning'); return; }
        this.selectedFile = file;
        const preview = document.getElementById('steelPriceFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `<div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]"><span class="text-[#2e7d32]">${svgIcon('file-earmark-excel')}</span><div class="min-w-0 flex-1"><p class="text-xs text-[#ffffff] truncate">${esc(file.name)}</p><p class="text-[10px] text-[#616161]">${window.formatFileSize(file.size)}</p></div></div>`;
        }
        const title = document.getElementById('steelPriceUploadTitle');
        if (title) title.textContent = '已选择文件';
    },
    reset() {
        this.selectedFile = null;
        const input = document.getElementById('steelPriceFileInput');
        if (input) input.value = '';
        document.getElementById('steelPriceFilePreview')?.classList.add('hidden');
        const title = document.getElementById('steelPriceUploadTitle');
        if (title) title.innerHTML = '拖拽文件到此处，或<span class="text-[#d32f2f]">点击选择</span>';
    },
    async submit() {
        if (!this.selectedFile) { showToast('请选择钢材价格文件', 'warning'); return; }
        const button = document.getElementById('steelPriceSubmitButton');
        if (button) { button.disabled = true; button.textContent = '正在导入...'; }
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        try {
            const response = await HttpClient.post('/api/steel-prices/upload', formData);
            const data = response.data || {};
            const created = data.created_count || 0;
            const updated = data.updated_count || 0;
            const total = data.imported_count || (created + updated);
            showToast(`导入成功，新增 ${created} 条，更新 ${updated} 条，共 ${total} 条`, 'success');
            this.reset();
        } catch (error) { showToast(error.message || '导入失败', 'error'); }
        finally { if (button) { button.disabled = false; button.innerHTML = `${svgIcon('upload', 'w-3.5 h-3.5')}上传并导入`; } }
    },
};

export const pageConfig = { render: steelPriceUploadTemplate, init: () => SteelPriceUploadPage.init() };
