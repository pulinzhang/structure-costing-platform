/**
 * 微信内置浏览器打开帮助时补一枚「关闭」。
 * 网页用标签页关掉，这里不出现。手机微信、企业微信、电脑版微信窗口都算。
 */
(() => {
  if (!/MicroMessenger/i.test(navigator.userAgent || "")) return;

  const button = document.createElement("button");
  button.type = "button";
  button.id = "wechatHelpClose";
  button.className = "wechat-help-close no-print";
  button.textContent = "关闭";
  button.addEventListener("click", () => {
    window.close();
    window.setTimeout(() => {
      if (window.closed || document.visibilityState === "hidden") return;
      window.location.replace("/");
    }, 200);
  });
  document.body.appendChild(button);
})();
