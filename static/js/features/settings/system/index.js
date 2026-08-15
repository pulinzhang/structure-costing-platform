/**
 * Settings Page
 * 系统设置页面逻辑
 */

import { settingsTemplate } from './template.js?v=8';

const API = '/api/settings/system/config';
const DEFAULT_DENSITY = 7.85;
const DEFAULT_LOSS_PERMILLE = 3;
const DEFAULT_RECOVERY_PERCENT = 97;

export const SettingsPage = {
    canUpdate: false,

    init() {
        this.canUpdate = typeof can === 'function' && can('op:settings-system:update');
        const saveBtn = document.getElementById('btnSaveSettings');
        if (!this.canUpdate) {
            saveBtn?.classList.add('hidden');
            ['settingsAppName', 'settingsSteelDensity', 'settingsMaterialLossPermille', 'settingsScrapRecoveryPercent']
                .forEach((id) => document.getElementById(id)?.setAttribute('disabled', 'disabled'));
        } else {
            saveBtn?.addEventListener('click', () => this.save());
        }
        this.load();
    },

    async load() {
        try {
            const res = await HttpClient.get(API);
            const data = res.data || {};
            const appNameEl = document.getElementById('settingsAppName');
            const versionEl = document.getElementById('settingsVersion');
            const densityEl = document.getElementById('settingsSteelDensity');
            const lossEl = document.getElementById('settingsMaterialLossPermille');
            const recoveryEl = document.getElementById('settingsScrapRecoveryPercent');
            if (appNameEl) appNameEl.value = data.app_name || '';
            if (versionEl) versionEl.value = data.version || '1.0.0';
            if (densityEl) {
                const density = Number(data.steel_density);
                densityEl.value = Number.isFinite(density) && density > 0
                    ? String(density)
                    : String(DEFAULT_DENSITY);
            }
            if (lossEl) {
                const rate = Number(data.material_loss_rate);
                const permille = Number.isFinite(rate) && rate >= 0
                    ? rate * 1000
                    : DEFAULT_LOSS_PERMILLE;
                lossEl.value = String(Number(permille.toFixed(4)));
            }
            if (recoveryEl) {
                const rate = Number(data.scrap_recovery_rate);
                const percent = Number.isFinite(rate) && rate > 0
                    ? rate * 100
                    : DEFAULT_RECOVERY_PERCENT;
                recoveryEl.value = String(Number(percent.toFixed(4)));
            }
        } catch (error) {
            showToast(error.message || '加载系统设置失败', 'error');
        }
    },

    async save() {
        if (!this.canUpdate) {
            showToast('无保存权限', 'warning');
            return;
        }
        const appName = (document.getElementById('settingsAppName')?.value || '').trim();
        const density = Number(document.getElementById('settingsSteelDensity')?.value);
        const lossPermille = Number(document.getElementById('settingsMaterialLossPermille')?.value);
        const recoveryPercent = Number(document.getElementById('settingsScrapRecoveryPercent')?.value);
        if (!appName) {
            showToast('请填写应用名称', 'warning');
            return;
        }
        if (!Number.isFinite(density) || density <= 0 || density > 20) {
            showToast('钢材密度须大于 0 且不超过 20', 'warning');
            return;
        }
        if (!Number.isFinite(lossPermille) || lossPermille < 0 || lossPermille > 200) {
            showToast('材料损耗率须为 0~200‰', 'warning');
            return;
        }
        if (!Number.isFinite(recoveryPercent) || recoveryPercent <= 0 || recoveryPercent > 100) {
            showToast('废料回收率须为 0~100%（不含 0）', 'warning');
            return;
        }

        const btn = document.getElementById('btnSaveSettings');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = '保存中…';
        }
        try {
            const res = await HttpClient.put(API, {
                app_name: appName,
                steel_density: density,
                material_loss_rate: lossPermille / 1000,
                scrap_recovery_rate: recoveryPercent / 100,
            });
            const data = res.data || {};
            if (document.getElementById('settingsAppName') && data.app_name) {
                document.getElementById('settingsAppName').value = data.app_name;
            }
            if (document.getElementById('settingsSteelDensity') && data.steel_density != null) {
                document.getElementById('settingsSteelDensity').value = String(data.steel_density);
            }
            if (document.getElementById('settingsMaterialLossPermille') && data.material_loss_rate != null) {
                document.getElementById('settingsMaterialLossPermille').value = String(
                    Number((Number(data.material_loss_rate) * 1000).toFixed(4)),
                );
            }
            if (document.getElementById('settingsScrapRecoveryPercent') && data.scrap_recovery_rate != null) {
                document.getElementById('settingsScrapRecoveryPercent').value = String(
                    Number((Number(data.scrap_recovery_rate) * 100).toFixed(4)),
                );
            }
            if (document.getElementById('settingsVersion') && data.version) {
                document.getElementById('settingsVersion').value = data.version;
            }
            showToast(res.message || '保存成功', 'success');
        } catch (error) {
            showToast(error.message || '保存失败', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    },
};

export const pageConfig = {
    render: settingsTemplate,
    init: () => SettingsPage.init(),
};
