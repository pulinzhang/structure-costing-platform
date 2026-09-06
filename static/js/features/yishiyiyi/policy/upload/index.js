import { policyUploadTemplate } from './template.js?v=1';

const MAX_RECENT_UPLOADS = 8;
const POLL_INTERVAL_MS = 2000;

const PolicyUploadPage = {
    selectedFile: null,
    recentUploads: [],
    pollTimer: null,
    pollInFlight: false,
    isUploading: false,
    activeTaskId: null,
    activeFileName: null,
    activeYear: null,
    activeMonth: null,

    init() {
        this.stopPolling();
        this.applyPermissionUi();
        this.bindEvents();
        this.renderRecentUploads();

        // 离开页面后再次进入：若任务仍在跑，恢复进度面板与轮询
        if (this.isUploading && this.activeTaskId) {
            this.setUploading(true);
            this.showProgress(0, '正在恢复任务进度...');
            this.startPolling(
                this.activeTaskId,
                this.activeFileName,
                this.activeYear,
                this.activeMonth,
            );
            return;
        }

        this.selectedFile = null;
        this.isUploading = false;
        this.activeTaskId = null;
        this.hideProgress();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:steel-price-policy-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('policySelectFileBtn')?.classList.add('hidden');
        document.getElementById('policySubmitButton')?.classList.add('hidden');
        document.getElementById('policyResetButton')?.classList.add('hidden');
        const input = document.getElementById('policyFileInput');
        if (input) input.disabled = true;
        const zone = document.getElementById('policyUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');
        ['policyYear', 'policyMonth'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
        const title = document.getElementById('policyUploadTitle');
        if (title) title.textContent = '无导入权限';
    },

    destroy() {
        // 仅停轮询，保留 activeTaskId / isUploading，便于回来继续跟进度
        this.stopPolling();
    },

    bindEvents() {
        const zone = document.getElementById('policyUploadZone');
        const input = document.getElementById('policyFileInput');
        const form = document.getElementById('policyUploadForm');
        const resetButton = document.getElementById('policyResetButton');
        const selectBtn = document.getElementById('policySelectFileBtn');
        const templateBtn = document.getElementById('policyUploadTemplateBtn');

        templateBtn?.addEventListener('click', () => this.downloadTemplate());

        zone?.addEventListener('click', (event) => {
            if (this.canUpload === false || this.isUploading) return;
            if (event.target.closest('button')) return;
            input?.click();
        });
        selectBtn?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (this.canUpload === false || this.isUploading) return;
            input?.click();
        });

        input?.addEventListener('change', () => this.selectFile(input.files?.[0]));

        zone?.addEventListener('dragover', (event) => {
            if (this.isUploading) return;
            event.preventDefault();
            zone.classList.add('border-[#d32f2f]');
        });
        zone?.addEventListener('dragleave', () => zone.classList.remove('border-[#d32f2f]'));
        zone?.addEventListener('drop', (event) => {
            event.preventDefault();
            zone.classList.remove('border-[#d32f2f]');
            if (this.isUploading) return;
            this.selectFile(event.dataTransfer.files?.[0]);
        });

        resetButton?.addEventListener('click', () => this.reset());

        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });

        window.resetPolicyUploadForm = () => this.reset();
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        const name = file.name.toLowerCase();
        if (!name.endsWith('.xlsx') && !name.endsWith('.xls') && !name.endsWith('.xlsm')) {
            showToast('仅支持 .xlsx, .xls, .xlsm 文件', 'warning');
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }
        this.hideProgress();
        this.selectedFile = file;
        const preview = document.getElementById('policyFilePreview');
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
        const title = document.getElementById('policyUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;
        const button = document.getElementById('policySubmitButton');
        if (button) button.disabled = false;
    },

    clearSelectedFile() {
        this.selectedFile = null;
        const input = document.getElementById('policyFileInput');
        if (input) input.value = '';
        const preview = document.getElementById('policyFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        const title = document.getElementById('policyUploadTitle');
        if (title) title.innerHTML = '拖拽文件到此处上传';
        const button = document.getElementById('policySubmitButton');
        if (button) button.disabled = true;
    },

    reset() {
        if (this.isUploading) {
            showToast('解析进行中，请稍候再重置', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.clearSelectedFile();
        this.activeTaskId = null;
        const yearInput = document.getElementById('policyYear');
        const monthInput = document.getElementById('policyMonth');
        if (yearInput) yearInput.value = '';
        if (monthInput) monthInput.value = '';
    },

    addRecentUpload(fileName, year, month, summary) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
        this.recentUploads.unshift({
            fileName,
            periodLabel: fmtPeriod(year, month),
            timeLabel,
            summary: summary || '',
        });
        if (this.recentUploads.length > MAX_RECENT_UPLOADS) {
            this.recentUploads = this.recentUploads.slice(0, MAX_RECENT_UPLOADS);
        }
        this.renderRecentUploads();
    },

    renderRecentUploads() {
        const container = document.getElementById('recentPolicyUploads');
        if (!container) return;

        if (this.recentUploads.length === 0) {
            container.innerHTML = `
                <div class="text-center py-6">
                    <div class="w-8 h-8 bg-[#262626] flex items-center justify-center mx-auto mb-2.5">
                        <svg class="w-4 h-4 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                    </div>
                    <p class="text-[11px] text-[#616161]">暂无导入记录</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="space-y-2">
                ${this.recentUploads.map((item) => `
                    <div class="flex items-start gap-2.5 p-2.5 bg-[#121212] border border-[#2c2c2c]">
                        <span class="text-[#2e7d32] shrink-0 mt-0.5">${window.svgIcon('file-earmark-excel', 'w-4 h-4')}</span>
                        <div class="min-w-0 flex-1">
                            <p class="text-[11px] text-[#ffffff] truncate" title="${esc(item.fileName)}">${esc(item.fileName)}</p>
                            <p class="text-[10px] text-[#616161] mt-0.5">${esc(item.periodLabel)} · ${esc(item.timeLabel)}</p>
                            ${item.summary ? `<p class="text-[10px] text-[#9e9e9e] mt-0.5">${esc(item.summary)}</p>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    showProgress(progress = 0, msg = '已提交解析队列') {
        const idle = document.getElementById('policyDropIdle');
        const panel = document.getElementById('policyProgressPanel');
        const zone = document.getElementById('policyUploadZone');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        const idle = document.getElementById('policyDropIdle');
        const panel = document.getElementById('policyProgressPanel');
        const zone = document.getElementById('policyUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('policyProgressBar');
        const percentEl = document.getElementById('policyProgressPercent');
        const msgEl = document.getElementById('policyProgressMsg');
        const titleEl = document.getElementById('policyProgressTitle');

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
                titleEl.textContent = '正在解析政策文件...';
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

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const button = document.getElementById('policySubmitButton');
        const resetButton = document.getElementById('policyResetButton');
        const yearInput = document.getElementById('policyYear');
        const monthInput = document.getElementById('policyMonth');
        const templateBtn = document.getElementById('policyUploadTemplateBtn');

        if (button) {
            button.disabled = isUploading || !this.selectedFile;
            button.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg> 导入政策`;
        }
        if (resetButton) resetButton.disabled = isUploading;
        if (yearInput) yearInput.disabled = isUploading;
        if (monthInput) monthInput.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/yishiyiyi/policy/template', {
                defaultFilename: '加减价政策导入模板.xlsx',
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
        this.activeYear = null;
        this.activeMonth = null;
    },

    async fetchTaskProgress(taskId) {
        const response = await HttpClient.get(
            `/api/yishiyiyi/policy/tasks/${encodeURIComponent(taskId)}`
        );
        return response.data;
    },

    startPolling(taskId, fileName, year, month) {
        this.stopPolling();
        this.activeTaskId = taskId;
        this.activeFileName = fileName;
        this.activeYear = year;
        this.activeMonth = month;

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
                    const created = result.created_count || 0;
                    const updated = result.updated_count || 0;
                    const skipped = result.skipped_count || 0;
                    const total = result.total || 0;
                    const summary = `新增 ${created} / 更新 ${updated} / 跳过 ${skipped} / 共 ${total}`;
                    showToast(
                        `导入完成：新增 ${created} 条，更新 ${updated} 条，跳过 ${skipped} 条，共 ${total} 条`,
                        'success'
                    );
                    this.addRecentUpload(fileName, year, month, summary);
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
                    showToast(msg || '导入失败', 'error');
                    this.clearActiveTask();
                    this.setUploading(false);
                    const button = document.getElementById('policySubmitButton');
                    if (button) button.disabled = !this.selectedFile;
                    return;
                }
            } catch (error) {
                this.stopPolling();
                showToast(error.message || '查询进度失败', 'error');
                this.clearActiveTask();
                this.setUploading(false);
                const button = document.getElementById('policySubmitButton');
                if (button) button.disabled = !this.selectedFile;
            } finally {
                this.pollInFlight = false;
            }
        };

        tick();
        this.pollTimer = setInterval(tick, POLL_INTERVAL_MS);
    },

    async submit() {
        if (this.canUpload === false) {
            showToast('无导入权限', 'warning');
            return;
        }
        if (this.isUploading) return;
        if (!this.selectedFile) {
            showToast('请选择政策文件', 'warning');
            return;
        }
        const year = document.getElementById('policyYear')?.value?.trim();
        const month = document.getElementById('policyMonth')?.value?.trim();

        if (!year || !/^\d{4}$/.test(year)) {
            showToast('请输入有效的 4 位年度，如 2026', 'warning');
            return;
        }
        if (!month || !/^\d{1,2}$/.test(month) || Number(month) < 1 || Number(month) > 12) {
            showToast('请输入有效的月份（1-12）', 'warning');
            return;
        }

        const fileName = this.selectedFile.name;
        const formData = new FormData();
        formData.append('year', year);
        formData.append('month', month);
        formData.append('file', this.selectedFile);

        this.setUploading(true);
        this.showProgress(0, '已提交解析队列');

        try {
            const response = await HttpClient.post('/api/yishiyiyi/policy/upload', formData, {
                timeout: 60000,
            });
            const taskId = response.data?.task_id;
            if (!taskId) {
                throw new Error('未返回任务 ID');
            }
            this.startPolling(taskId, fileName, year, month);
        } catch (error) {
            this.stopPolling();
            this.hideProgress();
            this.clearActiveTask();
            this.setUploading(false);
            const button = document.getElementById('policySubmitButton');
            if (button) button.disabled = !this.selectedFile;
        }
    },

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },
};

export const pageConfig = {
    render: policyUploadTemplate,
    init: () => PolicyUploadPage.init(),
    destroy: () => PolicyUploadPage.destroy(),
};
