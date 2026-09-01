/**
 * BOM 材料清单上传页
 * 仅负责 Excel 导入，不含列表 / 删除 / 树
 */

import { bomUploadTemplate } from './template.js';
import { can } from '../../../../permissions.js?v=6';

const MAX_FILE_SIZE = 50 * 1024 * 1024;

const BomUploadPage = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,

    init() {
        this.selectedFile = null;
        this.isUploading = false;
        this.applyPermissionUi();
        this.bindEvents();
        this.hideProgress();
        this.hideError();
        this.clearSelectedFile(false);
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function' ? can('op:bom-upload:upload') : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('bomUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('bomUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('bomUploadResetBtn')?.classList.add('hidden');

        const fileInput = document.getElementById('bomUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        const location = document.getElementById('bomUploadLocation');
        if (location) location.disabled = true;

        const zone = document.getElementById('bomUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');

        const title = document.getElementById('bomUploadTitle');
        const hint = document.getElementById('bomUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const zone = document.getElementById('bomUploadZone');
        const fileInput = document.getElementById('bomUploadFileInput');
        const form = document.getElementById('bomUploadForm');
        const selectBtn = document.getElementById('bomUploadSelectFileBtn');
        const resetBtn = document.getElementById('bomUploadResetBtn');
        const templateBtn = document.getElementById('bomUploadTemplateBtn');
        const errorCopyBtn = document.getElementById('bomUploadErrorCopyBtn');
        const errorCloseBtn = document.getElementById('bomUploadErrorCloseBtn');

        templateBtn?.addEventListener('click', () => this.downloadTemplate());
        errorCopyBtn?.addEventListener('click', () => this.copyErrorText());
        errorCloseBtn?.addEventListener('click', () => this.hideError());

        zone?.addEventListener('click', (event) => {
            if (this.canUpload === false || this.isUploading) return;
            if (event.target.closest('button')) return;
            fileInput?.click();
        });

        selectBtn?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (this.canUpload === false || this.isUploading) return;
            fileInput?.click();
        });

        fileInput?.addEventListener('change', () => {
            this.selectFile(fileInput.files?.[0]);
        });

        zone?.addEventListener('dragover', (event) => {
            if (this.canUpload === false || this.isUploading) return;
            event.preventDefault();
            zone.classList.add('border-[#d32f2f]');
        });
        zone?.addEventListener('dragleave', () => {
            zone.classList.remove('border-[#d32f2f]');
        });
        zone?.addEventListener('drop', (event) => {
            event.preventDefault();
            zone.classList.remove('border-[#d32f2f]');
            if (this.canUpload === false || this.isUploading) return;
            this.selectFile(event.dataTransfer.files?.[0]);
        });

        resetBtn?.addEventListener('click', () => this.reset());

        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        const lower = file.name.toLowerCase();
        if (!lower.endsWith('.xlsx') && !lower.endsWith('.xls')) {
            this.showError('仅支持 .xlsx / .xls 文件');
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            this.showError('文件过大，最大支持 50MB');
            return;
        }

        this.hideProgress();
        this.hideError();
        this.selectedFile = file;

        const preview = document.getElementById('bomUploadFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]">
                    ${window.svgIcon('file-earmark-excel', 'w-5 h-5 text-[#2e7d32]')}
                    <div class="min-w-0 flex-1">
                        <p class="text-xs text-[#ffffff] truncate">${esc(file.name)}</p>
                        <p class="text-[10px] text-[#616161]">${this.formatFileSize(file.size)}</p>
                    </div>
                </div>`;
        }

        const title = document.getElementById('bomUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;

        const submitBtn = document.getElementById('bomUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('bomUploadFileInput');
        if (input) input.value = '';

        const preview = document.getElementById('bomUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }

        if (resetTitle) {
            const title = document.getElementById('bomUploadTitle');
            if (title) title.textContent = '拖拽文件到此处';
        }

        const submitBtn = document.getElementById('bomUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            this.showError('导入进行中，请稍候再重置');
            return;
        }
        this.hideProgress();
        this.hideError();
        this.clearSelectedFile(true);
        const location = document.getElementById('bomUploadLocation');
        if (location) location.value = '';
    },

    showProgress(msg = '解析三级树并落盘简图，请稍候') {
        const idle = document.getElementById('bomUploadDropIdle');
        const panel = document.getElementById('bomUploadProgressPanel');
        const zone = document.getElementById('bomUploadZone');
        const progressMsg = document.getElementById('bomUploadProgressMsg');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        if (progressMsg) progressMsg.textContent = msg;
    },

    hideProgress() {
        const idle = document.getElementById('bomUploadDropIdle');
        const panel = document.getElementById('bomUploadProgressPanel');
        const zone = document.getElementById('bomUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
    },

    hideError() {
        const panel = document.getElementById('bomUploadErrorPanel');
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
        if (panel) panel.classList.add('hidden');
        if (body) {
            body.textContent = '';
            body.dataset.raw = '';
        }
        if (copyBtn) copyBtn.textContent = '复制';
    },

    showError(message) {
        const panel = document.getElementById('bomUploadErrorPanel');
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
        const text = String(message || '导入失败').trim() || '导入失败';
        if (!panel || !body) return;
        body.textContent = text;
        body.dataset.raw = text;
        if (copyBtn) copyBtn.textContent = '复制';
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    async copyErrorText() {
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
        const text = body?.dataset?.raw || body?.textContent || '';
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            if (copyBtn) copyBtn.textContent = '已复制';
            setTimeout(() => {
                if (copyBtn && copyBtn.textContent === '已复制') copyBtn.textContent = '复制';
            }, 1600);
        } catch (_) {
            const range = document.createRange();
            range.selectNodeContents(body);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        }
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('bomUploadSubmitBtn');
        const resetBtn = document.getElementById('bomUploadResetBtn');
        const location = document.getElementById('bomUploadLocation');
        const templateBtn = document.getElementById('bomUploadTemplateBtn');
        if (submitBtn) submitBtn.disabled = isUploading || !this.selectedFile;
        if (resetBtn) resetBtn.disabled = isUploading;
        if (location && this.canUpload) location.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/bom/template', {
                defaultFilename: '材料清单导入模板.xlsx',
            });
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
            showToast('模板已下载', 'success');
        } catch (error) {
            if (!error.status) {
                showToast(error.message || '模板下载失败', 'error');
            }
        }
    },

    async submit() {
        if (this.canUpload === false) {
            this.showError('无上传权限');
            return;
        }
        if (this.isUploading) return;

        const location = document.getElementById('bomUploadLocation')?.value?.trim();
        if (!location) {
            this.showError('请选择采购基地');
            return;
        }
        if (!this.selectedFile) {
            this.showError('请选择 Excel 文件');
            return;
        }

        const formData = new FormData();
        formData.append('location', location);
        formData.append('file', this.selectedFile);

        this.hideError();
        this.setUploading(true);
        this.showProgress();

        try {
            const res = await HttpClient.post('/api/bom/upload', formData, {
                skipToast: true,
                timeout: 120000,
            });
            const data = res.data || {};
            const msg = res.message
                || data.message
                || `导入成功：${data.node_count ?? '-'} 个节点`;
            showToast(msg, 'success');
            this.hideProgress();
            this.hideError();
            this.clearSelectedFile(true);
            const loc = document.getElementById('bomUploadLocation');
            if (loc) loc.value = location;
        } catch (err) {
            this.hideProgress();
            this.showError(err.message || '导入失败');
        } finally {
            this.setUploading(false);
        }
    },

    formatFileSize(bytes) {
        if (!bytes && bytes !== 0) return '-';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    },
};

export const pageConfig = {
    render: bomUploadTemplate,
    init: () => BomUploadPage.init(),
};
