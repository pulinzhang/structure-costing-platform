/**
 * 项目上传页 — 同步导入，页面不选基地
 */

import { vehicleModelUploadTemplate } from './template.js?v=1';

const API_BASE = '/api/masterdata/vehicle-models';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const VehicleModelUploadPage = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,

    init() {
        this.selectedFile = null;
        this.isUploading = false;
        this.applyPermissionUi();
        this.bindEvents();
        this.hideProgress();
        this.clearSelectedFile(false);
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:vehicle-model-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('vmUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('vmUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('vmUploadResetBtn')?.classList.add('hidden');
        const fileInput = document.getElementById('vmUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        const zone = document.getElementById('vmUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('vmUploadTitle');
        const hint = document.getElementById('vmUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const zone = document.getElementById('vmUploadZone');
        const fileInput = document.getElementById('vmUploadFileInput');
        const form = document.getElementById('vmUploadForm');
        const selectBtn = document.getElementById('vmUploadSelectFileBtn');
        const resetBtn = document.getElementById('vmUploadResetBtn');
        const templateBtn = document.getElementById('vmUploadTemplateBtn');

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
        fileInput?.addEventListener('change', () => this.selectFile(fileInput.files?.[0]));
        zone?.addEventListener('dragover', (event) => {
            if (this.canUpload === false || this.isUploading) return;
            event.preventDefault();
            zone.classList.add('border-[#d32f2f]');
        });
        zone?.addEventListener('dragleave', () => zone.classList.remove('border-[#d32f2f]'));
        zone?.addEventListener('drop', (event) => {
            event.preventDefault();
            zone.classList.remove('border-[#d32f2f]');
            if (this.canUpload === false || this.isUploading) return;
            this.selectFile(event.dataTransfer.files?.[0]);
        });
        resetBtn?.addEventListener('click', () => this.reset());
        templateBtn?.addEventListener('click', () => this.downloadTemplate());
        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        const name = file.name.toLowerCase();
        if (!name.endsWith('.xlsx') && !name.endsWith('.xls')) {
            showToast('仅支持 .xlsx, .xls 文件', 'warning');
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            showToast('文件过大，最大支持 5MB', 'warning');
            return;
        }
        this.hideProgress();
        this.selectedFile = file;
        const preview = document.getElementById('vmUploadFilePreview');
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
        const title = document.getElementById('vmUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;
        const submitBtn = document.getElementById('vmUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('vmUploadFileInput');
        if (input) input.value = '';
        const preview = document.getElementById('vmUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        if (resetTitle) {
            const title = document.getElementById('vmUploadTitle');
            if (title) title.textContent = '拖拽文件到此处上传';
        }
        const submitBtn = document.getElementById('vmUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        document.getElementById('vmUploadDropIdle')?.classList.add('hidden');
        document.getElementById('vmUploadProgressPanel')?.classList.remove('hidden');
        const zone = document.getElementById('vmUploadZone');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        const progressMsg = document.getElementById('vmUploadProgressMsg');
        if (progressMsg) progressMsg.textContent = msg;
    },

    hideProgress() {
        document.getElementById('vmUploadDropIdle')?.classList.remove('hidden');
        document.getElementById('vmUploadProgressPanel')?.classList.add('hidden');
        document.getElementById('vmUploadZone')?.classList.remove('pointer-events-none');
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('vmUploadSubmitBtn');
        const resetBtn = document.getElementById('vmUploadResetBtn');
        const templateBtn = document.getElementById('vmUploadTemplateBtn');
        if (submitBtn) submitBtn.disabled = isUploading || !this.selectedFile;
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                defaultFilename: '项目导入模板.xlsx',
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
            showToast('无上传权限', 'warning');
            return;
        }
        if (this.isUploading) return;
        if (!this.selectedFile) {
            showToast('请选择 Excel 文件', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        this.setUploading(true);
        this.showProgress();
        try {
            const res = await HttpClient.post(`${API_BASE}/upload`, formData);
            const data = res.data || {};
            const msg = res.message
                || `导入成功：新增 ${data.created_count ?? 0}，跳过 ${data.skipped_count ?? 0}`;
            showToast(msg, 'success');
            this.hideProgress();
            this.clearSelectedFile(true);
        } catch (err) {
            this.hideProgress();
            if (!err.status) {
                showToast(err.message || '导入失败', 'error');
            }
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
    render: vehicleModelUploadTemplate,
    init: () => VehicleModelUploadPage.init(),
};
