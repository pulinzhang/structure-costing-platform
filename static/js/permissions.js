/**
 * 前端权限工具：can()、菜单码映射、侧栏过滤
 * 会话字段：is_admin、permissions（来自登录 / me / touch）
 */

import { getUserSession } from './features/login/index.js?v=14';

/** 路由 page → 叶子菜单权限码（系统设置页特殊） */
const PAGE_MENU_CODE = {
    settings: 'menu:settings-system',
};

/**
 * @param {string} code
 * @returns {boolean}
 */
export function can(code) {
    if (!code) return false;
    const session = getUserSession();
    if (!session) return false;
    if (session.is_admin === true) return true;
    const permissions = Array.isArray(session.permissions) ? session.permissions : [];
    if (permissions.includes('*')) return true;
    return permissions.includes(code);
}

/**
 * @param {string} pageName
 * @returns {string}
 */
export function menuCodeForPage(pageName) {
    if (!pageName) return '';
    if (PAGE_MENU_CODE[pageName]) return PAGE_MENU_CODE[pageName];
    return `menu:${pageName}`;
}

/**
 * @param {string} pageName
 * @returns {boolean}
 */
export function canAccessPage(pageName) {
    return can(menuCodeForPage(pageName));
}

/**
 * 无权限时的回退页：优先仪表盘，否则个人资料
 * @returns {string}
 */
export function fallbackPageName() {
    if (canAccessPage('dashboard')) return 'dashboard';
    return 'settings-profile';
}

/**
 * 按权限隐藏侧栏菜单项；无可见子项的分组一并隐藏
 */
export function applySidebarPermissions() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    sidebar.querySelectorAll('a[data-page]').forEach((link) => {
        const pageName = link.getAttribute('data-page');
        const allowed = canAccessPage(pageName);
        const li = link.closest('li');
        if (li) {
            li.classList.toggle('hidden', !allowed);
        } else {
            link.classList.toggle('hidden', !allowed);
        }
    });

    // 自内向外隐藏空分组（含嵌套）
    const hideEmptyGroups = (root) => {
        root.querySelectorAll('.has-submenu').forEach((item) => {
            const submenu = item.querySelector(':scope > .submenu, :scope > ul.submenu');
            if (!submenu) return;
            const visibleChild = Array.from(submenu.children).some((child) => {
                if (!(child instanceof HTMLElement)) return false;
                if (child.classList.contains('hidden')) return false;
                // 嵌套 has-submenu 若自身未 hidden 算可见
                return true;
            });
            // 再精确：子 li 中是否有未 hidden
            const hasVisible = Array.from(submenu.querySelectorAll(':scope > li')).some(
                (li) => !li.classList.contains('hidden')
            );
            item.classList.toggle('hidden', !hasVisible);
            void visibleChild;
        });
    };

    // 多扫两轮以处理嵌套分组
    hideEmptyGroups(sidebar);
    hideEmptyGroups(sidebar);
}

/**
 * 无权限时给元素加 hidden（支持选择器或 HTMLElement）
 * @param {string} code
 * @param {...(string|Element|null|undefined)} targets
 */
export function hideIfCannot(code, ...targets) {
    if (can(code)) return;
    targets.forEach((target) => {
        const el = typeof target === 'string' ? document.querySelector(target) : target;
        if (el) el.classList.add('hidden');
    });
}

/**
 * 无权限时禁用元素
 * @param {string} code
 * @param {...(string|Element|null|undefined)} targets
 */
export function disableIfCannot(code, ...targets) {
    if (can(code)) return;
    targets.forEach((target) => {
        const el = typeof target === 'string' ? document.querySelector(target) : target;
        if (el) {
            el.disabled = true;
            el.classList.add('opacity-40', 'pointer-events-none');
        }
    });
}

if (typeof window !== 'undefined') {
    window.can = can;
    window.canAccessPage = canAccessPage;
    window.hideIfCannot = hideIfCannot;
}
