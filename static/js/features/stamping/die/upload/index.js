import { dieUploadTemplate } from './template.js?v=4';

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
            uploadZone.classList.add('drag-active');
        });
        uploadZone?.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-active');
        });
        uploadZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-active');
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
        try {
            const res = await HttpClient.get('/api/stamping/die/filters', {
                params: location ? { location } : {},
            });
            const data = res.data || {};
            this.fillSelect('dieLocation', data.locations || [], '请选择采购基地');
            if (location) {
                const locEl = document.getElementById('dieLocation');
                if (locEl) locEl.value = location;
            }
            this.fillSelect(
                'dieVehicleModel',
                data.vehicle_models || [],
                location ? '请选择项目' : '请先选择基地'
            );
        } catch (error) {
            showToast(error.message || '加载筛选项失败', 'error');
        }
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
                <div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]">
                    <span class="text-[#2e7d32]">${svgIcon('file-earmark-excel')}</span>
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-medium text-white truncate">${esc(file.name)}</div>
                        <div class="text-[10px] text-[#616161]">${window.formatFileSize(file.size)}</div>
                    </div>
                    <button type="button" id="dieRemoveFileBtn" class="p-1.5 text-[#616161] hover:text-[#d32f2f] hover:bg-[#262626] rounded-sm transition-all">
                        ${svgIcon('trash')}
                    </button>
                </div>
            `;
            document.getElementById('dieRemoveFileBtn')?.addEventListener('click', () => {
                if (this.isUploading) return;
                this.clearSelectedFile();
            });
        }
        document.getElementById('dieUploadZone')?.classList.add('file-selected');
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
        document.getElementById('dieUploadZone')?.classList.remove('file-selected');
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
            container.innerHTML = '<p class="text-[10px] text-[#4a4a4a] text-center py-5">暂无上传记录</p>';
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

    showProgress(progress = 0, msg = '已提交解析队列') {
        document.getElementById('dieDropIdle')?.classList.add('hidden');
        document.getElementById('dieProgressPanel')?.classList.remove('hidden');
        document.getElementById('dieUploadZone')?.classList.add('pointer-events-none');
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        document.getElementById('dieDropIdle')?.classList.remove('hidden');
        document.getElementById('dieProgressPanel')?.classList.add('hidden');
        document.getElementById('dieUploadZone')?.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
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
                titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
            } else if (status === 'failed') {
                titleEl.textContent = '解析失败';
                titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
            } else {
                titleEl.textContent = '正在解析模具布点...';
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
        const submitBtn = document.getElementById('dieSubmitBtn');
        const fileInput = document.getElementById('dieFileInput');
        if (submitBtn) {
            submitBtn.disabled = isUploading || !(fileInput?.files?.length);
            submitBtn.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg> 上传`;
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
            if (!error.status) showToast(error.message || '模板下载失败', 'error');
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
                const response = await HttpClient.get(`/api/stamping/die/tasks/${encodeURIComponent(taskId)}`);
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
                    const fullMsg = data?.msg || '上传失败';
                    const toastMsg = fullMsg.split('\n')[0] || fullMsg;
                    showToast(toastMsg, 'error');
                    this.activeTaskId = null;
                    this.setUploading(false);
                    document.getElementById('dieUploadZone')?.classList.remove('pointer-events-none');
                }
            } catch (error) {
                this.stopPolling();
                showToast(error.message || '查询进度失败', 'error');
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
        this.showProgress(0, '已提交解析队列');
        try {
            const response = await HttpClient.post('/api/stamping/die/upload', formData, { timeout: 60000 });
            const taskId = response.data?.task_id;
            if (!taskId) throw new Error('未返回任务 ID');
            this.startPolling(taskId, fileInput.files[0].name, scopeLabel);
        } catch (error) {
            this.stopPolling();
            this.hideProgress();
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
