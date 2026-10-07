/**
 * 年度零件价上传页
 * 下载模板：基地 + 项目 + 年度；导入：基地 + 年度
 */

import { annualPartPriceUploadTemplate } from './template.js?v=24';
import { bindSyncUploadProgress } from '../../../../ui/sync-upload-progress.js?v=3';

const API_BASE = '/api/bom/annual-part-price';
const CASCADE_API = '/api/bom/filters/cascade';

const uploadProgress = bindSyncUploadProgress({
    zoneId: 'annualPartPriceUploadZone',
    idleId: 'annualPartPriceUploadDropIdle',
    panelId: 'annualPartPriceUploadProgressPanel',
    iconId: 'annualPartPriceUploadProgressIcon',
    titleId: 'annualPartPriceUploadProgressTitle',
    barId: 'annualPartPriceUploadProgressBar',
    msgId: 'annualPartPriceUploadProgressMsg',
    runningTitle: '正在导入年度零件价...',
});
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const AnnualPartPriceUploadPage = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,
    hasBomOptions: false,
    locations: [],
    vehicleModels: [],

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
        this.loadCascadeFilters();
    },

    applyPermissionUi() {
        const canUpload = typeof window.can === 'function'
            ? window.can('op:bom-annual-part-price-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('annualPartPriceUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('annualPartPriceUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('annualPartPriceUploadResetBtn')?.classList.add('hidden');
        document.getElementById('annualPartPriceUploadTemplateBtn')?.classList.add('hidden');

        const fileInput = document.getElementById('annualPartPriceUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        ['annualPartPriceUploadLocation', 'annualPartPriceUploadVehicleModel', 'annualPartPriceUploadYear'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });

        const zone = document.getElementById('annualPartPriceUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');

        const title = document.getElementById('annualPartPriceUploadTitle');
        const hint = document.getElementById('annualPartPriceUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const zone = document.getElementById('annualPartPriceUploadZone');
        const fileInput = document.getElementById('annualPartPriceUploadFileInput');
        const form = document.getElementById('annualPartPriceUploadForm');
        const selectBtn = document.getElementById('annualPartPriceUploadSelectFileBtn');
        const resetBtn = document.getElementById('annualPartPriceUploadResetBtn');
        const templateBtn = document.getElementById('annualPartPriceUploadTemplateBtn');

        document.getElementById('annualPartPriceUploadLocation')?.addEventListener('change', () => {
            this.loadCascadeFilters({ clearVehicleModel: true });
        });

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
            zone.classList.add('border-brand');
        });
        zone?.addEventListener('dragleave', () => {
            zone.classList.remove('border-brand');
        });
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
        const location = this.val('annualPartPriceUploadLocation');
        let vehicleModel = clearVehicleModel ? '' : this.val('annualPartPriceUploadVehicleModel');
        try {
            const params = { status: '__all__' };
            if (location) params.location = location;
            if (vehicleModel) params.vehicle_model = vehicleModel;
            const res = await HttpClient.get(CASCADE_API, { params });
            const data = res.data || {};
            const locations = Array.isArray(data.locations) ? data.locations : [];
            const vehicleModels = Array.isArray(data.vehicle_models) ? data.vehicle_models : [];

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
                this.fillSelect('annualPartPriceUploadLocation', locations, locations[0], '请选择采购基地');
                return this.loadCascadeFilters({ clearVehicleModel: true });
            }
            if (location && !vehicleModel && vehicleModels.length === 1) {
                vehicleModel = vehicleModels[0];
            }

            this.fillSelect(
                'annualPartPriceUploadLocation',
                locations,
                location && locations.includes(location) ? location : '',
                locations.length ? '请选择采购基地' : '暂无材料清单基地',
            );
            this.fillSelect(
                'annualPartPriceUploadVehicleModel',
                location ? vehicleModels : [],
                vehicleModel,
                location
                    ? (vehicleModels.length ? '请选择项目' : '该基地暂无项目')
                    : '请先选择采购基地',
            );
        } catch (error) {
            console.error('加载材料清单基地/项目失败', error);
            this.hasBomOptions = false;
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

        const preview = document.getElementById('annualPartPriceUploadFilePreview');
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

        const title = document.getElementById('annualPartPriceUploadTitle');
        if (title) title.innerHTML = `<span class="text-ok">${esc(file.name)}</span> 已选择`;

        const submitBtn = document.getElementById('annualPartPriceUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('annualPartPriceUploadFileInput');
        if (input) input.value = '';

        const preview = document.getElementById('annualPartPriceUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }

        if (resetTitle) {
            const title = document.getElementById('annualPartPriceUploadTitle');
            if (title) title.textContent = '拖拽文件到此处';
        }

        const submitBtn = document.getElementById('annualPartPriceUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            showToast('导入进行中，请稍候再重置', 'warning');
            return;
        }
        this.hideProgress();
        this.clearSelectedFile(true);
        const location = document.getElementById('annualPartPriceUploadLocation');
        const year = document.getElementById('annualPartPriceUploadYear');
        if (location) location.value = '';
        const vehicleModel = document.getElementById('annualPartPriceUploadVehicleModel');
        if (vehicleModel) vehicleModel.value = '';
        if (year) year.value = '';
        this.loadCascadeFilters({ clearVehicleModel: true });
    },

    showProgress(msg = '解析并写入数据库，请稍候') {
        uploadProgress.setRunning(msg);
        document.getElementById('annualPartPriceUploadZone')?.classList.remove('border-brand');
    },

    showDoneOnPanel(message, opts = {}) {
        uploadProgress.setDone(message, opts);
    },

    failOnPanel(message) {
        uploadProgress.setFail(message);
    },

    hideProgress() {
        uploadProgress.hide();
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('annualPartPriceUploadSubmitBtn');
        const resetBtn = document.getElementById('annualPartPriceUploadResetBtn');
        const templateBtn = document.getElementById('annualPartPriceUploadTemplateBtn');
        const location = document.getElementById('annualPartPriceUploadLocation');
        const vehicleModel = document.getElementById('annualPartPriceUploadVehicleModel');
        const year = document.getElementById('annualPartPriceUploadYear');
        if (submitBtn) submitBtn.disabled = isUploading || !this.selectedFile;
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
        if (location && this.canUpload) location.disabled = isUploading;
        if (vehicleModel && this.canUpload) vehicleModel.disabled = isUploading;
        if (year && this.canUpload) year.disabled = isUploading;
    },

    async downloadTemplate() {
        const location = this.val('annualPartPriceUploadLocation');
        const vehicleModel = this.val('annualPartPriceUploadVehicleModel');
        const yearRaw = this.val('annualPartPriceUploadYear');
        if (!location) {
            showToast('请先选择采购基地', 'warning');
            return;
        }
        if (!vehicleModel) {
            showToast('请先选择项目', 'warning');
            return;
        }
        if (!yearRaw || !/^\d{4}$/.test(yearRaw)) {
            showToast('请填写正确的年度（4位年份）', 'warning');
            return;
        }
        try {
            const { blob, filename } = await HttpClient.download(`${API_BASE}/template`, {
                params: { location, vehicle_model: vehicleModel, year: yearRaw },
                defaultFilename: `年度零件价导入模板_${location}_${vehicleModel}_${yearRaw}.xlsx`,
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
        if (this.isUploading) return;

        const location = document.getElementById('annualPartPriceUploadLocation')?.value?.trim();
        const yearRaw = document.getElementById('annualPartPriceUploadYear')?.value?.trim();

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
            const created = data.created_count ?? 0;
            const updated = data.updated_count ?? 0;
            const skippedApproved = data.skipped_approved_count ?? 0;
            const written = created + updated;
            let msg = res.message || data.message || `导入成功：新增 ${created}，更新 ${updated}`;
            if (written === 0 && skippedApproved > 0) {
                msg = `更新 0 条：这 ${skippedApproved} 条已审核，导入不会覆盖。如需改价请先在列表反审核。`;
            } else if (skippedApproved > 0) {
                msg = `导入完成：新增 ${created} 条，更新 ${updated} 条；另有 ${skippedApproved} 条已审核未覆盖。`;
            }
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
    render: annualPartPriceUploadTemplate,
    init: () => AnnualPartPriceUploadPage.init(),
};
