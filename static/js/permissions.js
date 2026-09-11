/**
 * 前端权限工具：can()、菜单码映射、侧栏过滤
 * 会话字段：is_admin、permissions（来自登录 / me / touch）
 */

import { getUserSession } from './features/login/index.js?v=15';

/** 路由 page → 叶子菜单权限码（系统设置页 / Workspace 共用产品结构权限） */
const PAGE_MENU_CODE = {
    settings: 'menu:settings-system',
    'bom-viz': 'menu:bom-structure',
    // 核价分组下的引擎页（分组码为 menu:costing）
    costing: 'menu:costing-engine',
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
    if (pageName === 'costing') {
        // 兼容旧授权仅勾选 menu:costing 的情况
        return can('menu:costing-engine') || can('menu:costing');
    }
    if (pageName === 'assembly-cost-calc') {
        return can('menu:assembly-cost-calc');
    }
    if (pageName === 'assembly-cost') {
        return can('menu:assembly-cost');
    }
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

    const hideEmptyGroups = (root) => {
        root.querySelectorAll('.has-submenu').forEach((item) => {
            const submenu = item.querySelector(':scope > .submenu, :scope > ul.submenu');
            if (!submenu) return;
            const hasVisible = Array.from(submenu.querySelectorAll(':scope > li')).some(
                (li) => !li.classList.contains('hidden')
            );
            item.classList.toggle('hidden', !hasVisible);
        });
    };

    hideEmptyGroups(sidebar);
    hideEmptyGroups(sidebar);
}

if (typeof window !== 'undefined') {
    window.can = can;
    window.canAccessPage = canAccessPage;
}
