/**
 * Users Template
 * 用户管理
 *
 * 抽屉：编辑新增、修改密码、删除确认、授权
 */

import { paginationBarHtml } from '../../../ui/page-size.js?v=11';
import { DRAWER_SHELL, DRAWER_BACKDROP, HUD_FILTER, BTN_GHOST, BTN_HUD_CREATE, BTN_SOLID, BTN_SOLID_DANGER, filterInput, filterSelect } from '../../../ui/classes.js?v=14';
import { filterBarHtml } from '../../../ui/filter-bar.js?v=6';
import { opsIconButtonHtml } from '../../../ui/hud-table.js?v=3';


export function usersTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-ink-muted">

            <!-- 顶部概览 -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="bg-app-main border border-line p-3.5 flex items-center justify-between relative overflow-hidden hover:border-line transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-ink-faint"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-ink-dim tracking-wider">总用户数</div>
                        <div class="text-2xl font-mono font-bold text-ink tracking-tight" id="statTotalUsers">-</div>
                    </div>
                    <div class="text-ink-dim pr-1">${window.svgIcon('user', 'w-4 h-4')}</div>
                </div>

                <div class="bg-app-main border border-line p-3.5 flex items-center justify-between relative overflow-hidden hover:border-ok/40/50 transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-ok shadow-[0_0_8px_rgb(var(--success-color)/0.4)]"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-ok/90 tracking-wider">启用</div>
                        <div class="text-2xl font-mono font-bold text-ok tracking-tight" id="statActiveUsers">-</div>
                    </div>
                    <div class="flex items-center gap-1.5 px-2 py-0.5 bg-ok/20 border border-ok/40/40 text-ok text-[10px]">
                        <span class="w-1.5 h-1.5 bg-ok rounded-full animate-pulse"></span>
                        <span>启用</span>
                    </div>
                </div>

                <div class="bg-app-main border border-line p-3.5 flex items-center justify-between relative overflow-hidden hover:border-brand/50 transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-brand hud-brand-glow"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-brand/90 tracking-wider">管理员</div>
                        <div class="text-2xl font-mono font-bold text-brand tracking-tight" id="statAdminUsers">-</div>
                    </div>
                    <div class="p-1.5 bg-brand/15 border border-brand/30 text-brand">
                        ${window.svgIcon('shield', 'w-4 h-4')}
                    </div>
                </div>
            </div>

            <!-- 主面板-->
            <div class="bg-app-main border border-line">

                <div class="px-5 py-3 border-b border-line-subtle bg-gradient-to-b from-app-hud to-app-deep">
                    <div class="flex items-center justify-end mb-3">
                        <button id="btnAddUser" class="${BTN_HUD_CREATE}">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            <span>新增用户</span>
                        </button>
                    </div>
                    ${filterBarHtml({
                        prefix: 'users',
                        searchId: 'btnFilter',
                        capsules: [
                            { capsuleId: 'usersCapsuleKeyword', idleLabel: '全部账号' },
                            { capsuleId: 'usersCapsuleStatus', idleLabel: '全部状态' },
                        ],
                        fieldsHtml: [
                            filterInput('filterKeyword', '账号 / 姓名', '搜索账号 / 姓名', { widthClass: 'w-full sm:w-44' }),
                            filterSelect('filterIsActive', '状态', {
                                emptyLabel: '全部状态',
                                options: [
                                    { value: 'true', label: '启用' },
                                    { value: 'false', label: '停用' },
                                ],
                            }),
                            `<button id="usersResetBtn" type="button" class="${BTN_GHOST}">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>`,
                        ].join(''),
                    })}
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[800px] text-left text-xs border-separate border-spacing-0">
                        <thead>
                            <tr class="bg-app-deep border-b border-line text-ink-muted">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">用户信息</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">部门</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider whitespace-nowrap">联系方式</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center">状态</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">创建时间</th>
                                <th class="p-0 w-9 sticky right-0 z-[3] bg-app-deep" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="usersTableBody" class="divide-y divide-line-subtle">
                        </tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'totalCountPagination', selectId: 'usersPageSize', buttonsId: 'paginationBtns', wrapperId: 'paginationContainer', wrapperClass: 'flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-t border-line-subtle bg-app-deep' })}

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-app-surface border border-line text-ink-dim mb-2">
                        ${window.svgIcon('user', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-ink-muted mb-1">暂无匹配用户</p>
                    <p class="text-[11px] text-ink-dim">请调整筛选条件，或点击右上角新增用户</p>
                </div>

                <div id="loadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-line border-brand rounded-full animate-spin"></div>
                    <span class="text-[11px] text-ink-dim">加载中..</span>
                </div>
            </div>
        </div>

        <!-- 编辑 / 新增抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity" id="editDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="editDrawer" style="display:none; max-height: 100vh;">

            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="editDrawerTitle">编辑用户</h5>
                </div>
                <button type="button" id="closeEditDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-5" id="editDrawerContent">
                <form id="editForm" class="space-y-4">
                    <input type="hidden" id="editUserId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">登录账号 <span class="text-brand">*</span></label>
                        <input type="text" id="editUsername" required minlength="2" maxlength="50"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-colors">
                        <p id="editUsernameHint" class="hidden text-[10px] text-ink-dim mt-1">编辑时账号不可修改</p>
                    </div>
                    <div id="editPasswordGroup">
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">登录密码 <span class="text-brand">*</span></label>
                        <input type="password" id="editPassword" minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors" autocomplete="new-password">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">姓名</label>
                            <input type="text" id="editRealName" maxlength="50"
                                   class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">所属部门</label>
                            <input type="text" id="editDepartment" maxlength="50"
                                   class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">邮箱</label>
                            <input type="email" id="editEmail" maxlength="100"
                                   class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">电话</label>
                            <input type="text" id="editPhone" maxlength="20"
                                   class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">账号状态</label>
                        <select id="editIsActive" class="w-full ${HUD_FILTER}">
                            <option value="true">启用</option>
                            <option value="false">停用</option>
                        </select>
                    </div>
                </form>
            </div>

            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelEditBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitEditBtn" class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <!-- 修改密码抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity" id="passwordDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[380px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="passwordDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-warn"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">修改密码</h5>
                </div>
                <button type="button" id="closePasswordDrawer" class="text-ink-dim hover:text-ink">✕</button>
            </div>
            <div class="flex-1 p-5 space-y-4">
                <form id="passwordForm" class="space-y-4">
                    <input type="hidden" id="passwordUserId" value="">
                    <div class="p-3 bg-app-hud border border-line text-xs">
                        <span class="text-ink-dim">目标账号（</span>
                        <span id="passwordUsername" class="text-brand font-mono font-semibold ml-1"></span>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">新密码<span class="text-brand">*</span></label>
                        <input type="password" id="newPassword" required minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors" autocomplete="new-password">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">确认新密码<span class="text-brand">*</span></label>
                        <input type="password" id="confirmPassword" required minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active transition-colors" autocomplete="new-password">
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface">
                <button type="button" id="cancelPasswordBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitPasswordBtn" class="bg-brand hover:bg-brand-hover text-ink-onbrand font-semibold px-4 py-1.5 text-xs">确认修改</button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity" id="deleteDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="deleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-danger"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">确认删除</h5>
                </div>
                <button type="button" id="closeDeleteDrawer" class="text-ink-dim hover:text-ink">✕</button>
            </div>
            <div class="flex-1 p-5">
                <input type="hidden" id="deleteUserId" value="">
                <div class="p-3 bg-danger/15 border border-brand-hud/40/40 mb-3">
                    <p class="text-xs text-ink-muted">
                        确认删除用户 <span id="deleteUsername" class="text-brand font-mono font-bold"></span> （
                    </p>
                </div>
                <p class="text-[11px] text-ink-dim">此操作不可恢复。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface">
                <button type="button" id="cancelDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmDeleteBtn" class="${BTN_SOLID_DANGER}">确认删除</button>
            </div>
        </div>

        <!-- 授权抽屉 -->
        <div class="${DRAWER_BACKDROP} transition-opacity" id="grantDrawerBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[520px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="grantDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-ok"></span>
                    <div>
                        <h5 class="text-xs font-semibold text-ink tracking-wider">用户授权</h5>
                        <p class="text-[11px] text-ink-dim mt-0.5">用户<span id="grantUsername" class="text-ink font-mono font-semibold"></span></p>
                    </div>
                </div>
                <button type="button" id="closeGrantDrawer" class="text-ink-dim hover:text-ink">✕</button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <input type="hidden" id="grantUserId" value="">
                <p class="text-[11px] text-ink-dim mb-3">灰色项为必选，不可取消</p>
                <div id="grantTreeContainer" class="space-y-1 text-xs text-ink-muted">
                    <div class="flex items-center justify-center py-12">
                        <div class="w-5 h-5 border-2 border-line border-brand rounded-full animate-spin"></div>
                    </div>
                </div>
            </div>

            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface">
                <button type="button" id="cancelGrantBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitGrantBtn" class="${BTN_SOLID}">保存授权</button>
            </div>
        </div>
    `;
}

/**
 * 渲染表格表
 */
export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record) => {
        const isActive = record.is_active !== false;
        const statusBadge = isActive
            ? `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-ok bg-ok/20 border border-ok/40/40">
                 <span class="w-1.5 h-1.5 bg-ok rounded-full shadow-[0_0_6px_rgb(var(--success-color)/0.6)]"></span>启用
               </span>`
            : `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-ink-muted bg-app-elevated border border-line">
                 <span class="w-1.5 h-1.5 bg-ink-faint rounded-full"></span>停用
               </span>`;

        const createdAt = formatDateTime(record.created_at);
        const isAdminUser = record.is_admin === true;
        // ES Module 内无全局 can，必须走 window.can
        const canEdit = hasPermission('op:settings-users:update');
        const canPassword = hasPermission('op:settings-users:password');
        const canDelete = hasPermission('op:settings-users:delete');
        // 管理员账号本身拥有全量权限，不对管理员展示授权入口
        const showGrant = !isAdminUser && hasPermission('op:settings-users:grant');

        const firstLetter = (record.username || '用户').charAt(0).toUpperCase();
        const adminBadge = isAdminUser
            ? `<span class="ml-2 px-1.5 py-0.5 text-[9px] font-semibold bg-brand/20 text-brand border border-brand/40">管理员</span>`
            : '';

        const deptDisplay = record.department
            ? `<span class="text-ink-muted">${esc(record.department)}</span>`
            : `<span class="text-ink-dim">-</span>`;

        const contactDisplay = (record.email || record.phone)
            ? `<div class="text-ink-muted font-mono text-[11px]">${esc(record.email || '-')}</div>
               <div class="text-[10px] text-ink-dim font-mono">${esc(record.phone || '')}</div>`
            : `<span class="text-ink-dim">-</span>`;

        return `
        <tr class="hover:bg-ink/[0.02] transition-colors border-b border-line-subtle group" data-id="${esc(record.id)}">
            <td class="px-4 py-2.5 whitespace-nowrap">
                <div class="flex items-center gap-3">
                    <div class="w-7 h-7 bg-app-surface border border-line flex items-center justify-center font-mono font-bold text-xs text-brand group-hover:border-brand/50 transition-colors">
                        ${esc(firstLetter)}
                    </div>
                    <div>
                        <div class="flex items-center font-mono font-semibold text-xs text-ink">
                            ${esc(record.username)}
                            ${adminBadge}
                        </div>
                        <div class="text-[11px] text-ink-muted">${esc(record.real_name)}</div>
                    </div>
                </div>
            </td>
            <td class="px-4 py-2.5 whitespace-nowrap text-xs">${deptDisplay}</td>
            <td class="px-4 py-2.5 whitespace-nowrap">${contactDisplay}</td>
            <td class="px-4 py-2.5 text-center whitespace-nowrap">${statusBadge}</td>
            <td class="px-4 py-2.5 text-[11px] text-ink-dim font-mono whitespace-nowrap">${esc(createdAt)}</td>
            <td class="px-1 py-2 text-right whitespace-nowrap sticky right-0 z-[2] bg-app-deep group-hover:bg-ink/[0.02]">
                <div class="inline-flex items-center justify-end">
                    ${canEdit ? opsIconButtonHtml({
                        extraClass: 'edit-btn',
                        title: '编辑',
                        icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                    }) : ''}
                    ${showGrant ? opsIconButtonHtml({
                        extraClass: 'grant-btn',
                        title: '授权',
                        icon: window.svgIcon('shield', 'w-3.5 h-3.5'),
                    }) : ''}
                    ${canPassword ? opsIconButtonHtml({
                        extraClass: 'password-btn',
                        title: '修改密码',
                        icon: window.svgIcon('gear', 'w-3.5 h-3.5'),
                    }) : ''}
                    ${canDelete ? opsIconButtonHtml({
                        extraClass: 'delete-btn',
                        danger: true,
                        title: '删除',
                        icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                    }) : ''}
                </div>
            </td>
        </tr>`;
    }).join('');
}

function hasPermission(code) {
    if (typeof window.can === 'function') {
        return window.can(code);
    }
    // can 尚未挂载时：管理员会话仍可操作；否则与编辑等按钮一致默认放表
    try {
        const raw = localStorage.getItem('brabus_user');
        const session = raw ? JSON.parse(raw) : null;
        if (session?.is_admin === true) return true;
        const permissions = Array.isArray(session?.permissions) ? session.permissions : [];
        if (permissions.includes('*') || permissions.includes(code)) return true;
    } catch {
        /* ignore */
    }
    return true;
}

function formatDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

function esc(str) {
    if (typeof window.esc === 'function') return window.esc(str);
    if (str === null || str === undefined) return '-';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
