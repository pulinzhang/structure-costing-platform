/**
 * Profile Page
 * - 基本资料：PUT /api/auth/me
 * - 修改密码：PUT /api/auth/password（校验旧密码）
 * 顶部摘要与表单同源渲染，避免展示/编辑数据冲突
 */

import { updateUserSession } from '../../login/index.js';
import { profileLoadingTemplate, profileTemplate } from './template.js?v=3';

const profileState = {
    user: null,
    isSavingProfile: false,
    isSavingPassword: false,
    isUploadingAvatar: false,
};

const MIN_PASSWORD_LENGTH = 6;
const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
const ALLOWED_AVATAR_TYPES = new Set([
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
]);
const ALLOWED_AVATAR_EXTS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif']);

function emptyToNull(value) {
    const text = (value || '').trim();
    return text === '' ? null : text;
}

function syncSession(user) {
    if (!user) return;
    updateUserSession({
        id: user.id,
        username: user.username,
        real_name: user.real_name || '',
        email: user.email || '',
        phone: user.phone || '',
        department: user.department || '',
        avatar: user.avatar || '',
    });
}

function mountProfile(user) {
    const pageContent = document.getElementById('pageContent');
    if (!pageContent) return;
    profileState.user = user;
    pageContent.innerHTML = profileTemplate(user);
    bindEvents();
    applyPermissionUi();
    syncSession(user);
}

function applyPermissionUi() {
    if (typeof can !== 'function') return;
    if (!can('op:settings-profile:update')) {
        document.getElementById('btnSaveProfile')?.classList.add('hidden');
        document.getElementById('btnPickAvatar')?.classList.add('hidden');
        document.getElementById('avatarFileInput')?.setAttribute('disabled', 'disabled');
        ['profileRealName', 'profileEmail', 'profilePhone', 'profileDepartment'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
    }
    if (!can('op:settings-profile:password')) {
        document.getElementById('btnChangePassword')?.classList.add('hidden');
        document.getElementById('profilePasswordForm')?.classList.add('opacity-40', 'pointer-events-none');
    }
}

async function loadProfile() {
    try {
        const res = await HttpClient.get('/api/auth/me');
        const user = res.data;
        if (!user || !user.id) {
            showToast('无法获取当前用户信息', 'error');
            return;
        }
        mountProfile(user);
    } catch (error) {
        console.error('加载个人资料失败:', error);
        const pageContent = document.getElementById('pageContent');
        if (pageContent) {
            pageContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20">
                    <p class="text-xs text-ink-muted mb-3">加载失败，请重试</p>
                    <button type="button" id="btnRetryProfile"
                            class="inline-flex items-center gap-1.5 bg-brand text-white px-4 py-2 text-xs font-semibold rounded-sm hover:bg-brand-hover transition-all">
                        重新加载
                    </button>
                </div>
            `;
            document.getElementById('btnRetryProfile')?.addEventListener('click', () => {
                pageContent.innerHTML = profileLoadingTemplate();
                loadProfile();
            });
        }
    }
}

async function saveProfile() {
    if (profileState.isSavingProfile) return;

    const payload = {
        real_name: emptyToNull(document.getElementById('profileRealName')?.value),
        department: emptyToNull(document.getElementById('profileDepartment')?.value),
        phone: emptyToNull(document.getElementById('profilePhone')?.value),
        email: emptyToNull(document.getElementById('profileEmail')?.value),
    };

    const btn = document.getElementById('btnSaveProfile');
    profileState.isSavingProfile = true;
    if (btn) btn.disabled = true;

    try {
        const res = await HttpClient.put('/api/auth/me', payload);
        const user = res.data || {};
        mountProfile(user);
        showToast('资料已保存', 'success');
    } catch (error) {
        console.error('保存个人资料失败:', error);
    } finally {
        profileState.isSavingProfile = false;
        if (btn) btn.disabled = false;
    }
}

function passwordStrength(password) {
    if (!password) return { score: 0, label: '—', color: 'rgb(var(--text-dim))', width: '0%' };
    let score = 0;
    if (password.length >= 6) score += 1;
    if (password.length >= 10) score += 1;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    if (score <= 1) return { score, label: '弱', color: 'rgb(var(--danger-color))', width: '25%' };
    if (score <= 3) return { score, label: '中', color: 'rgb(var(--warning-color))', width: '55%' };
    return { score, label: '强', color: 'rgb(var(--success-color))', width: '100%' };
}

function updatePasswordHints() {
    const password = document.getElementById('profileNewPassword')?.value || '';
    const confirm = document.getElementById('profileConfirmPassword')?.value || '';
    const strength = passwordStrength(password);

    const bar = document.getElementById('passwordStrengthBar');
    const strengthTip = document.getElementById('passwordStrengthTip');
    const matchTip = document.getElementById('passwordMatchTip');

    if (bar) {
        bar.style.width = strength.width;
        bar.style.background = strength.color;
    }
    if (strengthTip) {
        strengthTip.textContent = password
            ? `密码强度：${strength.label}${password.length < MIN_PASSWORD_LENGTH ? '（至少 6 个字符）' : ''}`
            : '密码强度：—';
        strengthTip.className = `text-[10px] mt-1.5 ${password && password.length < MIN_PASSWORD_LENGTH ? 'text-warn' : 'text-ink-faint'}`;
    }

    if (matchTip) {
        if (!confirm) {
            matchTip.textContent = '';
            matchTip.className = 'text-[10px] text-ink-faint mt-1.5';
        } else if (password !== confirm) {
            matchTip.textContent = '两次输入的新密码不一致';
            matchTip.className = 'text-[10px] text-danger mt-1.5';
        } else {
            matchTip.textContent = '两次输入一致';
            matchTip.className = 'text-[10px] text-ok mt-1.5';
        }
    }
}

async function savePassword() {
    if (profileState.isSavingPassword) return;

    const oldPassword = document.getElementById('profileOldPassword')?.value || '';
    const password = document.getElementById('profileNewPassword')?.value || '';
    const confirm = document.getElementById('profileConfirmPassword')?.value || '';
    const logoutOther = document.getElementById('logoutOtherSessions')?.checked !== false;

    if (!oldPassword) {
        showToast('请输入当前密码', 'warning');
        document.getElementById('profileOldPassword')?.focus();
        return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
        showToast(`新密码至少 ${MIN_PASSWORD_LENGTH} 个字符`, 'warning');
        document.getElementById('profileNewPassword')?.focus();
        return;
    }
    if (!confirm) {
        showToast('请确认新密码', 'warning');
        document.getElementById('profileConfirmPassword')?.focus();
        return;
    }
    if (password !== confirm) {
        showToast('两次输入的新密码不一致', 'warning');
        document.getElementById('profileConfirmPassword')?.focus();
        return;
    }
    if (oldPassword === password) {
        showToast('新密码不能与当前密码相同', 'warning');
        return;
    }

    const btn = document.getElementById('btnChangePassword');
    profileState.isSavingPassword = true;
    if (btn) btn.disabled = true;

    try {
        await HttpClient.put('/api/auth/password', {
            old_password: oldPassword,
            password,
            logout_other_sessions: logoutOther,
        });
        document.getElementById('profilePasswordForm')?.reset();
        const logoutCheckbox = document.getElementById('logoutOtherSessions');
        if (logoutCheckbox) logoutCheckbox.checked = true;
        updatePasswordHints();
        showToast(logoutOther ? '密码已更新，其他设备已注销' : '密码已更新', 'success');
    } catch (error) {
        console.error('修改密码失败:', error);
    } finally {
        profileState.isSavingPassword = false;
        if (btn) btn.disabled = false;
    }
}

async function uploadAvatar(file) {
    if (profileState.isUploadingAvatar) return;
    if (!file) return;

    const ext = `.${String(file.name || '').split('.').pop() || ''}`.toLowerCase();
    const typeOk = ALLOWED_AVATAR_TYPES.has(file.type) || ALLOWED_AVATAR_EXTS.has(ext);
    if (!typeOk) {
        showToast('仅支持 jpg / png / webp / gif', 'warning');
        return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
        showToast('头像文件不能超过 2MB', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const pickBtn = document.getElementById('btnPickAvatar');
    profileState.isUploadingAvatar = true;
    if (pickBtn) pickBtn.disabled = true;

    try {
        // 1) 上传文件  2) 后端返回相对路径 url（如 /uploads/avatars/xxx.png）
        const res = await HttpClient.post('/api/auth/avatar', formData);
        const url = res.data?.url;
        if (!url) {
            showToast('上传成功但未返回头像地址', 'error');
            return;
        }

        const nextUser = {
            ...(profileState.user || {}),
            avatar: url,
        };
        profileState.user = nextUser;
        applyAvatarPreview(url);
        syncSession(nextUser);
        showToast('头像已更新', 'success');
    } catch (error) {
        console.error('上传头像失败:', error);
    } finally {
        profileState.isUploadingAvatar = false;
        if (pickBtn) pickBtn.disabled = false;
    }
}

function applyAvatarPreview(url) {
    const img = document.getElementById('profileAvatarImg');
    const initial = document.getElementById('profileAvatarInitial');
    if (img) {
        img.src = url;
        img.classList.remove('hidden');
    }
    if (initial) initial.classList.add('hidden');
}

function bindEvents() {
    document.getElementById('btnSaveProfile')?.addEventListener('click', () => saveProfile());
    document.getElementById('btnChangePassword')?.addEventListener('click', () => savePassword());

    document.getElementById('profileBasicForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        saveProfile();
    });
    document.getElementById('profilePasswordForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        savePassword();
    });

    document.getElementById('profileNewPassword')?.addEventListener('input', updatePasswordHints);
    document.getElementById('profileConfirmPassword')?.addEventListener('input', updatePasswordHints);

    const pickBtn = document.getElementById('btnPickAvatar');
    const fileInput = document.getElementById('avatarFileInput');
    if (pickBtn && fileInput) {
        pickBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            const file = fileInput.files && fileInput.files[0];
            fileInput.value = '';
            if (file) uploadAvatar(file);
        });
    }
}

function init() {
    loadProfile();
}

export const pageConfig = {
    render: profileLoadingTemplate,
    init: () => init(),
};
