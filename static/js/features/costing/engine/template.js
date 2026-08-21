/**
 * 月度智能自动核价引擎 — 页面 UI 模版 (BRABUS Pure Industrial Spec)
 * 原则：中文决定效率，英文负责氛围
 */

/** 英文微型角标（烘托，不抢主阅读流） */
const enMark = 'text-[9px] font-mono uppercase tracking-[0.16em] text-zinc-600';

export const costingTemplate = () => `
<div class="p-6 bg-[#030304] text-zinc-300 min-h-screen font-sans selection:bg-[#FF1E27] selection:text-white">
  <!-- 头部控制栏 -->
  <div class="border border-[#1A1A20] bg-[#0A0A0D] p-5 mb-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-2 h-6 bg-[#FF1E27]"></div>
        <div>
          <h1 class="text-base font-bold tracking-[0.12em] text-white">
            月度核价控制台
          </h1>
          <p class="${enMark} mt-0.5">// ENGINE</p>
        </div>
      </div>

      <!-- 全局状态指示 -->
      <div class="flex items-center gap-3 bg-[#121216] border border-[#22222A] px-4 py-2">
        <div id="engineReadyLed" class="w-2.5 h-2.5 bg-zinc-700 shrink-0"></div>
        <div>
          <div class="text-[10px] tracking-[0.08em] text-zinc-400">系统就绪状态</div>
          <div id="engineReadyStatusText" class="text-xs font-bold tracking-[0.06em] text-zinc-500 truncate mt-0.5">
            待命
          </div>
        </div>
      </div>
    </div>

    <div class="h-px bg-[#1A1A20] my-5"></div>

    <!-- 筛选与操作硬核面板 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
      <!-- 基地 -->
      <div>
        <label class="block text-[10px] tracking-[0.08em] text-zinc-400 mb-1.5">
          生产基地 <span class="${enMark}">// LOCATION</span>
        </label>
        <select id="engineLocation" class="w-full bg-[#121216] border border-[#22222A] text-white text-xs font-mono px-3 py-2 rounded-none focus:border-[#FF1E27] focus:outline-none">
          <option value="">加载中…</option>
        </select>
      </div>

      <!-- 年份 -->
      <div>
        <label class="block text-[10px] tracking-[0.08em] text-zinc-400 mb-1.5">
          核算年度 <span class="${enMark}">// YEAR</span>
        </label>
        <select id="engineYear" class="w-full bg-[#121216] border border-[#22222A] text-white text-xs font-mono px-3 py-2 rounded-none focus:border-[#FF1E27] focus:outline-none">
          <option value="2026">2026</option>
          <option value="2025">2025</option>
          <option value="2024">2024</option>
        </select>
      </div>

      <!-- 月份 -->
      <div>
        <label class="block text-[10px] tracking-[0.08em] text-zinc-400 mb-1.5">
          核算月份 <span class="${enMark}">// MONTH</span>
        </label>
        <select id="engineMonth" class="w-full bg-[#121216] border border-[#22222A] text-white text-xs font-mono px-3 py-2 rounded-none focus:border-[#FF1E27] focus:outline-none">
          ${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${String(i + 1).padStart(2, '0')}月</option>`).join('')}
        </select>
      </div>

      <!-- 检查就绪按钮 -->
      <div>
        <button id="engineReadyBtn" type="button" class="w-full h-[38px] bg-[#1A1A20] hover:bg-[#22222A] border border-[#33333E] text-white text-xs font-bold tracking-[0.08em] py-2 px-4 rounded-none transition-colors flex flex-col items-center justify-center gap-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none">
          <span>检查就绪</span>
          <span class="${enMark} text-zinc-500">CHECK READY</span>
        </button>
      </div>

      <!-- 启动核价按钮 -->
      <div>
        <button id="engineStartBtn" type="button" class="w-full h-[38px] bg-[#FF1E27] hover:bg-[#D6151E] disabled:bg-[#1A1A20] disabled:text-zinc-600 disabled:border-[#22222A] text-white text-xs font-bold tracking-[0.08em] py-2 px-4 rounded-none transition-colors flex flex-col items-center justify-center gap-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none border border-transparent disabled:border-[#22222A]">
          <span>启动核算引擎</span>
          <span class="text-[9px] font-mono uppercase tracking-[0.14em] text-white/55">LAUNCH ENGINE</span>
        </button>
      </div>
    </div>

    <div id="engineStartHint" class="hidden mt-4 text-[10px] tracking-wide"></div>
  </div>

  <!-- 实时进度面板 -->
  <div id="engineProgressPanel" class="hidden border border-[#1A1A20] bg-[#0A0A0D] p-5 mb-6">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span id="engineProgressSpinner" class="w-2 h-2 bg-[#FF1E27] animate-ping"></span>
        <div>
          <span id="engineProgressTitle" class="text-xs font-bold text-white tracking-[0.08em]">引擎运行中</span>
          <span class="${enMark} ml-2">PROCESSING</span>
        </div>
      </div>
      <span id="engineProgressPercent" class="text-sm font-mono font-bold text-[#FF1E27]">0%</span>
    </div>
    <div class="w-full bg-[#121216] border border-[#22222A] h-2 mb-2">
      <div id="engineProgressBar" class="bg-[#FF1E27] h-full transition-all duration-300" style="width: 0%"></div>
    </div>
    <div id="engineProgressMsg" class="text-[10px] font-mono text-zinc-400 truncate">正在初始化…</div>
  </div>

  <!-- 结果提示面板 -->
  <div id="engineResultPanel" class="hidden border border-[#1A1A20] bg-[#0A0A0D] p-5 mb-6">
    <div class="flex items-center justify-between gap-4">
      <div>
        <div class="text-[10px] tracking-[0.08em] text-zinc-400">执行结果 <span class="${enMark}">// RESULT</span></div>
        <div id="engineResultStatus" class="text-sm font-bold tracking-[0.06em] mt-0.5">—</div>
      </div>
      <div id="engineResultCounts" class="text-xs font-mono text-zinc-400">
        成功 0 · 失败 0 · 跳过 0
      </div>
    </div>
  </div>

  <!-- 核心三列网格：门禁检查 / 补算项 / 执行节点范围 -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

    <!-- 基础数据卡口检查 -->
    <div id="engineGateHardPanel" class="border border-[#1A1A20] bg-[#0A0A0D] flex flex-col">
      <div class="p-3 bg-[#121216] border-b border-[#1A1A20] flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span class="w-1.5 h-3 bg-[#FF1E27] shrink-0"></span>
          <div class="min-w-0">
            <span class="text-xs font-bold text-white tracking-[0.08em]">强约束硬停检查</span>
            <span class="${enMark} ml-2">GATES</span>
          </div>
        </div>
        <span id="engineHardStopBadge" class="text-[9px] tracking-[0.06em] bg-[#121216] text-zinc-500 border border-[#22222A] px-2 py-0.5 rounded-none shrink-0">未检查</span>
      </div>
      <div id="engineGateHardList" class="divide-y divide-[#1A1A20] min-h-[160px] flex-1">
        <div class="px-3 py-8 text-center text-[10px] tracking-wide text-zinc-600">请先点击「检查就绪」</div>
      </div>
    </div>

    <!-- 派生/补算项目 -->
    <div class="border border-[#1A1A20] bg-[#0A0A0D] flex flex-col">
      <div class="p-3 bg-[#121216] border-b border-[#1A1A20] flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span class="w-1.5 h-3 bg-amber-400 shrink-0"></span>
          <div class="min-w-0">
            <span class="text-xs font-bold text-white tracking-[0.08em]">待自动补算项</span>
            <span class="${enMark} ml-2">AUTO_CALC</span>
          </div>
        </div>
        <span id="engineAnnualBadge" class="text-[10px] text-zinc-600 shrink-0">未检查</span>
      </div>
      <div id="engineGateAnnualList" class="divide-y divide-[#1A1A20] min-h-[160px] flex-1">
        <div class="px-3 py-8 text-center text-[10px] tracking-wide text-zinc-600">请先点击「检查就绪」</div>
      </div>
    </div>

    <!-- 执行计划范围 -->
    <div class="border border-[#1A1A20] bg-[#0A0A0D] flex flex-col">
      <div class="p-3 bg-[#121216] border-b border-[#1A1A20]">
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-3 bg-emerald-400 shrink-0"></span>
          <div>
            <span class="text-xs font-bold text-white tracking-[0.08em]">覆盖范围</span>
            <span class="${enMark} ml-2">PLAN</span>
          </div>
        </div>
      </div>
      <div class="p-4 space-y-4 flex-1">
        <div>
          <div class="text-[10px] tracking-[0.08em] text-zinc-400 mb-2">
            冲压供应商节点 <span class="${enMark}">// SUPPLIER</span>
          </div>
          <div id="enginePlanSuppliers" class="grid grid-cols-1 gap-1.5">
            <div class="border border-dashed border-[#1E1E26] bg-[#0A0A0D] px-2 py-3 text-[10px] text-zinc-600 text-center">暂无数据</div>
          </div>
        </div>
        <div>
          <div class="text-[10px] tracking-[0.08em] text-zinc-400 mb-2">
            车型 BOM 范围 <span class="${enMark}">// L0 BOM</span>
          </div>
          <div id="enginePlanL0" class="grid grid-cols-1 gap-1.5">
            <div class="border border-dashed border-[#1E1E26] bg-[#0A0A0D] px-2 py-3 text-[10px] text-zinc-600 text-center">暂无数据</div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- 历史核查记录表 -->
  <div class="border border-[#1A1A20] bg-[#0A0A0D]">
    <div class="p-4 bg-[#121216] border-b border-[#1A1A20] flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <span class="w-1.5 h-3 bg-zinc-400 shrink-0"></span>
        <div>
          <span class="text-xs font-bold text-white tracking-[0.08em]">引擎运行历史</span>
          <span class="${enMark} ml-2">HISTORY</span>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <span id="engineHistoryTotal" class="text-[10px] font-mono text-zinc-500">共 0 条</span>
        <select id="engineHistoryPageSize" class="bg-[#030304] border border-[#22222A] text-zinc-400 text-[10px] font-mono px-2 py-1 rounded-none focus:outline-none">
          <option value="10">10 / 页</option>
          <option value="20">20 / 页</option>
          <option value="50">50 / 页</option>
        </select>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-[#08080B] border-b border-[#1A1A20] text-[10px] text-zinc-500 tracking-[0.06em]">
            <th class="px-3 py-2.5 font-medium">运行编号</th>
            <th class="px-3 py-2.5 font-medium">生产基地</th>
            <th class="px-3 py-2.5 font-medium text-right">核算账期</th>
            <th class="px-3 py-2.5 font-medium text-center">执行状态</th>
            <th class="px-3 py-2.5 font-medium">操作人</th>
            <th class="px-3 py-2.5 font-medium">启动时间</th>
            <th class="px-3 py-2.5 font-medium text-center">操作</th>
          </tr>
        </thead>
        <tbody id="engineHistoryBody" class="divide-y divide-[#1A1A20]">
          <tr>
            <td colspan="7" class="px-3 py-8 text-center text-[10px] text-zinc-600">加载历史中…</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div id="engineHistoryPager" class="p-3 bg-[#08080B] border-t border-[#1A1A20] flex items-center justify-end gap-1"></div>
  </div>
</div>
`;
