/**
 * 微信内置浏览器打开帮助时补一枚「关闭」。
 * 网页用标签页关掉，这里不出现。手机微信、企业微信、电脑版微信窗口都算。
 * 关不掉时先回上一页，和报告页一样。登录页不能当回去的地址。
 */
(() => {
  if (!/MicroMessenger/i.test(navigator.userAgent || "")) return;

  const returnUrl = () => {
    const referrer = document.referrer;
    if (!referrer) return "/app";
    try {
      const parsed = new URL(referrer);
      if (parsed.origin !== window.location.origin) return "/app";
      if (parsed.pathname === "/login") return "/app";
      return referrer;
    } catch {
      return "/app";
    }
  };

  const button = document.createElement("button");
  button.type = "button";
  button.id = "wechatHelpClose";
  button.className = "wechat-help-close no-print";
  button.textContent = "关闭";
  button.addEventListener("click", () => {
    window.close();
    window.setTimeout(() => {
      if (window.closed || document.visibilityState === "hidden") return;
      if (window.history.length > 1) {
        window.history.back();
        return;
      }
      window.location.replace(returnUrl());
    }, 200);
  });
  document.body.appendChild(button);
})();
