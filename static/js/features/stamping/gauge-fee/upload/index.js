/**
 * 冲压检具费同步上传
 */

import { gaugeFeeUploadTemplate } from './template.js?v=5';
import { setDropzoneDragActive } from '../../../../upload-dropzone.js?v=1';

const API_BASE = '/api/stamping/gauge-fees';

const GaugeFeeUploadPage = {
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
        this.loadFilters();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function' ? can('op:stamping-gauge-fee-upload:upload') : true;
        this.canUpload = canUpload;
        if (canUpload) return;
        ['gfuSelectFileBtn', 'gfuSubmitBtn', 'gfuResetBtn'].forEach((id) => {
            document.getElementById(id)?.classList.add('hidden');
        });
        const fileInput = document.getElementById('gfuFileInput');
        if (fileInput) fileInput.disabled = true;
        document.getElementById('gfuZone')?.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('gfuTitle');
        const hint = document.getElementById('gfuHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页';
    },

    bindEvents() {
        const zone = document.getElementById('gfuZone');
        const fileInput = document.getElementById('gfuFileInput');
        document.getElementById('gfuTemplateBtn')?.addEventListener('click', () => this.downloadTemplate());
        document.getElementById('gfuResetBtn')?.addEventListener('click', () => this.reset());
        document.getElementById('gfuLocation')?.addEventListener('change', () => this.loadFilters(true));
        document.getElementById('gfuSelectFileBtn')?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (!this.canUpload || this.isUploading) return;
            fileInput?.click();
        });
        zone?.addEventListener('click', (event) => {
            if (!this.canUpload || this.isUploading) return;
            if (event.target.closest('button')) return;
            fileInput?.click();
        });
        fileInput?.addEventListener('change', () => this.selectFile(fileInput.files?.[0]));
        zone?.addEventListener('dragover', (event) => {
            if (!this.canUpload || this.isUploading) return;
            event.preventDefault();
            setDropzoneDragActive(zone, true);
        });
        zone?.addEventListener('dragleave', () => setDropzoneDragActive(zone, false));
        zone?.addEventListener('drop', (event) => {
            event.preventDefault();
            setDropzoneDragActive(zone, false);
            if (!this.canUpload || this.isUploading) return;
            this.selectFile(event.dataTransfer?.files?.[0]);
        });
        document.getElementById('gfuForm')?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });
    },

    fillSelect(id, values, placeholder) {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        const options = [`<option value="">${esc(placeholder)}</option>`];
        (values || []).forEach((value) => {
            const text = String(value);
            options.push(
                `<option value="${esc(text)}"${text === current ? ' selected' : ''}>${esc(text)}</option>`
            );
        });
        select.innerHTML = options.join('');
    },

    async loadFilters(resetVehicle = false) {
        const location = document.getElementById('gfuLocation')?.value || '';
        if (resetVehicle) {
            const vehicle = document.getElementById('gfuVehicle');
            if (vehicle) vehicle.value = '';
        }
        const res = await HttpClient.get(`${API_BASE}/filters`, {
            params: location ? { location } : {},
        });
        const data = res.data || {};
        this.fillSelect('gfuLocation', data.locations || [], '请选择采购基地');
        if (location) {
            const locEl = document.getElementById('gfuLocation');
            if (locEl) locEl.value = location;
        }
        this.fillSelect(
            'gfuVehicle',
            data.vehicle_models || [],
            location ? '请选择项目' : '请先选择基地'
        );
    },

    scope() {
        return {
            location: document.getElementById('gfuLocation')?.value?.trim() || '',
            vehicleModel: document.getElementById('gfuVehicle')?.value?.trim() || '',
        };
    },

    selectFile(file) {
        if (!file) return;
        if (!String(file.name).toLowerCase().endsWith('.xlsx')) {
            showToast('仅支持 .xlsx 文件', 'warning');
            return;
        }
        this.selectedFile = file;
        const preview = document.getElementById('gfuFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `<p class="text-[11px] text-[#9e9e9e]">已选：${esc(file.name)}</p>`;
        }
        const submitBtn = document.getElementById('gfuSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetInput) {
        this.selectedFile = null;
        const preview = document.getElementById('gfuFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        if (resetInput) {
            const input = document.getElementById('gfuFileInput');
            if (input) input.value = '';
        }
        const submitBtn = document.getElementById('gfuSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        const idle = document.getElementById('gfuDropIdle');
        const panel = document.getElementById('gfuProgressPanel');
        const zone = document.getElementById('gfuZone');
        const progressMsg = document.getElementById('gfuProgressMsg');
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
        document.getElementById('gfuZone')?.classList.remove('pointer-events-none');
    },

    hideProgress() {
        const idle = document.getElementById('gfuDropIdle');
        const panel = document.getElementById('gfuProgressPanel');
        const zone = document.getElementById('gfuZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        ['gfuLocation', 'gfuVehicle', 'gfuTemplateBtn', 'gfuResetBtn', 'gfuSubmitBtn'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = isUploading || (id === 'gfuSubmitBtn' && !this.selectedFile);
        });
    },

    async downloadTemplate() {
        const { location, vehicleModel } = this.scope();
        if (!location || !vehicleModel) {
            showToast('请先选择基地和项目', 'warning');
            return;
        }
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                params: { location, vehicle_model: vehicleModel },
                defaultFilename: '冲压检具费导入模板.xlsx',
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

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
        this.loadFilters();
    },

    async submit() {
        if (!this.canUpload || this.isUploading) return;
        const { location, vehicleModel } = this.scope();
        if (!location || !vehicleModel) {
            showToast('请选择基地和项目', 'warning');
            return;
        }
        if (!this.selectedFile) {
            showToast('请选择 Excel 文件', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('location', location);
        formData.append('vehicle_model', vehicleModel);
        formData.append('file', this.selectedFile);
        this.setUploading(true);
        this.showProgress();
        try {
            const res = await HttpClient.post(`${API_BASE}/upload`, formData, { skipToast: true });
            showToast(res.message || res.data?.message || '导入成功', 'success');
            this.hideProgress();
            this.clearSelectedFile(true);
        } catch (err) {
            this.failOnPanel(err.message || '导入失败');
        } finally {
            this.setUploading(false);
        }
    },
};

export const pageConfig = {
    render: gaugeFeeUploadTemplate,
    init: () => GaugeFeeUploadPage.init(),
};
