/**
 * BOM 材料清单上传页
 * 与冲压工艺上传同一模式：task_id + 进度轮询
 */

import { bomUploadTemplate } from './template.js?v=12';
import { can } from '../../../../core/permissions.js?v=8';
import {
    SOP_INTRO,
    loadProjectPeriod,
    renderSopBanner,
    sopBannerHtml,
} from '../../../common/period-ui.js?v=7';

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const POLL_INTERVAL_MS = 2000;

const BomUploadPage = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,
    pollTimer: null,
    pollInFlight: false,
    activeTaskId: null,
    activeFileName: null,

    init() {
        this.stopPolling();
        this.selectedFile = null;
        this.applyPermissionUi();
        this.bindEvents();
        this.hideError();
        this.clearSelectedFile(false);
        const slot = document.getElementById('sopBannerSlot');
        if (slot && !document.getElementById('sopBanner')) {
            slot.innerHTML = sopBannerHtml();
        }
        this.loadScopeOptions();

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

    destroy() {
        this.stopPolling();
    },

    applyPermissionUi() {
        const canUpload = typeof can === 'function' ? can('op:bom-upload:upload') : true;
        this.canUpload = canUpload;
        if (canUpload) return;

        document.getElementById('bomUploadSelectFileBtn')?.classList.add('hidden');
        document.getElementById('bomUploadSubmitBtn')?.classList.add('hidden');
        document.getElementById('bomUploadResetBtn')?.classList.add('hidden');

        const fileInput = document.getElementById('bomUploadFileInput');
        if (fileInput) {
            fileInput.disabled = true;
            fileInput.value = '';
        }
        const location = document.getElementById('bomUploadLocation');
        if (location) location.disabled = true;
        const vehicle = document.getElementById('bomUploadVehicleModel');
        if (vehicle) vehicle.disabled = true;

        const zone = document.getElementById('bomUploadZone');
        if (zone) zone.classList.add('pointer-events-none', 'opacity-60');

        const title = document.getElementById('bomUploadTitle');
        const hint = document.getElementById('bomUploadHint');
        if (title) title.textContent = '无上传权限';
        if (hint) hint.textContent = '当前账号仅可查看本页，无法选择或上传文件';
    },

    async loadScopeOptions(resetVehicle = false) {
        const locationEl = document.getElementById('bomUploadLocation');
        const vehicleEl = document.getElementById('bomUploadVehicleModel');
        const location = locationEl?.value || '';
        if (resetVehicle && vehicleEl) vehicleEl.value = '';
        const now = new Date();
        try {
            const params = {
                year: now.getFullYear(),
                month: now.getMonth() + 1,
            };
            if (location) params.location = location;
            const res = await HttpClient.get('/api/bom/filters/cascade', { params });
            const data = res && res.data;
            const locations = Array.isArray(data)
                ? data
                : (data && Array.isArray(data.locations) ? data.locations : []);
            const vehicles = location && data && Array.isArray(data.vehicle_models)
                ? data.vehicle_models
                : [];
            if (locationEl) {
                const current = location;
                locationEl.innerHTML = '<option value="">请选择采购基地</option>' +
                    locations.map((loc) => `<option value="${esc(loc)}">${esc(loc)}</option>`).join('');
                if (current) locationEl.value = current;
            }
            if (vehicleEl) {
                const currentVehicle = vehicleEl.value;
                const placeholder = location
                    ? (vehicles.length ? '请选择项目' : '该基地本月无可引入项目')
                    : '请先选择采购基地';
                vehicleEl.innerHTML = `<option value="">${esc(placeholder)}</option>` +
                    vehicles.map((code) => `<option value="${esc(code)}">${esc(code)}</option>`).join('');
                if (currentVehicle && vehicles.includes(currentVehicle)) {
                    vehicleEl.value = currentVehicle;
                }
            }
            await this.refreshSopBanner();
        } catch (error) {
            console.error('加载采购基地/项目失败', error);
        }
    },

    async refreshSopBanner() {
        const intro = document.querySelector('#sopBanner p');
        if (intro) intro.textContent = SOP_INTRO;
        const location = document.getElementById('bomUploadLocation')?.value || '';
        const vehicleModel = document.getElementById('bomUploadVehicleModel')?.value || '';
        if (!location || !vehicleModel) {
            renderSopBanner({ hasSop: false });
            return;
        }
        let hasSop = false;
        try {
            const res = await HttpClient.get('/api/bom/snapshots', {
                params: { location, vehicle_model: vehicleModel, page: 1, size: 1 },
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

    bindEvents() {
        const zone = document.getElementById('bomUploadZone');
        const fileInput = document.getElementById('bomUploadFileInput');
        const form = document.getElementById('bomUploadForm');
        const selectBtn = document.getElementById('bomUploadSelectFileBtn');
        const resetBtn = document.getElementById('bomUploadResetBtn');
        const templateBtn = document.getElementById('bomUploadTemplateBtn');
        const errorCopyBtn = document.getElementById('bomUploadErrorCopyBtn');
        const errorCloseBtn = document.getElementById('bomUploadErrorCloseBtn');

        templateBtn?.addEventListener('click', () => this.downloadTemplate());
        document.getElementById('bomUploadLocation')?.addEventListener('change', () => {
            this.loadScopeOptions(true);
        });
        document.getElementById('bomUploadVehicleModel')?.addEventListener('change', () => {
            this.refreshSopBanner();
        });
        errorCopyBtn?.addEventListener('click', () => this.copyErrorText());
        errorCloseBtn?.addEventListener('click', () => this.hideError());

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

        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.submit();
        });
    },

    selectFile(file) {
        if (!file || this.isUploading) return;
        const lower = file.name.toLowerCase();
        if (!lower.endsWith('.xlsx') && !lower.endsWith('.xls')) {
            showToast('仅支持 .xlsx / .xls 文件', 'warning');
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }

        this.hideProgress();
        this.hideError();
        this.selectedFile = file;

        const preview = document.getElementById('bomUploadFilePreview');
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

        const title = document.getElementById('bomUploadTitle');
        if (title) title.innerHTML = `<span class="text-ok">${esc(file.name)}</span> 已选择`;

        this.updateSubmitEnabled();
    },

    clearSelectedFile(resetTitle = true) {
        this.selectedFile = null;
        const input = document.getElementById('bomUploadFileInput');
        if (input) input.value = '';

        const preview = document.getElementById('bomUploadFilePreview');
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }

        if (resetTitle) {
            const title = document.getElementById('bomUploadTitle');
            if (title) title.textContent = '拖拽文件到此处';
        }

        this.updateSubmitEnabled();
    },

    reset() {
        if (this.isUploading) {
            showToast('解析进行中，请稍候再重置', 'warning');
            return;
        }
        this.stopPolling();
        this.hideProgress();
        this.hideError();
        this.clearActiveTask();
        this.clearSelectedFile(true);
        const location = document.getElementById('bomUploadLocation');
        if (location) location.value = '';
        const vehicle = document.getElementById('bomUploadVehicleModel');
        if (vehicle) vehicle.value = '';
    },

    showProgress(progress = 0, msg = '已提交解析队列') {
        const idle = document.getElementById('bomUploadDropIdle');
        const panel = document.getElementById('bomUploadProgressPanel');
        const zone = document.getElementById('bomUploadZone');
        if (idle) idle.classList.add('hidden');
        if (panel) panel.classList.remove('hidden');
        if (zone) {
            zone.classList.add('pointer-events-none');
            zone.classList.remove('border-brand');
        }
        this.updateProgress(progress, msg);
    },

    hideProgress() {
        const idle = document.getElementById('bomUploadDropIdle');
        const panel = document.getElementById('bomUploadProgressPanel');
        const zone = document.getElementById('bomUploadZone');
        if (idle) idle.classList.remove('hidden');
        if (panel) panel.classList.add('hidden');
        if (zone) zone.classList.remove('pointer-events-none');
        this.updateProgress(0, '已提交解析队列');
    },

    updateProgress(progress, msg, status) {
        const pct = Math.max(0, Math.min(100, Number(progress) || 0));
        const bar = document.getElementById('bomUploadProgressBar');
        const percentEl = document.getElementById('bomUploadProgressPercent');
        const msgEl = document.getElementById('bomUploadProgressMsg');
        const titleEl = document.getElementById('bomUploadProgressTitle');

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
                titleEl.textContent = '正在解析材料清单...';
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
    },

    hideError() {
        const panel = document.getElementById('bomUploadErrorPanel');
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
        if (panel) panel.classList.add('hidden');
        if (body) {
            body.textContent = '';
            body.dataset.raw = '';
        }
        if (copyBtn) copyBtn.textContent = '复制';
    },

    showError(message) {
        const panel = document.getElementById('bomUploadErrorPanel');
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
        const text = String(message || '导入失败').trim() || '导入失败';
        if (!panel || !body) return;
        body.textContent = text;
        body.dataset.raw = text;
        if (copyBtn) copyBtn.textContent = '复制';
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    async copyErrorText() {
        const body = document.getElementById('bomUploadErrorBody');
        const copyBtn = document.getElementById('bomUploadErrorCopyBtn');
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

    updateSubmitEnabled() {
        const submitBtn = document.getElementById('bomUploadSubmitBtn');
        if (!submitBtn) return;
        submitBtn.disabled = this.isUploading || this.canUpload === false || !this.selectedFile;
    },

    setUploading(isUploading) {
        this.isUploading = isUploading;
        const submitBtn = document.getElementById('bomUploadSubmitBtn');
        const resetBtn = document.getElementById('bomUploadResetBtn');
        const location = document.getElementById('bomUploadLocation');
        const vehicle = document.getElementById('bomUploadVehicleModel');
        const templateBtn = document.getElementById('bomUploadTemplateBtn');
        if (submitBtn) {
            submitBtn.innerHTML = isUploading
                ? `${window.svgIcon('spinner', 'w-3.5 h-3.5')} 解析中...`
                : `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg> 上传`;
        }
        this.updateSubmitEnabled();
        if (resetBtn) resetBtn.disabled = isUploading;
        if (location && this.canUpload) location.disabled = isUploading;
        if (vehicle && this.canUpload) vehicle.disabled = isUploading;
        if (templateBtn) templateBtn.disabled = isUploading;
    },

    async downloadTemplate() {
        try {
            const { blob, filename } = await HttpClient.download('/api/bom/template', {
                defaultFilename: '材料清单导入模板.xlsx',
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
            this.showError(error.message || '模板下载失败');
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
            `/api/bom/upload/tasks/${encodeURIComponent(taskId)}`,
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
                    const nodeCount = result.node_count ?? '-';
                    showToast(msg || `导入成功：${nodeCount} 个节点`, 'success');
                    this.clearActiveTask();
                    this.setUploading(false);
                    this.clearSelectedFile(true);
                    this.refreshSopBanner();
                    setTimeout(() => {
                        if (!this.isUploading) this.hideProgress();
                    }, 1800);
                    return;
                }

                if (status === 'failed') {
                    this.stopPolling();
                    this.showError(msg || '导入失败');
                    this.clearActiveTask();
                    this.setUploading(false);
                    document.getElementById('bomUploadZone')?.classList.remove('pointer-events-none');
                    return;
                }
            } catch (error) {
                this.stopPolling();
                this.showError(error.message || '查询进度失败');
                this.updateProgress(0, error.message || '查询进度失败', 'failed');
                this.clearActiveTask();
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
            showToast('无上传权限', 'warning');
            return;
        }
        if (this.isUploading) return;

        const location = document.getElementById('bomUploadLocation')?.value?.trim();
        const vehicleModel = document.getElementById('bomUploadVehicleModel')?.value?.trim();
        if (!location) {
            showToast('请选择采购基地', 'warning');
            return;
        }
        if (!vehicleModel) {
            showToast('请选择项目', 'warning');
            return;
        }
        if (!this.selectedFile) {
            showToast('请选择 Excel 文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('location', location);
        formData.append('vehicle_model', vehicleModel);
        formData.append('file', this.selectedFile);

        const fileName = this.selectedFile.name;
        this.hideError();
        this.setUploading(true);
        this.showProgress(0, '已提交解析队列');

        try {
            const res = await HttpClient.post('/api/bom/upload', formData, {
                skipToast: true,
                timeout: 60000,
            });
            const taskId = res.data?.task_id;
            if (!taskId) {
                throw new Error('未返回任务 ID');
            }
            this.startPolling(taskId, fileName);
        } catch (error) {
            this.stopPolling();
            this.showError(error.message || '提交失败');
            this.updateProgress(0, error.message || '提交失败', 'failed');
            this.clearActiveTask();
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
    render: bomUploadTemplate,
    init: () => BomUploadPage.init(),
    destroy: () => BomUploadPage.destroy(),
};
