/**
 * Settings Page
 * 系统设置页面逻辑
 *
 * 密度按 4 位小数；各类「率」界面按 2 位小数（‰ / %），提交时再换算为小数串。
 */

import { settingsTemplate } from './template.js?v=35';

const API = '/api/settings/system/config';
const DEFAULT_APP_NAME = '结构件自动核价平台';
const DEFAULT_DENSITY = '7.8500';
const DEFAULT_LOSS_PERMILLE = '3.00';
const DEFAULT_RECOVERY_PERCENT = '97.00';
const DEFAULT_FINISHED_FINANCE_PERCENT = '2.00';
const DEFAULT_FINISHED_MANAGEMENT_PERCENT = '2.00';
const DEFAULT_FINISHED_WAREHOUSE_PACKAGING_PERCENT = '1.00';
const DEFAULT_FINISHED_SCRAP_PERMILLE = '3.00';
const DEFAULT_FINISHED_PRETAX_PROFIT_PERCENT = '2.00';
const DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON = '150.00';
const DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT = '300.00';
const DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT = '120.00';
const DEFAULT_BODY_PANEL_MAX_THICKNESS = '3.00';
const DEFAULT_LOGIN_LOCK_MINUTES = '15';

const RATE_INPUT_IDS = [
    'settingsCompanyName',
    'settingsProcurementAgreementRemarks',
    'settingsSteelDensity',
    'settingsMaterialLossPermille',
    'settingsScrapRecoveryPercent',
    'settingsFinishedFinancePercent',
    'settingsFinishedManagementPercent',
    'settingsFinishedWarehousePackagingPercent',
    'settingsFinishedScrapPermille',
    'settingsFinishedPretaxProfitPercent',
    'settingsSwingShearProcessFeePerTon',
    'settingsBasePriceMonthMoveLimit',
    'settingsBasePriceProcessingFeeLimit',
    'settingsBodyPanelMaxThickness',
    'settingsLoginLockMinutes',
];

/** 小数率 → 界面 %（2 位小数） */
function rateToPercentDisplay(rawRate, fallback) {
    const percent = scaleDecimalByPow10(rawRate, 2, 2);
    return percent != null && compareDecimalStrings(percent, '0') >= 0 ? percent : fallback;
}

/** 小数率 → 界面 ‰（2 位小数） */
function rateToPermilleDisplay(rawRate, fallback) {
    const permille = scaleDecimalByPow10(rawRate, 3, 2);
    return permille != null && compareDecimalStrings(permille, '0') >= 0 ? permille : fallback;
}

function isPercentInRange(value) {
    return (
        value != null
        && compareDecimalStrings(value, '0') >= 0
        && compareDecimalStrings(value, '100') <= 0
    );
}

function normalizeLoginLockMinutes(raw) {
    const minutes = Number.parseInt(String(raw ?? ''), 10);
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440) {
        return DEFAULT_LOGIN_LOCK_MINUTES;
    }
    return String(minutes);
}

function isPermilleInRange(value) {
    return (
        value != null
        && compareDecimalStrings(value, '0') >= 0
        && compareDecimalStrings(value, '200') <= 0
    );
}

function setSystemInfo(appName, version) {
    const nameEl = document.getElementById('settingsAppNameText');
    const versionEl = document.getElementById('settingsVersionTag');
    if (nameEl) {
        nameEl.textContent = appName || '—';
        nameEl.title = appName || '';
    }
    if (versionEl) {
        versionEl.textContent = version || '—';
    }
}

function applyFormValues({
    companyName,
    remarks,
    density,
    lossPermille,
    recoveryPercent,
    financePercent,
    managementPercent,
    warehousePackagingPercent,
    scrapPermille,
    pretaxProfitPercent,
    swingShearFeePerTon,
    basePriceMonthMoveLimit,
    basePriceProcessingFeeLimit,
    bodyPanelMaxThickness,
    loginLockMinutes,
}) {
    const companyEl = document.getElementById('settingsCompanyName');
    if (companyEl && companyName != null) companyEl.value = companyName;
    const remarksEl = document.getElementById('settingsProcurementAgreementRemarks');
    if (remarksEl && remarks != null) remarksEl.value = remarks;
    const densityEl = document.getElementById('settingsSteelDensity');
    if (densityEl) densityEl.value = density;
    const lossEl = document.getElementById('settingsMaterialLossPermille');
    if (lossEl) lossEl.value = lossPermille;
    const recoveryEl = document.getElementById('settingsScrapRecoveryPercent');
    if (recoveryEl) recoveryEl.value = recoveryPercent;
    const financeEl = document.getElementById('settingsFinishedFinancePercent');
    if (financeEl) financeEl.value = financePercent;
    const managementEl = document.getElementById('settingsFinishedManagementPercent');
    if (managementEl) managementEl.value = managementPercent;
    const warehousePackagingEl = document.getElementById(
        'settingsFinishedWarehousePackagingPercent',
    );
    if (warehousePackagingEl) warehousePackagingEl.value = warehousePackagingPercent;
    const scrapEl = document.getElementById('settingsFinishedScrapPermille');
    if (scrapEl) scrapEl.value = scrapPermille;
    const pretaxEl = document.getElementById('settingsFinishedPretaxProfitPercent');
    if (pretaxEl) pretaxEl.value = pretaxProfitPercent;
    const swingShearEl = document.getElementById('settingsSwingShearProcessFeePerTon');
    if (swingShearEl) swingShearEl.value = swingShearFeePerTon;
    const moveLimitEl = document.getElementById('settingsBasePriceMonthMoveLimit');
    if (moveLimitEl) moveLimitEl.value = basePriceMonthMoveLimit;
    const feeLimitEl = document.getElementById('settingsBasePriceProcessingFeeLimit');
    if (feeLimitEl) feeLimitEl.value = basePriceProcessingFeeLimit;
    const bodyPanelEl = document.getElementById('settingsBodyPanelMaxThickness');
    if (bodyPanelEl) bodyPanelEl.value = bodyPanelMaxThickness;
    const loginLockEl = document.getElementById('settingsLoginLockMinutes');
    if (loginLockEl && loginLockMinutes != null) loginLockEl.value = loginLockMinutes;
}

export const SettingsPage = {
    canUpdate: false,
    appName: DEFAULT_APP_NAME,
    remarksSample: '',

    init() {
        this.canUpdate = typeof can === 'function' && can('op:settings-system:update');
        const saveBtn = document.getElementById('btnSaveSettings');
        const resetBtn = document.getElementById('btnResetSettings');
        if (!this.canUpdate) {
            saveBtn?.classList.add('hidden');
            resetBtn?.classList.add('hidden');
            RATE_INPUT_IDS.forEach((id) => {
                document.getElementById(id)?.setAttribute('disabled', 'disabled');
            });
        } else {
            saveBtn?.addEventListener('click', () => this.save());
            resetBtn?.addEventListener('click', () => this.resetToDefaults());
        }
        this.load();
    },

    resetToDefaults() {
        if (!this.canUpdate) return;
        applyFormValues({
            companyName: '',
            remarks: this.remarksSample || '',
            density: DEFAULT_DENSITY,
            lossPermille: DEFAULT_LOSS_PERMILLE,
            recoveryPercent: DEFAULT_RECOVERY_PERCENT,
            financePercent: DEFAULT_FINISHED_FINANCE_PERCENT,
            managementPercent: DEFAULT_FINISHED_MANAGEMENT_PERCENT,
            warehousePackagingPercent: DEFAULT_FINISHED_WAREHOUSE_PACKAGING_PERCENT,
            scrapPermille: DEFAULT_FINISHED_SCRAP_PERMILLE,
            pretaxProfitPercent: DEFAULT_FINISHED_PRETAX_PROFIT_PERCENT,
            swingShearFeePerTon: DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
            basePriceMonthMoveLimit: DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
            basePriceProcessingFeeLimit: DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
            bodyPanelMaxThickness: DEFAULT_BODY_PANEL_MAX_THICKNESS,
            loginLockMinutes: DEFAULT_LOGIN_LOCK_MINUTES,
        });
        showToast('已填入默认值，点击保存后生效', 'success');
    },

    async load() {
        try {
            const res = await HttpClient.get(API);
            const data = res.data || {};
            this.appName = (data.app_name || DEFAULT_APP_NAME).trim() || DEFAULT_APP_NAME;
            this.remarksSample = (data.procurement_agreement_remarks_sample || '').trim();
            setSystemInfo(this.appName, data.version || '1.0.0');

            const density = formatDecimalFixed(data.steel_density, 4);
            const recoveryPercent = (() => {
                const percent = scaleDecimalByPow10(data.scrap_recovery_rate, 2, 2);
                return percent != null && compareDecimalStrings(percent, '0') > 0
                    ? percent
                    : DEFAULT_RECOVERY_PERCENT;
            })();
            applyFormValues({
                companyName: (data.company_name || '').trim(),
                remarks: (data.procurement_agreement_remarks || '').trim()
                    || this.remarksSample,
                density: density && compareDecimalStrings(density, '0') > 0
                    ? density
                    : DEFAULT_DENSITY,
                lossPermille: rateToPermilleDisplay(
                    data.material_loss_rate, DEFAULT_LOSS_PERMILLE,
                ),
                recoveryPercent,
                financePercent: rateToPercentDisplay(
                    data.finished_finance_rate, DEFAULT_FINISHED_FINANCE_PERCENT,
                ),
                managementPercent: rateToPercentDisplay(
                    data.finished_management_rate, DEFAULT_FINISHED_MANAGEMENT_PERCENT,
                ),
                warehousePackagingPercent: rateToPercentDisplay(
                    data.finished_warehouse_packaging_rate,
                    DEFAULT_FINISHED_WAREHOUSE_PACKAGING_PERCENT,
                ),
                scrapPermille: rateToPermilleDisplay(
                    data.finished_scrap_rate, DEFAULT_FINISHED_SCRAP_PERMILLE,
                ),
                pretaxProfitPercent: rateToPercentDisplay(
                    data.finished_pretax_profit_rate, DEFAULT_FINISHED_PRETAX_PROFIT_PERCENT,
                ),
                swingShearFeePerTon: (() => {
                    const fee = formatDecimalFixed(data.swing_shear_process_fee_per_ton, 2);
                    return fee != null && compareDecimalStrings(fee, '0') >= 0
                        ? fee
                        : DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON;
                })(),
                basePriceMonthMoveLimit: (() => {
                    const limit = formatDecimalFixed(data.base_price_month_move_limit, 2);
                    return limit != null && compareDecimalStrings(limit, '0') >= 0
                        ? limit
                        : DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT;
                })(),
                basePriceProcessingFeeLimit: (() => {
                    const limit = formatDecimalFixed(data.base_price_processing_fee_limit, 2);
                    return limit != null && compareDecimalStrings(limit, '0') >= 0
                        ? limit
                        : DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT;
                })(),
                bodyPanelMaxThickness: (() => {
                    const thickness = formatDecimalFixed(data.body_panel_max_thickness, 2);
                    return thickness != null && compareDecimalStrings(thickness, '0') >= 0
                        ? thickness
                        : DEFAULT_BODY_PANEL_MAX_THICKNESS;
                })(),
                loginLockMinutes: normalizeLoginLockMinutes(data.login_lock_minutes),
            });
        } catch (error) {
            showToast(error.message || '加载系统设置失败', 'error');
        }
    },

    async save() {
        if (!this.canUpdate) {
            showToast('无保存权限', 'warning');
            return;
        }
        const appName = (this.appName || '').trim();
        const companyName = (
            document.getElementById('settingsCompanyName')?.value || ''
        ).trim();
        const remarks = (
            document.getElementById('settingsProcurementAgreementRemarks')?.value || ''
        ).trim();
        const density = parseDecimalInput(document.getElementById('settingsSteelDensity')?.value, 4);
        const lossPermille = parseDecimalInput(
            document.getElementById('settingsMaterialLossPermille')?.value, 2,
        );
        const recoveryPercent = parseDecimalInput(
            document.getElementById('settingsScrapRecoveryPercent')?.value, 2,
        );
        const financePercent = parseDecimalInput(
            document.getElementById('settingsFinishedFinancePercent')?.value, 2,
        );
        const managementPercent = parseDecimalInput(
            document.getElementById('settingsFinishedManagementPercent')?.value, 2,
        );
        const warehousePackagingPercent = parseDecimalInput(
            document.getElementById('settingsFinishedWarehousePackagingPercent')?.value, 2,
        );
        const scrapPermille = parseDecimalInput(
            document.getElementById('settingsFinishedScrapPermille')?.value, 2,
        );
        const pretaxProfitPercent = parseDecimalInput(
            document.getElementById('settingsFinishedPretaxProfitPercent')?.value, 2,
        );
        const swingShearFeePerTon = parseDecimalInput(
            document.getElementById('settingsSwingShearProcessFeePerTon')?.value, 2,
        );
        const basePriceMonthMoveLimit = parseDecimalInput(
            document.getElementById('settingsBasePriceMonthMoveLimit')?.value, 2,
        );
        const basePriceProcessingFeeLimit = parseDecimalInput(
            document.getElementById('settingsBasePriceProcessingFeeLimit')?.value, 2,
        );
        const bodyPanelMaxThickness = parseDecimalInput(
            document.getElementById('settingsBodyPanelMaxThickness')?.value, 2,
        );
        const loginLockMinutes = Number.parseInt(
            document.getElementById('settingsLoginLockMinutes')?.value || '',
            10,
        );
        if (!appName) {
            showToast('应用名称缺失，请刷新后重试', 'warning');
            return;
        }
        if (companyName.length > 100) {
            showToast('公司名称不超过 100 字', 'warning');
            return;
        }
        if (remarks.length > 20000) {
            showToast('采购协议备注不超过 20000 字', 'warning');
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
        if (!isPermilleInRange(lossPermille)) {
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
        if (!isPercentInRange(financePercent)) {
            showToast('成品财务费率须为 0~100%', 'warning');
            return;
        }
        if (!isPercentInRange(managementPercent)) {
            showToast('成品管理费率须为 0~100%', 'warning');
            return;
        }
        if (!isPercentInRange(warehousePackagingPercent)) {
            showToast('仓储+包装管理费用率须为 0~100%', 'warning');
            return;
        }
        if (!isPermilleInRange(scrapPermille)) {
            showToast('成品报废率须为 0~200‰', 'warning');
            return;
        }
        if (!isPercentInRange(pretaxProfitPercent)) {
            showToast('成品税前利润率须为 0~100%', 'warning');
            return;
        }
        if (
            swingShearFeePerTon == null
            || compareDecimalStrings(swingShearFeePerTon, '0') < 0
            || compareDecimalStrings(swingShearFeePerTon, '100000') > 0
        ) {
            showToast('摆剪工序加工费须为 0~100000 元/吨', 'warning');
            return;
        }
        if (
            basePriceMonthMoveLimit == null
            || compareDecimalStrings(basePriceMonthMoveLimit, '0') < 0
            || compareDecimalStrings(basePriceMonthMoveLimit, '100000') > 0
        ) {
            showToast('基准价月度价格变动范围须为 ±0 ~ ±100000 元/吨', 'warning');
            return;
        }
        if (
            basePriceProcessingFeeLimit == null
            || compareDecimalStrings(basePriceProcessingFeeLimit, '0') < 0
            || compareDecimalStrings(basePriceProcessingFeeLimit, '300') > 0
        ) {
            showToast('基准价加工费上限须为 0 ~ 300 元/吨', 'warning');
            return;
        }
        if (
            bodyPanelMaxThickness == null
            || compareDecimalStrings(bodyPanelMaxThickness, '0') < 0
            || compareDecimalStrings(bodyPanelMaxThickness, '100') > 0
        ) {
            showToast('车身件料厚上限须为 0 ~ 100 mm', 'warning');
            return;
        }
        if (!Number.isInteger(loginLockMinutes) || loginLockMinutes < 1 || loginLockMinutes > 1440) {
            showToast('登录锁定分钟须为 1~1440', 'warning');
            return;
        }

        const materialLossRate = scaleDecimalByPow10(lossPermille, -3, 6);
        const scrapRecoveryRate = scaleDecimalByPow10(recoveryPercent, -2, 6);
        const finishedFinanceRate = scaleDecimalByPow10(financePercent, -2, 6);
        const finishedManagementRate = scaleDecimalByPow10(managementPercent, -2, 6);
        const finishedWarehousePackagingRate = scaleDecimalByPow10(
            warehousePackagingPercent, -2, 6,
        );
        const finishedScrapRate = scaleDecimalByPow10(scrapPermille, -3, 6);
        const finishedPretaxProfitRate = scaleDecimalByPow10(pretaxProfitPercent, -2, 6);
        if (
            materialLossRate == null
            || scrapRecoveryRate == null
            || finishedFinanceRate == null
            || finishedManagementRate == null
            || finishedWarehousePackagingRate == null
            || finishedScrapRate == null
            || finishedPretaxProfitRate == null
        ) {
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
                company_name: companyName,
                procurement_agreement_remarks: remarks,
                steel_density: density,
                material_loss_rate: materialLossRate,
                scrap_recovery_rate: scrapRecoveryRate,
                finished_finance_rate: finishedFinanceRate,
                finished_management_rate: finishedManagementRate,
                finished_warehouse_packaging_rate: finishedWarehousePackagingRate,
                finished_scrap_rate: finishedScrapRate,
                finished_pretax_profit_rate: finishedPretaxProfitRate,
                swing_shear_process_fee_per_ton: swingShearFeePerTon,
                base_price_month_move_limit: basePriceMonthMoveLimit,
                base_price_processing_fee_limit: basePriceProcessingFeeLimit,
                body_panel_max_thickness: bodyPanelMaxThickness,
                login_lock_minutes: loginLockMinutes,
            });
            const data = res.data || {};
            if (data.app_name) {
                this.appName = data.app_name;
            }
            setSystemInfo(this.appName, data.version || '1.0.0');
            applyFormValues({
                companyName: (data.company_name || '').trim(),
                remarks: (data.procurement_agreement_remarks || '').trim(),
                density: data.steel_density != null
                    ? (formatDecimalFixed(data.steel_density, 4) || density)
                    : density,
                lossPermille: data.material_loss_rate != null
                    ? rateToPermilleDisplay(data.material_loss_rate, lossPermille)
                    : lossPermille,
                recoveryPercent: data.scrap_recovery_rate != null
                    ? (() => {
                        const percent = scaleDecimalByPow10(data.scrap_recovery_rate, 2, 2);
                        return percent != null && compareDecimalStrings(percent, '0') > 0
                            ? percent
                            : recoveryPercent;
                    })()
                    : recoveryPercent,
                financePercent: data.finished_finance_rate != null
                    ? rateToPercentDisplay(data.finished_finance_rate, financePercent)
                    : financePercent,
                managementPercent: data.finished_management_rate != null
                    ? rateToPercentDisplay(data.finished_management_rate, managementPercent)
                    : managementPercent,
                warehousePackagingPercent: data.finished_warehouse_packaging_rate != null
                    ? rateToPercentDisplay(
                        data.finished_warehouse_packaging_rate,
                        warehousePackagingPercent,
                    )
                    : warehousePackagingPercent,
                scrapPermille: data.finished_scrap_rate != null
                    ? rateToPermilleDisplay(data.finished_scrap_rate, scrapPermille)
                    : scrapPermille,
                pretaxProfitPercent: data.finished_pretax_profit_rate != null
                    ? rateToPercentDisplay(data.finished_pretax_profit_rate, pretaxProfitPercent)
                    : pretaxProfitPercent,
                swingShearFeePerTon: data.swing_shear_process_fee_per_ton != null
                    ? (formatDecimalFixed(data.swing_shear_process_fee_per_ton, 2)
                        || swingShearFeePerTon)
                    : swingShearFeePerTon,
                basePriceMonthMoveLimit: data.base_price_month_move_limit != null
                    ? (formatDecimalFixed(data.base_price_month_move_limit, 2)
                        || basePriceMonthMoveLimit)
                    : basePriceMonthMoveLimit,
                basePriceProcessingFeeLimit: data.base_price_processing_fee_limit != null
                    ? (formatDecimalFixed(data.base_price_processing_fee_limit, 2)
                        || basePriceProcessingFeeLimit)
                    : basePriceProcessingFeeLimit,
                bodyPanelMaxThickness: data.body_panel_max_thickness != null
                    ? (formatDecimalFixed(data.body_panel_max_thickness, 2)
                        || bodyPanelMaxThickness)
                    : bodyPanelMaxThickness,
                loginLockMinutes: normalizeLoginLockMinutes(
                    data.login_lock_minutes != null ? data.login_lock_minutes : loginLockMinutes,
                ),
            });
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
