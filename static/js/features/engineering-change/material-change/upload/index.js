/**
 * 材料变更上传页
 */

import { materialChangeUploadTemplate } from './template.js?v=10';
import { copyElementText } from '../../../../ui/copy-text.js?v=3';
import { uploadSubmitLabelHtml } from '../../../../ui/upload-actions.js?v=2';
import { can } from '../../../../core/permissions.js?v=8';
import {
    setDropzoneDragActive,
    setDropzoneFileSelected,
} from '../../../../ui/upload-dropzone.js?v=3';
import { fillAsOfSelects } from '../../../common/period-ui.js?v=7';

const POLL_INTERVAL_MS = 2000;
const MAX_RECENT_UPLOADS = 8;
const API = '/api/engineering-change/material';

const MaterialChangeUploadPage = {
    selectedFile: null,
    isUploading: false,
    pollTimer: null,
    pollInFlight: false,
    activeTaskId: null,
    activeFileName: null,
    activeScope: null,
    recentUploads: [],
    canUpload: true,

    init() {
        this.stopPolling();
        this.applyPermissionUi();
        this.bindEvents();
        this.hideError();
        this.renderRecentUploads();
        this.fillPeriodSelects();
        this.loadScopeOptions();
        if (this.isUploading && this.activeTaskId) {
            this.setUploading(true);
            this.showProgress(0, '正在恢复任务进度...');
            this.startPolling(this.activeTaskId, this.activeFileName, this.activeScope);
        }
    },

    destroy() {
        this.stopPolling();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:engineering-change-material-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;
        ['ecmUploadSelectFileBtn', 'ecmUploadSubmitBtn', 'ecmUploadResetBtn', 'ecmUploadTemplateBtn']
            .forEach((id) => document.getElementById(id)?.classList.add('hidden'));
        ['ecmUploadLocation', 'ecmUploadVehicleModel', 'ecmUploadYear', 'ecmUploadMonth'].forEach((id) => {
            document.getElementById(id)?.setAttribute('disabled', 'disabled');
        });
        document.getElementById('ecmUploadZone')?.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('ecmUploadTitle');
        const hint = document.getElementById('ecmUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页';
    },

    bindEvents() {
        const uploadZone = document.getElementById('ecmUploadZone');
        const fileInput = document.getElementById('ecmUploadFileInput');
        document.getElementById('ecmUploadTemplateBtn')?.addEventListener('click', () => this.downloadTemplate());
        document.getElementById('ecmUploadResetBtn')?.addEventListener('click', () => this.resetForm());
        document.getElementById('ecmUploadLocation')?.addEventListener('change', () => this.loadScopeOptions(true));
        ['ecmUploadYear', 'ecmUploadMonth'].forEach((id) => {
            document.getElementById(id)?.addEventListener('change', () => this.loadScopeOptions(false));
        });
        document.getElementById('ecmUploadSelectFileBtn')?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (!this.canUpload || this.isUploading) return;
            fileInput?.click();
        });
        uploadZone?.addEventListener('click', (event) => {
            if (!this.canUpload || this.isUploading) return;
            if (event.target.tagName === 'BUTTON' || event.target.closest('button')) return;
            fileInput?.click();
        });
        fileInput?.addEventListener('change', (event) => this.handleFiles(event.target.files));
        uploadZone?.addEventListener('dragover', (event) => {
            if (!this.canUpload || this.isUploading) return;
            event.preventDefault();
            setDropzoneDragActive(uploadZone, true);
        });
        uploadZone?.addEventListener('dragleave', (event) => {
            event.preventDefault();
            setDropzoneDragActive(uploadZone, false);
        });
        uploadZone?.addEventListener('drop', (event) => {
            event.preventDefault();
            setDropzoneDragActive(uploadZone, false);
            if (!this.canUpload || this.isUploading) return;
            this.handleFiles(event.dataTransfer.files);
        });
        document.getElementById('ecmUploadForm')?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSubmit();
        });
        document.getElementById('ecmUploadErrorCopyBtn')?.addEventListener('click', (event) => {
            copyElementText(
                document.getElementById('ecmUploadErrorBody'),
                event.currentTarget,
            );
        });
        document.getElementById('ecmUploadErrorCloseBtn')?.addEventListener('click', () => this.hideError());
    },

    fillPeriodSelects() {
        const now = new Date();
        fillAsOfSelects('ecmUpload', now.getFullYear(), now.getMonth() + 1);
    },

    fillSelect(id, values, placeholder, current) {
        const select = document.getElementById(id);
        if (!select) return;
        const options = [`<option value="">${esc(placeholder)}</option>`];
        (values || []).forEach((value) => {
            const text = String(value);
            options.push(`<option value="${esc(text)}"${text === current ? ' selected' : ''}>${esc(text)}</option>`);
        });
        select.innerHTML = options.join('');
        if (current) select.value = current;
    },

    async loadScopeOptions(resetVehicle = false) {
        const location = document.getElementById('ecmUploadLocation')?.value || '';
        const keptVehicle = resetVehicle
            ? ''
            : (document.getElementById('ecmUploadVehicleModel')?.value || '');
        const year = Number(document.getElementById('ecmUploadYear')?.value) || new Date().getFullYear();
        const month = Number(document.getElementById('ecmUploadMonth')?.value) || (new Date().getMonth() + 1);
        try {
            const params = { year, month };
            if (location) params.location = location;
            const res = await HttpClient.get('/api/bom/filters/cascade', { skipToast: true, params });
            const data = res && res.data;
            const locations = Array.isArray(data)
                ? data
                : (data && Array.isArray(data.locations) ? data.locations : []);
            const vehicles = location && data && Array.isArray(data.vehicle_models)
                ? data.vehicle_models
                : [];
            this.fillSelect('ecmUploadLocation', locations, '请选择采购基地', location);
            const vehiclePlaceholder = location
                ? (vehicles.length ? '请选择项目' : '这个月没有可以上传的项目')
                : '请先选择采购基地';
            const currentVehicle = vehicles.includes(keptVehicle) ? keptVehicle : '';
            this.fillSelect('ecmUploadVehicleModel', vehicles, vehiclePlaceholder, currentVehicle);
        } catch (error) {
            this.failOnPanel(error?.message || '加载基地项目失败');
        }
    },

    handleFiles(files) {
        if (!this.canUpload) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (!files || files.length === 0 || this.isUploading) return;
        const file = files[0];
        const ext = `.${file.name.split('.').pop().toLowerCase()}`;
        if (ext !== '.xlsx') {
            showToast('只收 .xlsx 文件', 'warning');
            return;
        }
        this.hideProgress();
        this.hideError();
        this.selectedFile = file;
        const preview = document.getElementById('ecmFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `<div class="text-xs text-ink truncate p-3 border border-line">${esc(file.name)}</div>`;
        }
        setDropzoneFileSelected(document.getElementById('ecmUploadZone'), true);
        const title = document.getElementById('ecmUploadTitle');
        const hint = document.getElementById('ecmUploadHint');
        if (title) title.textContent = '已选择文件';
        if (hint) hint.textContent = file.name;
        const submitBtn = document.getElementById('ecmUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile() {
        this.selectedFile = null;
        const fileInput = document.getElementById('ecmUploadFileInput');
        const preview = document.getElementById('ecmFilePreview');
        if (fileInput) fileInput.value = '';
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        setDropzoneFileSelected(document.getElementById('ecmUploadZone'), false);
        const title = document.getElementById('ecmUploadTitle');
        const hint = document.getElementById('ecmUploadHint');
        if (title) title.textContent = '拖拽文件到此处';
        if (hint) hint.textContent = '或点击下方按钮选择文件';
        const submitBtn = document.getElementById('ecmUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    addRecentUpload(fileName, scopeLabel, summary) {
        const timeLabel = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        this.recentUploads.unshift({ fileName, scopeLabel, timeLabel, summary: summary || '' });
        this.recentUploads = this.recentUploads.slice(0, MAX_RECENT_UPLOADS);
        this.renderRecentUploads();
    },

    renderRecentUploads() {
        const container = document.getElementById('ecmRecentUploads');
        if (!container) return;
        if (this.recentUploads.length === 0) {
            container.innerHTML = '<p class="text-[10px] text-ink-faint text-center py-5">暂无上传记录</p>';
            return;
        }
        container.innerHTML = this.recentUploads.map((item) => `
            <div class="mb-2 last:mb-0">
                <p class="text-[11px] text-ink truncate">${esc(item.fileName)}</p>
                <p class="text-[10px] text-ink-dim">${esc(item.scopeLabel)} · ${esc(item.timeLabel)}</p>
            </div>
        `).join('');
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(0, text);
        this.updateProgress(0, text, 'failed');
        this.showError(text);
        document.getElementById('ecmUploadZone')?.classList.remove('pointer-events-none');
    },

    hideError() {
        document.getElementById('ecmUploadErrorPanel')?.classList.add('hidden');
        const body = document.getElementById('ecmUploadErrorBody');
        const copyBtn = document.getElementById('ecmUploadErrorCopyBtn');
        if (body) body.textContent = '';
        if (copyBtn) copyBtn.textContent = '复制';
    },

    showError(message) {
        const panel = document.getElementById('ecmUploadErrorPanel');
        const body = document.getElementById('ecmUploadErrorBody');
        const copyBtn = document.getElementById('ecmUploadErrorCopyBtn');
        const text = String(message || '导入失败').trim() || '导入失败';
        if (!panel || !body) return;
        body.textContent = text;
        if (copyBtn) copyBtn.textContent = '复制';
        panel.classList.remove('hidden');
        showToast(text, 'error');
    },

    showProgress(progress = 0, msg = '正在导入。') {
        document.getElementById('ecmDropIdle')?.classList.add('hidden');
        document.getElementById('ecmProgressPanel')?.classList.remove('hidden');
        document.getElementById('ecmUploadZone')?.classList.add('pointer-events-none');
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        document.getElementById('ecmDropIdle')?.classList.remove('hidden');
        document.getElementById('ecmProgressPanel')?.classList.add('hidden');
        document.getElementById('ecmUploadZone')?.classList.remove('pointer-events-none');
        this.updateProgress(0, '正在导入。');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('ecmProgressBar');
        const percentEl = document.getElementById('ecmProgressPercent');
        const msgEl = document.getElementById('ecmProgressMsg');
        const titleEl = document.getElementById('ecmProgressTitle');
        if (bar) bar.style.width = `${pct}%`;
        if (percentEl) percentEl.textContent = `${pct}%`;
        if (msgEl) msgEl.textContent = msg || '';
        if (titleEl) {
            if (status === 'completed') titleEl.textContent = '解析成功';
            else if (status === 'failed') titleEl.textContent = '解析失败';
            else titleEl.textContent = '正在解析材料变更...';
        }
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('ecmUploadSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = isUploading || !this.selectedFile;
            submitBtn.innerHTML = uploadSubmitLabelHtml(isUploading);
        }
        ['ecmUploadResetBtn', 'ecmUploadLocation', 'ecmUploadVehicleModel', 'ecmUploadYear', 'ecmUploadMonth', 'ecmUploadTemplateBtn']
            .forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.disabled = isUploading;
            });
    },

    async downloadTemplate() {
        const location = document.getElementById('ecmUploadLocation')?.value?.trim();
        const vehicleModel = document.getElementById('ecmUploadVehicleModel')?.value?.trim();
        const year = Number(document.getElementById('ecmUploadYear')?.value);
        const month = Number(document.getElementById('ecmUploadMonth')?.value);
        if (!location || !vehicleModel) {
            showToast('请先选择采购基地和项目，再下载模板', 'warning');
            return;
        }
        if (!year || !month) {
            showToast('请先选择生效年月，再下载模板', 'warning');
            return;
        }
        try {
            const { blob, filename } = await HttpClient.download(`${API}/template`, {
                params: {
                    location,
                    vehicle_model: vehicleModel,
                    effective_year: year,
                    effective_month: month,
                },
                defaultFilename: `材料变更导入模板_${location}_${vehicleModel}.xlsx`,
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
            if (error?.wechatGuide) return;
            this.failOnPanel(error?.message || '下载模板失败');
        }
    },

    resetForm() {
        if (this.isUploading) {
            showToast('导入进行中，不能重置。', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.hideError();
        this.activeTaskId = null;
        document.getElementById('ecmUploadForm')?.reset();
        this.clearSelectedFile();
        this.fillPeriodSelects();
        this.loadScopeOptions();
    },

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.pollInFlight = false;
    },

    startPolling(taskId, fileName, scopeLabel) {
        this.stopPolling();
        this.activeTaskId = taskId;
        this.activeFileName = fileName;
        this.activeScope = scopeLabel;
        const tick = async () => {
            if (this.pollInFlight) return;
            this.pollInFlight = true;
            try {
                const response = await HttpClient.get(
                    `${API}/upload/tasks/${encodeURIComponent(taskId)}`,
                    { skipToast: true },
                );
                const data = response.data;
                const status = data?.status || 'running';
                this.updateProgress(data?.progress ?? 0, data?.msg || '', status);
                if (status === 'completed') {
                    this.stopPolling();
                    const result = data?.result || {};
                    const count = Array.isArray(result.order_ids) ? result.order_ids.length : 0;
                    showToast(data?.msg || `材料变更成功，改了 ${count} 个零件。`, 'success');
                    this.addRecentUpload(fileName, scopeLabel, `${count} 个零件`);
                    this.activeTaskId = null;
                    this.setUploading(false);
                    this.clearSelectedFile();
                    setTimeout(() => {
                        if (!this.isUploading) this.hideProgress();
                    }, 1800);
                    return;
                }
                if (status === 'failed') {
                    this.stopPolling();
                    this.activeTaskId = null;
                    this.setUploading(false);
                    document.getElementById('ecmUploadZone')?.classList.remove('pointer-events-none');
                    this.showError(data?.msg || '解析失败');
                }
            } catch (error) {
                this.stopPolling();
                this.failOnPanel(error?.message || '查询进度失败');
                this.activeTaskId = null;
                this.setUploading(false);
            } finally {
                this.pollInFlight = false;
            }
        };
        tick();
        this.pollTimer = setInterval(tick, POLL_INTERVAL_MS);
    },

    async handleSubmit() {
        if (!this.canUpload) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (this.isUploading) return;
        if (!this.selectedFile) {
            showToast('请先选择文件', 'warning');
            return;
        }
        const location = document.getElementById('ecmUploadLocation')?.value?.trim();
        const vehicleModel = document.getElementById('ecmUploadVehicleModel')?.value?.trim();
        const year = Number(document.getElementById('ecmUploadYear')?.value);
        const month = Number(document.getElementById('ecmUploadMonth')?.value);
        if (!location || !vehicleModel || !year || !month || month < 1 || month > 12) {
            showToast('请填写基地、项目、生效年度和月份', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('location', location);
        formData.append('vehicle_model', vehicleModel);
        formData.append('effective_year', String(year));
        formData.append('effective_month', String(month));
        formData.append('file', this.selectedFile);
        const periodLabel = typeof fmtPeriod === 'function' ? fmtPeriod(year, month) : `${year}年${String(month).padStart(2, '0')}月`;
        const scopeLabel = `${location} / ${vehicleModel} / ${periodLabel}`;
        this.setUploading(true);
        this.hideError();
        this.showProgress(0, '正在导入。');
        try {
            const res = await HttpClient.post(`${API}/upload`, formData, { skipToast: true, timeout: 60000 });
            const taskId = res?.data?.task_id;
            if (!taskId) throw new Error(res?.message || '导入没有开始。');
            this.startPolling(taskId, this.selectedFile.name, scopeLabel);
        } catch (error) {
            this.stopPolling();
            this.failOnPanel(error?.message || '提交失败');
            this.activeTaskId = null;
            this.setUploading(false);
        }
    },
};

export const pageConfig = {
    render: () => materialChangeUploadTemplate(),
    init: () => MaterialChangeUploadPage.init(),
    destroy: () => MaterialChangeUploadPage.destroy(),
};
