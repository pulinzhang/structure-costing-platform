/**
 * 登录页启动：画出页面，再绑上登录逻辑
 */

import { loginTemplate } from './template.js?v=3';
import { LoginPage } from './index.js?v=20';

const root = document.getElementById('loginRoot');
if (root) {
    root.innerHTML = loginTemplate();
    LoginPage.init();
}
