/**
 * Upload Page
 * 冲压工艺上传 — 异步 task_id + 进度轮询
 */

import { uploadTemplate } from './template.js?v=28';
import { uploadSubmitLabelHtml } from '../../../../ui/upload-actions.js?v=2';
import { paintUploadProgressIcon } from '../../../../ui/sync-upload-progress.js?v=4';
import {
    setDropzoneDragActive,
    setDropzoneFileSelected,
} from '../../../../ui/upload-dropzone.js?v=3';
import { SOP_INTRO, sopBannerHtml } from '../../../common/period-ui.js?v=9';

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
        const slot = document.getElementById('sopBannerSlot');
        if (slot && !document.getElementById('sopBanner')) {
            slot.innerHTML = sopBannerHtml();
            const detail = document.getElementById('sopBannerDetail');
            if (detail) {
                detail.textContent = '工艺页只选文件。已经投产后再传，文件里出现新零件号会整份拒绝，换零件号请走工程变更。';
            }
            const intro = document.querySelector('#sopBanner p');
            if (intro) intro.textContent = SOP_INTRO;
        }

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
            tip.className = 'text-[11px] text-ink-dim w-full text-right';
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

        document.getElementById('stampingResetButton')?.addEventListener('click', () => {
            this.resetForm();
        });
        document.getElementById('filePreview')?.addEventListener('click', (event) => {
            if (!event.target.closest('[data-action="remove-file"]')) return;
            if (this.isUploading) return;
            this.clearSelectedFile();
        });
    },

    resetForm() {
        if (this.isUploading) {
            showToast('解析进行中，请稍候再重置', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.clearActiveTask();
        const form = document.getElementById('uploadForm');
        if (form) {
            form.reset();
            this.clearSelectedFile();
        }
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(0, text);
        this.updateProgress(0, text, 'failed');
        document.getElementById('uploadZone')?.classList.remove('pointer-events-none');
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
            <div class="flex items-center gap-3 p-3 bg-app-main border border-line">
                <span class="text-ok">${svgIcon('file-earmark-excel')}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-medium text-ink truncate">${esc(file.name)}</div>
                    <div class="text-[10px] text-ink-dim">${window.formatFileSize(file.size)}</div>
                </div>
                <button type="button" data-action="remove-file" class="p-1.5 text-ink-dim hover:text-brand hover:bg-app-elevated rounded-sm transition-all">
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
                        <span class="text-ok shrink-0 mt-0.5">${svgIcon('file-earmark-excel')}</span>
                        <div class="min-w-0 flex-1">
                            <p class="text-[11px] text-ink truncate" title="${esc(item.fileName)}">${esc(item.fileName)}</p>
                            <p class="text-[10px] text-ink-dim mt-0.5">${esc(item.location)} · ${esc(item.timeLabel)}</p>
                            ${item.summary ? `<p class="text-[10px] text-ink-muted mt-0.5">${esc(item.summary)}</p>` : ''}
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
        const actionEl = document.getElementById('stampingGradeAction');
        const isMissingGrade = status === 'failed' && (msg || '').includes('牌号分类');
        if (actionEl) actionEl.classList.toggle('hidden', !isMissingGrade);

        if (titleEl) {
            if (status === 'completed') {
                titleEl.textContent = '解析成功';
                titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
            } else if (isMissingGrade) {
                titleEl.textContent = '未导入';
                titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
            } else if (status === 'failed') {
                titleEl.textContent = '解析失败';
                titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
            } else {
                titleEl.textContent = '正在解析工艺文件...';
                titleEl.className = 'text-xs font-medium text-ink truncate mb-0';
            }
        }

        if (status === 'completed' && bar) {
            bar.className = 'h-full bg-ok transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-ok shrink-0';
        } else if (status === 'failed' && bar) {
            bar.className = 'h-full bg-danger transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-danger shrink-0';
        } else if (bar) {
            bar.className = 'h-full bg-brand hud-brand-glow transition-all duration-300';
            if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-brand shrink-0';
        }
        paintUploadProgressIcon(document.getElementById('stampingProgressIcon'), status);
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
            submitBtn.innerHTML = uploadSubmitLabelHtml(isUploading);
        }
        this.updateSubmitEnabled();
        if (resetBtn) resetBtn.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/stamping/upload/template', {
                defaultFilename: '冲压工艺导入模板.xlsx',
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
            `/api/stamping/upload/tasks/${encodeURIComponent(taskId)}`,
            { skipToast: true },
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
                    this.clearActiveTask();
                    this.setUploading(false);
                    document.getElementById('uploadZone')?.classList.remove('pointer-events-none');
                    return;
                }
            } catch (error) {
                this.stopPolling();
                this.failOnPanel(error.message || '查询进度失败');
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
            const response = await HttpClient.post('/api/stamping/upload/', formData, { skipToast: true, timeout: 60000 });
            const taskId = response.data?.task_id;
            if (!taskId) {
                throw new Error('未返回任务 ID');
            }
            this.startPolling(taskId, fileName);
        } catch (error) {
            this.stopPolling();
            this.failOnPanel(error.message || '提交失败');
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
