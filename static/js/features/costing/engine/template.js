/**
 * 月度智能自动核价引擎 — 页面 UI
 * 视觉原则：唯一焦点 + 异常优先 + 渐进披露；中文为主
 */

import { paginationBarHtml } from '../../../page-size.js?v=3';

const engineMotionStyles = `
<style id="engineConsoleMotion">
@keyframes engine-ignite-breathe {
  0%, 100% { opacity: 0.45; box-shadow: 0 0 4px rgba(255, 30, 39, 0.3); }
  50% { opacity: 1; box-shadow: 0 0 10px rgba(255, 30, 39, 0.7); }
}
@keyframes engine-ignite-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}
.engine-ignition-ready {
  animation: engine-ignite-breathe 2.2s ease-in-out infinite;
}
.engine-ignition-running {
  animation: engine-ignite-flash 0.55s ease-in-out infinite;
}
.engine-audit-hash {
  opacity: 0;
  transition: opacity 0.15s ease;
}
.engine-history-row:hover .engine-audit-hash,
.engine-history-row:focus-within .engine-audit-hash {
  opacity: 1;
}
/* Chrome 原生 option 悬停高亮不可改，改用自绘下拉 */
.engine-select-native {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
.engine-select-wrap {
  position: relative;
  width: 100%;
}
.engine-select-wrap.is-sm {
  width: auto;
  display: inline-block;
}
.engine-select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  height: 40px;
  padding: 0 12px;
  background: #0a0a0a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e5e5e5;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  text-align: left;
  cursor: pointer;
  outline: none;
}
.engine-select-wrap.is-sm .engine-select-trigger {
  height: auto;
  min-height: 26px;
  padding: 4px 10px;
  font-size: 10px;
  color: #a3a3a3;
}
.engine-select-trigger:hover {
  border-color: rgba(255, 255, 255, 0.22);
}
.engine-select-wrap.is-open .engine-select-trigger,
.engine-select-trigger:focus {
  border-color: rgba(255, 30, 39, 0.55);
}
.engine-select-caret {
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 4px solid #666;
  flex-shrink: 0;
}
.engine-select-menu {
  position: absolute;
  z-index: 40;
  left: 0;
  right: 0;
  top: calc(100% + 2px);
  max-height: 240px;
  overflow-y: auto;
  background: #0a0a0a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.55);
}
.engine-select-wrap.is-sm .engine-select-menu {
  right: auto;
  min-width: 100%;
}
.engine-select-option {
  display: block;
  width: 100%;
  padding: 8px 12px;
  text-align: left;
  background: transparent;
  border: 0;
  color: #a3a3a3;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  cursor: pointer;
}
.engine-select-wrap.is-sm .engine-select-option {
  padding: 6px 10px;
  font-size: 10px;
}
.engine-select-option:hover {
  background: #141414;
  color: #ffffff;
}
.engine-select-option.is-selected {
  background: #1a080a;
  color: #ff1e27;
}
.engine-select-option.is-selected:hover {
  background: #220a0c;
  color: #ff1e27;
}
</style>
`;

export const costingTemplate = () => `
${engineMotionStyles}
<div class="px-6 py-8 bg-[#050505] text-neutral-400 min-h-screen font-sans selection:bg-[#FF1E27] selection:text-white">

  <!-- Hero：唯一一级视觉中心 -->
  <div class="mb-10">
    <div class="flex flex-wrap items-start justify-between gap-4 mb-8">
      <div class="flex items-start gap-3">
        <div class="w-0.5 h-8 bg-[#FF1E27] mt-0.5 shrink-0"></div>
        <div>
          <h1 class="text-xl font-semibold tracking-[0.1em] text-white">月度核价控制台</h1>
          <p class="text-[11px] text-neutral-600 mt-1.5">引擎控制 · 校验与审计</p>
        </div>
      </div>
      <div class="flex items-center gap-4 opacity-40">
        <span class="text-[9px] font-mono tracking-wide text-neutral-500">v2.5.0 · 生产环境</span>
        <div class="flex items-center gap-2">
          <div id="engineReadyLed" class="w-1.5 h-1.5 bg-neutral-700 shrink-0"></div>
          <span id="engineReadyStatusText" class="text-[10px] text-neutral-500">待命</span>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-end gap-4">
      <div class="min-w-[140px]">
        <label class="block text-[10px] text-neutral-600 mb-1.5">生产基地</label>
        <select id="engineLocation" class="engine-select-source">
          <option value="">加载中…</option>
        </select>
      </div>
      <div class="min-w-[100px]">
        <label class="block text-[10px] text-neutral-600 mb-1.5">核算年度</label>
        <select id="engineYear" class="engine-select-source">
          <option value="2026">2026年</option>
          <option value="2025">2025年</option>
          <option value="2024">2024年</option>
        </select>
      </div>
      <div class="min-w-[100px]">
        <label class="block text-[10px] text-neutral-600 mb-1.5">核算月份</label>
        <select id="engineMonth" class="engine-select-source">
          ${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${fmtMonth(i + 1)}</option>`).join('')}
        </select>
      </div>
      <button id="engineReadyBtn" type="button" class="h-10 px-4 border border-white/10 text-neutral-300 text-xs hover:border-white/20 hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none">
        检查就绪
      </button>
      <button id="engineStartBtn" type="button" class="h-10 px-6 bg-[#FF1E27] hover:bg-[#D6151E] text-white text-sm font-semibold tracking-[0.08em] flex items-center gap-2.5 disabled:bg-transparent disabled:text-neutral-600 disabled:border disabled:border-white/10 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none transition-colors">
        <span id="engineIgnitionLed" class="w-2 h-2 rounded-full bg-neutral-700 shrink-0" aria-hidden="true"></span>
        启动核算引擎
      </button>
    </div>
    <div id="engineStartHint" class="hidden mt-3 text-[10px] text-neutral-600"></div>
  </div>

  <!-- 数据管道：弱化 -->
  <div id="enginePipelinePanel" class="mb-10">
    <div class="flex items-center justify-between gap-2 mb-3">
      <span class="text-[10px] text-neutral-600 tracking-wide">核算数据管道</span>
      <span id="enginePipelineStatus" class="text-[10px] text-neutral-700">待命</span>
    </div>
    <div id="enginePipelineTrack" class="relative flex items-stretch gap-0 overflow-x-auto py-1"></div>
  </div>

  <!-- 进度 / 结果：轻量 -->
  <div id="engineProgressPanel" class="hidden mb-8">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span id="engineProgressSpinner" class="w-1.5 h-1.5 bg-[#FF1E27] animate-ping"></span>
        <span id="engineProgressTitle" class="text-xs text-white">引擎运行中</span>
      </div>
      <span id="engineProgressPercent" class="text-sm font-mono text-[#FF1E27] tabular-nums">0%</span>
    </div>
    <div class="w-full bg-white/5 h-1 mb-2">
      <div id="engineProgressBar" class="bg-[#FF1E27] h-full transition-all duration-300" style="width: 0%"></div>
    </div>
    <div id="engineProgressMsg" class="text-[10px] font-mono text-neutral-600 truncate">正在初始化…</div>
  </div>

  <div id="engineResultPanel" class="hidden mb-8">
    <div class="text-[10px] text-neutral-600">执行结果</div>
    <div id="engineResultStatus" class="text-sm font-medium text-white mt-0.5">—</div>
    <div id="engineResultTiming" class="hidden text-[10px] font-mono text-neutral-600 mt-1 tabular-nums"></div>
    <p id="engineResultHeadline" class="text-[11px] text-neutral-400 mt-1 leading-relaxed"></p>
    <div id="engineResultSteps" class="mt-4"></div>
  </div>

  <!-- 三列：靠留白分区，极淡边框 -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-10 mb-12">

    <div id="engineGateHardPanel" class="min-w-0">
      <div class="flex items-center justify-between gap-2 mb-3">
        <span class="text-[11px] text-neutral-300 tracking-wide">强约束检查</span>
        <span id="engineHardStopBadge" class="text-[10px] text-neutral-600">未检查</span>
      </div>
      <div id="engineGateHardList" class="min-h-[80px]">
        <div class="py-6 text-[10px] text-neutral-700">请先点击「检查就绪」</div>
      </div>
    </div>

    <div class="min-w-0">
      <div class="flex items-center justify-between gap-2 mb-3">
        <span class="text-[11px] text-neutral-300 tracking-wide">待自动补算</span>
        <span id="engineAnnualBadge" class="text-[10px] text-neutral-600">未检查</span>
      </div>
      <div id="engineGateAnnualList" class="min-h-[80px]">
        <div class="py-6 text-[10px] text-neutral-700">请先点击「检查就绪」</div>
      </div>
    </div>

    <div class="min-w-0">
      <div class="flex items-center justify-between gap-2 mb-3">
        <span class="text-[11px] text-neutral-300 tracking-wide">覆盖范围</span>
        <span id="engineScopeSummary" class="text-[10px] font-mono text-neutral-600 tabular-nums">节点 0</span>
      </div>
      <div id="enginePlanTree" class="min-h-[80px]">
        <div class="py-6 text-[10px] text-neutral-700">请先检查就绪</div>
      </div>
    </div>

  </div>

  <!-- 历史：暗影化 -->
  <div class="border-t border-white/5 pt-8">
    <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
      <span class="text-[11px] text-neutral-300 tracking-wide">引擎运行历史</span>
      <button id="engineHistoryDeleteAllBtn" type="button"
              class="hidden text-[10px] text-neutral-600 hover:text-[#FF1E27] transition-colors">
        全部删除
      </button>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse table-fixed" style="min-width: 980px;">
        <colgroup>
          <col style="width: 14%">
          <col style="width: 10%">
          <col style="width: 9%">
          <col style="width: 8%">
          <col style="width: 9%">
          <col style="width: 15%">
          <col style="width: 15%">
          <col style="width: 8%">
          <col style="width: 12%">
        </colgroup>
        <thead>
          <tr class="border-b border-white/5">
            <th class="px-2 py-2.5 text-left text-[9px] font-normal tracking-wide text-neutral-600">运行编号</th>
            <th class="px-2 py-2.5 text-left text-[9px] font-normal tracking-wide text-neutral-600">生产基地</th>
            <th class="px-2 py-2.5 text-right text-[9px] font-normal tracking-wide text-neutral-600">核算账期</th>
            <th class="px-2 py-2.5 text-center text-[9px] font-normal tracking-wide text-neutral-600">状态</th>
            <th class="px-2 py-2.5 text-left text-[9px] font-normal tracking-wide text-neutral-600">操作人</th>
            <th class="px-2 py-2.5 text-left text-[9px] font-normal tracking-wide text-neutral-600">开始</th>
            <th class="px-2 py-2.5 text-left text-[9px] font-normal tracking-wide text-neutral-600">结束</th>
            <th class="px-2 py-2.5 text-right text-[9px] font-normal tracking-wide text-neutral-600">耗时</th>
            <th class="px-2 py-2.5 text-center text-[9px] font-normal tracking-wide text-neutral-600">操作</th>
          </tr>
        </thead>
        <tbody id="engineHistoryBody">
          <tr>
            <td colspan="9" class="px-2 py-8 text-center text-[10px] text-neutral-700">加载历史中…</td>
          </tr>
        </tbody>
      </table>
    </div>

    ${paginationBarHtml({
      infoId: 'engineHistoryTotal',
      selectId: 'engineHistoryPageSize',
      buttonsId: 'engineHistoryPager',
      wrapperClass: 'flex items-center justify-between pt-4',
    })}
  </div>
</div>
`;
