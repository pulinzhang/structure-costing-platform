import { policyUploadTemplate } from './template.js';

const MAX_RECENT_UPLOADS = 8;

const PolicyUploadPage = {
    selectedFile: null,
    recentUploads: [],

    init() {
        this.selectedFile = null;
        const zone = document.getElementById('policyUploadZone');
        const input = document.getElementById('policyFileInput');
        const form = document.getElementById('policyUploadForm');
        const resetButton = document.getElementById('policyResetButton');

        // 拖拽区域点击触发文件选择
        zone?.addEventListener('click', () => input?.click());

        // 文件选择变化
        input?.addEventListener('change', () => this.selectFile(input.files?.[0]));

        // 拖拽事件
        zone?.addEventListener('dragover', event => {
            event.preventDefault();
            zone.classList.add('border-[#d32f2f]');
        });
        zone?.addEventListener('dragleave', () => zone.classList.remove('border-[#d32f2f]'));
        zone?.addEventListener('drop', event => {
            event.preventDefault();
            zone.classList.remove('border-[#d32f2f]');
            this.selectFile(event.dataTransfer.files?.[0]);
        });

        // 重置按钮
        resetButton?.addEventListener('click', () => this.reset());

        // 表单提交
        form?.addEventListener('submit', event => {
            event.preventDefault();
            this.submit();
        });

        // 暴露 reset 函数到 window
        window.resetPolicyUploadForm = () => this.reset();

        this.renderRecentUploads();
    },

    selectFile(file) {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
            showToast('仅支持 .xlsx, .xls 文件', 'warning');
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }
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

    /**
     * 仅清除已选文件，保留年度/月份，便于连续导入
     */
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
        this.clearSelectedFile();
        const yearInput = document.getElementById('policyYear');
        const monthInput = document.getElementById('policyMonth');
        if (yearInput) yearInput.value = '';
        if (monthInput) monthInput.value = '';
    },

    addRecentUpload(fileName, year, month) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
        this.recentUploads.unshift({
            fileName,
            periodLabel: `${year}年${month}月`,
            timeLabel,
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
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    async submit() {
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
        if (!month || !/^\d{1,2}$/.test(month)) {
            showToast('请输入有效的月份（1-12）', 'warning');
            return;
        }

        const fileName = this.selectedFile.name;
        const button = document.getElementById('policySubmitButton');
        if (button) {
            button.disabled = true;
            button.innerHTML = `${window.svgIcon('upload', 'w-3.5 h-3.5')} 导入中...`;
        }

        const formData = new FormData();
        formData.append('year', year);
        formData.append('month', month);
        formData.append('file', this.selectedFile);

        try {
            const response = await HttpClient.post('/api/steel-price-policies/upload', formData, {
                timeout: 300000, // 政策 Excel 解析较慢，5 分钟
            });
            const data = response.data || {};
            const created = data.created_count || 0;
            const updated = data.updated_count || 0;
            const skipped = data.skipped_count || 0;
            const total = data.total || 0;
            showToast(
                `导入完成：新增 ${created} 条，更新 ${updated} 条，跳过 ${skipped} 条，共 ${total} 条`,
                'success'
            );
            this.addRecentUpload(fileName, year, month);
            // 保留年度/月份，仅清除文件，便于连续导入
            this.clearSelectedFile();
        } catch (error) {
            showToast(error.message || '导入失败', 'error');
        } finally {
            if (button) {
                button.disabled = !this.selectedFile;
                button.innerHTML = `${window.svgIcon('upload', 'w-3.5 h-3.5')} 导入政策`;
            }
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
};
