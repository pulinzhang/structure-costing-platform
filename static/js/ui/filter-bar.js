/**
 * 列表筛选控件：胶囊条 + 可展开高级筛选（一体）。
 * 各页只传胶囊映射和字段 HTML，禁止再复制 FILTER_STRIP / 展开面板。
 */

import {
    FILTER_STRIP,
    FILTER_ADVANCED,
    CAPSULE_IDLE,
    BTN_FILTER_SEARCH,
    capsuleClass,
} from './classes.js?v=11';

const TOGGLE_BTN_CLASS =
    'text-ink-dim hover:text-ink transition-colors flex items-center gap-1.5 text-[11px]';

/** @type {Map<string, { unbind: () => void, paint: () => void, setOpen: (isOpen: boolean) => void, isOpen: () => boolean }>} */
const barsByPrefix = new Map();

/**
 * @param {string} prefix
 * @param {{ searchId?: string }} [opts]
 */
export function filterBarIds(prefix, opts = {}) {
    return {
        toggleId: `${prefix}ToggleAdvancedFilter`,
        labelId: `${prefix}AdvancedFilterLabel`,
        countId: `${prefix}AdvancedFilterCount`,
        panelId: `${prefix}AdvancedFilterPanel`,
        searchId: opts.searchId || `${prefix}SearchBtn`,
        capsulesWrapId: `${prefix}FilterCapsules`,
    };
}

/**
 * @param {{
 *   prefix: string,
 *   capsules: Array<{ capsuleId: string, idleLabel: string, hideWhenIdle?: boolean }>,
 *   fieldsHtml: string,
 *   hintHtml?: string,
 *   alwaysHintHtml?: string,
 *   leadHtml?: string,
 *   extraCapsulesHtml?: string,
 *   searchId?: string,
 * }} spec
 * @returns {string}
 */
export function filterBarHtml({
    prefix,
    capsules,
    fieldsHtml,
    hintHtml = '',
    alwaysHintHtml = '',
    leadHtml = '',
    extraCapsulesHtml = '',
    searchId,
}) {
    const ids = filterBarIds(prefix, { searchId });
    const capsuleHtml = (capsules || []).map((item) => {
        const hiddenClass = item.hideWhenIdle ? ' hidden' : '';
        const label = item.hideWhenIdle ? '' : item.idleLabel;
        return `<span id="${item.capsuleId}" class="${CAPSULE_IDLE}${hiddenClass}">${label}</span>`;
    }).join('');
    const hint = hintHtml
        ? `<p class="mt-2 text-[10px] text-ink-faint">${hintHtml}</p>`
        : '';
    const alwaysHint = alwaysHintHtml
        ? `<p class="mt-2 text-[10px] text-ink-faint">${alwaysHintHtml}</p>`
        : '';
    const searchIcon = typeof window.svgIcon === 'function'
        ? window.svgIcon('search', 'w-3 h-3')
        : '';
    return `
                    <div class="${FILTER_STRIP}">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-ink-faint shrink-0 tracking-wider">当前筛选：</span>
                            <div id="${ids.capsulesWrapId}" class="flex items-center gap-2 flex-wrap min-w-0">
                                ${leadHtml}
                                ${capsuleHtml}
                                ${extraCapsulesHtml}
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="${ids.toggleId}" class="${TOGGLE_BTN_CLASS}">
                                <span id="${ids.labelId}">展开高级筛选</span>
                                <span id="${ids.countId}" class="text-ink-faint">(0)</span>
                            </button>
                            <button type="button" id="${ids.searchId}" class="${BTN_FILTER_SEARCH}">
                                ${searchIcon}
                                查询
                            </button>
                        </div>
                    </div>
                    ${alwaysHint}
                    <div id="${ids.panelId}" class="${FILTER_ADVANCED}">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${fieldsHtml}
                        </div>
                        ${hint}
                    </div>`;
}

/**
 * @param {{
 *   prefix: string,
 *   capsules: Array<{
 *     capsuleId: string,
 *     idleLabel: string,
 *     fieldId?: string,
 *     fieldIds?: string[],
 *     hideWhenIdle?: boolean,
 *     display?: () => string,
 *   }>,
 *   countFieldIds?: string[],
 *   searchId?: string,
 *   resetId?: string,
 *   enterFieldIds?: string[],
 *   startOpen?: boolean,
 *   onSearch: () => void,
 *   onReset?: () => void,
 * }} spec
 */
export function bindFilterBar(spec) {
    const prefix = spec.prefix;
    const prev = barsByPrefix.get(prefix);
    if (prev) prev.unbind();

    const ids = filterBarIds(prefix, { searchId: spec.searchId });
    const capsules = spec.capsules || [];
    const countFieldIds = spec.countFieldIds || [];
    const resetId = spec.resetId || `${prefix}ResetBtn`;
    const enterFieldIds = spec.enterFieldIds || [];
    let advancedOpen = Boolean(spec.startOpen);

    const fieldIdsOf = (item) => {
        if (item.fieldIds && item.fieldIds.length) return item.fieldIds;
        return item.fieldId ? [item.fieldId] : [];
    };

    const fieldValue = (fieldId) => (document.getElementById(fieldId)?.value || '').trim();

    const fieldLabel = (fieldId) => {
        const el = document.getElementById(fieldId);
        if (!el) return '';
        const value = (el.value || '').trim();
        if (!value) return '';
        if (el.tagName === 'SELECT') {
            const option = el.selectedOptions && el.selectedOptions[0];
            return (option && option.textContent) ? option.textContent.trim() : value;
        }
        return value;
    };

    const paint = () => {
        const counted = new Set();
        capsules.forEach((item) => {
            const el = document.getElementById(item.capsuleId);
            const idsForItem = fieldIdsOf(item);
            const hasValue = idsForItem.some((id) => Boolean(fieldValue(id)));
            idsForItem.forEach((id) => {
                if (fieldValue(id)) counted.add(id);
            });
            let text = item.idleLabel;
            if (typeof item.display === 'function') {
                text = item.display() || item.idleLabel;
            } else if (hasValue) {
                text = idsForItem.map(fieldLabel).filter(Boolean).join(' · ') || item.idleLabel;
            }
            if (el) {
                if (item.hideWhenIdle && !hasValue) {
                    el.textContent = '';
                    el.className = `${capsuleClass(false)} hidden`;
                } else {
                    el.textContent = text;
                    el.className = capsuleClass(hasValue);
                }
            }
        });
        countFieldIds.forEach((id) => {
            if (fieldValue(id)) counted.add(id);
        });
        const countEl = document.getElementById(ids.countId);
        if (countEl) countEl.textContent = `(${counted.size})`;
    };

    const setOpen = (isOpen) => {
        advancedOpen = Boolean(isOpen);
        document.getElementById(ids.panelId)?.classList.toggle('hidden', !advancedOpen);
        const label = document.getElementById(ids.labelId);
        if (label) label.textContent = advancedOpen ? '收起高级筛选' : '展开高级筛选';
    };

    const onToggle = () => setOpen(!advancedOpen);
    const onSearch = () => {
        paint();
        spec.onSearch?.();
    };
    const onReset = () => {
        spec.onReset?.();
        paint();
    };
    const onEnter = (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        onSearch();
    };
    const onFieldChange = () => paint();

    const watchIds = [
        ...capsules.flatMap(fieldIdsOf),
        ...countFieldIds,
        ...enterFieldIds,
    ].filter((id, index, list) => id && list.indexOf(id) === index);

    document.getElementById(ids.toggleId)?.addEventListener('click', onToggle);
    document.getElementById(ids.searchId)?.addEventListener('click', onSearch);
    document.getElementById(resetId)?.addEventListener('click', onReset);
    enterFieldIds.forEach((id) => {
        document.getElementById(id)?.addEventListener('keydown', onEnter);
    });
    watchIds.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('change', onFieldChange);
        el.addEventListener('input', onFieldChange);
    });

    setOpen(advancedOpen);
    paint();

    const unbind = () => {
        document.getElementById(ids.toggleId)?.removeEventListener('click', onToggle);
        document.getElementById(ids.searchId)?.removeEventListener('click', onSearch);
        document.getElementById(resetId)?.removeEventListener('click', onReset);
        enterFieldIds.forEach((id) => {
            document.getElementById(id)?.removeEventListener('keydown', onEnter);
        });
        watchIds.forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.removeEventListener('change', onFieldChange);
            el.removeEventListener('input', onFieldChange);
        });
        if (barsByPrefix.get(prefix)?.unbind === unbind) {
            barsByPrefix.delete(prefix);
        }
    };

    const api = {
        paint,
        setOpen,
        isOpen: () => advancedOpen,
        unbind,
    };
    barsByPrefix.set(prefix, api);
    return api;
}
