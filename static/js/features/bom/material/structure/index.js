/**
 * BOM 产品结构
 * Phase A：基地 + Project Cards
 * Phase B：L0 Assembly Selection（#/bom-structure?snapshot_id=）
 */

import { can } from '../../../../core/permissions.js?v=10';
import { bomStructureTemplate } from './template.js?v=9';
import { fmtPeriodRange, hasClosedPeriod } from '../../../common/period-ui.js?v=5';

const bomStructureState = {
    view: 'projects', // projects | assemblies
    locations: [],
    selectedLocation: '',
    items: [],
    snapshot: null,
    snapshotId: null,
    assemblies: [],
    assemblySearch: '',
    isLoading: false,
};

const STAGE_LABEL = {
    initial: '初始清单',
    mass: '批量清单',
};

const STATUS_LABEL = {
    draft: '草稿',
    active: '生效',
    archived: '归档',
};

function readHashSnapshotId() {
    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex < 0) return null;
    const qs = new URLSearchParams(hash.slice(queryIndex + 1));
    const raw = qs.get('snapshot_id');
    if (!raw) return null;
    const id = Number.parseInt(raw, 10);
    return Number.isFinite(id) && id > 0 ? id : null;
}

function formatUpdatedAt(value) {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value).slice(0, 10);
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function stageLabel(stage) {
    if (!stage) return null;
    return STAGE_LABEL[stage] || stage;
}

function statusLabel(status) {
    if (!status) return null;
    return STATUS_LABEL[status] || status;
}

/** 统计子树节点数（不含自身） */
function countDescendants(node) {
    const children = Array.isArray(node?.children) ? node.children : [];
    let total = children.length;
    for (const child of children) {
        total += countDescendants(child);
    }
    return total;
}

/** BOM 层级数：从 L0 到最深子节点（含 L0） */
function countLevels(node) {
    const rootLevel = typeof node?.level === 'number' ? node.level : 0;

    function deepest(n) {
        const children = Array.isArray(n?.children) ? n.children : [];
        if (!children.length) {
            return typeof n?.level === 'number' ? n.level : rootLevel;
        }
        return Math.max(...children.map((child) => deepest(child)));
    }

    return deepest(node) - rootLevel + 1;
}

function sketchSrc(sketchUrl) {
    if (!sketchUrl) return null;
    if (sketchUrl.startsWith('http://') || sketchUrl.startsWith('https://') || sketchUrl.startsWith('/')) {
        return sketchUrl;
    }
    return `/uploads/${sketchUrl}`;
}

/**
 * 企业口语短号：取零件号数字段末 4 位。
 * 例：554002087AA → 2087；501006873AA → 6873
 * 标准件/无足够数字时返回 null，仅展示完整零件号。
 */
function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/** 卡片展示序号：优先 Excel seq_no，否则按树序 1-based */
function assemblySeqNo(node, index) {
    if (node?.seq_no != null && node.seq_no !== '') {
        return Number(node.seq_no);
    }
    return index + 1;
}

/** 前端模糊匹配：零件号 / 短号 / 名称（不请求后端） */
function matchAssemblySearch(node, rawQuery) {
    const query = String(rawQuery || '').trim().toLowerCase();
    if (!query) return true;

    const partNumber = String(node?.part_number || '').toLowerCase();
    const partName = String(node?.part_name || '').toLowerCase();
    const shortNo = String(shortPartNumber(node?.part_number) || '').toLowerCase();

    return (
        partNumber.includes(query) ||
        partName.includes(query) ||
        (shortNo && shortNo.includes(query))
    );
}

function showProjectsView() {
    const projects = document.getElementById('bomStructureProjectsView');
    const assemblies = document.getElementById('bomStructureAssembliesView');
    if (projects) projects.classList.remove('hidden');
    if (assemblies) assemblies.classList.add('hidden');
    bomStructureState.view = 'projects';
}

function showAssembliesView() {
    const projects = document.getElementById('bomStructureProjectsView');
    const assemblies = document.getElementById('bomStructureAssembliesView');
    if (projects) projects.classList.add('hidden');
    if (assemblies) assemblies.classList.remove('hidden');
    bomStructureState.view = 'assemblies';
}

const BomStructurePage = {
    init() {
        if (!can('op:bom-structure:view')) {
            showProjectsView();
            const grid = document.getElementById('bomStructureProjectGrid');
            if (grid) {
                grid.innerHTML = `
                    <div class="col-span-full flex flex-col items-center justify-center py-16 border border-line bg-app-surface">
                        <p class="text-xs text-ink-muted">无权查看产品结构</p>
                        <p class="text-[11px] text-ink-dim mt-1">需要权限 op:bom-structure:view</p>
                    </div>
                `;
            }
            return;
        }

        document.getElementById('bomStructureBackToProjects')?.addEventListener('click', () => {
            window.location.hash = '/bom-structure';
        });

        const searchInput = document.getElementById('bomStructureAssemblySearch');
        if (searchInput) {
            searchInput.value = bomStructureState.assemblySearch || '';
            searchInput.addEventListener('input', () => {
                bomStructureState.assemblySearch = searchInput.value || '';
                if (bomStructureState.view !== 'assemblies') return;
                this.applyAssemblyFilter();
            });
        }

        const snapshotId = readHashSnapshotId();
        if (snapshotId) {
            this.loadAssemblies(snapshotId);
        } else {
            this.loadSnapshots();
        }
    },

    async loadSnapshots() {
        if (bomStructureState.isLoading) return;
        bomStructureState.isLoading = true;
        showProjectsView();
        this.renderProjectsLoading();

        try {
            const params = {
                page: 1,
                size: 100,
                status: 'active',
            };
            if (bomStructureState.selectedLocation) {
                params.location = bomStructureState.selectedLocation;
            }

            const resp = await HttpClient.get('/api/bom/snapshots', { params });
            const pageInfo = resp.data ?? {};
            const items = Array.isArray(pageInfo.items) ? pageInfo.items : [];
            const filters = pageInfo.filters || {};
            const locations = Array.isArray(filters.locations) ? filters.locations : [];

            bomStructureState.locations = locations;
            bomStructureState.items = items;
            bomStructureState.snapshot = null;
            bomStructureState.snapshotId = null;
            bomStructureState.assemblies = [];
            bomStructureState.assemblySearch = '';
            const searchInput = document.getElementById('bomStructureAssemblySearch');
            if (searchInput) searchInput.value = '';

            if (locations.length === 1) {
                bomStructureState.selectedLocation = locations[0];
            }

            this.renderBaseContext();
            this.renderProjectCards(items);
        } catch (error) {
            console.error('加载 BOM 清单失败:', error);
            this.renderProjectsError(error.message || '加载失败');
        } finally {
            bomStructureState.isLoading = false;
        }
    },

    async loadAssemblies(snapshotId) {
        if (bomStructureState.isLoading) return;
        bomStructureState.isLoading = true;
        showAssembliesView();
        this.renderAssembliesLoading();

        try {
            const [snapResp, treeResp] = await Promise.all([
                HttpClient.get(`/api/bom/snapshots/${snapshotId}`),
                HttpClient.get(`/api/bom/snapshots/${snapshotId}/tree`, {
                    params: { include_expired: true },
                }),
            ]);

            const snapshot = snapResp.data || null;
            const tree = Array.isArray(treeResp.data) ? treeResp.data : [];

            // Tree 根节点即为 L0（level === 0）；再过滤一次以防脏数据
            const assemblies = tree.filter((node) => node && node.level === 0);

            bomStructureState.snapshot = snapshot;
            bomStructureState.snapshotId = snapshotId;
            bomStructureState.assemblies = assemblies.map((node, index) => ({
                ...node,
                _displaySeq: assemblySeqNo(node, index),
            }));

            const searchInput = document.getElementById('bomStructureAssemblySearch');
            if (searchInput && !searchInput.value) {
                bomStructureState.assemblySearch = '';
            }

            this.renderAssemblyHeader(snapshot, bomStructureState.assemblies.length);
            this.applyAssemblyFilter();
        } catch (error) {
            console.error('加载供货总成失败:', error);
            this.renderAssembliesError(error.message || '加载失败');
        } finally {
            bomStructureState.isLoading = false;
        }
    },

    applyAssemblyFilter() {
        const snapshotId = bomStructureState.snapshotId;
        const all = bomStructureState.assemblies;
        const filtered = all.filter((node) =>
            matchAssemblySearch(node, bomStructureState.assemblySearch)
        );

        const countEl = document.getElementById('bomStructureAssemblyCount');
        if (countEl) {
            if (!all.length) {
                countEl.textContent = '';
            } else if (filtered.length === all.length) {
                countEl.textContent = `${all.length} 个总成`;
            } else {
                countEl.textContent = `${filtered.length} / ${all.length} 个总成`;
            }
        }

        this.renderAssemblyCards(filtered, snapshotId, { isFiltered: filtered.length !== all.length });
    },

    renderProjectsLoading() {
        const grid = document.getElementById('bomStructureProjectGrid');
        const base = document.getElementById('bomStructureBaseContext');
        if (base) {
            base.innerHTML = `<span class="text-sm text-ink-dim">加载中…</span>`;
        }
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full flex items-center justify-center py-16">
                    <div class="w-6 h-6 border-2 border-line border-brand rounded-full animate-spin"></div>
                </div>
            `;
        }
    },

    renderProjectsError(message) {
        const grid = document.getElementById('bomStructureProjectGrid');
        if (!grid) return;
        grid.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-14 border border-line bg-app-surface">
                <p class="text-xs text-danger mb-1">加载失败</p>
                <p class="text-[11px] text-ink-dim">${esc(message)}</p>
            </div>
        `;
    },

    renderAssembliesLoading() {
        const grid = document.getElementById('bomStructureAssemblyGrid');
        const path = document.getElementById('bomStructureAssemblyPath');
        const count = document.getElementById('bomStructureAssemblyCount');
        if (path) path.textContent = '加载中…';
        if (count) count.textContent = '';
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full flex items-center justify-center py-16">
                    <div class="w-6 h-6 border-2 border-line border-brand rounded-full animate-spin"></div>
                </div>
            `;
        }
    },

    renderAssembliesError(message) {
        const grid = document.getElementById('bomStructureAssemblyGrid');
        if (!grid) return;
        grid.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-14 border border-line bg-app-surface">
                <p class="text-xs text-danger mb-1">加载失败</p>
                <p class="text-[11px] text-ink-dim">${esc(message)}</p>
            </div>
        `;
    },

    renderBaseContext() {
        const el = document.getElementById('bomStructureBaseContext');
        if (!el) return;

        const locations = bomStructureState.locations;

        if (!locations.length) {
            el.innerHTML = `<span class="text-sm text-ink-dim">暂无基地数据</span>`;
            return;
        }

        if (locations.length === 1) {
            el.innerHTML = `
                <div class="flex items-baseline gap-3">
                    <h2 class="text-xl font-semibold text-ink tracking-wide">${esc(locations[0])}</h2>
                    <span class="text-[10px] uppercase tracking-[0.14em] text-ink-dim">基地</span>
                </div>
            `;
            return;
        }

        const selected = bomStructureState.selectedLocation || locations[0];
        if (!bomStructureState.selectedLocation) {
            bomStructureState.selectedLocation = selected;
        }

        el.innerHTML = `
            <div class="flex flex-wrap max-w-full items-stretch border border-line bg-app-deep p-0.5" role="tablist" aria-label="采购基地">
                ${locations
                    .map((loc) => {
                        const isActive = loc === bomStructureState.selectedLocation;
                        const activeCls = isActive
                            ? 'bg-app-surface text-ink border border-brand/60'
                            : 'text-ink-muted border border-transparent hover:text-ink hover:bg-app-surface';
                        return `
                            <button type="button"
                                    data-bom-base="${esc(loc)}"
                                    class="bom-base-seg px-4 py-2 text-xs font-medium transition-all ${activeCls}">
                                ${esc(loc)}
                            </button>
                        `;
                    })
                    .join('')}
            </div>
        `;

        el.querySelectorAll('.bom-base-seg').forEach((btn) => {
            btn.addEventListener('click', () => {
                const loc = btn.getAttribute('data-bom-base');
                if (!loc || loc === bomStructureState.selectedLocation) return;
                bomStructureState.selectedLocation = loc;
                this.loadSnapshots();
            });
        });
    },

    renderProjectCards(items) {
        const grid = document.getElementById('bomStructureProjectGrid');
        const countEl = document.getElementById('bomStructureProjectCount');
        if (!grid) return;

        let list = items;
        if (bomStructureState.selectedLocation && bomStructureState.locations.length > 1) {
            list = items.filter((row) => row.location === bomStructureState.selectedLocation);
        }

        if (countEl) {
            countEl.textContent = list.length ? `${list.length}` : '';
        }

        if (!list.length) {
            grid.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-16 border border-dashed border-line bg-app-surface">
                    <div class="w-10 h-10 bg-app-elevated flex items-center justify-center mb-3">
                        <svg class="w-5 h-5 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                        </svg>
                    </div>
                    <h5 class="text-xs font-medium text-ink-muted mb-1">暂无项目</h5>
                    <p class="text-[11px] text-ink-dim">请先上传材料清单</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = list.map((row) => this.buildProjectCard(row)).join('');

        grid.querySelectorAll('[data-snapshot-id]').forEach((card) => {
            card.addEventListener('click', () => {
                const id = card.getAttribute('data-snapshot-id');
                if (!id) return;
                window.location.hash = `/bom-structure?snapshot_id=${encodeURIComponent(id)}`;
            });
            card.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter' && event.key !== ' ') return;
                event.preventDefault();
                card.click();
            });
        });
    },

    buildProjectCard(row) {
        const customer = row.customer_name || null;
        const vehicle = row.vehicle_model || null;
        const version = row.bom_version || null;
        const location = row.location || null;
        const category = row.product_category || null;
        const title = row.title || null;
        const nodeCount = row.node_count != null ? row.node_count : null;
        const updated = formatUpdatedAt(row.updated_at);
        const stage = stageLabel(row.stage);
        const status = statusLabel(row.status);

        const metaBits = [];
        if (nodeCount != null) {
            metaBits.push(`<span class="font-mono tabular-nums">${esc(String(nodeCount))}</span> 零件`);
        }
        if (version) {
            metaBits.push(`版本 ${esc(version)}`);
        }
        if (stage) {
            metaBits.push(esc(stage));
        }

        return `
            <article class="group relative bg-app-surface border border-line hover:border-line transition-all duration-300 flex flex-col min-h-[220px] cursor-pointer"
                     role="button"
                     tabindex="0"
                     data-snapshot-id="${esc(String(row.id))}">
                <div class="absolute left-0 top-6 bottom-6 w-0.5 bg-transparent group-hover:bg-brand hud-brand-glow-hover transition-all"></div>
                <div class="px-6 pt-6 pb-5 flex-1 flex flex-col">
                    <div class="flex items-start justify-between gap-3 mb-5">
                        <div class="min-w-0">
                            ${
                                customer
                                    ? `<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-muted truncate">${esc(customer)}</p>`
                                    : `<p class="text-[10px] font-semibold tracking-[0.12em] text-ink-faint">客户</p>`
                            }
                            ${
                                location && bomStructureState.locations.length > 1
                                    ? `<p class="text-[10px] text-ink-dim mt-1">${esc(location)}</p>`
                                    : ''
                            }
                        </div>
                        ${
                            status
                                ? `<span class="shrink-0 inline-flex items-center px-2 py-0.5 text-[10px] font-semibold rounded bg-ok/15 text-ok">${esc(status)}</span>`
                                : ''
                        }
                    </div>

                    <h3 class="text-lg font-semibold text-ink tracking-wide leading-snug mb-1">
                        ${vehicle ? esc(vehicle) : '—'}
                    </h3>
                    ${
                        version
                            ? `<p class="text-sm text-ink-muted font-mono tracking-wider mb-1">${esc(version)}</p>`
                            : ''
                    }
                    ${
                        category || title
                            ? `<p class="text-[11px] text-ink-dim mt-1 line-clamp-2">${esc(category || title)}</p>`
                            : ''
                    }
                    ${
                        row.source_filename
                            ? `<p class="text-[10px] text-ink-faint mt-2 font-mono truncate" title="${esc(row.source_filename)}${row.source_sheet_name ? ` / ${esc(row.source_sheet_name)}` : ''}">来源 ${esc(row.source_filename)}${row.source_sheet_name ? ` · ${esc(row.source_sheet_name)}` : ''}</p>`
                            : ''
                    }

                    <div class="mt-auto pt-6">
                        ${
                            metaBits.length
                                ? `<p class="text-[10px] uppercase tracking-[0.12em] text-ink-dim mb-3">${metaBits.join(' <span class="text-ink-faint mx-1">·</span> ')}</p>`
                                : ''
                        }
                        ${
                            updated
                                ? `<p class="text-[11px] text-ink-faint mb-4">更新于 ${esc(updated)}</p>`
                                : ''
                        }
                        <div class="flex items-center justify-end">
                            <span class="text-[11px] font-semibold tracking-wide text-ink-dim group-hover:text-brand transition-colors">
                                打开 <span class="inline-block transition-transform group-hover:translate-x-0.5">→</span>
                            </span>
                        </div>
                    </div>
                </div>
            </article>
        `;
    },

    renderAssemblyHeader(snapshot, assemblyCount) {
        const pathEl = document.getElementById('bomStructureAssemblyPath');
        const countEl = document.getElementById('bomStructureAssemblyCount');

        if (pathEl) {
            if (!snapshot) {
                pathEl.textContent = '—';
            } else {
                const parts = [
                    snapshot.location,
                    snapshot.customer_name,
                    snapshot.vehicle_model,
                    snapshot.bom_version,
                ].filter(Boolean);
                let text = parts.join(' / ');
                if (snapshot.source_filename) {
                    const sheet = snapshot.source_sheet_name
                        ? ` · ${snapshot.source_sheet_name}`
                        : '';
                    text += `  ·  来源 ${snapshot.source_filename}${sheet}`;
                }
                pathEl.textContent = text;
            }
        }

        if (countEl) {
            countEl.textContent = assemblyCount ? `${assemblyCount} 个总成` : '';
        }
    },

    renderAssemblyCards(assemblies, snapshotId, options = {}) {
        const grid = document.getElementById('bomStructureAssemblyGrid');
        if (!grid) return;

        if (!assemblies.length) {
            const emptyHint = options.isFiltered
                ? '没有匹配的供货总成'
                : '该项目下暂无供货总成';
            const emptyTitle = options.isFiltered ? '无搜索结果' : '暂无供货总成';
            grid.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-16 border border-dashed border-line bg-app-surface">
                    <h5 class="text-xs font-medium text-ink-muted mb-1">${esc(emptyTitle)}</h5>
                    <p class="text-[11px] text-ink-dim">${esc(emptyHint)}</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = assemblies
            .map((node) => this.buildAssemblyCard(node, snapshotId))
            .join('');

        grid.querySelectorAll('[data-node-id]').forEach((card) => {
            card.addEventListener('click', () => {
                const nodeId = card.getAttribute('data-node-id');
                const sid = card.getAttribute('data-snapshot-id') || String(snapshotId);
                if (!nodeId || !sid) return;
                window.location.hash =
                    `/bom-viz?snapshot_id=${encodeURIComponent(sid)}&node_id=${encodeURIComponent(nodeId)}`;
            });
            card.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter' && event.key !== ' ') return;
                event.preventDefault();
                card.click();
            });
        });
    },

    buildAssemblyCard(node, snapshotId) {
        const snapshot = bomStructureState.snapshot || {};
        const name = node.part_name || null;
        const partNumber = node.part_number || null;
        const shortNo = shortPartNumber(partNumber);
        const componentCount = countDescendants(node);
        const levelCount = countLevels(node);
        const src = sketchSrc(node.sketch_url);
        const titleText = name || partNumber || '—';
        const seqNo = node._displaySeq != null ? node._displaySeq : assemblySeqNo(node, 0);
        const seqLabel = String(seqNo).padStart(2, '0');
        const isChanged = hasClosedPeriod(
            node.effective_year,
            node.effective_month,
            node.expiry_year,
            node.expiry_month,
        );
        const periodClass = isChanged ? 'text-brand' : 'text-ink-dim';
        const periodTitle = isChanged ? ' title="已变更"' : '';

        const sketchBlock = src
            ? `
                <div class="relative h-48 bg-app-main border-b border-line-subtle flex items-center justify-center px-6 py-5 overflow-hidden">
                    <span class="absolute top-3 left-3 text-[10px] font-mono tabular-nums tracking-[0.14em] text-ink-dim">
                        ${esc(seqLabel)}
                    </span>
                    <img src="${esc(src)}"
                         alt="${esc(titleText)}"
                         loading="lazy"
                         class="max-h-full max-w-full w-auto h-auto object-contain transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                         draggable="false">
                </div>
            `
            : `
                <div class="relative h-48 bg-app-main border-b border-line-subtle flex items-center justify-center px-6 py-5">
                    <span class="absolute top-3 left-3 text-[10px] font-mono tabular-nums tracking-[0.14em] text-ink-dim">
                        ${esc(seqLabel)}
                    </span>
                    <span class="text-[10px] text-ink-faint">暂无图</span>
                </div>
            `;

        // 短号视觉主角；完整零件号降为次要标注
        const partNumberBlock = shortNo
            ? `
                <p class="text-2xl font-mono font-semibold tabular-nums text-ink tracking-[0.14em] hud-kpi-num-glow mb-0.5">
                    ${esc(shortNo)}
                </p>
                ${
                    partNumber
                        ? `<p class="text-[11px] font-mono text-ink-dim tracking-wider mb-3">${esc(partNumber)}</p>`
                        : `<div class="mb-3"></div>`
                }
            `
            : partNumber
              ? `<p class="text-sm font-mono text-ink-muted tracking-wider mb-3">${esc(partNumber)}</p>`
              : `<div class="mb-3"></div>`;

        return `
            <article class="group bg-app-surface border border-line hover:border-line hover:shadow-[0_8px_24px_rgb(var(--overlay)/0.35)] transition-all duration-300 flex flex-col cursor-pointer overflow-hidden"
                     role="button"
                     tabindex="0"
                     data-snapshot-id="${esc(String(snapshotId))}"
                     data-node-id="${esc(String(node.id))}">
                ${sketchBlock}
                <div class="px-5 pt-4 pb-5 flex-1 flex flex-col">
                    ${
                        name
                            ? `<h3 class="text-sm font-semibold text-ink tracking-wide leading-snug mb-2 line-clamp-2">${esc(name)}</h3>`
                            : ''
                    }
                    ${partNumberBlock}
                    <div class="mt-auto space-y-1">
                        <p class="text-[10px] tracking-wide text-ink-dim">
                            ${esc(node.location || snapshot?.location || '')}
                            · ${esc(node.vehicle_model || snapshot?.vehicle_model || '')}
                            · ${esc(node.bom_version || snapshot?.bom_version || '')}
                        </p>
                        <p class="text-[10px] tracking-wide ${periodClass}"${periodTitle}>
                            ${esc(fmtPeriodRange(node.effective_year, node.effective_month, node.expiry_year, node.expiry_month))}
                        </p>
                        <p class="text-[10px] tracking-wide text-ink-dim">
                            <span class="font-mono tabular-nums text-ink-muted">${esc(String(componentCount))}</span> 个子件
                        </p>
                        <p class="text-[10px] tracking-wide text-ink-dim">
                            <span class="font-mono tabular-nums text-ink-muted">${esc(String(levelCount))}</span> 层结构
                        </p>
                    </div>
                    <div class="flex items-center justify-end mt-4">
                        <span class="text-[11px] font-semibold tracking-wide text-ink-dim group-hover:text-brand transition-colors">
                            打开 <span class="inline-block transition-transform duration-300 group-hover:translate-x-0.5">→</span>
                        </span>
                    </div>
                </div>
            </article>
        `;
    },
};

export const pageConfig = {
    render: bomStructureTemplate,
    init: () => BomStructurePage.init(),
};
