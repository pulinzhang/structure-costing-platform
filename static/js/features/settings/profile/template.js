/**
 * Profile Template
 * 个人资料 + 安全设置（两张独立卡片，操作物理隔离）
 */

export function profileLoadingTemplate() {
    return `
        <div class="flex items-center justify-center py-20">
            <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
        </div>
    `;
}

export function profileTemplate(user = {}) {
    const username = user.username || '';
    const realName = user.real_name || '';
    const department = user.department || '';
    const email = user.email || '';
    const phone = user.phone || '';
    const avatar = user.avatar || '';
    const isActive = user.is_active !== false;
    const initial = (realName || username || 'U').charAt(0).toUpperCase();
    const displayName = realName || username || '—';
    const departmentLabel = department || '未分配';
    const hasCustomAvatar = isCustomAvatar(avatar);

    return `
        <div class="space-y-4 w-full max-w-5xl mx-auto">

            <!-- 身份摘要：与下方表单同源字段，仅只读展示 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] border-t-2 border-t-[#d32f2f] p-5"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div class="flex items-center gap-4">
                        <div class="relative group shrink-0">
                            <button type="button" id="btnPickAvatar"
                                    class="relative w-14 h-14 bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden flex items-center justify-center text-xl font-bold text-[#d32f2f] font-mono hover:border-[#d32f2f] transition-colors"
                                    title="点击更换头像" aria-label="更换头像">
                                <img id="profileAvatarImg" src="${esc(hasCustomAvatar ? avatar : '')}" alt=""
                                     class="absolute inset-0 w-full h-full object-cover ${hasCustomAvatar ? '' : 'hidden'}">
                                <span id="profileAvatarInitial" class="${hasCustomAvatar ? 'hidden' : ''}">${esc(initial)}</span>
                                <span class="absolute inset-0 bg-black/55 opacity-0 group-hover:opacity-100 flex items-center justify-center text-[10px] text-white tracking-wide transition-opacity">
                                    更换
                                </span>
                            </button>
                            <input type="file" id="avatarFileInput" accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif" class="hidden">
                        </div>
                        <div class="space-y-1">
                            <div class="flex items-center gap-3">
                                <h2 class="text-sm font-semibold text-white tracking-wide" id="headerRealName">${esc(displayName)}</h2>
                                <span id="headerStatus" class="px-2 py-0.5 text-[10px] font-semibold ${isActive ? 'bg-[#2e7d32]/20 text-[#4caf50]' : 'bg-[#c62828]/20 text-[#ef5350]'} rounded">
                                    ${isActive ? '启用' : '停用'}
                                </span>
                            </div>
                            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[#9e9e9e] font-mono">
                                <span>账号 <strong class="text-[#c8c8c8]" id="headerUsername">${esc(username || '—')}</strong></span>
                                <span class="text-[#333333] hidden sm:inline">|</span>
                                <span>部门 <strong class="text-[#c8c8c8]" id="headerDepartment">${esc(departmentLabel)}</strong></span>
                            </div>
                            <p class="text-[10px] text-[#484848]">支持 jpg / png / webp / gif，不超过 2MB</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

                <!-- 卡片 1：基本资料（手动保存） -->
                <div class="lg:col-span-2 bg-[#1e1e1e] border border-[#2c2c2c] flex flex-col"
                     style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">
                    <div class="px-5 py-3.5 border-b border-[#222222] flex items-center justify-between"
                         style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                        <h3 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide flex items-center gap-2">
                            <span class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></span>
                            基本资料
                        </h3>
                        <span class="text-[10px] text-[#616161]">修改后点击保存生效</span>
                    </div>

                    <form id="profileBasicForm" class="p-5 space-y-4 flex-1">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">登录账号</label>
                            <input type="text" id="profileUsername" value="${esc(username)}" readonly
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a]/50 border border-[#222222] rounded-sm text-[#616161] cursor-not-allowed font-mono">
                            <p class="text-[10px] text-[#484848] mt-1.5">系统登录凭证，不可自行修改</p>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">姓名</label>
                                <input type="text" id="profileRealName" value="${esc(realName)}" maxlength="50"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                       placeholder="真实姓名">
                            </div>
                            <div>
                                <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">部门</label>
                                <input type="text" id="profileDepartment" value="${esc(department)}" maxlength="50"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                       placeholder="所属部门">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">邮箱</label>
                                <input type="email" id="profileEmail" value="${esc(email)}" maxlength="100"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                       placeholder="name@company.com">
                            </div>
                            <div>
                                <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">电话</label>
                                <input type="text" id="profilePhone" value="${esc(phone)}" maxlength="20"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                       placeholder="联系电话">
                            </div>
                        </div>
                    </form>

                    <div class="px-5 py-4 border-t border-[#222222] bg-[#141414] flex items-center justify-end">
                        <button type="button" id="btnSaveProfile"
                                class="inline-flex items-center gap-1.5 bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-4 py-2 text-xs font-semibold rounded-sm transition-all">
                            ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                            保存基本资料
                        </button>
                    </div>
                </div>

                <!-- 卡片 2：安全设置 / 改密（独立提交） -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c] flex flex-col"
                     style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">
                    <div class="px-5 py-3.5 border-b border-[#222222]"
                         style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                        <h3 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide flex items-center gap-2">
                            <span class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></span>
                            安全设置
                        </h3>
                        <p class="text-[10px] text-[#616161] mt-1">须验证当前密码；成功后注销其他设备</p>
                    </div>

                    <form id="profilePasswordForm" class="p-5 space-y-4 flex-1" autocomplete="off">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">当前密码 <span class="text-[#d32f2f]">*</span></label>
                            <input type="password" id="profileOldPassword" required autocomplete="current-password"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                   placeholder="输入当前密码">
                        </div>

                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">新密码 <span class="text-[#d32f2f]">*</span></label>
                            <input type="password" id="profileNewPassword" required minlength="6" maxlength="64" autocomplete="new-password"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                   placeholder="至少 6 个字符">
                            <div class="mt-2 h-1 bg-[#222222] rounded-sm overflow-hidden">
                                <div id="passwordStrengthBar" class="h-full w-0 bg-[#616161] transition-all duration-200"></div>
                            </div>
                            <p id="passwordStrengthTip" class="text-[10px] text-[#484848] mt-1.5">密码强度：—</p>
                        </div>

                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">确认新密码 <span class="text-[#d32f2f]">*</span></label>
                            <input type="password" id="profileConfirmPassword" required minlength="6" maxlength="64" autocomplete="new-password"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all"
                                   placeholder="再次输入新密码">
                            <p id="passwordMatchTip" class="text-[10px] text-[#484848] mt-1.5"></p>
                        </div>

                        <label class="flex items-start gap-2 cursor-pointer select-none">
                            <input type="checkbox" id="logoutOtherSessions" checked
                                   class="mt-0.5 accent-[#d32f2f]">
                            <span class="text-[11px] text-[#9e9e9e] leading-relaxed">改密成功后注销其他设备登录</span>
                        </label>
                    </form>

                    <div class="px-5 py-4 border-t border-[#222222] bg-[#141414] flex items-center justify-end">
                        <button type="button" id="btnChangePassword"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] hover:border-[#d32f2f] hover:text-[#d32f2f] px-4 py-2 text-xs font-medium rounded-sm transition-all">
                            ${window.svgIcon('gear', 'w-3.5 h-3.5')}
                            确认修改密码
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function esc(value) {
    if (value == null || value === '') return '';
    if (typeof window.esc === 'function') {
        const out = window.esc(value);
        return out === '-' ? '' : out;
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isCustomAvatar(avatarUrl) {
    return typeof avatarUrl === 'string' && avatarUrl.startsWith('/uploads/avatars/');
}
