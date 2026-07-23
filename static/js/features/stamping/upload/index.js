/**
 * Upload Page
 * 上传页面逻辑
 */

import { uploadTemplate } from './template.js';

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export const UploadPage = {
    /**
     * 初始化上传页面
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const uploadForm = document.getElementById('uploadForm');

        if (!uploadZone || !fileInput) return;

        // 点击上传区域
        uploadZone.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
                fileInput.click();
            }
        });

        // 文件选择
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        // 拖拽上传
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-active');
        });

        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-active');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-active');
            this.handleFiles(e.dataTransfer.files);
        });

        // 表单提交
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
    },

    /**
     * 处理文件选择
     */
    handleFiles(files) {
        if (!files || files.length === 0) return;

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

        const preview = document.getElementById('filePreview');
        const uploadZone = document.getElementById('uploadZone');

        preview.classList.remove('hidden');
        preview.innerHTML = `
            <div class="flex items-center gap-3 p-3 bg-[#121212] border border-[#2c2c2c]">
                <span class="text-[#2e7d32]">${svgIcon('file-earmark-excel')}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-medium text-white truncate">${esc(file.name)}</div>
                    <div class="text-[10px] text-[#616161]">${formatFileSize(file.size)}</div>
                </div>
                <button type="button" onclick="window.removeUploadFile()" class="p-1.5 text-[#616161] hover:text-[#d32f2f] hover:bg-[#262626] rounded-sm transition-all">
                    ${svgIcon('trash')}
                </button>
            </div>
        `;

        uploadZone.classList.add('border-green-700/50', 'bg-green-950/10');
        document.getElementById('uploadTitle').textContent = '已选择文件';
        document.getElementById('uploadHint').textContent = file.name;
    },

    /**
     * 处理表单提交
     */
    handleSubmit() {
        const vehicleModel = document.getElementById('vehicleModel');
        const version = document.getElementById('version');
        const fileInput = document.getElementById('fileInput');

        if (!vehicleModel.value.trim()) {
            showToast('请输入车型', 'warning');
            vehicleModel.focus();
            return;
        }

        if (!version.value.trim()) {
            showToast('请输入版本', 'warning');
            version.focus();
            return;
        }

        if (!fileInput.files || fileInput.files.length === 0) {
            showToast('请选择文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('vehicle_model', vehicleModel.value.trim());
        formData.append('version', version.value.trim());
        formData.append('file', fileInput.files[0]);

        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;

        HttpClient.post('/api/stamping/upload/', formData)
            .then(() => {
                showToast('文件上传成功', 'success');
                window.resetUploadForm();
            })
            .catch(error => {
                console.error('上传失败:', error);
                showToast(error.message || '上传失败', 'danger');
            })
            .finally(() => {
                submitBtn.disabled = false;
            });
    },
};

/**
 * 页面导出 - 用于 app.js 注册
 */
export const pageConfig = {
    render: uploadTemplate,
    init: () => UploadPage.init(),
};

// 全局函数供 onclick 调用
window.removeUploadFile = function() {
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('filePreview');
    const uploadZone = document.getElementById('uploadZone');

    if (fileInput) fileInput.value = '';
    if (preview) preview.classList.add('hidden');
    if (uploadZone) {
        uploadZone.classList.remove('border-green-700/50', 'bg-green-950/10');
        document.getElementById('uploadTitle').textContent = '拖拽文件到此处上传';
        document.getElementById('uploadHint').textContent = '或点击选择文件';
    }
};

window.resetUploadForm = function() {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.reset();
        window.removeUploadFile();
    }
};
