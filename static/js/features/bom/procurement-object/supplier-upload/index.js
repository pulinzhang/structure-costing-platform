/**
 * 采购对象批量上传供应商
 */

import { procurementObjectSupplierUploadTemplate } from './template.js?v=16';
import { bindSyncUploadProgress } from '../../../../ui/sync-upload-progress.js?v=3';
import { loadSnapshotCascade } from '../snapshot-cascade.js?v=5';

const API_BASE = '/api/bom/procurement-objects';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const uploadProgress = bindSyncUploadProgress({
    zoneId: 'poSupplierUploadZone',
    idleId: 'poSupplierUploadDropIdle',
    panelId: 'poSupplierUploadProgressPanel',
    iconId: 'poSupplierUploadProgressIcon',
    titleId: 'poSupplierUploadProgressTitle',
    barId: 'poSupplierUploadProgressBar',
    msgId: 'poSupplierUploadProgressMsg',
    runningTitle: '正在导入供应商指定...',
});

const uploadState = {
    selectedFile: null,
    isUploading: false,
    canUpload: true,
    location: '',
    vehicleModel: '',
    bomVersion: '',
};

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function loadCascade() {
    return loadSnapshotCascade({
        state: uploadState,
        locationId: 'poSupplierUploadLocation',
        modelId: 'poSupplierUploadModel',
        versionId: 'poSupplierUploadVersion',
    });
}

function requireScope() {
    const location = val('poSupplierUploadLocation');
    const vehicleModel = val('poSupplierUploadModel');
    const bomVersion = val('poSupplierUploadVersion');
    if (!location || !vehicleModel || !bomVersion) {
        showToast('须选定基地、项目、版本', 'warning');
        return null;
    }
    return { location, vehicle_model: vehicleModel, bom_version: bomVersion };
}

function applyPermissionUi() {
    const canFn = typeof window.can === 'function' ? window.can : () => true;
    uploadState.canUpload = canFn('op:bom-procurement-object-supplier-upload:upload');
    if (uploadState.canUpload) return;
    ['poSupplierUploadSelectFileBtn', 'poSupplierUploadSubmitBtn', 'poSupplierUploadResetBtn']
        .forEach((id) => document.getElementById(id)?.classList.add('hidden'));
    const fileInput = document.getElementById('poSupplierUploadFileInput');
    if (fileInput) {
        fileInput.disabled = true;
        fileInput.value = '';
    }
    document.getElementById('poSupplierUploadZone')?.classList.add('pointer-events-none', 'opacity-60');
    const title = document.getElementById('poSupplierUploadTitle');
    const hint = document.getElementById('poSupplierUploadHint');
    if (title) title.textContent = '无上传权限';
    if (hint) hint.textContent = '当前账号仅可下载模板，无法选择或上传文件';
}

function bindEvents() {
    document.getElementById('poSupplierUploadLocation')?.addEventListener('change', () => {
        uploadState.location = val('poSupplierUploadLocation');
        uploadState.vehicleModel = '';
        uploadState.bomVersion = '';
        loadCascade();
        loadQaBanner();
    });
    document.getElementById('poSupplierUploadModel')?.addEventListener('change', () => {
        uploadState.vehicleModel = val('poSupplierUploadModel');
        uploadState.bomVersion = '';
        loadCascade();
        loadQaBanner();
    });
    document.getElementById('poSupplierUploadVersion')?.addEventListener('change', () => {
        uploadState.bomVersion = val('poSupplierUploadVersion');
        loadQaBanner();
    });
    const zone = document.getElementById('poSupplierUploadZone');
    const fileInput = document.getElementById('poSupplierUploadFileInput');
    zone?.addEventListener('click', (event) => {
        if (!uploadState.canUpload || uploadState.isUploading) return;
        if (event.target.closest('button')) return;
        fileInput?.click();
    });
    zone?.addEventListener('dragover', (event) => {
        event.preventDefault();
        zone.classList.add('border-brand');
    });
    zone?.addEventListener('dragleave', () => zone.classList.remove('border-brand'));
    zone?.addEventListener('drop', (event) => {
        event.preventDefault();
        zone.classList.remove('border-brand');
        if (!uploadState.canUpload || uploadState.isUploading) return;
        const file = event.dataTransfer?.files?.[0];
        if (file) setSelectedFile(file);
    });
    fileInput?.addEventListener('change', () => {
        const file = fileInput.files?.[0];
        if (file) setSelectedFile(file);
    });
    document.getElementById('poSupplierUploadSelectFileBtn')?.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        fileInput?.click();
    });
    document.getElementById('poSupplierUploadTemplateBtn')?.addEventListener('click', downloadTemplate);
    document.getElementById('poSupplierUploadResetBtn')?.addEventListener('click', resetForm);
    document.getElementById('poSupplierUploadForm')?.addEventListener('submit', (event) => {
        event.preventDefault();
        submitUpload();
    });
}

function setSelectedFile(file) {
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
        showToast('仅支持 .xlsx 文件', 'warning');
        return;
    }
    if (file.size > MAX_FILE_SIZE) {
        showToast('文件过大，最大 5MB', 'warning');
        return;
    }
    uploadState.selectedFile = file;
    const preview = document.getElementById('poSupplierUploadFilePreview');
    if (preview) {
        preview.classList.remove('hidden');
        preview.innerHTML = `<div class="text-[11px] text-ink-muted border border-line px-3 py-2">${esc(file.name)}</div>`;
    }
    const submitBtn = document.getElementById('poSupplierUploadSubmitBtn');
    if (submitBtn) submitBtn.disabled = uploadState.isUploading;
}

function clearSelectedFile() {
    uploadState.selectedFile = null;
    const fileInput = document.getElementById('poSupplierUploadFileInput');
    if (fileInput) fileInput.value = '';
    document.getElementById('poSupplierUploadFilePreview')?.classList.add('hidden');
    const submitBtn = document.getElementById('poSupplierUploadSubmitBtn');
    if (submitBtn) submitBtn.disabled = true;
}

function resetForm() {
    if (uploadState.isUploading) return;
    uploadState.location = '';
    uploadState.vehicleModel = '';
    uploadState.bomVersion = '';
    clearSelectedFile();
    hideProgress();
    loadCascade();
}

function showProgress(msg = '解析并写入数据库，请稍候') {
    uploadProgress.setRunning(msg);
}

function showDoneOnPanel(message, opts = {}) {
    uploadProgress.setDone(message, opts);
}

function failOnPanel(message) {
    uploadProgress.setFail(message);
}

function hideProgress() {
    uploadProgress.hide();
}

function setUploading(isUploading) {
    uploadState.isUploading = isUploading;
    const submitBtn = document.getElementById('poSupplierUploadSubmitBtn');
    if (submitBtn) submitBtn.disabled = isUploading || !uploadState.selectedFile;
    ['poSupplierUploadResetBtn', 'poSupplierUploadTemplateBtn', 'poSupplierUploadLocation', 'poSupplierUploadModel', 'poSupplierUploadVersion']
        .forEach((id) => {
            const el = document.getElementById(id);
            if (el && (uploadState.canUpload || id === 'poSupplierUploadResetBtn')) el.disabled = isUploading;
        });
}

async function loadQaBanner() {
    const banner = document.getElementById('poSupplierUploadQaBanner');
    if (!banner) return;
    const location = uploadState.location || val('poSupplierUploadLocation');
    const vehicleModel = uploadState.vehicleModel || val('poSupplierUploadModel');
    const bomVersion = uploadState.bomVersion || val('poSupplierUploadVersion');
    if (!location || !vehicleModel || !bomVersion) {
        banner.classList.add('hidden');
        banner.textContent = '';
        return;
    }
    try {
        const res = await HttpClient.get(`${API_BASE}/summary`, {
            params: {
                location,
                vehicle_model: vehicleModel,
            },
            skipToast: true,
        });
        const header = res.data || {};
        if (header.qa_passed === false) {
            const detail = String(header.qa_error_text || '').trim() || '检测未通过';
            banner.textContent = `检测未通过：${detail}。仍可上传改待审行；已审行跳过不改。`;
            banner.classList.remove('hidden');
            return;
        }
        banner.classList.add('hidden');
        banner.textContent = '';
    } catch (_) {
        banner.classList.add('hidden');
        banner.textContent = '';
    }
}

async function downloadTemplate() {
    const scope = requireScope();
    if (!scope) return;
    try {
        const { blob, filename } = await HttpClient.download(`${API_BASE}/supplier-template`, {
            params: scope,
            defaultFilename: `采购对象供应商_${scope.location}_${scope.vehicle_model}_${scope.bom_version}.xlsx`,
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
        await loadQaBanner();
    } catch (error) {
        if (error.wechatGuide) return;
        failOnPanel(error.message || '模板下载失败');
    }
}

async function submitUpload() {
    if (!uploadState.canUpload) return showToast('无上传权限', 'warning');
    if (uploadState.isUploading) return;
    const scope = requireScope();
    if (!scope) return;
    if (!uploadState.selectedFile) {
        showToast('请选择 Excel 文件', 'warning');
        return;
    }
    const formData = new FormData();
    formData.append('location', scope.location);
    formData.append('vehicle_model', scope.vehicle_model);
    formData.append('bom_version', scope.bom_version);
    formData.append('file', uploadState.selectedFile);
    setUploading(true);
    showProgress();
    try {
        const res = await HttpClient.post(`${API_BASE}/supplier-upload`, formData, { skipToast: true });
        const data = res.data || {};
        const skipped = Array.isArray(data.skipped_details) ? data.skipped_details : [];
        const lines = [
            `已更新 ${data.updated_count ?? 0} 条，清空 ${data.cleared_count ?? 0} 条，未变 ${data.unchanged_count ?? 0} 条`,
        ];
        if (skipped.length) {
            lines.push(`跳过 ${data.skipped_count ?? skipped.length} 条：`);
            lines.push(...skipped);
        }
        showDoneOnPanel(lines.join('\n'), { hasSkip: skipped.length > 0 });
        clearSelectedFile();
    } catch (error) {
        failOnPanel(error.message || '上传失败');
    } finally {
        setUploading(false);
    }
}

function init() {
    uploadState.selectedFile = null;
    uploadState.isUploading = false;
    uploadState.location = '';
    uploadState.vehicleModel = '';
    uploadState.bomVersion = '';
    applyPermissionUi();
    bindEvents();
    hideProgress();
    loadCascade();
}

export const pageConfig = {
    render: procurementObjectSupplierUploadTemplate,
    init,
};
