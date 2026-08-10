/**
 * Steel Price Linked Settlement Template
 * 钢材基准价与加减价联动计算 — 极简降噪版
 */

export function steelPriceCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-[#bbb]">
            
            <!-- 1. 顶部标题栏 -->
            <div class="flex items-center justify-between pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">钢材基准价与加减价联动计算</h1>
            </div>

            <!-- 2. 查询与核算条件栏（与钢材价格表筛选风格一致） -->
            <div class="flex items-center justify-between py-2.5 border-y border-[#1e1e1e]"
                 style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('calcYear', '年度')}
                    ${filterSelect('calcMonth', '月份')}
                    ${filterSelect('calcLocation', '基地')}
                    ${filterSelect('calcSupplier', '冲压工厂')}
                    ${filterSelect('calcVehicleModel', '配套车型')}

                    <button id="calcResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <!-- 3. 数据依据与执行栏（扁平化指标展示） -->
            <div class="flex items-center justify-between border-b border-[#222] py-2.5">
                
                <!-- 3 项核心指标横排 -->
                <div class="flex items-center gap-8">
                    <a href="javascript:void(0)" onclick="openDetailModal('basePrice')" class="group">
                        <span class="text-[9px] text-[#666] block group-hover:text-[#888]">中标基价库</span>
                        <span id="cntBasePrice" class="text-xs font-mono font-bold text-[#dddddd] group-hover:text-[#fff]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </a>
                    
                    <div class="w-px h-5 bg-[#222]"></div>

                    <a href="javascript:void(0)" onclick="openDetailModal('adjustRule')" class="group">
                        <span class="text-[9px] text-[#666] block group-hover:text-[#888]">厚/宽调价规则</span>
                        <span id="cntAdjustment" class="text-xs font-mono font-bold text-[#dddddd] group-hover:text-[#fff]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </a>

                    <div class="w-px h-5 bg-[#222]"></div>

                    <a href="javascript:void(0)" onclick="openDetailModal('specs')" class="group">
                        <span class="text-[9px] text-[#666] block group-hover:text-[#888]">厚度规格行数</span>
                        <span id="cntThicknessRows" class="text-xs font-mono font-bold text-[#dddddd] group-hover:text-[#fff]">- <span class="text-[9px] font-normal text-[#555]">行</span></span>
                    </a>
                </div>

                <!-- 右侧动作按钮 -->
                <div class="flex items-center gap-3">
                    <span id="reCalcNotice" class="text-[9px] text-[#666]">
                        再次计算将覆盖现有数据
                    </span>
                    <button id="startCalcBtn"
                            class="h-7 px-4 text-[10px] bg-[#b71c1c] hover:bg-[#c62828] text-white font-medium rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                        开始计算
                    </button>
                </div>
            </div>

            <!-- 缺失数据拦截提示 -->
            <div id="dataReadyErrorBanner" class="hidden text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]">
                提示：当前所选年月缺失中标基价或调价规则，无法计算。
            </div>

            <!-- 4. 历史计算记录 -->
            <div class="pt-2">
                <div class="text-[10px] text-[#666] mb-1.5 font-medium">历史计算记录</div>
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-[#222] text-[9px] text-[#555]">
                            <th class="py-1.5 px-2 font-normal">序号</th>
                            <th class="py-1.5 px-2 font-normal">计算时间</th>
                            <th class="py-1.5 px-2 font-normal">生产基地</th>
                            <th class="py-1.5 px-2 font-normal">核价年月</th>
                            <th class="py-1.5 px-2 font-normal text-right">基价条数</th>
                            <th class="py-1.5 px-2 font-normal text-right">规则条数</th>
                            <th class="py-1.5 px-2 font-normal text-right">规格行数</th>
                            <th class="py-1.5 px-2 font-normal text-center">状态</th>
                            <th class="py-1.5 px-2 font-normal text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody class="text-[10px] divide-y divide-[#1a1a1a]">
                        ${renderLogRow(1, '2026-08-10 14:20', '芜湖基地', '2026-08', '1,280', '42', '156', '成功')}
                        ${renderLogRow(2, '2026-08-01 09:12', '青岛基地', '2026-08', '960', '38', '120', '成功')}
                        ${renderLogRow(3, '2026-07-15 16:45', '开封基地', '2026-07', '850', '30', '98', '成功')}
                        ${renderLogRow(4, '2026-07-02 11:05', '芜湖基地', '2026-07', '1,240', '42', '150', '成功')}
                        ${renderLogRow(5, '2026-06-30 18:30', '青岛基地', '2026-06', '920', '35', '115', '成功')}
                    </tbody>
                </table>
            </div>

        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <select id="${id}" class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function renderLogRow(seq, time, base, period, basePrice, adj, thick, status) {
    return `
        <tr class="hover:bg-[#141414] transition-colors text-[#999]">
            <td class="py-1.5 px-2 font-mono text-[#444]">${seq}</td>
            <td class="py-1.5 px-2 font-mono text-[#666]">${time}</td>
            <td class="py-1.5 px-2 text-[#ccc]">${base}</td>
            <td class="py-1.5 px-2 font-mono text-[#ccc]">${period}</td>
            <td class="py-1.5 px-2 font-mono text-right text-[#777]">${basePrice}</td>
            <td class="py-1.5 px-2 font-mono text-right text-[#777]">${adj}</td>
            <td class="py-1.5 px-2 font-mono text-right text-[#777]">${thick}</td>
            <td class="py-1.5 px-2 text-center text-[9px] text-[#66bb6a]">${status}</td>
            <td class="py-1.5 px-2 text-right">
                <button class="text-[9px] text-[#777] hover:text-[#fff]">查看结果</button>
            </td>
        </tr>
    `;
}