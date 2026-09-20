/**
 * 工程变更上传页 — 异步 task_id + 拖拽区原位进度（对齐布点 / 工艺上传）
 */

import { engineeringChangeUploadTemplate } from './template.js?v=13';
import { can } from '../../../permissions.js?v=6';
import {
    setDropzoneDragActive,
    setDropzoneFileSelected,
} from '../../../upload-dropzone.js?v=1';
import { fillAsOfSelects } from '../../common/period-ui.js?v=5';

const POLL_INTERVAL_MS = 2000;
const MAX_RECENT_UPLOADS = 8;
const API = '/api/engineering-change';
const SUBMIT_IDLE_HTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg> 上传`;

const EngineeringChangeUploadPage = {
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
            return;
        }
        this.isUploading = false;
        this.activeTaskId = null;
        this.hideProgress();
    },

    destroy() {
        this.stopPolling();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:engineering-change-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;
        ['ecUploadSelectFileBtn', 'ecUploadSubmitBtn', 'ecUploadResetBtn', 'ecUploadTemplateBtn']
            .forEach((id) => document.getElementById(id)?.classList.add('hidden'));
        ['ecUploadLocation', 'ecUploadVehicleModel', 'ecUploadYear', 'ecUploadMonth'].forEach((id) => {
            document.getElementById(id)?.setAttribute('disabled', 'disabled');
        });
        const zone = document.getElementById('ecUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('ecUploadTitle');
        const hint = document.getElementById('ecUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    bindEvents() {
        const uploadZone = document.getElementById('ecUploadZone');
        const fileInput = document.getElementById('ecUploadFileInput');
        document.getElementById('ecUploadTemplateBtn')?.addEventListener('click', () => this.downloadTemplate());
        document.getElementById('ecUploadResetBtn')?.addEventListener('click', () => this.resetForm());
        document.getElementById('ecUploadLocation')?.addEventListener('change', () => this.loadScopeOptions(true));
        ['ecUploadYear', 'ecUploadMonth'].forEach((id) => {
            document.getElementById(id)?.addEventListener('change', () => this.loadScopeOptions(false));
        });
        document.getElementById('ecUploadSelectFileBtn')?.addEventListener('click', (event) => {
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
        document.getElementById('ecUploadForm')?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSubmit();
        });
        document.getElementById('ecUploadErrorCopyBtn')?.addEventListener('click', () => this.copyErrorText());
        document.getElementById('ecUploadErrorCloseBtn')?.addEventListener('click', () => this.hideError());
    },

    fillPeriodSelects() {
        const now = new Date();
        fillAsOfSelects('ecUpload', now.getFullYear(), now.getMonth() + 1);
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
        const location = document.getElementById('ecUploadLocation')?.value || '';
        const keptVehicle = resetVehicle
            ? ''
            : (document.getElementById('ecUploadVehicleModel')?.value || '');
        const year = Number(document.getElementById('ecUploadYear')?.value) || new Date().getFullYear();
        const month = Number(document.getElementById('ecUploadMonth')?.value) || (new Date().getMonth() + 1);
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
            this.fillSelect('ecUploadLocation', locations, '请选择采购基地', location);
            const vehiclePlaceholder = location
                ? (vehicles.length ? '请选择项目' : '该基地该月无可引入项目')
                : '请先选择采购基地';
            const currentVehicle = vehicles.includes(keptVehicle) ? keptVehicle : '';
            this.fillSelect('ecUploadVehicleModel', vehicles, vehiclePlaceholder, currentVehicle);
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
        if (!['.xlsx', '.xls'].includes(ext)) {
            showToast('不支持的文件格式，请上传 .xlsx 或 .xls 文件', 'warning');
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }
        this.hideProgress();
        this.hideError();
        this.selectedFile = file;
        const preview = document.getElementById('ecFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]">
                    <span class="text-[#2e7d32]">${svgIcon('file-earmark-excel')}</span>
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-medium text-white truncate">${esc(file.name)}</div>
                        <div class="text-[10px] text-[#616161]">${window.formatFileSize(file.size)}</div>
                    </div>
                    <button type="button" id="ecRemoveFileBtn" class="p-1.5 text-[#616161] hover:text-[#d32f2f] hover:bg-[#262626] rounded-sm transition-all">
                        ${svgIcon('trash')}
                    </button>
                </div>
            `;
            document.getElementById('ecRemoveFileBtn')?.addEventListener('click', () => {
                if (this.isUploading) return;
                this.clearSelectedFile();
            });
        }
        setDropzoneFileSelected(document.getElementById('ecUploadZone'), true);
        const title = document.getElementById('ecUploadTitle');
        const hint = document.getElementById('ecUploadHint');
        if (title) title.textContent = '已选择文件';
        if (hint) hint.textContent = file.name;
        const submitBtn = document.getElementById('ecUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile() {
        this.selectedFile = null;
        const fileInput = document.getElementById('ecUploadFileInput');
        const preview = document.getElementById('ecFilePreview');
        if (fileInput) fileInput.value = '';
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        setDropzoneFileSelected(document.getElementById('ecUploadZone'), false);
        const title = document.getElementById('ecUploadTitle');
        const hint = document.getElementById('ecUploadHint');
        if (title) title.textContent = '拖拽文件到此处';
        if (hint) hint.textContent = '或点击下方按钮选择文件';
        const submitBtn = document.getElementById('ecUploadSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
    },

    addRecentUpload(fileName, scopeLabel, summary) {
        const timeLabel = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
        this.recentUploads.unshift({ fileName, scopeLabel, timeLabel, summary: summary || '' });
        this.recentUploads = this.recentUploads.slice(0, MAX_RECENT_UPLOADS);
        this.renderRecentUploads();
    },

    renderRecentUploads() {
        const container = document.getElementById('ecRecentUploads');
        if (!container) return;
        if (this.recentUploads.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="w-8 h-8 bg-[#1a1a1a] border border-[#2a2a2a] flex items-center justify-center mx-auto mb-2.5">
                        <svg class="w-4 h-4 text-[#4a4a4a]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                    </div>
                    <p class="text-[10px] text-[#4a4a4a]">暂无上传记录</p>
                </div>
            `;
            return;
        }
        container.innerHTML = this.recentUploads.map((item) => `
            <div class="flex items-start gap-2.5 p-2.5 bg-[#121212] border border-[#2c2c2c] mb-2 last:mb-0">
                <span class="text-[#2e7d32] shrink-0 mt-0.5">${svgIcon('file-earmark-excel')}</span>
                <div class="min-w-0 flex-1">
                    <p class="text-[11px] text-[#ffffff] truncate">${esc(item.fileName)}</p>
                    <p class="text-[10px] text-[#616161] mt-0.5">${esc(item.scopeLabel)} · ${esc(item.timeLabel)}</p>
                    ${item.summary ? `<p class="text-[10px] text-[#9e9e9e] mt-0.5">${esc(item.summary)}</p>` : ''}
                </div>
            </div>
        `).join('');
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(0, text);
        this.updateProgress(0, text, 'failed');
        this.showError(text);
        document.getElementById('ecUploadZone')?.classList.remove('pointer-events-none');
    },

    hideError() {
        const panel = document.getElementById('ecUploadErrorPanel');
        const body = document.getElementById('ecUploadErrorBody');
        const copyBtn = document.getElementById('ecUploadErrorCopyBtn');
        panel?.classList.add('hidden');
        if (body) {
            body.textContent = '';
            body.dataset.raw = '';
        }
        if (copyBtn) copyBtn.textContent = '复制';
    },

    showError(message) {
        const panel = document.getElementById('ecUploadErrorPanel');
        const body = document.getElementById('ecUploadErrorBody');
        const copyBtn = document.getElementById('ecUploadErrorCopyBtn');
        const text = String(message || '导入失败').trim() || '导入失败';
        if (!panel || !body) return;
        body.textContent = text;
        body.dataset.raw = text;
        if (copyBtn) copyBtn.textContent = '复制';
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        showToast(text, 'error');
    },

    async copyErrorText() {
        const body = document.getElementById('ecUploadErrorBody');
        const copyBtn = document.getElementById('ecUploadErrorCopyBtn');
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

    showProgress(progress = 0, msg = '已提交解析队列') {
        document.getElementById('ecDropIdle')?.classList.add('hidden');
        document.getElementById('ecProgressPanel')?.classList.remove('hidden');
        document.getElementById('ecUploadZone')?.classList.add('pointer-events-none');
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        document.getElementById('ecDropIdle')?.classList.remove('hidden');
        document.getElementById('ecProgressPanel')?.classList.add('hidden');
        document.getElementById('ecUploadZone')?.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('ecProgressBar');
        const percentEl = document.getElementById('ecProgressPercent');
        const msgEl = document.getElementById('ecProgressMsg');
        const titleEl = document.getElementById('ecProgressTitle');
        if (bar) bar.style.width = `${pct}%`;
        if (percentEl) percentEl.textContent = `${pct}%`;
        if (msgEl) msgEl.textContent = msg || '';
        if (titleEl) {
            if (status === 'completed') {
                titleEl.textContent = '解析成功';
                titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
            } else if (status === 'failed') {
                titleEl.textContent = '解析失败';
                titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
            } else {
                titleEl.textContent = '正在解析工程变更...';
                titleEl.className = 'text-xs font-medium text-[#ffffff] truncate mb-0';
            }
        }
        if (status === 'completed' && bar) {
            bar.className = 'h-full bg-[#2e7d32] transition-all duration-300';
        } else if (status === 'failed' && bar) {
            bar.className = 'h-full bg-[#c62828] transition-all duration-300';
        } else if (bar) {
            bar.className = 'h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300';
        }
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('ecUploadSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = isUploading || !this.selectedFile;
            submitBtn.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : SUBMIT_IDLE_HTML;
        }
        ['ecUploadResetBtn', 'ecUploadLocation', 'ecUploadVehicleModel', 'ecUploadYear', 'ecUploadMonth', 'ecUploadTemplateBtn']
            .forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.disabled = isUploading;
            });
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download(`${API}/template`, {
                defaultFilename: '工程变更导入模板.xlsx',
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
            this.failOnPanel(error?.message || '下载模板失败');
        }
    },

    resetForm() {
        if (this.isUploading) {
            showToast('解析进行中，请稍候再重置', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.hideError();
        this.activeTaskId = null;
        document.getElementById('ecUploadForm')?.reset();
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
                    const changeOrderCount = Array.isArray(result.change_order_ids)
                        ? result.change_order_ids.length
                        : 0;
                    const summary = `${changeOrderCount} 行变更单`;
                    showToast(data?.msg || `工程变更上传成功：${summary}`, 'success');
                    this.addRecentUpload(fileName, scopeLabel, summary);
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
                    document.getElementById('ecUploadZone')?.classList.remove('pointer-events-none');
                    this.showError(data?.msg || '解析失败');
                    return;
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
        const location = document.getElementById('ecUploadLocation')?.value?.trim();
        const vehicleModel = document.getElementById('ecUploadVehicleModel')?.value?.trim();
        const year = Number(document.getElementById('ecUploadYear')?.value);
        const month = Number(document.getElementById('ecUploadMonth')?.value);
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
        this.showProgress(0, '已提交解析队列');
        try {
            const res = await HttpClient.post(`${API}/upload`, formData, { skipToast: true, timeout: 60000 });
            const taskId = res?.data?.task_id;
            if (!taskId) throw new Error(res?.message || '未返回任务 ID');
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
    render: () => engineeringChangeUploadTemplate(),
    init: () => EngineeringChangeUploadPage.init(),
    destroy: () => EngineeringChangeUploadPage.destroy(),
};
