/**
 * 包装运输费上传页
 * 同步导入：基地 + 年度 + 项目必选；基地/项目取自材料清单（BOM）
 */

import { pkgTransportFeeUploadTemplate } from './template.js?v=16';
import { bindSyncUploadProgress } from '../../../../ui/sync-upload-progress.js?v=3';

const API_BASE = '/api/bom/packaging-transport-fee';
const CASCADE_API = '/api/bom/filters/cascade';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const uploadProgress = bindSyncUploadProgress({
    zoneId: 'pkgTransportFeeUploadZone',
    idleId: 'pkgTransportFeeUploadDropIdle',
    panelId: 'pkgTransportFeeUploadProgressPanel',
    iconId: 'pkgTransportFeeUploadProgressIcon',
    titleId: 'pkgTransportFeeUploadProgressTitle',
    barId: 'pkgTransportFeeUploadProgressBar',
    msgId: 'pkgTransportFeeUploadProgressMsg',
    runningTitle: '正在导入包装运输费...',
});
const MAX_RECENT_UPLOADS = 8;

const PkgTransportFeeUploadPage = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,
    hasBomOptions: false,
    locations: [],
    vehicleModels: [],
    recentUploads: [],

    init() {
        this.selectedFile = null;
        this.isUploading = false;
        this.hasBomOptions = false;
        this.locations = [];
        this.vehicleModels = [];
        this.applyPermissionUi();
        this.bindEvents();
        this.hideProgress();
        this.clearSelectedFile(false);
        this.renderRecentUploads();
        this.loadCascadeFilters();
    },

    applyPermissionUi() {
        const canUpload = typeof window.can === 'function'
            ? window.can('op:bom-packaging-transport-fee-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        ['pkgTransportFeeUploadSelectFileBtn', 'pkgTransportFeeUploadSubmitBtn', 'pkgTransportFeeUploadResetBtn', 'pkgTransportFeeUploadTemplateBtn']
            .forEach((id) => document.getElementById(id)?.classList.add('hidden'));
        const fileInput = document.getElementById('pkgTransportFeeUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        ['pkgTransportFeeUploadLocation', 'pkgTransportFeeUploadYear', 'pkgTransportFeeUploadVehicleModel'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
        document.getElementById('pkgTransportFeeUploadZone')?.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('pkgTransportFeeUploadTitle');
        const hint = document.getElementById('pkgTransportFeeUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const zone = document.getElementById('pkgTransportFeeUploadZone');
        const fileInput = document.getElementById('pkgTransportFeeUploadFileInput');
        const form = document.getElementById('pkgTransportFeeUploadForm');
        const selectBtn = document.getElementById('pkgTransportFeeUploadSelectFileBtn');
        const resetBtn = document.getElementById('pkgTransportFeeUploadResetBtn');
        const templateBtn = document.getElementById('pkgTransportFeeUploadTemplateBtn');

        document.getElementById('pkgTransportFeeUploadLocation')?.addEventListener('change', () => {
            this.loadCascadeFilters({ clearVehicleModel: true });
        });
        document.getElementById('pkgTransportFeeUploadYear')?.addEventListener('input', () => {
            this.loadCascadeFilters({ clearVehicleModel: true });
        });
        document.getElementById('pkgTransportFeeUploadVehicleModel')?.addEventListener('change', () => {
            this.refreshSubmitState();
        });

        zone?.addEventListener('click', (event) => {
            if (this.canUpload === false || this.isUploading || !this.hasBomOptions) return;
            if (event.target.closest('button')) return;
            fileInput?.click();
        });
        selectBtn?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (this.canUpload === false || this.isUploading || !this.hasBomOptions) return;
            fileInput?.click();
        });
        fileInput?.addEventListener('change', () => this.selectFile(fileInput.files?.[0]));
        zone?.addEventListener('dragover', (event) => {
            if (this.canUpload === false || this.isUploading || !this.hasBomOptions) return;
            event.preventDefault();
            zone.classList.add('border-brand');
        });
        zone?.addEventListener('dragleave', () => zone.classList.remove('border-brand'));
        zone?.addEventListener('drop', (event) => {
            event.preventDefault();
            zone.classList.remove('border-brand');
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

    val(id) {
        return (document.getElementById(id)?.value || '').trim();
    },

    parseScopeYear() {
        const yearRaw = this.val('pkgTransportFeeUploadYear');
        if (!/^\d{4}$/.test(yearRaw)) return null;
        const year = Number(yearRaw);
        if (year < 2000 || year > 2100) return null;
        return year;
    },

    vehicleEmptyLabel(location, year) {
        if (!location) return '请先选择采购基地';
        if (year == null) return '请先填写年度';
        if (!this.vehicleModels.length) return '这一年和项目的有效期对不上';
        return '请选择项目';
    },

    fillSelect(id, values, selected, emptyLabel) {
        const el = document.getElementById(id);
        if (!el) return;
        let html = `<option value="">${esc(emptyLabel)}</option>`;
        (values || []).forEach((item) => {
            const mark = item === selected ? ' selected' : '';
            html += `<option value="${esc(item)}"${mark}>${esc(item)}</option>`;
        });
        el.innerHTML = html;
        if (selected && (values || []).includes(selected)) {
            el.value = selected;
        } else {
            el.value = '';
        }
    },

    async loadCascadeFilters({ clearVehicleModel = false } = {}) {
        const location = this.val('pkgTransportFeeUploadLocation');
        const year = this.parseScopeYear();
        let vehicleModel = clearVehicleModel ? '' : this.val('pkgTransportFeeUploadVehicleModel');
        try {
            const params = { status: '__all__' };
            if (location) params.location = location;
            if (year != null) params.year = year;
            const res = await HttpClient.get(CASCADE_API, { params });
            const data = res.data || {};
            const locations = Array.isArray(data.locations) ? data.locations : [];
            const vehicleModels = (location && year != null && Array.isArray(data.vehicle_models))
                ? data.vehicle_models
                : [];

            this.locations = locations;
            this.vehicleModels = vehicleModels;
            this.hasBomOptions = locations.length > 0;

            if (location && !locations.includes(location)) {
                vehicleModel = '';
            }
            if (vehicleModel && !vehicleModels.includes(vehicleModel)) {
                vehicleModel = '';
            }
            if (!location && locations.length === 1) {
                this.fillSelect('pkgTransportFeeUploadLocation', locations, locations[0], '请选择采购基地');
                return this.loadCascadeFilters({ clearVehicleModel: true });
            }
            if (location && year != null && !vehicleModel && vehicleModels.length === 1) {
                vehicleModel = vehicleModels[0];
            }

            this.fillSelect(
                'pkgTransportFeeUploadLocation',
                locations,
                location && locations.includes(location) ? location : '',
                locations.length ? '请选择采购基地' : '暂无材料清单基地',
            );
            this.fillSelect(
                'pkgTransportFeeUploadVehicleModel',
                vehicleModels,
                vehicleModel,
                this.vehicleEmptyLabel(location, year),
            );
        } catch (error) {
            console.error('加载材料清单基地/项目失败', error);
            this.locations = [];
            this.vehicleModels = [];
            this.hasBomOptions = false;
            this.fillSelect('pkgTransportFeeUploadLocation', [], '', '加载失败');
            this.fillSelect('pkgTransportFeeUploadVehicleModel', [], '', '请先选择采购基地和年度');
        }
        this.applyBomGateUi();
        this.refreshSubmitState();
    },

    applyBomGateUi() {
        const banner = document.getElementById('pkgTransportFeeUploadNoBomBanner');
        banner?.classList.toggle('hidden', this.hasBomOptions);

        if (!this.canUpload) return;

        const zone = document.getElementById('pkgTransportFeeUploadZone');
        const selectBtn = document.getElementById('pkgTransportFeeUploadSelectFileBtn');
        const fileInput = document.getElementById('pkgTransportFeeUploadFileInput');
        const locationEl = document.getElementById('pkgTransportFeeUploadLocation');
        const vehicleEl = document.getElementById('pkgTransportFeeUploadVehicleModel');

        if (!this.hasBomOptions) {
            zone?.classList.add('pointer-events-none', 'opacity-60');
            if (selectBtn) selectBtn.disabled = true;
            if (fileInput) {
                fileInput.disabled = true;
                fileInput.value = '';
            }
            if (locationEl) locationEl.disabled = true;
            if (vehicleEl) vehicleEl.disabled = true;
            this.clearSelectedFile(true);
            const title = document.getElementById('pkgTransportFeeUploadTitle');
            const hint = document.getElementById('pkgTransportFeeUploadHint');
            if (title) title.textContent = '请先上传材料清单';
            if (hint) hint.textContent = '基地 / 项目来自 BOM，无清单时不可导入包装运输费';
            return;
        }

        zone?.classList.remove('pointer-events-none', 'opacity-60');
        if (selectBtn) selectBtn.disabled = false;
        if (fileInput) fileInput.disabled = false;
        if (locationEl && !this.isUploading) locationEl.disabled = false;
        if (vehicleEl && !this.isUploading) {
            vehicleEl.disabled = !this.val('pkgTransportFeeUploadLocation') || this.parseScopeYear() == null;
        }
        if (!this.selectedFile) {
            const title = document.getElementById('pkgTransportFeeUploadTitle');
            const hint = document.getElementById('pkgTransportFeeUploadHint');
            if (title) title.textContent = '拖拽文件到此处';
            if (hint) hint.textContent = '或点击下方按钮选择文件';
        }
    },

    refreshSubmitState() {
        const submitBtn = document.getElementById('pkgTransportFeeUploadSubmitBtn');
        if (!submitBtn) return;
        const location = this.val('pkgTransportFeeUploadLocation');
        const vehicleModel = this.val('pkgTransportFeeUploadVehicleModel');
        const ready = this.canUpload
            && this.hasBomOptions
            && !!location
            && !!vehicleModel
            && !!this.selectedFile
            && !this.isUploading;
        submitBtn.disabled = !ready;
    },

    selectFile(file) {
        if (!file || this.isUploading || !this.hasBomOptions) return;
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
        const preview = document.getElementById('pkgTransportFeeUploadFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-app-main border border-line">
                    ${window.svgIcon('file-earmark-excel', 'w-5 h-5 text-ok')}
                    <div class="min-w-0 flex-1">
                        <p class="text-xs text-ink truncate">${esc(file.name)}</p>
                        <p class="text-[10px] text-ink-dim">${this.formatFileSize(file.size)}</p>
                    </div>
                </div>`;
        }
        const title = document.getElementById('pkgTransportFeeUploadTitle');
        if (title) title.innerHTML = `<span class="text-ok">${esc(file.name)}</span> 已选择`;
        this.refreshSubmitState();
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('pkgTransportFeeUploadFileInput');
        if (input) input.value = '';
        const preview = document.getElementById('pkgTransportFeeUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        if (resetTitle && this.hasBomOptions) {
            const title = document.getElementById('pkgTransportFeeUploadTitle');
            const hint = document.getElementById('pkgTransportFeeUploadHint');
            if (title) title.textContent = '拖拽文件到此处';
            if (hint) hint.textContent = '或点击下方按钮选择文件';
        }
        this.refreshSubmitState();
    },

    addRecentUpload(fileName, location, year, vehicleModel, summary) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
        this.recentUploads.unshift({
            fileName,
            scopeLabel: `${location} · ${year} · ${vehicleModel}`,
            timeLabel,
            summary: summary || '',
        });
        if (this.recentUploads.length > MAX_RECENT_UPLOADS) {
            this.recentUploads = this.recentUploads.slice(0, MAX_RECENT_UPLOADS);
        }
        this.renderRecentUploads();
    },

    renderRecentUploads() {
        const container = document.getElementById('pkgTransportFeeRecentUploads');
        if (!container) return;

        if (this.recentUploads.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="w-8 h-8 bg-app-surface border border-line flex items-center justify-center mx-auto mb-2.5">
                        <svg class="w-4 h-4 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                    </div>
                    <p class="text-[10px] text-ink-faint">暂无上传记录</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="space-y-2">
                ${this.recentUploads.map((item) => `
                    <div class="flex items-start gap-2.5 p-2.5 bg-app-main border border-line">
                        <span class="text-ok shrink-0 mt-0.5">${window.svgIcon('file-earmark-excel', 'w-4 h-4')}</span>
                        <div class="min-w-0 flex-1">
                            <p class="text-[11px] text-ink truncate" title="${esc(item.fileName)}">${esc(item.fileName)}</p>
                            <p class="text-[10px] text-ink-dim mt-0.5">${esc(item.scopeLabel)} · ${esc(item.timeLabel)}</p>
                            ${item.summary ? `<p class="text-[10px] text-ink-muted mt-0.5">${esc(item.summary)}</p>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
        const yearEl = document.getElementById('pkgTransportFeeUploadYear');
        if (yearEl) yearEl.value = '';
        this.fillSelect('pkgTransportFeeUploadLocation', this.locations, '', this.locations.length ? '请选择采购基地' : '暂无材料清单基地');
        this.fillSelect('pkgTransportFeeUploadVehicleModel', [], '', '请先选择采购基地和年度');
        this.loadCascadeFilters({ clearVehicleModel: true });
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        uploadProgress.setRunning(msg);
    },

    showDoneOnPanel(message, opts = {}) {
        uploadProgress.setDone(message, opts);
        this.lockZoneIfNeeded();
    },

    failOnPanel(message) {
        uploadProgress.setFail(message);
        this.lockZoneIfNeeded();
    },

    hideProgress() {
        uploadProgress.hide();
        this.lockZoneIfNeeded();
    },

    lockZoneIfNeeded() {
        if (this.hasBomOptions && this.canUpload) return;
        document.getElementById('pkgTransportFeeUploadZone')?.classList.add('pointer-events-none');
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        ['pkgTransportFeeUploadResetBtn', 'pkgTransportFeeUploadTemplateBtn'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = isUploading;
        });
        ['pkgTransportFeeUploadLocation', 'pkgTransportFeeUploadYear', 'pkgTransportFeeUploadVehicleModel'].forEach((id) => {
            const el = document.getElementById(id);
            if (el && this.canUpload && this.hasBomOptions) el.disabled = isUploading;
        });
        this.refreshSubmitState();
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                defaultFilename: '包装运输费导入模板.xlsx',
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
            if (error.wechatGuide) return;
            this.failOnPanel(error.message || '模板下载失败');
        }
    },

    async submit() {
        if (this.canUpload === false) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (!this.hasBomOptions) {
            showToast('请先上传材料清单后再导入包装运输费', 'warning');
            return;
        }
        if (this.isUploading) return;

        const location = this.val('pkgTransportFeeUploadLocation');
        const yearRaw = this.val('pkgTransportFeeUploadYear');
        const vehicleModel = this.val('pkgTransportFeeUploadVehicleModel');

        if (!location) {
            showToast('请选择采购基地', 'warning');
            return;
        }
        if (!this.locations.includes(location)) {
            showToast('采购基地不在材料清单中，请重新选择', 'warning');
            return;
        }
        if (!yearRaw || !/^\d{4}$/.test(yearRaw)) {
            showToast('请填写正确的年度（4位年份）', 'warning');
            return;
        }
        if (!vehicleModel) {
            showToast('请选择项目', 'warning');
            return;
        }
        if (!this.vehicleModels.includes(vehicleModel)) {
            showToast('该项目与所选年度无交集，请重新选择', 'warning');
            return;
        }
        if (!this.selectedFile) {
            showToast('请选择 Excel 文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('location', location);
        formData.append('year', yearRaw);
        formData.append('vehicle_model', vehicleModel);
        formData.append('file', this.selectedFile);

        this.setUploading(true);
        this.showProgress();
        try {
            const res = await HttpClient.post(`${API_BASE}/upload`, formData, { skipToast: true });
            const data = res.data || {};
            const skippedApproved = data.skipped_approved_count ?? 0;
            const summary = `新增 ${data.created_count ?? 0}，更新 ${data.updated_count ?? 0}`
                + (skippedApproved ? `，跳过已审 ${skippedApproved}` : '');
            const msg = res.message || data.message || `导入成功：${summary}`;
            this.addRecentUpload(
                this.selectedFile.name,
                location,
                yearRaw,
                vehicleModel,
                summary,
            );
            this.showDoneOnPanel(msg, { hasSkip: skippedApproved > 0 });
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
    render: pkgTransportFeeUploadTemplate,
    init: () => PkgTransportFeeUploadPage.init(),
};
