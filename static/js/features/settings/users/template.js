/**
 * Users Template
 * 用户管理 — Brabus Carbon & Precision Dark
 *
 * 抽屉式交互：
 * - 编辑/新增  → editDrawer
 * - 修改密码  → passwordDrawer
 * - 删除确认  → deleteDrawer
 */

export function usersTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <!-- 面板头部 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">用户管理</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnAddUser" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-sm hover:bg-[#b71c1c] transition-all duration-150">
                            ${window.svgIcon('plus', 'w-3 h-3')}
                            新增用户
                        </button>
                    </div>
                </div>

                <!-- 筛选栏 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-center gap-3 flex-wrap">
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">账号</label>
                            <input type="text" id="filterUsername" placeholder="模糊搜索"
                                   class="w-32 h-7 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">姓名</label>
                            <input type="text" id="filterRealName" placeholder="模糊搜索"
                                   class="w-32 h-7 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">状态</label>
                            <select id="filterIsActive"
                                    class="w-28 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">全部</option>
                                <option value="true">启用</option>
                                <option value="false">停用</option>
                            </select>
                        </div>
                        <button id="btnFilter"
                                class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium bg-[#242424] text-[#787878] border border-[#272727] rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <!-- 表格 -->
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #111111 0%, #0e0e0e 100%); border-bottom: 1px solid #222222;">
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">账号</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">姓名</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">部门</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">邮箱</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">电话</th>
                                <th class="px-5 py-2.5 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">状态</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">创建时间</th>
                                <th class="px-5 py-2.5 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap w-36">操作</th>
                            </tr>
                        </thead>
                        <tbody id="usersTableBody" class="divide-y divide-[#1d1d1d]">
                        </tbody>
                    </table>
                </div>

                <!-- 分页 -->
                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1e1e1e] bg-[#141414]" id="paginationContainer">
                    <span id="totalCountPagination" class="text-[10px] text-[#484848]"></span>
                    <div class="flex items-center gap-0.5" id="paginationBtns"></div>
                </div>

                <!-- 空状态 -->
                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-10">
                    <div class="w-8 h-8 flex items-center justify-center mb-3 rounded-sm" style="background:#141414; border: 1px solid #222222;">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#3a3a3a]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#555555] mb-1">暂无用户</h5>
                    <p class="text-[10px] text-[#3a3a3a]">点击上方「新增用户」添加账号</p>
                </div>

                <!-- 加载中 -->
                <div id="loadingState" class="hidden flex items-center justify-center py-10">
                    <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        <!-- 编辑/新增抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase" id="editDrawerTitle">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    编辑用户
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="editDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editUserId" value="">

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">登录账号 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="editUsername" required minlength="2" maxlength="50"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="至少 2 个字符">
                        <p id="editUsernameHint" class="hidden text-[10px] text-[#616161] mt-1.5">编辑时账号不可修改</p>
                    </div>

                    <div id="editPasswordGroup">
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">登录密码 <span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="editPassword" minlength="4" maxlength="64"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="至少 4 个字符" autocomplete="new-password">
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">姓名</label>
                            <input type="text" id="editRealName" maxlength="50"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                   placeholder="真实姓名">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">部门</label>
                            <input type="text" id="editDepartment" maxlength="50"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                   placeholder="所属部门">
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">邮箱</label>
                            <input type="email" id="editEmail" maxlength="100"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                   placeholder="邮箱地址">
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">电话</label>
                            <input type="text" id="editPhone" maxlength="20"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                   placeholder="联系电话">
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">启用状态</label>
                        <select id="editIsActive"
                                class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded">
                            <option value="true">启用</option>
                            <option value="false">停用</option>
                        </select>
                    </div>
                </form>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="submitEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <!-- 修改密码抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="passwordDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="passwordDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    修改密码
                </h5>
                <button type="button" id="closePasswordDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <form id="passwordForm" class="p-6 space-y-5">
                    <input type="hidden" id="passwordUserId" value="">
                    <p class="text-[11px] text-[#616161]">用户：<span id="passwordUsername" class="text-[#9e9e9e] font-mono"></span></p>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">新密码 <span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="newPassword" required minlength="4" maxlength="64"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="至少 4 个字符" autocomplete="new-password">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">确认密码 <span class="text-[#d32f2f]">*</span></label>
                        <input type="password" id="confirmPassword" required minlength="4" maxlength="64"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="再次输入新密码" autocomplete="new-password">
                    </div>
                </form>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelPasswordBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="submitPasswordBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    确认修改
                </button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="deleteDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#c62828;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(198,40,40,0.5);"></span>
                    确认删除
                </h5>
                <button type="button" id="closeDeleteDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <input type="hidden" id="deleteUserId" value="">
                <div class="p-6">
                    <p class="text-[12px] text-[#9e9e9e] mb-3">
                        确定要删除用户 <span id="deleteUsername" class="text-[#d32f2f] font-mono"></span> 吗？
                    </p>
                    <p class="text-[11px] text-[#616161]">此操作不可撤销。</p>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}

/**
 * 渲染表格行
 */
export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1;
        const isActive = record.is_active !== false;
        const statusBadge = isActive
            ? '<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold bg-[#2e7d32]/20 text-[#4caf50] rounded">启用</span>'
            : '<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold bg-[#c62828]/20 text-[#ef5350] rounded">停用</span>';
        const createdAt = formatDateTime(record.created_at);

        return `
        <tr class="group transition-colors duration-150 cursor-default"
            data-id="${esc(record.id)}"
            style="${isEven ? 'background: rgba(255,255,255,0.012);' : ''}">
            <td class="px-5 py-2.5 text-[11px] text-[#b0b0b0] whitespace-nowrap font-mono tracking-wide border-b border-[#1d1d1d]">${esc(record.username)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.real_name)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.department)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.email)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.phone)}</td>
            <td class="px-5 py-2.5 text-center whitespace-nowrap border-b border-[#1d1d1d]">${statusBadge}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#484848] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(createdAt)}</td>
            <td class="px-5 py-2.5 text-center whitespace-nowrap border-b border-[#1d1d1d]">
                <div class="flex items-center justify-center gap-0.5">
                    <button class="edit-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="编辑">
                        ${window.svgIcon('pencil', 'w-3 h-3')}
                    </button>
                    <button class="password-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#ffb74d] hover:bg-[#f57f17]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="修改密码">
                        ${window.svgIcon('gear', 'w-3 h-3')}
                    </button>
                    <button class="delete-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#c62828] hover:bg-[#c62828]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="删除">
                        ${window.svgIcon('trash', 'w-3 h-3')}
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function formatDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

/**
 * 渲染分页按钮
 */
export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    buttons += `
        <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
            </svg>
        </button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white shadow-[0_0_8px_rgba(211,47,47,0.25)]' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
        buttons += `<button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
        </button>
    `;

    return buttons;
}
