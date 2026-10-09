import { dieUploadTemplate } from './template.js?v=24';
import { uploadSubmitLabelHtml } from '../../../../ui/upload-actions.js?v=2';
import { paintUploadProgressIcon } from '../../../../ui/sync-upload-progress.js?v=4';
import {
    setDropzoneDragActive,
    setDropzoneFileSelected,
} from '../../../../ui/upload-dropzone.js?v=3';
import {
    SOP_INTRO,
    loadProjectPeriod,
    renderSopBanner,
    sopBannerHtml,
} from '../../../common/period-ui.js?v=9';

const MAX_RECENT_UPLOADS = 8;
const POLL_INTERVAL_MS = 2000;

export const DieUploadPage = {
    recentUploads: [],
    pollTimer: null,
    pollInFlight: false,
    isUploading: false,
    activeTaskId: null,
    activeFileName: null,
    activeScope: null,
    canUpload: true,

    init() {
        this.stopPolling();
        this.applyPermissionUi();
        this.bindEvents();
        this.renderRecentUploads();
        const slot = document.getElementById('sopBannerSlot');
        if (slot && !document.getElementById('sopBanner')) {
            slot.innerHTML = sopBannerHtml();
            const intro = document.querySelector('#sopBanner p');
            if (intro) intro.textContent = SOP_INTRO;
        }
        this.loadFilters();
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

    applyPermissionUi() {
        const canUpload = typeof can === 'function' ? can('op:stamping-die-upload:upload') : true;
        this.canUpload = canUpload;
        if (canUpload) return;
        ['dieSelectFileBtn', 'dieSubmitBtn', 'dieResetButton'].forEach((id) => {
            document.getElementById(id)?.classList.add('hidden');
        });
        const fileInput = document.getElementById('dieFileInput');
        if (fileInput) fileInput.disabled = true;
        document.getElementById('dieLocation')?.setAttribute('disabled', 'disabled');
        document.getElementById('dieVehicleModel')?.setAttribute('disabled', 'disabled');
        document.getElementById('dieUploadZone')?.classList.add('pointer-events-none', 'opacity-60');
        const title = document.getElementById('dieUploadTitle');
        const hint = document.getElementById('dieUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    destroy() {
        this.stopPolling();
    },

    bindEvents() {
        const uploadZone = document.getElementById('dieUploadZone');
        const fileInput = document.getElementById('dieFileInput');
        const uploadForm = document.getElementById('dieUploadForm');
        document.getElementById('dieUploadTemplateBtn')?.addEventListener('click', () => this.downloadTemplate());
        document.getElementById('dieResetButton')?.addEventListener('click', () => this.resetForm());
        document.getElementById('dieLocation')?.addEventListener('change', () => this.loadFilters(true));
        document.getElementById('dieVehicleModel')?.addEventListener('change', () => this.refreshSopBanner());
        document.getElementById('dieSelectFileBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!this.canUpload || this.isUploading) return;
            fileInput?.click();
        });
        uploadZone?.addEventListener('click', (e) => {
            if (!this.canUpload || this.isUploading) return;
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            fileInput?.click();
        });
        fileInput?.addEventListener('change', (e) => this.handleFiles(e.target.files));
        uploadZone?.addEventListener('dragover', (e) => {
            if (!this.canUpload || this.isUploading) return;
            e.preventDefault();
            setDropzoneDragActive(uploadZone, true);
        });
        uploadZone?.addEventListener('dragleave', (e) => {
            e.preventDefault();
            setDropzoneDragActive(uploadZone, false);
        });
        uploadZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            setDropzoneDragActive(uploadZone, false);
            if (!this.canUpload || this.isUploading) return;
            this.handleFiles(e.dataTransfer.files);
        });
        uploadForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
    },

    fillSelect(id, values, placeholder) {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        const options = [`<option value="">${esc(placeholder)}</option>`];
        (values || []).forEach((value) => {
            const text = String(value);
            options.push(`<option value="${esc(text)}"${text === current ? ' selected' : ''}>${esc(text)}</option>`);
        });
        select.innerHTML = options.join('');
    },

    async loadFilters(resetVehicle = false) {
        const location = document.getElementById('dieLocation')?.value || '';
        if (resetVehicle) {
            const vehicle = document.getElementById('dieVehicleModel');
            if (vehicle) vehicle.value = '';
        }
        const now = new Date();
        try {
            const params = {
                year: now.getFullYear(),
                month: now.getMonth() + 1,
            };
            if (location) params.location = location;
            const res = await HttpClient.get('/api/stamping/die/filters', { skipToast: true, params });
            const data = res.data || {};
            this.fillSelect('dieLocation', data.locations || [], '请选择采购基地');
            if (location) {
                const locEl = document.getElementById('dieLocation');
                if (locEl) locEl.value = location;
            }
            const vehicles = location ? (data.vehicle_models || []) : [];
            const vehiclePlaceholder = location
                ? (vehicles.length ? '请选择项目' : '这个月没有可以上传的项目')
                : '请先选择采购基地';
            this.fillSelect('dieVehicleModel', vehicles, vehiclePlaceholder);
            await this.refreshSopBanner();
        } catch (error) {
            this.failOnPanel(error.message || '加载筛选项失败');
        }
    },

    async refreshSopBanner() {
        const location = document.getElementById('dieLocation')?.value || '';
        const vehicleModel = document.getElementById('dieVehicleModel')?.value || '';
        if (!location || !vehicleModel) {
            renderSopBanner({ hasSop: false });
            return;
        }
        let hasSop = false;
        try {
            const res = await HttpClient.get('/api/stamping/die/parts', {
                params: {
                    location,
                    vehicle_model: vehicleModel,
                    page: 1,
                    size: 1,
                    include_expired: true,
                },
            });
            hasSop = Number(res.data?.total || 0) > 0;
        } catch (_) {
            hasSop = false;
        }
        if (hasSop) {
            renderSopBanner({ hasSop: true });
            return;
        }
        const period = await loadProjectPeriod(location, vehicleModel);
        renderSopBanner({
            hasSop: false,
            startLabel: period?.startLabel,
            endLabel: period?.endLabel,
        });
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(0, text);
        this.updateProgress(0, text, 'failed');
        document.getElementById('dieUploadZone')?.classList.remove('pointer-events-none');
    },

    handleFiles(files) {
        if (!this.canUpload) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (!files || files.length === 0 || this.isUploading) return;
        const file = files[0];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!['.xlsx', '.xls'].includes(ext)) {
            showToast('不支持的文件格式，请上传 .xlsx 或 .xls 文件', 'warning');
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }
        this.hideProgress();
        const preview = document.getElementById('dieFilePreview');
        if (preview) {
            preview.classList.remove('hidden');
            preview.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-app-main border border-line">
                    <span class="text-ok">${svgIcon('file-earmark-excel')}</span>
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-medium text-ink truncate">${esc(file.name)}</div>
                        <div class="text-[10px] text-ink-dim">${window.formatFileSize(file.size)}</div>
                    </div>
                    <button type="button" id="dieRemoveFileBtn" class="p-1.5 text-ink-dim hover:text-brand hover:bg-app-elevated rounded-sm transition-all">
                        ${svgIcon('trash')}
                    </button>
                </div>
            `;
            document.getElementById('dieRemoveFileBtn')?.addEventListener('click', () => {
                if (this.isUploading) return;
                this.clearSelectedFile();
            });
        }
        setDropzoneFileSelected(document.getElementById('dieUploadZone'), true);
        const title = document.getElementById('dieUploadTitle');
        const hint = document.getElementById('dieUploadHint');
        if (title) title.textContent = '已选择文件';
        if (hint) hint.textContent = file.name;
        const submitBtn = document.getElementById('dieSubmitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    clearSelectedFile() {
        const fileInput = document.getElementById('dieFileInput');
        const preview = document.getElementById('dieFilePreview');
        if (fileInput) fileInput.value = '';
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        setDropzoneFileSelected(document.getElementById('dieUploadZone'), false);
        const title = document.getElementById('dieUploadTitle');
        const hint = document.getElementById('dieUploadHint');
        if (title) title.textContent = '拖拽文件到此处';
        if (hint) hint.textContent = '或点击下方按钮选择文件';
        const submitBtn = document.getElementById('dieSubmitBtn');
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
        const container = document.getElementById('dieRecentUploads');
        if (!container) return;
        if (this.recentUploads.length === 0) {
            container.innerHTML = '<p class="text-[10px] text-ink-faint text-center py-5">暂无上传记录</p>';
            return;
        }
        container.innerHTML = this.recentUploads.map((item) => `
            <div class="flex items-start gap-2.5 p-2.5 bg-app-main border border-line mb-2 last:mb-0">
                <span class="text-ok shrink-0 mt-0.5">${svgIcon('file-earmark-excel')}</span>
                <div class="min-w-0 flex-1">
                    <p class="text-[11px] text-ink truncate">${esc(item.fileName)}</p>
                    <p class="text-[10px] text-ink-dim mt-0.5">${esc(item.scopeLabel)} · ${esc(item.timeLabel)}</p>
                    ${item.summary ? `<p class="text-[10px] text-ink-muted mt-0.5">${esc(item.summary)}</p>` : ''}
                </div>
            </div>
        `).join('');
    },

    showProgress(progress = 0, msg = '正在导入，请稍候') {
        document.getElementById('dieDropIdle')?.classList.add('hidden');
        document.getElementById('dieProgressPanel')?.classList.remove('hidden');
        document.getElementById('dieUploadZone')?.classList.add('pointer-events-none');
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        document.getElementById('dieDropIdle')?.classList.remove('hidden');
        document.getElementById('dieProgressPanel')?.classList.add('hidden');
        document.getElementById('dieUploadZone')?.classList.remove('pointer-events-none');
        this.updateProgress(0, '正在导入，请稍候');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('dieProgressBar');
        const percentEl = document.getElementById('dieProgressPercent');
        const msgEl = document.getElementById('dieProgressMsg');
        const titleEl = document.getElementById('dieProgressTitle');
        if (bar) bar.style.width = `${pct}%`;
        if (percentEl) percentEl.textContent = `${pct}%`;
        if (msgEl) msgEl.textContent = msg || '';
        if (titleEl) {
            if (status === 'completed') {
                titleEl.textContent = '解析成功';
                titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
            } else if (status === 'failed') {
                titleEl.textContent = '解析失败';
                titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
            } else {
                titleEl.textContent = '正在解析模具布点...';
                titleEl.className = 'text-xs font-medium text-ink truncate mb-0';
            }
        }
        if (status === 'completed' && bar) {
            bar.className = 'h-full bg-ok transition-all duration-300';
        } else if (status === 'failed' && bar) {
            bar.className = 'h-full bg-danger transition-all duration-300';
        } else if (bar) {
            bar.className = 'h-full bg-brand hud-brand-glow transition-all duration-300';
        }
        paintUploadProgressIcon(document.getElementById('dieProgressIcon'), status);
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('dieSubmitBtn');
        const fileInput = document.getElementById('dieFileInput');
        if (submitBtn) {
            submitBtn.disabled = isUploading || !(fileInput?.files?.length);
            submitBtn.innerHTML = uploadSubmitLabelHtml(isUploading);
        }
        ['dieResetButton', 'dieLocation', 'dieVehicleModel', 'dieUploadTemplateBtn'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = isUploading;
        });
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/stamping/die/template', {
                defaultFilename: '冲压模具布点导入模板.xlsx',
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

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.pollInFlight = false;
    },

    resetForm() {
        if (this.isUploading) {
            showToast('解析进行中，请稍候再重置', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.activeTaskId = null;
        document.getElementById('dieUploadForm')?.reset();
        this.clearSelectedFile();
        this.loadFilters();
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
                    `/api/stamping/die/tasks/${encodeURIComponent(taskId)}`,
                    { skipToast: true },
                );
                const data = response.data;
                const status = data?.status || 'running';
                this.updateProgress(data?.progress ?? 0, data?.msg || '', status);
                if (status === 'completed') {
                    this.stopPolling();
                    const result = data?.result || {};
                    const summary = `${result.parts_count || 0} 零件 / ${result.processes_count || 0} 工序`;
                    showToast(data?.msg || `上传成功: ${summary}`, 'success');
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
                    document.getElementById('dieUploadZone')?.classList.remove('pointer-events-none');
                }
            } catch (error) {
                this.stopPolling();
                this.failOnPanel(error.message || '查询进度失败');
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
        const location = document.getElementById('dieLocation')?.value?.trim() || '';
        const vehicleModel = document.getElementById('dieVehicleModel')?.value?.trim() || '';
        const fileInput = document.getElementById('dieFileInput');
        if (!location) {
            showToast('请选择采购基地', 'warning');
            return;
        }
        if (!vehicleModel) {
            showToast('请选择项目', 'warning');
            return;
        }
        if (!fileInput?.files?.length) {
            showToast('请选择文件', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('location', location);
        formData.append('vehicle_model', vehicleModel);
        formData.append('file', fileInput.files[0]);
        const scopeLabel = `${location} / ${vehicleModel}`;
        this.setUploading(true);
        this.showProgress(0, '正在导入，请稍候');
        try {
            const response = await HttpClient.post('/api/stamping/die/upload', formData, { skipToast: true, timeout: 60000 });
            const taskId = response.data?.task_id;
            if (!taskId) throw new Error('未返回任务 ID');
            this.startPolling(taskId, fileInput.files[0].name, scopeLabel);
        } catch (error) {
            this.stopPolling();
            this.failOnPanel(error.message || '提交失败');
            this.activeTaskId = null;
            this.setUploading(false);
        }
    },
};

export const pageConfig = {
    render: dieUploadTemplate,
    init: () => DieUploadPage.init(),
    destroy: () => DieUploadPage.destroy(),
};
