/**
 * Scope 条：基地 / 年 / 月 / 车型 / BOM
 */

const LOCATION_HINTS = ['芜湖', '大连', '鄂尔多斯', '青岛', '福州'];

/**
 * @param {HTMLElement} root
 * @param {{
 *   scope: object,
 *   onChange: (scope: object) => void,
 * }} options
 */
export function mountScopeBar(root, options) {
    const scope = { ...defaultScope(), ...(options.scope || {}) };
    root.innerHTML = `
<div class="grid grid-cols-2 gap-1.5">
  <label class="block">
    <span class="text-[9px] text-[#555555] tracking-wide">基地</span>
    <input id="llmScopeLocation" type="text" list="llmScopeLocationList" value="${escAttr(scope.location)}"
           class="mt-0.5 w-full h-7 px-1.5 text-[11px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] focus:outline-none focus:border-[#ff5252]"
           autocomplete="off">
    <datalist id="llmScopeLocationList">
      ${LOCATION_HINTS.map((loc) => `<option value="${escAttr(loc)}"></option>`).join('')}
    </datalist>
  </label>
  <div class="grid grid-cols-2 gap-1.5">
    <label class="block">
      <span class="text-[9px] text-[#555555]">年</span>
      <input id="llmScopeYear" type="number" min="2000" max="2100" value="${escAttr(scope.year)}"
             class="mt-0.5 w-full h-7 px-1.5 text-[11px] font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] focus:outline-none focus:border-[#ff5252]">
    </label>
    <label class="block">
      <span class="text-[9px] text-[#555555]">月</span>
      <input id="llmScopeMonth" type="number" min="1" max="12" value="${escAttr(scope.month)}"
             class="mt-0.5 w-full h-7 px-1.5 text-[11px] font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] focus:outline-none focus:border-[#ff5252]">
    </label>
  </div>
  <label class="block">
    <span class="text-[9px] text-[#555555]">车型</span>
    <input id="llmScopeVehicle" type="text" value="${escAttr(scope.vehicle_model)}" placeholder="如 T28"
           class="mt-0.5 w-full h-7 px-1.5 text-[11px] font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252]">
  </label>
  <label class="block">
    <span class="text-[9px] text-[#555555]">BOM</span>
    <input id="llmScopeBom" type="text" value="${escAttr(scope.bom_version)}" placeholder="如 V1"
           class="mt-0.5 w-full h-7 px-1.5 text-[11px] font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252]">
  </label>
  <label class="block col-span-2">
    <span class="text-[9px] text-[#555555]">零件号（可选）</span>
    <input id="llmScopePart" type="text" value="${escAttr(scope.part_number || '')}" placeholder="解读单件时填写"
           class="mt-0.5 w-full h-7 px-1.5 text-[11px] font-mono bg-[#0a0a0a] border border-[#2c2c2c] text-[#e0e0e0] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252]">
  </label>
</div>
`.trim();

    const emit = () => options.onChange(readScope(root));
    root.querySelectorAll('input').forEach((el) => {
        el.addEventListener('change', emit);
        el.addEventListener('blur', emit);
    });
}

/**
 * @param {HTMLElement} root
 * @returns {object}
 */
export function readScope(root) {
    const yearRaw = root.querySelector('#llmScopeYear')?.value;
    const monthRaw = root.querySelector('#llmScopeMonth')?.value;
    return {
        location: String(root.querySelector('#llmScopeLocation')?.value || '').trim(),
        year: yearRaw ? Number(yearRaw) : null,
        month: monthRaw ? Number(monthRaw) : null,
        vehicle_model: String(root.querySelector('#llmScopeVehicle')?.value || '').trim(),
        bom_version: String(root.querySelector('#llmScopeBom')?.value || '').trim(),
        part_number: String(root.querySelector('#llmScopePart')?.value || '').trim() || null,
    };
}

/**
 * @param {HTMLElement} root
 * @param {object} scope
 */
export function writeScope(root, scope) {
    const s = { ...defaultScope(), ...(scope || {}) };
    const set = (sel, value) => {
        const el = root.querySelector(sel);
        if (el) el.value = value == null ? '' : String(value);
    };
    set('#llmScopeLocation', s.location);
    set('#llmScopeYear', s.year);
    set('#llmScopeMonth', s.month);
    set('#llmScopeVehicle', s.vehicle_model);
    set('#llmScopeBom', s.bom_version);
    set('#llmScopePart', s.part_number || '');
}

/**
 * @param {object} scope
 * @returns {string|null}
 */
export function validateScope(scope) {
    if (!scope?.location) return '请填写基地';
    if (!scope?.year || scope.year < 2000) return '请填写年份';
    if (!scope?.month || scope.month < 1 || scope.month > 12) return '请填写月份';
    if (!scope?.vehicle_model) return '请填写车型';
    if (!scope?.bom_version) return '请填写 BOM 版本';
    return null;
}

export function defaultScope() {
    const now = new Date();
    return {
        location: '青岛',
        year: now.getFullYear(),
        month: now.getMonth() + 1,
        vehicle_model: '',
        bom_version: '',
        part_number: null,
    };
}

function escAttr(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}
