/**
 * 焊接单价上传页
 * 同步导入：基地 + 年度必选，仅 .xlsx
 */

import { weldingUnitPriceUploadTemplate } from './template.js';

const API_BASE = '/api/bom/welding-unit-price';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const WeldingUnitPriceUploadPage = {
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
        this.fillDefaultYear();
    },

    applyPermissionUi() {
        const canUpload = typeof window.can === 'function'
            ? window.can('op:bom-welding-unit-price-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('weldingUnitPriceUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('weldingUnitPriceUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('weldingUnitPriceUploadResetBtn')?.classList.add('hidden');
        document.getElementById('weldingUnitPriceUploadTemplateBtn')?.classList.add('hidden');

        const fileInput = document.getElementById('weldingUnitPriceUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        ['weldingUnitPriceUploadLocation', 'weldingUnitPriceUploadYear'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });

        const zone = document.getElementById('weldingUnitPriceUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');

        const title = document.getElementById('weldingUnitPriceUploadTitle');
        const hint = document.getElementById('weldingUnitPriceUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const zone = document.getElementById('weldingUnitPriceUploadZone');
        const fileInput = document.getElementById('weldingUnitPriceUploadFileInput');
        const form = document.getElementById('weldingUnitPriceUploadForm');
        const selectBtn = document.getElementById('weldingUnitPriceUploadSelectFileBtn');
        const resetBtn = document.getElementById('weldingUnitPriceUploadResetBtn');
        const templateBtn = document.getElementById('weldingUnitPriceUploadTemplateBtn');

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
        templateBtn?.addEventListener('click', () => this.downloadTemplate());

        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });
    },

    fillDefaultYear() {
        const yearInput = document.getElementById('weldingUnitPriceUploadYear');
        if (yearInput && !yearInput.value) {
            yearInput.value = String(new Date().getFullYear());
        }
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        if (!file.name.toLowerCase().endsWith('.xlsx')) {
            showToast('仅支持 .xlsx 文件', 'warning');
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            showToast('文件过大，最大支持 5MB', 'warning');
            return;
        }

        this.hideProgress();
        this.selectedFile = file;

        const preview = document.getElementById('weldingUnitPriceUploadFilePreview');
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

        const title = document.getElementById('weldingUnitPriceUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;

        const submitBtn = document.getElementById('weldingUnitPriceUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('weldingUnitPriceUploadFileInput');
        if (input) input.value = '';

        const preview = document.getElementById('weldingUnitPriceUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }

        if (resetTitle) {
            const title = document.getElementById('weldingUnitPriceUploadTitle');
            if (title) title.textContent = '拖拽文件到此处';
        }

        const submitBtn = document.getElementById('weldingUnitPriceUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
        const location = document.getElementById('weldingUnitPriceUploadLocation');
        const year = document.getElementById('weldingUnitPriceUploadYear');
        if (location) location.value = '';
        if (year) year.value = '';
        this.fillDefaultYear();
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        const idle = document.getElementById('weldingUnitPriceUploadDropIdle');
        const panel = document.getElementById('weldingUnitPriceUploadProgressPanel');
        const zone = document.getElementById('weldingUnitPriceUploadZone');
        const progressMsg = document.getElementById('weldingUnitPriceUploadProgressMsg');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        if (progressMsg) progressMsg.textContent = msg;
    },

    hideProgress() {
        const idle = document.getElementById('weldingUnitPriceUploadDropIdle');
        const panel = document.getElementById('weldingUnitPriceUploadProgressPanel');
        const zone = document.getElementById('weldingUnitPriceUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('weldingUnitPriceUploadSubmitBtn');
        const resetBtn = document.getElementById('weldingUnitPriceUploadResetBtn');
        const templateBtn = document.getElementById('weldingUnitPriceUploadTemplateBtn');
        const location = document.getElementById('weldingUnitPriceUploadLocation');
        const year = document.getElementById('weldingUnitPriceUploadYear');
        if (submitBtn) submitBtn.disabled = isUploading || !this.selectedFile;
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
        if (location && this.canUpload) location.disabled = isUploading;
        if (year && this.canUpload) year.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                defaultFilename: '焊接单价导入模板.xlsx',
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

        const location = document.getElementById('weldingUnitPriceUploadLocation')?.value?.trim();
        const yearRaw = document.getElementById('weldingUnitPriceUploadYear')?.value?.trim();

        if (!location) {
            showToast('请选择采购基地', 'warning');
            return;
        }
        if (!yearRaw || !/^\d{4}$/.test(yearRaw)) {
            showToast('请填写正确的年度（4位年份）', 'warning');
            return;
        }
        if (!this.selectedFile) {
            showToast('请选择 Excel 文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('location', location);
        formData.append('year', yearRaw);
        formData.append('file', this.selectedFile);

        this.setUploading(true);
        this.showProgress();

        try {
            const res = await HttpClient.post(`${API_BASE}/upload`, formData);
            const data = res.data || {};
            const msg = res.message
                || data.message
                || `导入成功：新增 ${data.created_count ?? 0}，更新 ${data.updated_count ?? 0}`;
            showToast(msg, 'success');
            this.hideProgress();
            this.clearSelectedFile(true);
        } catch (err) {
            this.hideProgress();
            showToast(err.message || '导入失败', 'error');
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
    render: weldingUnitPriceUploadTemplate,
    init: () => WeldingUnitPriceUploadPage.init(),
};
