/**
 * 登录页启动：画出页面，再绑上登录逻辑
 */

import { loginTemplate } from './template.js';
import { LoginPage } from './index.js';

const root = document.getElementById('loginRoot');
if (root) {
    root.innerHTML = loginTemplate();
    LoginPage.init();
}
