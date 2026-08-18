/**
 * Settings Page
 * 系统设置页面逻辑
 *
 * 密度 / 损耗率 / 回收率一律按十进制字符串处理（不经 Number），
 * 提交给后端为固定小数位字符串，避免 JS 尾差。
 */

import { settingsTemplate } from './template.js?v=8';

const API = '/api/settings/system/config';
const DEFAULT_DENSITY = '7.8500';
const DEFAULT_LOSS_PERMILLE = '3.0000';
const DEFAULT_RECOVERY_PERCENT = '97.0000';

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
                const density = formatDecimalFixed(data.steel_density, 4);
                densityEl.value = density && compareDecimalStrings(density, '0') > 0
                    ? density
                    : DEFAULT_DENSITY;
            }
            if (lossEl) {
                const permille = scaleDecimalByPow10(data.material_loss_rate, 3, 4);
                lossEl.value = permille != null && compareDecimalStrings(permille, '0') >= 0
                    ? permille
                    : DEFAULT_LOSS_PERMILLE;
            }
            if (recoveryEl) {
                const percent = scaleDecimalByPow10(data.scrap_recovery_rate, 2, 4);
                recoveryEl.value = percent != null && compareDecimalStrings(percent, '0') > 0
                    ? percent
                    : DEFAULT_RECOVERY_PERCENT;
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
        const density = parseDecimalInput(document.getElementById('settingsSteelDensity')?.value, 4);
        const lossPermille = parseDecimalInput(
            document.getElementById('settingsMaterialLossPermille')?.value, 4,
        );
        const recoveryPercent = parseDecimalInput(
            document.getElementById('settingsScrapRecoveryPercent')?.value, 4,
        );
        if (!appName) {
            showToast('请填写应用名称', 'warning');
            return;
        }
        if (
            density == null
            || compareDecimalStrings(density, '0') <= 0
            || compareDecimalStrings(density, '20') > 0
        ) {
            showToast('钢材密度须大于 0 且不超过 20', 'warning');
            return;
        }
        if (
            lossPermille == null
            || compareDecimalStrings(lossPermille, '0') < 0
            || compareDecimalStrings(lossPermille, '200') > 0
        ) {
            showToast('材料损耗率须为 0~200‰', 'warning');
            return;
        }
        if (
            recoveryPercent == null
            || compareDecimalStrings(recoveryPercent, '0') <= 0
            || compareDecimalStrings(recoveryPercent, '100') > 0
        ) {
            showToast('废料回收率须为 0~100%（不含 0）', 'warning');
            return;
        }

        const materialLossRate = scaleDecimalByPow10(lossPermille, -3, 6);
        const scrapRecoveryRate = scaleDecimalByPow10(recoveryPercent, -2, 6);
        if (materialLossRate == null || scrapRecoveryRate == null) {
            showToast('费率换算失败，请检查输入', 'warning');
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
                material_loss_rate: materialLossRate,
                scrap_recovery_rate: scrapRecoveryRate,
            });
            const data = res.data || {};
            if (document.getElementById('settingsAppName') && data.app_name) {
                document.getElementById('settingsAppName').value = data.app_name;
            }
            if (document.getElementById('settingsSteelDensity') && data.steel_density != null) {
                document.getElementById('settingsSteelDensity').value =
                    formatDecimalFixed(data.steel_density, 4) || density;
            }
            if (document.getElementById('settingsMaterialLossPermille') && data.material_loss_rate != null) {
                document.getElementById('settingsMaterialLossPermille').value =
                    scaleDecimalByPow10(data.material_loss_rate, 3, 4) || lossPermille;
            }
            if (document.getElementById('settingsScrapRecoveryPercent') && data.scrap_recovery_rate != null) {
                document.getElementById('settingsScrapRecoveryPercent').value =
                    scaleDecimalByPow10(data.scrap_recovery_rate, 2, 4) || recoveryPercent;
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
