/**
 * Steel Base Price Upload Page
 * 基准价格上传 — 异步 task_id + 进度轮询
 */

import { basePriceUploadTemplate } from './template.js?v=39';

const POLL_INTERVAL_MS = 2000;

const BasePriceUploadPage = {
    selectedFile: null,
    pollTimer: null,
    pollInFlight: false,
    isUploading: false,
    activeTaskId: null,

    init() {
        this.stopPolling();
        this.applyPermissionUi();
        this.bindEvents();

        if (this.isUploading && this.activeTaskId) {
            this.setUploading(true);
            this.showProgress(0, '正在恢复任务进度...');
            this.startPolling(this.activeTaskId);
            return;
        }

        this.selectedFile = null;
        this.isUploading = false;
        this.activeTaskId = null;
        this.hideProgress();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function'
            ? can('op:base-price-upload:upload')
            : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('basePriceSelectFileBtn')?.classList.add('hidden');
        document.getElementById('basePriceSubmitButton')?.classList.add('hidden');
        document.querySelector('#basePriceUploadForm button[type="submit"]')?.classList.add('hidden');
        document.getElementById('basePriceResetButton')?.classList.add('hidden');
        const input = document.getElementById('basePriceFileInput');
        if (input) input.disabled = true;
        const zone = document.getElementById('basePriceUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');
        ['basePriceYear', 'basePriceMonth'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
    },

    destroy() {
        this.stopPolling();
    },

    bindEvents() {
        const zone = document.getElementById('basePriceUploadZone');
        const input = document.getElementById('basePriceFileInput');
        const form = document.getElementById('basePriceUploadForm');
        const resetButton = document.getElementById('basePriceResetButton');
        const selectBtn = document.getElementById('basePriceSelectFileBtn');
        const templateBtn = document.getElementById('basePriceUploadTemplateBtn');

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

        window.resetBasePriceUploadForm = () => this.reset();
    },

    failOnPanel(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        this.showProgress(0, text);
        this.updateProgress(0, text, 'failed');
        document.getElementById('basePriceUploadZone')?.classList.remove('pointer-events-none');
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
            showToast('仅支持 .xlsx, .xls 文件', 'warning');
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }
        this.hideProgress();
        this.selectedFile = file;
        const preview = document.getElementById('basePriceFilePreview');
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
        const title = document.getElementById('basePriceUploadTitle');
        if (title) title.innerHTML = `<span class="text-[#2e7d32]">${esc(file.name)}</span> 已选择`;
        const button = document.getElementById('basePriceSubmitButton');
        if (button) button.disabled = false;
    },

    clearSelectedFile() {
        this.selectedFile = null;
        const input = document.getElementById('basePriceFileInput');
        if (input) input.value = '';
        const preview = document.getElementById('basePriceFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        const title = document.getElementById('basePriceUploadTitle');
        if (title) title.innerHTML = '拖拽文件到此处上传';
        const button = document.getElementById('basePriceSubmitButton');
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
        const yearInput = document.getElementById('basePriceYear');
        const monthInput = document.getElementById('basePriceMonth');
        if (yearInput) yearInput.value = '';
        if (monthInput) monthInput.value = '';
    },

    showProgress(progress = 0, msg = '已提交解析队列') {
        const idle = document.getElementById('basePriceDropIdle');
        const panel = document.getElementById('basePriceProgressPanel');
        const zone = document.getElementById('basePriceUploadZone');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-[#d32f2f]');
        }
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        const idle = document.getElementById('basePriceDropIdle');
        const panel = document.getElementById('basePriceProgressPanel');
        const zone = document.getElementById('basePriceUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('basePriceProgressBar');
        const percentEl = document.getElementById('basePriceProgressPercent');
        const msgEl = document.getElementById('basePriceProgressMsg');
        const titleEl = document.getElementById('basePriceProgressTitle');

        if (bar) bar.style.width = `${pct}%`;
        if (percentEl) percentEl.textContent = `${pct}%`;
        if (msgEl) msgEl.textContent = msg || '';
        const actionEl = document.getElementById('basePriceGradeAction');
        const isMissingGrade = status === 'failed' && (msg || '').includes('牌号分类');
        if (actionEl) actionEl.classList.toggle('hidden', !isMissingGrade);

        if (titleEl) {
            if (status === 'completed') {
                titleEl.textContent = '解析成功';
                titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
            } else if (isMissingGrade) {
                titleEl.textContent = '未导入';
                titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
            } else if (status === 'failed') {
                titleEl.textContent = '解析失败';
                titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
            } else {
                titleEl.textContent = '正在解析基准价格...';
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
        const button = document.getElementById('basePriceSubmitButton');
        const resetButton = document.getElementById('basePriceResetButton');
        const yearInput = document.getElementById('basePriceYear');
        const monthInput = document.getElementById('basePriceMonth');
        const templateBtn = document.getElementById('basePriceUploadTemplateBtn');

        if (button) {
            button.disabled = isUploading || !this.selectedFile;
            button.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : `${window.svgIcon('upload', 'w-3.5 h-3.5')} 导入基准价格`;
        }
        if (resetButton) resetButton.disabled = isUploading;
        if (yearInput) yearInput.disabled = isUploading;
        if (monthInput) monthInput.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/yishiyiyi/base-price/template', {
                defaultFilename: '基准价格导入模板.xlsx',
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

    async fetchTaskProgress(taskId) {
        const response = await HttpClient.get(
            `/api/yishiyiyi/base-price/tasks/${encodeURIComponent(taskId)}`,
            { skipToast: true },
        );
        return response.data;
    },

    startPolling(taskId) {
        this.stopPolling();
        this.activeTaskId = taskId;

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
                    const total = result.total || 0;
                    const doneMsg = `导入完成：新增 ${created} 条，更新 ${updated} 条，共 ${total} 条`;
                    this.updateProgress(100, doneMsg, 'completed');
                    showToast(doneMsg, 'success');
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
                    document.getElementById('basePriceUploadZone')?.classList.remove('pointer-events-none');
                    return;
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

    async submit() {
        if (this.canUpload === false) {
            showToast('无导入权限', 'warning');
            return;
        }
        if (this.isUploading) return;
        if (!this.selectedFile) {
            showToast('请选择基准价格文件', 'warning');
            return;
        }

        const yearInput = document.getElementById('basePriceYear');
        const monthInput = document.getElementById('basePriceMonth');
        const year = yearInput?.value?.trim();
        const month = monthInput?.value?.trim();

        if (!year || !/^\d{4}$/.test(year)) {
            showToast('请输入有效的 4 位年度，如 2026', 'warning');
            return;
        }
        if (!month || !/^\d{1,2}$/.test(month) || Number(month) < 1 || Number(month) > 12) {
            showToast('请输入有效的月份（1-12）', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', this.selectedFile);

        this.setUploading(true);
        this.showProgress(0, '已提交解析队列');

        try {
            const url = `/api/yishiyiyi/base-price/import?year=${year}&month=${month}`;
            const response = await HttpClient.post(url, formData, { skipToast: true, timeout: 60000 });
            const taskId = response.data?.task_id;
            if (!taskId) {
                throw new Error('未返回任务 ID');
            }
            this.startPolling(taskId);
        } catch (error) {
            this.stopPolling();
            this.failOnPanel(error.message || '提交失败');
            this.activeTaskId = null;
            this.setUploading(false);
        }
    },

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },
};

export const pageConfig = {
    render: basePriceUploadTemplate,
    init: () => BasePriceUploadPage.init(),
    destroy: () => BasePriceUploadPage.destroy(),
};
