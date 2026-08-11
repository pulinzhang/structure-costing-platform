/**
 * Upload Page
 * 上传页面逻辑
 */

import { uploadTemplate } from './template.js';

const MAX_RECENT_UPLOADS = 8;

export const UploadPage = {
    recentUploads: [],

    /**
     * 初始化上传页面
     */
    init() {
        this.bindEvents();
        this.renderRecentUploads();
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
                    <div class="text-[10px] text-[#616161]">${window.formatFileSize(file.size)}</div>
                </div>
                <button type="button" onclick="window.removeUploadFile()" class="p-1.5 text-[#616161] hover:text-[#d32f2f] hover:bg-[#262626] rounded-sm transition-all">
                    ${svgIcon('trash')}
                </button>
            </div>
        `;

        uploadZone.classList.add('file-selected');
        document.getElementById('uploadTitle').textContent = '已选择文件';
        document.getElementById('uploadHint').textContent = file.name;

        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) submitBtn.disabled = false;
    },

    /**
     * 仅清除已选文件，保留采购基地等参数，便于连续上传
     */
    clearSelectedFile() {
        const fileInput = document.getElementById('fileInput');
        const preview = document.getElementById('filePreview');
        const uploadZone = document.getElementById('uploadZone');
        const submitBtn = document.getElementById('submitBtn');

        if (fileInput) fileInput.value = '';
        if (preview) {
            preview.classList.add('hidden');
            preview.innerHTML = '';
        }
        if (uploadZone) {
            uploadZone.classList.remove('file-selected');
            const title = document.getElementById('uploadTitle');
            const hint = document.getElementById('uploadHint');
            if (title) title.textContent = '拖拽文件到此处';
            if (hint) hint.textContent = '或点击下方按钮选择文件';
        }
        if (submitBtn) submitBtn.disabled = true;
    },

    /**
     * 写入右侧最近上传列表
     */
    addRecentUpload(fileName, location) {
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
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    /**
     * 处理表单提交
     */
    handleSubmit() {
        const location = document.getElementById('location');
        const fileInput = document.getElementById('fileInput');

        if (!location.value.trim()) {
            showToast('请选择采购基地', 'warning');
            location.focus();
            return;
        }

        if (!fileInput.files || fileInput.files.length === 0) {
            showToast('请选择文件', 'warning');
            return;
        }

        const fileName = fileInput.files[0].name;
        const locationValue = location.value.trim();

        const formData = new FormData();
        formData.append('location', locationValue);
        formData.append('file', fileInput.files[0]);

        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;

        HttpClient.post('/api/stamping/upload/', formData, {
            timeout: 300000, // 工艺文件解析较慢，5 分钟
        })
            .then((res) => {
                showToast(res.message || '文件上传成功', 'success');
                this.addRecentUpload(fileName, locationValue);
                // 保留采购基地，仅清除文件，便于连续上传
                this.clearSelectedFile();
            })
            .catch(error => {
                console.error('上传失败:', error);
                showToast(error.message || '上传失败', 'error');
            })
            .finally(() => {
                const hasFile = fileInput.files && fileInput.files.length > 0;
                submitBtn.disabled = !hasFile;
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
    UploadPage.clearSelectedFile();
};

window.resetUploadForm = function() {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.reset();
        UploadPage.clearSelectedFile();
    }
};
