/**
 * 登录页模板
 * BRABUS：克制、精密、零装饰噪音
 */

export function loginTemplate() {
    return `
<div class="min-h-screen flex items-center justify-center p-6 bg-app-deep">
    <div class="w-full max-w-[340px] bg-app-main border border-line rounded-[2px]">
        <div class="h-px w-full bg-brand"></div>

        <div class="px-6 pt-5 pb-6">
            <h1 class="text-sm font-semibold tracking-wide text-ink mb-6">系统登录</h1>

            <form id="loginForm" class="space-y-4" autocomplete="off" novalidate>
                <div>
                    <label for="loginUsername" class="block text-[11px] text-ink-muted mb-1.5">账号</label>
                    <input type="text" id="loginUsername" name="username" required
                        autocomplete="username"
                        class="w-full h-9 px-3 text-xs bg-app-deep border border-line rounded-[2px] text-ink focus:outline-none focus:border-brand transition-colors" />
                </div>

                <div>
                    <label for="loginPassword" class="block text-[11px] text-ink-muted mb-1.5">密码</label>
                    <input type="password" id="loginPassword" name="password" required
                        autocomplete="current-password"
                        class="w-full h-9 px-3 text-xs bg-app-deep border border-line rounded-[2px] text-ink focus:outline-none focus:border-brand transition-colors" />
                </div>

                <div id="loginError" class="hidden text-[11px] text-danger border border-brand-hud/40/40 bg-danger/10 px-3 py-2 rounded-[2px]"></div>

                <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" id="loginRememberMe"
                        class="brabus-check">
                    <span class="text-[11px] text-ink-muted">记住账号</span>
                </label>

                <button type="submit" id="btnLogin"
                    class="w-full h-9 mt-1 bg-brand hover:bg-brand-hover text-white text-xs font-semibold rounded-[2px] transition-colors disabled:opacity-50 disabled:pointer-events-none">
                    登录
                </button>
            </form>

            <p class="mt-4 text-[10px] leading-relaxed text-ink-dim">
                初次登录默认账号 <span class="font-mono text-ink-muted">admin</span>
                / 密码 <span class="font-mono text-ink-muted">admin123</span>
            </p>
        </div>
    </div>
</div>
`;
}
