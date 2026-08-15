/**
 * Users Template
 * 用户管理
 *
 * 抽屉：编辑新增、修改密码、删除确认、授权
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

export function usersTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-[#9e9e9e]">

            <!-- 顶部概览 -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="bg-[#121215] border border-[#2c2c2c] p-3.5 flex items-center justify-between relative overflow-hidden hover:border-[#3a3a3a] transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#616161]"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-[#616161] tracking-wider">总用户数</div>
                        <div class="text-2xl font-mono font-bold text-white tracking-tight" id="statTotalUsers">-</div>
                    </div>
                    <div class="text-[#616161] pr-1">${window.svgIcon('user', 'w-4 h-4')}</div>
                </div>

                <div class="bg-[#121215] border border-[#2c2c2c] p-3.5 flex items-center justify-between relative overflow-hidden hover:border-[#2e7d32]/50 transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#4caf50] shadow-[0_0_8px_rgba(76,175,80,0.4)]"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-[#4caf50]/90 tracking-wider">启用</div>
                        <div class="text-2xl font-mono font-bold text-[#4caf50] tracking-tight" id="statActiveUsers">-</div>
                    </div>
                    <div class="flex items-center gap-1.5 px-2 py-0.5 bg-[#2e7d32]/20 border border-[#2e7d32]/40 text-[#4caf50] text-[10px]">
                        <span class="w-1.5 h-1.5 bg-[#4caf50] rounded-full animate-pulse"></span>
                        <span>启用</span>
                    </div>
                </div>

                <div class="bg-[#121215] border border-[#2c2c2c] p-3.5 flex items-center justify-between relative overflow-hidden hover:border-[#d32f2f]/50 transition-colors">
                    <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)]"></div>
                    <div class="pl-2 space-y-0.5">
                        <div class="text-[10px] font-semibold text-[#d32f2f]/90 tracking-wider">管理员/div>
                        <div class="text-2xl font-mono font-bold text-[#d32f2f] tracking-tight" id="statAdminUsers">-</div>
                    </div>
                    <div class="p-1.5 bg-[#d32f2f]/15 border border-[#d32f2f]/30 text-[#d32f2f]">
                        ${window.svgIcon('shield', 'w-4 h-4')}
                    </div>
                </div>
            </div>

            <!-- 主面板-->
            <div class="bg-[#121215] border border-[#2c2c2c]">

                <div class="p-3 border-b border-[#222222] flex flex-wrap items-center justify-between gap-3 bg-[#16161a]">
                    <div class="flex items-center gap-2 flex-wrap flex-1 min-w-[280px]">
                        <div class="relative flex-1 max-w-xs">
                            <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#616161]">
                                ${window.svgIcon('search', 'w-3.5 h-3.5')}
                            </span>
                            <input type="text" id="filterKeyword" placeholder="搜索账号 / 姓名..."
                                   class="w-full h-8 pl-8 pr-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                        </div>

                        <select id="filterIsActive"
                                class="h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-pointer focus:outline-none focus:border-[#ff5252] transition-colors">
                            <option value="">全部状总/option>
                            <option value="true">启用</option>
                            <option value="false">停用</option>
                        </select>

                        <button id="btnFilter"
                                class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>

                    <button id="btnAddUser" class="h-8 inline-flex items-center gap-1.5 bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-4 text-xs font-semibold transition-all">
                        ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                        <span>新增用户</span>
                    </button>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-[#0e0e11] border-b border-[#2c2c2c] text-[#9e9e9e]">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">用户信息</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">部门</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">联系方式</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center">状总/th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">创建时间</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="usersTableBody" class="divide-y divide-[#222222]">
                        </tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-4 py-2.5 border-t border-[#222222] bg-[#0e0e11]" id="paginationContainer">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="totalCountPagination" class="text-xs text-[#616161] font-mono"></span>
                        ${pageSizeSelectHtml('usersPageSize')}
                    </div>
                    <div class="flex items-center gap-1" id="paginationBtns"></div>
                </div>

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-[#1e1e1e] border border-[#2c2c2c] text-[#616161] mb-2">
                        ${window.svgIcon('user', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-[#9e9e9e] mb-1">暂无匹配用户</p>
                    <p class="text-[11px] text-[#616161]">请调整筛选条件，或点击右上角新增用户</p>
                </div>

                <div id="loadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#616161]">加载中..</span>
                </div>
            </div>
        </div>

        <!-- 编辑 / 新增抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="editDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh;">

            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="editDrawerTitle">编辑用户</h5>
                </div>
                <button type="button" id="closeEditDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕/button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-5" id="editDrawerContent">
                <form id="editForm" class="space-y-4">
                    <input type="hidden" id="editUserId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">登录账号 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="editUsername" required minlength="2" maxlength="50"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                        <p id="editUsernameHint" class="hidden text-[10px] text-[#616161] mt-1">编辑时账号不可修收/p>
                    </div>
                    <div id="editPasswordGroup">
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">登录密码 <span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="editPassword" minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors" autocomplete="new-password">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">姓名</label>
                            <input type="text" id="editRealName" maxlength="50"
                                   class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">所属部间/label>
                            <input type="text" id="editDepartment" maxlength="50"
                                   class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">邮箱</label>
                            <input type="email" id="editEmail" maxlength="100"
                                   class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">电话</label>
                            <input type="text" id="editPhone" maxlength="20"
                                   class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">账号状总/label>
                        <select id="editIsActive" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-colors">
                            <option value="true">启用</option>
                            <option value="false">停用</option>
                        </select>
                    </div>
                </form>
            </div>

            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelEditBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="submitEditBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <!-- 修改密码抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="passwordDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="passwordDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#f57f17]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">修改密码</h5>
                </div>
                <button type="button" id="closePasswordDrawer" class="text-[#616161] hover:text-white">✕/button>
            </div>
            <div class="flex-1 p-5 space-y-4">
                <form id="passwordForm" class="space-y-4">
                    <input type="hidden" id="passwordUserId" value="">
                    <div class="p-3 bg-[#0a0a0c] border border-[#2c2c2c] text-xs">
                        <span class="text-[#616161]">目标账号（/span>
                        <span id="passwordUsername" class="text-[#d32f2f] font-mono font-semibold ml-1"></span>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">新密码<span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="newPassword" required minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors" autocomplete="new-password">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">确认新密码<span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="confirmPassword" required minlength="4" maxlength="64"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252] transition-colors" autocomplete="new-password">
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelPasswordBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="submitPasswordBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white font-semibold px-4 py-1.5 text-xs">确认修改</button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="deleteDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="deleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#c62828]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">确认删除</h5>
                </div>
                <button type="button" id="closeDeleteDrawer" class="text-[#616161] hover:text-white">✕/button>
            </div>
            <div class="flex-1 p-5">
                <input type="hidden" id="deleteUserId" value="">
                <div class="p-3 bg-[#c62828]/15 border border-[#c62828]/40 mb-3">
                    <p class="text-xs text-[#9e9e9e]">
                        确认删除用户 <span id="deleteUsername" class="text-[#d32f2f] font-mono font-bold"></span> （
                    </p>
                </div>
                <p class="text-[11px] text-[#616161]">此操作不可恢复。/p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelDeleteBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmDeleteBtn" class="bg-[#c62828] hover:bg-[#b71c1c] text-white font-semibold px-4 py-1.5 text-xs">确认删除</button>
            </div>
        </div>

        <!-- 授权抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="grantDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[520px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="grantDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#4caf50]"></span>
                    <div>
                        <h5 class="text-xs font-semibold text-white tracking-wider">用户授权</h5>
                        <p class="text-[11px] text-[#616161] mt-0.5">用户（span id="grantUsername" class="text-[#ffffff] font-mono font-semibold"></span></p>
                    </div>
                </div>
                <button type="button" id="closeGrantDrawer" class="text-[#616161] hover:text-white">✕/button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <input type="hidden" id="grantUserId" value="">
                <p class="text-[11px] text-[#616161] mb-3">灰色项为必选，不可取消</p>
                <div id="grantTreeContainer" class="space-y-1 text-xs text-[#9e9e9e]">
                    <div class="flex items-center justify-center py-12">
                        <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                    </div>
                </div>
            </div>

            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelGrantBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="submitGrantBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white font-semibold px-5 py-1.5 text-xs">保存授权</button>
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
            ? `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-[#4caf50] bg-[#2e7d32]/20 border border-[#2e7d32]/40">
                 <span class="w-1.5 h-1.5 bg-[#4caf50] rounded-full shadow-[0_0_6px_rgba(76,175,80,0.6)]"></span>启用
               </span>`
            : `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] text-[#9e9e9e] bg-[#262626] border border-[#2c2c2c]">
                 <span class="w-1.5 h-1.5 bg-[#616161] rounded-full"></span>停用
               </span>`;

        const createdAt = formatDateTime(record.created_at);
        const isAdminUser = record.is_admin === true;
        // ES Module 内无全局 can，必须走 window.can
        const canEdit = hasPermission('op:settings-users:update');
        const canPassword = hasPermission('op:settings-users:password');
        const canDelete = hasPermission('op:settings-users:delete');
        // 管理员账号本身拥有全量权限，不对管理员展示授权入史
        const showGrant = !isAdminUser && hasPermission('op:settings-users:grant');

        const firstLetter = (record.username || '用).charAt(0).toUpperCase();
        const adminBadge = isAdminUser
            ? `<span class="ml-2 px-1.5 py-0.5 text-[9px] font-semibold bg-[#d32f2f]/20 text-[#d32f2f] border border-[#d32f2f]/40">管理员/span>`
            : '';

        const deptDisplay = record.department
            ? `<span class="text-[#9e9e9e]">${esc(record.department)}</span>`
            : `<span class="text-[#616161]">-</span>`;

        const contactDisplay = (record.email || record.phone)
            ? `<div class="text-[#9e9e9e] font-mono text-[11px]">${esc(record.email || '-')}</div>
               <div class="text-[10px] text-[#616161] font-mono">${esc(record.phone || '')}</div>`
            : `<span class="text-[#616161]">-</span>`;

        return `
        <tr class="hover:bg-[#ffffff]/[0.02] transition-colors border-b border-[#222222] group" data-id="${esc(record.id)}">
            <td class="px-4 py-2.5 whitespace-nowrap">
                <div class="flex items-center gap-3">
                    <div class="w-7 h-7 bg-[#1c1c22] border border-[#2c2c2c] flex items-center justify-center font-mono font-bold text-xs text-[#d32f2f] group-hover:border-[#d32f2f]/50 transition-colors">
                        ${esc(firstLetter)}
                    </div>
                    <div>
                        <div class="flex items-center font-mono font-semibold text-xs text-[#ffffff]">
                            ${esc(record.username)}
                            ${adminBadge}
                        </div>
                        <div class="text-[11px] text-[#9e9e9e]">${esc(record.real_name)}</div>
                    </div>
                </div>
            </td>
            <td class="px-4 py-2.5 whitespace-nowrap text-xs">${deptDisplay}</td>
            <td class="px-4 py-2.5 whitespace-nowrap">${contactDisplay}</td>
            <td class="px-4 py-2.5 text-center whitespace-nowrap">${statusBadge}</td>
            <td class="px-4 py-2.5 text-[11px] text-[#616161] font-mono whitespace-nowrap">${esc(createdAt)}</td>
            <td class="px-4 py-2.5 text-right whitespace-nowrap pr-5">
                <div class="inline-flex items-center gap-0.5 bg-[#0a0a0c] border border-[#2c2c2c] p-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity">
                    ${canEdit ? `<button class="edit-btn p-1.5 text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" title="编辑">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${showGrant ? `<button class="grant-btn p-1.5 text-[#9e9e9e] hover:text-[#4caf50] hover:bg-[#262626] transition-all" title="授权">
                        ${window.svgIcon('shield', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canPassword ? `<button class="password-btn p-1.5 text-[#9e9e9e] hover:text-[#ffb74d] hover:bg-[#262626] transition-all" title="修改密码">
                        ${window.svgIcon('gear', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canDelete ? `<button class="delete-btn p-1.5 text-[#9e9e9e] hover:text-[#ef5350] hover:bg-[#262626] transition-all" title="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : ''}
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

/**
 * 分页
 */
export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === 1 ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>上一页/button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-1 text-[#616161] text-xs">—/span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn w-6 h-6 text-[11px] font-mono ${isActive ? 'bg-[#d32f2f] border border-[#d32f2f] text-white' : 'border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-1 text-[#616161] text-xs">—/span>`;
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === totalPages ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>下一页/button>
    `;

    return buttons;
}
