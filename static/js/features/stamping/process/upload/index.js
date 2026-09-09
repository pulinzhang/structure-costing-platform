/**
 * Upload Page
 * 冲压工艺上传 — 异步 task_id + 进度轮询
 */

import { uploadTemplate } from './template.js?v=15';
import {
    setDropzoneDragActive,
    setDropzoneFileSelected,
} from '../../../../upload-dropzone.js?v=1';

const MAX_RECENT_UPLOADS = 8;
const POLL_INTERVAL_MS = 2000;

export const UploadPage = {
    recentUploads: [],
    pollTimer: null,
    pollInFlight: false,
    isUploading: false,
    activeTaskId: null,
    activeFileName: null,

    init() {
        this.stopPolling();
        this.applyPermissionUi();
        this.bindEvents();
        this.renderRecentUploads();

        if (this.isUploading && this.activeTaskId) {
            this.setUploading(true);
            this.showProgress(0, '正在恢复任务进度...');
            this.startPolling(this.activeTaskId, this.activeFileName);
            return;
        }

        this.isUploading = false;
        this.activeTaskId = null;
        this.hideProgress();
    },

    /**
     * 无 op:stamping-upload:upload 时隐藏选文件 / 上传操作
     */
    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:stamping-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        const selectBtn = document.getElementById('stampingSelectFileBtn');
        const submitBtn = document.getElementById('submitBtn');
        const resetBtn = document.getElementById('stampingResetButton');
        const fileInput = document.getElementById('fileInput');
        const uploadZone = document.getElementById('uploadZone');
        const title = document.getElementById('uploadTitle');
        const hint = document.getElementById('uploadHint');
        const actionsRow = submitBtn?.parentElement;

        if (selectBtn) selectBtn.classList.add('hidden');
        if (submitBtn) submitBtn.classList.add('hidden');
        if (resetBtn) resetBtn.classList.add('hidden');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        if (uploadZone) {
            uploadZone.classList.add('pointer-events-none', 'opacity-60');
        }
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';

        if (actionsRow && !document.getElementById('stampingUploadNoPermHint')) {
            const tip = document.createElement('p');
            tip.id = 'stampingUploadNoPermHint';
            tip.className = 'text-[11px] text-[#616161] w-full text-right';
            tip.textContent = '无「上传」权限，请联系管理员授权';
            actionsRow.appendChild(tip);
        }
    },

    destroy() {
        this.stopPolling();
    },

    bindEvents() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const uploadForm = document.getElementById('uploadForm');
        const selectBtn = document.getElementById('stampingSelectFileBtn');
        const templateBtn = document.getElementById('stampingUploadTemplateBtn');

        templateBtn?.addEventListener('click', () => this.downloadTemplate());

        if (!uploadZone || !fileInput) return;

        uploadZone.addEventListener('click', (e) => {
            if (this.canUpload === false || this.isUploading) return;
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            fileInput.click();
        });

        selectBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.canUpload === false || this.isUploading) return;
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        uploadZone.addEventListener('dragover', (e) => {
            if (this.canUpload === false || this.isUploading) return;
            e.preventDefault();
            setDropzoneDragActive(uploadZone, true);
        });

        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            setDropzoneDragActive(uploadZone, false);
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            setDropzoneDragActive(uploadZone, false);
            if (this.canUpload === false || this.isUploading) return;
            this.handleFiles(e.dataTransfer.files);
        });

        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
    },

    handleFiles(files) {
        if (this.canUpload === false) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (!files || files.length === 0 || this.isUploading) return;

        const file = files[0];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const allowedExts = ['.xlsx', '.xls'];

        if (!allowedExts.includes(ext)) {
            showToast('不支持的文件格式，请上传 .xlsx 或 .xls 文件', 'warning');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }

        this.hideProgress();

        const preview = document.getElementById('filePreview');
        const uploadZone = document.getElementById('uploadZone');

        preview.classList.remove('hidden');
        preview.innerHTML = `
            <div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]">
                <span class="text-[#2e7d32]">${svgIcon('file-earmark-excel')}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-medium text-white truncate">${esc(file.name)}</div>
                    <div class="text-[10px] text-[#616161]">${window.formatFileSize(file.size)}</div>
                </div>
                <button type="button" onclick="window.removeUploadFile()" class="p-1.5 text-[#616161] hover:text-[#d32f2f] hover:bg-[#262626] rounded-sm transition-all">
                    ${svgIcon('trash')}
                </button>
            </div>
        `;

        setDropzoneFileSelected(uploadZone, true);
        document.getElementById('uploadTitle').textContent = '已选择文件';
        document.getElementById('uploadHint').textContent = file.name;

        this.updateSubmitEnabled();
    },

    clearSelectedFile() {
        const fileInput = document.getElementById('fileInput');
        const preview = document.getElementById('filePreview');
        const uploadZone = document.getElementById('uploadZone');

        if (fileInput) fileInput.value = '';
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        if (uploadZone) {
            setDropzoneFileSelected(uploadZone, false);
            const title = document.getElementById('uploadTitle');
            const hint = document.getElementById('uploadHint');
            if (title) title.textContent = '拖拽文件到此处';
            if (hint) hint.textContent = '或点击下方按钮选择文件';
        }
        this.updateSubmitEnabled();
    },

    addRecentUpload(fileName, location, summary) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
        this.recentUploads.unshift({
            fileName,
            location,
            timeLabel,
            summary: summary || '',
        });
        if (this.recentUploads.length > MAX_RECENT_UPLOADS) {
            this.recentUploads = this.recentUploads.slice(0, MAX_RECENT_UPLOADS);
        }
        this.renderRecentUploads();
    },

    renderRecentUploads() {
        const container = document.getElementById('recentUploads');
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

        container.innerHTML = `
            <div class="space-y-2">
                ${this.recentUploads.map((item) => `
                    <div class="flex items-start gap-2.5 p-2.5 bg-[#121212] border border-[#2c2c2c]">
                        <span class="text-[#2e7d32] shrink-0 mt-0.5">${svgIcon('file-earmark-excel')}</span>
                        <div class="min-w-0 flex-1">
                            <p class="text-[11px] text-[#ffffff] truncate" title="${esc(item.fileName)}">${esc(item.fileName)}</p>
                            <p class="text-[10px] text-[#616161] mt-0.5">${esc(item.location)} · ${esc(item.timeLabel)}</p>
                            ${item.summary ? `<p class="text-[10px] text-[#9e9e9e] mt-0.5">${esc(item.summary)}</p>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    showProgress(progress = 0, msg = '已提交解析队列') {
        const idle = document.getElementById('stampingDropIdle');
        const panel = document.getElementById('stampingProgressPanel');
        const zone = document.getElementById('uploadZone');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            setDropzoneDragActive(zone, false);
        }
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        const idle = document.getElementById('stampingDropIdle');
        const panel = document.getElementById('stampingProgressPanel');
        const zone = document.getElementById('uploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('stampingProgressBar');
        const percentEl = document.getElementById('stampingProgressPercent');
        const msgEl = document.getElementById('stampingProgressMsg');
        const titleEl = document.getElementById('stampingProgressTitle');

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
                titleEl.textContent = '正在解析工艺文件...';
                titleEl.className = 'text-xs font-medium text-[#ffffff] truncate mb-0';
            }
        }

        if (status === 'completed' && bar) {
            bar.className = 'h-full bg-[#2e7d32] transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#4caf50] shrink-0';
        } else if (status === 'failed' && bar) {
            bar.className = 'h-full bg-[#c62828] transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#ef5350] shrink-0';
        } else if (bar) {
            bar.className = 'h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#d32f2f] shrink-0';
        }
    },

    updateSubmitEnabled() {
        const submitBtn = document.getElementById('submitBtn');
        if (!submitBtn) return;
        const hasFile = document.getElementById('fileInput')?.files?.length > 0;
        submitBtn.disabled = this.isUploading || this.canUpload === false || !hasFile;
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('submitBtn');
        const resetBtn = document.getElementById('stampingResetButton');
        const templateBtn = document.getElementById('stampingUploadTemplateBtn');

        if (submitBtn) {
            submitBtn.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg> 上传`;
        }
        this.updateSubmitEnabled();
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/stamping/upload/template', {
                defaultFilename: '冲压工艺导入模板.xlsx',
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

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.pollInFlight = false;
    },

    clearActiveTask() {
        this.activeTaskId = null;
        this.activeFileName = null;
    },

    async fetchTaskProgress(taskId) {
        const response = await HttpClient.get(
            `/api/stamping/upload/tasks/${encodeURIComponent(taskId)}`
        );
        return response.data;
    },

    startPolling(taskId, fileName) {
        this.stopPolling();
        this.activeTaskId = taskId;
        this.activeFileName = fileName;

        const tick = async () => {
            if (this.pollInFlight) return;
            this.pollInFlight = true;
            try {
                const data = await this.fetchTaskProgress(taskId);
                const status = data?.status || 'running';
                const progress = data?.progress ?? 0;
                const msg = data?.msg || '';

                this.updateProgress(progress, msg, status);

                if (status === 'completed') {
                    this.stopPolling();
                    const result = data?.result || {};
                    const parts = result.parts_count || 0;
                    const processes = result.processes_count || 0;
                    const summary = `${parts} 零件 / ${processes} 工序`;
                    const scopeLabel = [result.location, result.vehicle_model]
                        .filter(Boolean)
                        .join(' · ') || '—';
                    showToast(msg || `上传成功: ${parts} 个零件, ${processes} 道工序`, 'success');
                    this.addRecentUpload(fileName, scopeLabel, summary);
                    this.clearActiveTask();
                    this.setUploading(false);
                    this.clearSelectedFile();
                    setTimeout(() => {
                        if (!this.isUploading) this.hideProgress();
                    }, 1800);
                    return;
                }

                if (status === 'failed') {
                    this.stopPolling();
                    const fullMsg = msg || '上传失败';
                    showToast(fullMsg.split('\n')[0] || fullMsg, 'error');
                    this.clearActiveTask();
                    this.setUploading(false);
                    document.getElementById('uploadZone')?.classList.remove('pointer-events-none');
                    return;
                }
            } catch (error) {
                this.stopPolling();
                showToast(error.message || '查询进度失败', 'error');
                this.clearActiveTask();
                this.setUploading(false);
            } finally {
                this.pollInFlight = false;
            }
        };

        tick();
        this.pollTimer = setInterval(tick, POLL_INTERVAL_MS);
    },

    async handleSubmit() {
        if (this.canUpload === false) {
            showToast('无上传权限', 'warning');
            return;
        }
        if (this.isUploading) return;

        const fileInput = document.getElementById('fileInput');

        if (!fileInput.files || fileInput.files.length === 0) {
            showToast('请选择文件', 'warning');
            return;
        }

        const fileName = fileInput.files[0].name;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        this.setUploading(true);
        this.showProgress(0, '已提交解析队列');

        try {
            const response = await HttpClient.post('/api/stamping/upload/', formData, {
                timeout: 60000,
            });
            const taskId = response.data?.task_id;
            if (!taskId) {
                throw new Error('未返回任务 ID');
            }
            this.startPolling(taskId, fileName);
        } catch (error) {
            this.stopPolling();
            this.hideProgress();
            this.clearActiveTask();
            this.setUploading(false);
        }
    },
};

export const pageConfig = {
    render: uploadTemplate,
    init: () => UploadPage.init(),
    destroy: () => UploadPage.destroy(),
};

window.removeUploadFile = function() {
    if (UploadPage.isUploading) return;
    UploadPage.clearSelectedFile();
};

window.resetUploadForm = function() {
    if (UploadPage.isUploading) {
        showToast('解析进行中，请稍候再重置', 'warning');
        return;
    }
    UploadPage.stopPolling();
    UploadPage.hideProgress();
    UploadPage.clearActiveTask();
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.reset();
        UploadPage.clearSelectedFile();
    }
};
