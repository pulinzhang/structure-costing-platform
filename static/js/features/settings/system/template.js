/**
 * Settings Template
 * 系统设置 — 卡片网格布局
 */

function fieldLabel(text, tip) {
    const tipHtml = tip
        ? `<span class="inline-flex text-[#555555] hover:text-[#9e9e9e] cursor-help"
                 title="${tip}">${window.svgIcon('info-circle', 'w-3 h-3')}</span>`
        : '';
    return `
        <label class="mb-1.5 flex items-center gap-1.5 text-[10px] font-medium tracking-[0.06em] text-[#8E8E93]">
            <span>${text}</span>
            ${tipHtml}
        </label>
    `;
}

function suffixInput({
    id,
    label,
    tip = '',
    unit,
    step,
    min,
    max,
    placeholder,
    helper = '',
    inputmode = 'decimal',
}) {
    return `
        <div>
            ${fieldLabel(label, tip)}
            <div class="relative">
                <input id="${id}" type="number" step="${step}" min="${min}" max="${max}"
                       inputmode="${inputmode}"
                       class="w-full h-9 pl-3 pr-12 text-xs text-right bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] tabular-nums focus:outline-none focus:border-[#ff5252] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                       placeholder="${placeholder}">
                <span class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-[10px] text-[#616161]">${unit}</span>
            </div>
            ${helper ? `<p class="mt-1 text-[10px] leading-relaxed text-[#555555]">${helper}</p>` : ''}
        </div>
    `;
}

export function settingsTemplate() {
    const densityField = suffixInput({
        id: 'settingsSteelDensity',
        label: '钢材密度',
        tip: '毛坯重量公式使用；默认 7.85',
        unit: 'g/cm³',
        step: '0.01',
        min: '0.01',
        max: '20',
        placeholder: '7.85',
        helper: '用于毛坯重量计算',
    });
    const lossField = suffixInput({
        id: 'settingsMaterialLossPermille',
        label: '冲压材料损耗率',
        tip: '采购按 (1+损耗率) 买料；默认 3‰',
        unit: '‰',
        step: '0.01',
        min: '0',
        max: '200',
        placeholder: '3',
        helper: '采购加量系数',
    });
    const recoveryField = suffixInput({
        id: 'settingsScrapRecoveryPercent',
        label: '废料回收率',
        tip: '废料扣除 × 回收率（含损耗废料）；默认 97%',
        unit: '%',
        step: '0.01',
        min: '0.01',
        max: '100',
        placeholder: '97',
        helper: '废料价值回收比例',
    });
    const financeField = suffixInput({
        id: 'settingsFinishedFinancePercent',
        label: '财务费率',
        tip: '默认 2%',
        unit: '%',
        step: '0.01',
        min: '0',
        max: '100',
        placeholder: '2',
    });
    const managementField = suffixInput({
        id: 'settingsFinishedManagementPercent',
        label: '管理费率',
        tip: '默认 2%',
        unit: '%',
        step: '0.01',
        min: '0',
        max: '100',
        placeholder: '2',
    });
    const warehousePackagingField = suffixInput({
        id: 'settingsFinishedWarehousePackagingPercent',
        label: '仓储+包装，管理费用率',
        tip: '默认 1%',
        unit: '%',
        step: '0.01',
        min: '0',
        max: '100',
        placeholder: '1',
    });
    const scrapField = suffixInput({
        id: 'settingsFinishedScrapPermille',
        label: '报废率',
        tip: '默认 3‰',
        unit: '‰',
        step: '0.01',
        min: '0',
        max: '200',
        placeholder: '3',
    });
    const pretaxField = suffixInput({
        id: 'settingsFinishedPretaxProfitPercent',
        label: '税前利润率',
        tip: '默认 2%',
        unit: '%',
        step: '0.01',
        min: '0',
        max: '100',
        placeholder: '2',
    });
    const swingShearFeeField = suffixInput({
        id: 'settingsSwingShearProcessFeePerTon',
        label: '摆剪钢价加价',
        tip: '摆剪件材料核算时加到联动钢价上；默认 150 元/吨。改了只影响之后重算。',
        unit: '元/吨',
        step: '0.01',
        min: '0',
        max: '100000',
        placeholder: '150',
        helper: '工艺确认表出现「摆剪」的零件会带此加价',
    });

    return `
        <div class="relative">
            <div class="grid grid-cols-1 xl:grid-cols-12 gap-4">
                <!-- 系统信息 -->
                <section class="xl:col-span-12 bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-2.5 border-b border-[#222222] flex items-center gap-2">
                        <div class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#616161]">系统信息</h3>
                    </div>
                    <div class="px-4 py-4 grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
                        <div class="md:col-span-8 min-w-0">
                            <div class="text-[10px] text-[#555555] tracking-[0.06em] mb-1">应用名称</div>
                            <div id="settingsAppNameText" class="text-sm text-[#F0F0F2] truncate">—</div>
                        </div>
                        <div class="md:col-span-4">
                            <div class="text-[10px] text-[#555555] tracking-[0.06em] mb-1">当前版本</div>
                            <span id="settingsVersionTag"
                                  class="inline-flex items-center h-6 px-2 text-[11px] tracking-[0.04em] text-[#9e9e9e] bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm">—</span>
                        </div>
                    </div>
                </section>

                <!-- 材料基础参数 -->
                <section class="xl:col-span-5 h-full flex flex-col bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-2.5 border-b border-[#222222] flex items-center gap-2 shrink-0">
                        <div class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#616161]">材料基础参数</h3>
                    </div>
                    <div class="p-4 space-y-4 flex-1">
                        ${densityField}
                        ${lossField}
                        ${recoveryField}
                        ${swingShearFeeField}
                    </div>
                </section>

                <!-- 成品费率 -->
                <section class="xl:col-span-7 h-full flex flex-col bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-2.5 border-b border-[#222222] flex items-center gap-2 shrink-0">
                        <div class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#616161]">成品费率</h3>
                    </div>
                    <div class="p-4 grid grid-cols-1 sm:grid-cols-2 gap-4 content-start flex-1">
                        ${financeField}
                        ${managementField}
                        ${warehousePackagingField}
                        ${scrapField}
                        ${pretaxField}
                    </div>
                </section>

                <!-- 采购协议备注 -->
                <section class="xl:col-span-12 bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-2.5 border-b border-[#222222] flex items-center gap-2">
                        <div class="w-[2px] h-3.5 bg-[#d32f2f] rounded-[1px]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#616161]">采购协议备注</h3>
                    </div>
                    <div class="px-4 py-4 space-y-4">
                        <div>
                            ${fieldLabel('公司名称', '采购协议甲方；未填则导出为空')}
                            <input id="settingsCompanyName" type="text" maxlength="100"
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                   placeholder="芜湖普威技研有限公司">
                            <p class="mt-1 text-[10px] leading-relaxed text-[#555555]">导出《批量零部件价格协议》时作为甲方</p>
                        </div>
                        ${fieldLabel('文尾条款', '导出《批量零部件价格协议》时写入「备注」区')}
                        <textarea id="settingsProcurementAgreementRemarks" rows="18" maxlength="20000"
                                  class="w-full min-h-[18rem] px-3 py-2 text-xs font-mono leading-relaxed bg-[#0a0a0a] border border-[#2c2c2c] rounded-sm text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-colors disabled:opacity-50 disabled:cursor-not-allowed resize-y"
                                  placeholder=""></textarea>
                        <p class="mt-1 text-[10px] leading-relaxed text-[#555555]">
                            空框时显示普威样例，改完后保存才进入导出。占位符：
                            <span class="font-mono text-[#9e9e9e]">{company_name}</span>
                            <span class="font-mono text-[#9e9e9e]">{start_year}</span>
                            <span class="font-mono text-[#9e9e9e]">{start_month}</span>
                            <span class="font-mono text-[#9e9e9e]">{end_year}</span>
                            <span class="font-mono text-[#9e9e9e]">{end_month}</span>
                            <span class="font-mono text-[#9e9e9e]">{end_day}</span>
                            。空行分段，每段导出成 Excel 一行。
                        </p>
                    </div>
                </section>
            </div>

            <!-- 底部操作栏 -->
            <div id="settingsActionBar"
                 class="sticky bottom-0 z-[10] mt-6 flex items-center justify-between gap-3 px-4 py-3 bg-[#121212]/95 border border-[#2c2c2c] backdrop-blur-sm">
                <p class="text-[10px] text-[#555555] hidden sm:block">修改后请保存；恢复默认仅填充表单，不会自动提交</p>
                <div class="flex items-center gap-2 ml-auto">
                    <button id="btnResetSettings" type="button"
                            class="inline-flex items-center gap-1.5 h-9 px-3 text-xs font-medium text-[#9e9e9e] border border-[#2c2c2c] rounded-sm bg-transparent hover:border-[#9e9e9e] hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                        ${window.svgIcon('refresh', 'w-3.5 h-3.5')}
                        恢复默认
                    </button>
                    <button id="btnSaveSettings" type="button"
                            class="inline-flex items-center gap-1.5 h-9 px-4 text-xs font-semibold text-white bg-[#d32f2f] border border-[#d32f2f] rounded-sm hover:bg-[#b71c1c] hover:border-[#b71c1c] active:scale-[0.98] transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                        ${window.svgIcon('check-circle', 'w-3.5 h-3.5')}
                        保存设置
                    </button>
                </div>
            </div>
        </div>
    `;
}
