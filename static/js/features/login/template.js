/**
 * 登录页模板
 * BRABUS：克制、精密、零装饰噪音
 */

export function loginTemplate() {
    return `
<div class="min-h-screen flex items-center justify-center p-6 bg-[#0a0a0a]">
    <div class="w-full max-w-[340px] bg-[#121212] border border-[#2c2c2c] rounded-[2px]">
        <div class="h-px w-full bg-[#d32f2f]"></div>

        <div class="px-6 pt-5 pb-6">
            <h1 class="text-sm font-semibold tracking-wide text-[#ffffff] mb-6">系统登录</h1>

            <form id="loginForm" class="space-y-4" autocomplete="off" novalidate>
                <div>
                    <label for="loginUsername" class="block text-[11px] text-[#9e9e9e] mb-1.5">账号</label>
                    <input type="text" id="loginUsername" name="username" required
                        autocomplete="username"
                        class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-[2px] text-[#ffffff] focus:outline-none focus:border-[#d32f2f] transition-colors" />
                </div>

                <div>
                    <label for="loginPassword" class="block text-[11px] text-[#9e9e9e] mb-1.5">密码</label>
                    <input type="password" id="loginPassword" name="password" required
                        autocomplete="current-password"
                        class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-[2px] text-[#ffffff] focus:outline-none focus:border-[#d32f2f] transition-colors" />
                </div>

                <div id="loginError" class="hidden text-[11px] text-[#ef5350] border border-[#c62828]/40 bg-[#c62828]/10 px-3 py-2 rounded-[2px]"></div>

                <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" id="loginRememberMe"
                        class="accent-[#d32f2f] w-3.5 h-3.5 rounded-[2px]">
                    <span class="text-[11px] text-[#9e9e9e]">记住账号</span>
                </label>

                <button type="submit" id="btnLogin"
                    class="w-full h-9 mt-1 bg-[#d32f2f] hover:bg-[#b71c1c] text-white text-xs font-semibold rounded-[2px] transition-colors disabled:opacity-50 disabled:pointer-events-none">
                    登录
                </button>
            </form>

            <p class="mt-4 text-[10px] leading-relaxed text-[#616161]">
                初次登录默认账号 <span class="font-mono text-[#9e9e9e]">admin</span>
                / 密码 <span class="font-mono text-[#9e9e9e]">admin123</span>
            </p>
        </div>
    </div>
</div>
`;
}
