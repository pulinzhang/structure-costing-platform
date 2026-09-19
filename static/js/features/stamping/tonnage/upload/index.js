/**
 * 冲次单价上传页
 * 同步导入：基地 + 年度必选，仅 .xlsx
 */

import { tonnageUploadTemplate } from './template.js?v=7';
import { can } from '../../../../permissions.js?v=8';

const API_BASE = '/api/stamping/tonnage-price';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const TonnageUploadPage = {
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
        this.loadLocationOptions();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:stamping-tonnage-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('tonnageUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('tonnageUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('tonnageUploadResetBtn')?.classList.add('hidden');
        document.getElementById('tonnageUploadTemplateBtn')?.classList.add('hidden');

        const fileInput = document.getElementById('tonnageUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        ['tonnageUploadLocation', 'tonnageUploadYear'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });

        const zone = document.getElementById('tonnageUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');

        const title = document.getElementById('tonnageUploadTitle');
        const hint = document.getElementById('tonnageUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    async loadLocationOptions() {
        try {
            const res = await HttpClient.get(`${API_BASE}/filters/locations`);
            const data = res && res.data;
            const locations = Array.isArray(data)
                ? data
                : (data && Array.isArray(data.locations) ? data.locations : []);
            const el = document.getElementById('tonnageUploadLocation');
            if (!el) return;
            const current = el.value;
            el.innerHTML = '<option value="">请选择采购基地</option>' +
                locations.map((loc) => `<option value="${esc(loc)}">${esc(loc)}</option>`).join('');
            if (current) el.value = current;
        } catch (error) {
            console.error('加载采购基地失败', error);
        }
    },

    bindEvents() {
        const zone = document.getElementById('tonnageUploadZone');
        const fileInput = document.getElementById('tonnageUploadFileInput');
        const form = document.getElementById('tonnageUploadForm');
        const selectBtn = document.getElementById('tonnageUploadSelectFileBtn');
        const resetBtn = document.getElementById('tonnageUploadResetBtn');
        const templateBtn = document.getElementById('tonnageUploadTemplateBtn');

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

        const preview = document.getElementById('tonnageUploadFilePreview');
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

        const title = document.getElementById('tonnageUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;

        const submitBtn = document.getElementById('tonnageUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('tonnageUploadFileInput');
        if (input) input.value = '';

        const preview = document.getElementById('tonnageUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }

        if (resetTitle) {
            const title = document.getElementById('tonnageUploadTitle');
            if (title) title.textContent = '拖拽文件到此处';
        }

        const submitBtn = document.getElementById('tonnageUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
        const location = document.getElementById('tonnageUploadLocation');
        const year = document.getElementById('tonnageUploadYear');
        if (location) location.value = '';
        if (year) year.value = '';
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        const idle = document.getElementById('tonnageUploadDropIdle');
        const panel = document.getElementById('tonnageUploadProgressPanel');
        const zone = document.getElementById('tonnageUploadZone');
        const progressMsg = document.getElementById('tonnageUploadProgressMsg');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        if (progressMsg) progressMsg.textContent = msg;
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(text);
        document.getElementById('tonnageUploadZone')?.classList.remove('pointer-events-none');
    },

    hideProgress() {
        const idle = document.getElementById('tonnageUploadDropIdle');
        const panel = document.getElementById('tonnageUploadProgressPanel');
        const zone = document.getElementById('tonnageUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('tonnageUploadSubmitBtn');
        const resetBtn = document.getElementById('tonnageUploadResetBtn');
        const templateBtn = document.getElementById('tonnageUploadTemplateBtn');
        const location = document.getElementById('tonnageUploadLocation');
        const year = document.getElementById('tonnageUploadYear');
        if (submitBtn) submitBtn.disabled = isUploading || !this.selectedFile;
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
        if (location && this.canUpload) location.disabled = isUploading;
        if (year && this.canUpload) year.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                defaultFilename: '冲次单价导入模板.xlsx',
                skipToast: true,
            });
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            this.failOnPanel(error.message || '模板下载失败');
        }
    },

    async submit() {
        if (this.canUpload === false) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (this.isUploading) return;

        const location = document.getElementById('tonnageUploadLocation')?.value?.trim();
        const yearRaw = document.getElementById('tonnageUploadYear')?.value?.trim();

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
            const res = await HttpClient.post(`${API_BASE}/upload`, formData, { skipToast: true });
            const data = res.data || {};
            const msg = res.message
                || data.message
                || `导入成功：新增 ${data.created_count ?? 0}，更新 ${data.updated_count ?? 0}`;
            showToast(msg, 'success');
            this.hideProgress();
            this.clearSelectedFile(true);
        } catch (err) {
            this.failOnPanel(err.message || '导入失败');
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
    render: tonnageUploadTemplate,
    init: () => TonnageUploadPage.init(),
};
