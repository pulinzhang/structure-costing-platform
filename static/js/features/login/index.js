/**
 * 登录页逻辑（对接后端 /api/auth/login）
 */

import { bindThemeSwitch } from '../../ui/theme.js?v=3';

const SESSION_KEY = 'brabus_user';
const REMEMBER_KEY = 'brabus_operator_id';

const BTN_IDLE_HTML = `登录`;
const BTN_LOADING_HTML = `登录中…`;

/**
 * 读取本地登录会话
 * @returns {{ token: string, id: number, username: string, name: string, real_name?: string, department?: string, avatar?: string } | null}
 */
export function getUserSession() {
    try {
        const raw = localStorage.getItem(SESSION_KEY);
        if (!raw) return null;
        const session = JSON.parse(raw);
        if (!session || typeof session !== 'object' || !session.token) return null;
        return session;
    } catch {
        return null;
    }
}

/**
 * 合并更新本地会话（保留 token），并同步顶栏显示
 * @param {Record<string, unknown>} patch
 */
export function updateUserSession(patch) {
    const session = getUserSession();
    if (!session) return null;
    const next = { ...session, ...patch };
    if (patch.real_name !== undefined || patch.username !== undefined) {
        next.name = next.real_name || next.username || next.name;
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    syncHeaderUser();
    return next;
}

/**
 * 清除登录状态并回到登录页
 */
export function clearUserSession() {
    const session = getUserSession();
    const token = session?.token;

    const goLogin = () => {
        localStorage.removeItem(SESSION_KEY);
        window.location.href = '/login';
    };

    if (token && typeof HttpClient !== 'undefined') {
        HttpClient.post('/api/auth/logout', null, {
            skipAuth: true,
            headers: {
                'X-Token': token,
                Authorization: `Bearer ${token}`,
            },
        }).catch(() => {}).finally(goLogin);
        return;
    }
    goLogin();
}

/**
 * 定时探活：只检查会话是否仍有效，不续期。
 * 空闲 15 分钟无业务请求后，下次探活会 401 并回登录页。
 */
export function startTokenHeartbeat(intervalMs = 60 * 1000) {
    if (window.__tokenHeartbeatTimer) {
        clearInterval(window.__tokenHeartbeatTimer);
    }

    const beat = () => {
        const session = getUserSession();
        if (!session?.token || typeof HttpClient === 'undefined') return;
        if (document.hidden) return;
        HttpClient.post('/api/auth/touch', null)
            .then((res) => {
                const user = res?.data;
                if (!user) return;
                updateUserSession({
                    is_admin: user.is_admin === true,
                    permissions: Array.isArray(user.permissions) ? user.permissions : [],
                    real_name: user.real_name,
                    username: user.username,
                    avatar: user.avatar,
                    department: user.department,
                    email: user.email,
                });
            })
            .catch(() => {});
    };

    // 进入系统先续一次
    beat();
    window.__tokenHeartbeatTimer = setInterval(beat, intervalMs);

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) beat();
    });
}

function getDisplayName(session) {
    if (!session) return '用户';
    return session.real_name || session.name || session.username || '用户';
}

function getDisplayInitial(name) {
    const text = String(name || '').trim();
    if (!text) return '?';
    return text.charAt(0).toUpperCase();
}

/**
 * 同步顶栏头像菜单（姓名只在下拉里显示）
 */
export function syncHeaderUser() {
    const session = getUserSession();
    const name = getDisplayName(session);
    const meta = session?.department || session?.username || '';
    const initial = getDisplayInitial(name);
    const avatarUrl = typeof session?.avatar === 'string' ? session.avatar : '';
    const hasCustomAvatar = avatarUrl.startsWith('/uploads/avatars/');

    const avatarInitial = document.getElementById('userAvatarInitial');
    const menuAvatar = document.getElementById('userMenuAvatar');
    const menuName = document.getElementById('userMenuName');
    const menuRole = document.getElementById('userMenuRole');

    if (avatarInitial) {
        if (hasCustomAvatar) {
            avatarInitial.innerHTML = `<img src="${avatarUrl.replace(/"/g, '')}" alt="" class="w-full h-full object-cover rounded-full">`;
            avatarInitial.classList.add('w-full', 'h-full', 'overflow-hidden', 'flex', 'items-center', 'justify-center');
        } else {
            avatarInitial.textContent = initial;
        }
    }

    if (menuAvatar) {
        if (hasCustomAvatar) {
            menuAvatar.innerHTML = `<img src="${avatarUrl.replace(/"/g, '')}" alt="" class="w-full h-full object-cover rounded-full">`;
            menuAvatar.classList.add('overflow-hidden', 'p-0');
        } else {
            menuAvatar.textContent = initial;
            menuAvatar.classList.remove('p-0');
        }
    }

    if (menuName) menuName.textContent = name;
    if (menuRole) menuRole.textContent = meta || '—';
}

function setUserMenuOpen(isOpen) {
    const btn = document.getElementById('userMenuBtn');
    const panel = document.getElementById('userMenuPanel');
    if (!btn || !panel) return;

    btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    panel.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
    panel.classList.toggle('hidden', !isOpen);
}

/**
 * 绑定顶栏用户菜单（只初始化一次）
 */
export function initUserMenu() {
    const root = document.getElementById('userMenuRoot');
    const btn = document.getElementById('userMenuBtn');
    const panel = document.getElementById('userMenuPanel');
    const logoutBtn = document.getElementById('userLogoutBtn');
    if (!root || !btn || !panel || btn.dataset.bound === '1') return;

    btn.dataset.bound = '1';

    btn.addEventListener('click', (event) => {
        event.stopPropagation();
        const isOpen = btn.getAttribute('aria-expanded') === 'true';
        setUserMenuOpen(!isOpen);
    });

    panel.addEventListener('click', (event) => {
        if (event.target.closest('a[href]')) {
            setUserMenuOpen(false);
        }
    });

    document.addEventListener('click', (event) => {
        if (!root.contains(event.target)) {
            setUserMenuOpen(false);
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            setUserMenuOpen(false);
        }
    });

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            clearUserSession();
        });
    }

    bindThemeSwitch(document.getElementById('userThemeLightSwitch'));
    syncHeaderUser();
}

function showLoginError(message) {
    const el = document.getElementById('loginError');
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
}

function clearLoginError() {
    const el = document.getElementById('loginError');
    if (!el) return;
    el.textContent = '';
    el.classList.add('hidden');
}

function encryptPassword(publicKeySpki, password) {
    const forgeApi = window.forge;
    if (!forgeApi?.pki || !forgeApi.md?.sha256) {
        throw new Error('登录加密组件没有加载，请刷新页面后再试');
    }
    const der = forgeApi.util.decode64(publicKeySpki);
    const publicKey = forgeApi.pki.publicKeyFromAsn1(forgeApi.asn1.fromDer(der));
    const encrypted = publicKey.encrypt(forgeApi.util.encodeUtf8(password), 'RSA-OAEP', {
        md: forgeApi.md.sha256.create(),
        mgf1: { md: forgeApi.md.sha256.create() },
    });
    return forgeApi.util.encode64(encrypted);
}

function setButtonLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.innerHTML = isLoading ? BTN_LOADING_HTML : BTN_IDLE_HTML;
}

export const LoginPage = {
    init() {
        const form = document.getElementById('loginForm');
        const usernameInput = document.getElementById('loginUsername');
        const rememberInput = document.getElementById('loginRememberMe');

        const remembered = localStorage.getItem(REMEMBER_KEY);
        if (remembered && usernameInput) {
            usernameInput.value = remembered;
            if (rememberInput) rememberInput.checked = true;
        }

        if (form) {
            form.addEventListener('submit', (event) => this.handleSubmit(event));
        }

        usernameInput?.focus();
    },

    async handleSubmit(event) {
        event.preventDefault();
        clearLoginError();

        const btn = document.getElementById('btnLogin');
        const username = (document.getElementById('loginUsername')?.value || '').trim();
        const password = document.getElementById('loginPassword')?.value || '';
        const remember = document.getElementById('loginRememberMe')?.checked === true;

        if (!username) {
            showLoginError('请输入账号');
            document.getElementById('loginUsername')?.focus();
            return;
        }
        if (!password) {
            showLoginError('请输入密码');
            document.getElementById('loginPassword')?.focus();
            return;
        }

        setButtonLoading(btn, true);

        try {
            const keyRes = await HttpClient.get('/api/auth/login-key', { skipAuth: true, skipToast: true });
            const key = keyRes.data || {};
            const passwordCipher = await encryptPassword(key.public_key_spki, password);
            const res = await HttpClient.post('/api/auth/login', {
                username,
                key_id: key.key_id,
                password_cipher: passwordCipher,
            }, { skipAuth: true, skipToast: true });
            const payload = res.data || {};
            const user = payload.user || {};

            const userSession = {
                token: payload.token,
                id: user.id,
                username: user.username,
                real_name: user.real_name || '',
                name: user.real_name || user.username,
                email: user.email || '',
                department: user.department || '',
                avatar: user.avatar || '',
                is_admin: user.is_admin === true,
                permissions: Array.isArray(user.permissions) ? user.permissions : [],
            };

            localStorage.setItem(SESSION_KEY, JSON.stringify(userSession));

            if (remember) {
                localStorage.setItem(REMEMBER_KEY, username);
            } else {
                localStorage.removeItem(REMEMBER_KEY);
            }

            if (typeof showToast === 'function') {
                showToast('登录成功', 'success');
            }

            window.location.href = '/app#/dashboard';
        } catch (error) {
            showLoginError(error.message || '登录失败');
            setButtonLoading(btn, false);
        }
    },
};
