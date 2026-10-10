/**
 * 计算过程 — 取数填纸。构成树可逐级展开。
 */

const CALC_STATUS = { ok: '价齐', partial: '有缺价', failed: '未算出' };
const AUDIT_STATUS = { pending: '待审核', approved: '已审核' };
const WELD_MATCH = {
    matched: '有价',
    missing_price: '缺价',
    unmapped: '认不出工序',
};

function padMonth(month) {
    const n = Number(month);
    return Number.isFinite(n) ? String(n).padStart(2, '0') : '';
}

function display(value) {
    if (value == null || value === '') return '—';
    return window.esc(value);
}

function money(value) {
    return display(value);
}

function fact(label, text, extraClass) {
    if (!text) return '';
    const mark = extraClass ? ` ${extraClass}` : '';
    return `<div class="fact-row${mark}"><span class="k">${display(label)}</span><span>${text}</span></div>`;
}

function sessionUser() {
    try {
        const raw = localStorage.getItem('brabus_user');
        if (!raw) return null;
        const session = JSON.parse(raw);
        if (!session || typeof session !== 'object') return null;
        return session;
    } catch (_) {
        return null;
    }
}

function authHeaders() {
    const session = sessionUser();
    if (session && session.token) {
        return {
            'X-Token': session.token,
            Authorization: `Bearer ${session.token}`,
        };
    }
    return {};
}

function paramsFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const view = params.get('view') === 'procurement' ? 'procurement' : 'finance';
    return {
        year: params.get('year') || '',
        month: params.get('month') || '',
        part_number: (params.get('part_number') || '').trim(),
        location: (params.get('location') || '').trim(),
        vehicle_model: params.get('vehicle_model') || '',
        bom_version: params.get('bom_version') || '',
        view,
        id: parseInt(params.get('id') || '', 10),
    };
}

async function loadRestore(params) {
    const query = new URLSearchParams({ view: params.view, _t: String(Date.now()) });
    let url;
    if (params.year && params.month && params.part_number) {
        query.set('year', params.year);
        query.set('month', params.month);
        query.set('part_number', params.part_number);
        if (params.location) query.set('location', params.location);
        if (params.vehicle_model) query.set('vehicle_model', params.vehicle_model);
        if (params.bom_version) query.set('bom_version', params.bom_version);
        url = `/api/costing/assembly-costs/restore?${query}`;
    } else if (Number.isFinite(params.id) && params.id > 0) {
        url = `/api/costing/assembly-costs/${params.id}/restore?${query}`;
    } else {
        throw new Error('缺少年度、月份、零件号');
    }
    const response = await fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            ...authHeaders(),
        },
    });
    if (response.status === 401) {
        const error = new Error('请先登录核价台后再打开');
        error.status = 401;
        throw error;
    }
    const payload = await response.json();
    if (!payload || payload.success === false) {
        throw new Error((payload && payload.message) || '加载失败');
    }
    return payload.data || {};
}

function setTabTitle(row) {
    const month = padMonth(row.month);
    document.title = `${row.part_number} ${row.year}年${month}月计算过程`;
}

function printDateText() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    return `${now.getFullYear()}年${month}月${day}日 ${hour}:${minute}`;
}

function operatorName() {
    const session = sessionUser();
    if (!session) return '未登录';
    const name = (session.real_name || session.name || session.username || '').trim();
    return name || '未登录';
}

function paintWatermark() {
    const layer = document.getElementById('reportWatermark');
    if (!layer) return;
    const line = `公司核心机密  ${operatorName()}  ${printDateText()}`;
    const mark = window.esc ? window.esc(line) : line;
    layer.innerHTML = Array.from({ length: 8 }, () => `<span>${mark}</span>`).join('');
}

function wallClockText(value) {
    if (value == null || value === '') return '—';
    const match = String(value).trim().match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (!match) return display(value);
    return `${match[1]}年${match[2]}月${match[3]}日 ${match[4]}:${match[5]}`;
}

function signOffHtml(row) {
    return `
        <footer class="sign-off">
            <p>核价人 ${display(row.calculated_by)}</p>
            <p>核价时间 ${wallClockText(row.calculated_at)}</p>
        </footer>
    `;
}

function coverHtml(row) {
    const month = padMonth(row.month);
    const moneyHint = row.highlight_label
        || (row.view === 'procurement' ? '结算价' : '总成价');
    const company = (row.company_name || '').trim();
    return `
        <header class="cover">
            <div class="masthead">
                ${company ? `<p class="company">${display(company)}</p>` : '<p class="company"></p>'}
                <div class="masthead-meta">
                    <span class="report-badge">计算过程</span>
                    <p class="print-date">打印 ${printDateText()}</p>
                </div>
            </div>
            <div class="cover-row">
                <div>
                    <h1 class="short-code">${display(row.short_code)}</h1>
                    <p class="full-part">${display(row.part_number)}</p>
                    <p class="part-name">${display(row.part_name)}</p>
                </div>
                <div class="cover-money">
                    <p class="hero-label">${display(moneyHint)}</p>
                    <p class="hero-amount">${money(row.highlight_amount)}</p>
                </div>
            </div>
            <dl class="spec">
                <div><dt>期间</dt><dd>${display(row.year)}年${display(month)}月</dd></div>
                <div><dt>基地</dt><dd>${display(row.location)}</dd></div>
                <div><dt>项目</dt><dd>${display(row.vehicle_model)}</dd></div>
                <div><dt>清单版本</dt><dd>${display(row.bom_version)}</dd></div>
            </dl>
            <p class="status-word">
                ${display(CALC_STATUS[row.calc_status] || row.calc_status)}
                · ${display(AUDIT_STATUS[row.audit_status] || row.audit_status)}
            </p>
        </header>
    `;
}

function exceptionsHtml(row) {
    const items = row.exceptions || [];
    if (!items.length) return null;
    const body = `<ul class="ex-list">${items.map((item) => `
        <li>
            <div class="ex-short">${display(item.short_code)}</div>
            <div class="ex-msg">${display(item.message)}</div>
        </li>
    `).join('')}</ul>`;
    return { title: '缺价', inner: body };
}

function identityHtml(row) {
    const bad = (row.identity_checks || []).filter((item) => !item.is_match);
    if (!bad.length) return null;
    const rows = `
        <div class="ledger-head">
            <span>项目</span><span class="num">本页</span><span class="num">明细加总</span><span class="num">结论</span>
        </div>
        ${bad.map((item) => `
        <div class="id-row">
            <div class="label">${display(item.label)}</div>
            <div class="num">${money(item.recorded)}</div>
            <div class="num">${money(item.summed)}</div>
            <div class="num bad">加总不符</div>
        </div>`).join('')}
    `;
    return { title: '数字核对', inner: rows };
}

function isZero(value) {
    return value == null || value === '' || Number(value) === 0;
}

function waterfallHtml(row) {
    const isProcurement = row.view === 'procurement';
    const weldLabel = isProcurement ? '焊装' : '本总成焊装';
    const items = [
        ['冲压件', row.stamping_amount],
        ['分总成', row.purchased_amount],
        ['外购件', row.bundle_amount],
        [weldLabel, row.welding_amount],
    ];
    if (isProcurement) {
        items.push(['结算价', row.total_amount, true]);
    } else {
        items.push(['摊入费用', row.indirect_amount]);
        items.push(['总成价', row.grand_total, true]);
    }
    const body = `<ul class="waterfall">${items.map(([label, amount, hero]) => {
        if (!hero && isZero(amount)) return '';
        return `
        <li class="${hero ? 'hero' : ''}">
            <span class="k">${display(label)}</span>
            <span class="amt">${money(amount)}</span>
        </li>`;
    }).join('')}</ul>`;
    return { title: '价格构成', inner: body };
}

function opsTable(rows) {
    if (!rows) return '';
    return `
        <div class="ops">
            <div class="ops-head"><span>序号</span><span>工序</span><span>说明</span><span>金额</span></div>
            ${rows}
        </div>
    `;
}

function ratioText(value) {
    if (value == null || value === '') return '';
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return number.toFixed(2);
}

function hasValue(value) {
    return value != null && value !== '';
}

function processOpHtml(op) {
    const inherit = op.tonnage_source === 'inherited' && op.inherited_from_part_number
        ? `吨位同 ${display(op.inherited_from_part_number)}${op.inherited_from_process_seq ? ` ${display(op.inherited_from_process_seq)}` : ''}`
        : (op.tonnage_source === 'swing_shear' ? '摆剪不计费' : '');
    // 吨位与系数空格相连，仅与冲次单价用 ×（避免读成三元相乘）
    const head = hasValue(op.resolved_tonnage) ? `${display(op.resolved_tonnage)}T` : '';
    const ratioPart = hasValue(op.cost_ratio) ? `系数 ${ratioText(op.cost_ratio)}` : '';
    const pricePart = hasValue(op.price_per_stroke)
        ? `冲次单价 ${money(op.price_per_stroke)}`
        : '';
    const left = [head, ratioPart].filter(Boolean).join(' ');
    const body = [left, pricePart].filter(Boolean).join(' × ');
    const equation = body ? `${body} = ${money(op.line_fee)}` : '';
    return `
        <div class="calc-op">
            <div class="calc-head">
                <span>${display(op.process_seq)}</span>
                <span>${display(op.process_code)}</span>
                <span>${money(op.line_fee)}</span>
            </div>
            ${equation ? `<p class="calc-eq">${equation}</p>` : ''}
            ${inherit ? `<p class="calc-note">${inherit}</p>` : ''}
            ${!equation && op.basis_text ? `<p class="calc-proof">${display(op.basis_text)}</p>` : ''}
        </div>
    `;
}

function dieOpHtml(op) {
    const bits = [];
    if (hasValue(op.estimated_weight_t)) bits.push(`估重 ${money(op.estimated_weight_t)} 吨`);
    if (hasValue(op.unit_price)) bits.push(`单价 ${money(op.unit_price)} 万元/吨`);
    if (hasValue(op.alloc_ratio)) bits.push(`系数 ${ratioText(op.alloc_ratio)}`);
    let equation = bits.join(' × ');
    if (hasValue(op.allocation_qty)) {
        equation = `${equation}${equation ? ' ÷ ' : ''}分摊 ${money(op.allocation_qty)} 万台`;
    }
    if (equation) {
        equation = `${equation} = ${money(op.line_die_fee)}`;
    }
    const sets = hasValue(op.die_sets)
        ? `<p class="calc-note">模具套数 ${display(op.die_sets)}</p>`
        : '';
    return `
        <div class="calc-op">
            <div class="calc-head">
                <span>${display(op.process_seq)}</span>
                <span>${display(op.process_code)}</span>
                <span>${money(op.line_die_fee)}</span>
            </div>
            ${equation ? `<p class="calc-eq">${equation}</p>` : ''}
            ${sets}
            ${op.basis_text ? `<p class="calc-proof">${display(op.basis_text)}</p>` : ''}
        </div>
    `;
}

function addMoney(values) {
    let total = 0;
    let any = false;
    values.forEach((value) => {
        if (!hasValue(value)) return;
        const number = Number(value);
        if (!Number.isFinite(number)) return;
        total += number;
        any = true;
    });
    return any ? total.toFixed(4) : '';
}

function thicknessText(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return display(value);
    const text = String(number);
    return text.includes('.') ? text : `${text}.0`;
}

function materialBasis(st) {
    const steel = st.steel || {};
    const bits = [];
    if (hasValue(st.material)) bits.push(`材质 ${display(st.material)}`);
    if (hasValue(st.thickness)) bits.push(`厚度 ${thicknessText(st.thickness)} mm`);
    if (steel.steel_mill || hasValue(steel.steel_ton_price)) {
        bits.push(`${display(steel.steel_mill)} ${money(steel.steel_ton_price)} 元/吨`);
    }
    return bits.join('  ');
}

function stampingBlock(node) {
    const st = node.stamping;
    if (!st) return '';
    if (st.record_missing) {
        return `<div class="facts">${fact('说明', display(st.missing_reason))}</div>`;
    }
    const material = st.is_offal_nested
        ? `利用废料 ${money(st.material_net_per_part)}`
        : money(st.material_net_per_part);
    const basis = materialBasis(st);
    const otherTotal = addMoney([
        st.finished_warehouse_packaging_fee,
        st.finished_management_fee,
        st.finished_finance_fee,
        st.finished_pretax_profit_fee,
    ]);
    const processOps = (st.process_ops || []).map(processOpHtml).join('');
    const dieOps = (st.die_ops || []).map(dieOpHtml).join('');
    return `
        <div class="facts fee-ledger">
            ${fact('材料', material)}
            ${basis ? `<div class="fact-note">${basis}</div>` : ''}
            ${fact('加工费', money(st.process_fee_amount))}
            ${fact('模具费', money(st.die_fee_amount))}
            ${hasValue(st.gauge_fee_amount) && Number(st.gauge_fee_amount) !== 0 ? fact('检具费', money(st.gauge_fee_amount)) : ''}
            ${fact('合计', money(st.direct_cost), 'is-sum')}
            ${!isZero(otherTotal) ? fact('其它费用', money(otherTotal)) : ''}
            ${isZero(st.finished_warehouse_packaging_fee) ? '' : fact('仓储+包装', money(st.finished_warehouse_packaging_fee), 'is-sub')}
            ${isZero(st.finished_management_fee) ? '' : fact('管理费', money(st.finished_management_fee), 'is-sub')}
            ${isZero(st.finished_finance_fee) ? '' : fact('财务费', money(st.finished_finance_fee), 'is-sub')}
            ${isZero(st.finished_pretax_profit_fee) ? '' : fact('税前利润', money(st.finished_pretax_profit_fee), 'is-sub')}
            ${fact('总计', money(st.unit_cost), 'is-total')}
            ${fact('本件', `${money(st.unit_cost)} × 用量 ${display(node.effective_qty)} = ${money(node.line_amount)}`)}
        </div>
        ${processOps ? `<div class="calc-block"><p class="calc-caption">加工费怎么算</p>${processOps}</div>` : ''}
        ${dieOps ? `<div class="calc-block"><p class="calc-caption">模具怎么算</p>${dieOps}</div>` : ''}
    `;
}

function nestByIndent(nodes) {
    const root = { children: [], indent: -1 };
    const stack = [root];
    (nodes || []).forEach((node) => {
        const indent = Number(node.indent_level) || 0;
        while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
            stack.pop();
        }
        const item = { node, indent, children: [] };
        stack[stack.length - 1].children.push(item);
        stack.push(item);
    });
    return root.children;
}

function isPurchasedPart(node) {
    return node.cost_source === 'annual'
        || node.cost_source === 'skipped_by_bundle'
        || node.cost_source === 'bundle'
        || node.supply_type === '标准件';
}

function canOpenRestore(node) {
    if (!node || !node.part_number) return false;
    if (isPurchasedPart(node)) return false;
    return true;
}

function restoreHref(report, node) {
    const query = new URLSearchParams({
        year: String(report.year || ''),
        month: String(report.month || ''),
        part_number: node.part_number || '',
        view: node.cost_source === 'sub_assembly' || node.cost_source === 'stamping'
            ? 'procurement'
            : (report.view || 'finance'),
    });
    if (report.location) query.set('location', report.location);
    if (report.vehicle_model) query.set('vehicle_model', report.vehicle_model);
    if (report.bom_version) query.set('bom_version', report.bom_version);
    return `/assembly-cost-restore?${query}`;
}

function nodeHead(node, childCount, report) {
    const hint = childCount
        ? `<span class="fold-hint"> · 下级 ${childCount} 件</span>`
        : '';
    const openLabel = node.cost_source === 'sub_assembly' ? '采购对象' : '计算过程';
    const openLink = report && canOpenRestore(node)
        ? `<a class="node-open" href="${restoreHref(report, node)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">${openLabel}</a>`
        : '';
    const hideFull = Boolean(node.part_number) && node.short_code === node.part_number;
    const fullLine = hideFull
        ? ''
        : `<div class="node-full">${display(node.part_number)}</div>`;
    return `
        <span class="fold-mark" aria-hidden="true"></span>
        <div class="node-seq">${node.seq_label ? display(node.seq_label) : ''}</div>
        <div class="node-short">${display(node.short_code)}</div>
        <div class="node-main">
            ${fullLine}
            <div class="node-name">${display(node.part_name)}<span class="node-src"> · ${display(node.cost_source_label)}</span>${hint}${openLink}</div>
        </div>
        <div class="node-amt">${money(node.line_amount)}</div>
    `;
}

function nodeFold(item, report) {
    const node = item.node;
    const kidsHtml = item.children.length ? treeList(item.children, report) : '';
    const broken = node.cost_source === 'missing' || (node.stamping && node.stamping.record_missing);
        const annual = node.annual && !node.annual.record_missing
        ? `<div class="facts">${fact('单价', money(node.annual.unit_price))}</div>`
        : '';
    const body = `${annual}${stampingBlock(node)}`;
    const mark = broken ? ' is-break' : '';
    if (!kidsHtml && !body) {
        return `<article class="node${mark}"><div class="node-head">${nodeHead(node, 0, report)}</div></article>`;
    }
    return `
        <details class="node-fold${mark}">
            <summary class="node-head">${nodeHead(node, item.children.length, report)}</summary>
            ${body ? `<div class="node-body">${body}</div>` : ''}
            ${kidsHtml}
        </details>
    `;
}

function treeList(items, report) {
    return `<ol class="bom-tree">${items.map((item) => `<li>${nodeFold(item, report)}</li>`).join('')}</ol>`;
}

function nodesHtml(row) {
    const nested = nestByIndent(row.material_nodes || []);
    if (!nested.length) {
        return { title: '零件构成', inner: '<p class="quiet">无子件</p>' };
    }
    const hasSubAssembly = (row.material_nodes || []).some(
        (node) => node.cost_source === 'sub_assembly',
    );
    const reasons = [];
    // is_purchased_assembly / welding.message 都由后端 P4 写出，前端不另造文案。
    if (row.is_purchased_assembly && row.welding && row.welding.message) {
        reasons.push(`<details class="why-fold">
            <summary>为什么子件是 0、不计焊装</summary>
            <p>${display(row.welding.message)}</p>
        </details>`);
    } else if (row.view !== 'procurement' && hasSubAssembly) {
        reasons.push(`<details class="why-fold">
            <summary>为什么分总成只计材料</summary>
            <p>总成的焊信上已经包含所有分总成焊信。采购对象结算价另含焊装，两页不能加在一起。</p>
        </details>`);
    }
    const inner = `
        <p class="compose-lead">${display(row.short_code)}　点行展开下级与算价</p>
        ${reasons.join('')}
        ${treeList(nested, row)}
    `;
    return { title: '零件构成', inner };
}

function weldingHtml(row) {
    const weld = row.welding || {};
    if (!weld.has_record) {
        return { title: '焊装', inner: `<p class="quiet">${display(weld.message || '无焊装')}</p>` };
    }
    const lines = (weld.items || []).map((line) => `
        <div class="ops-row">
            <span>${display(WELD_MATCH[line.match_status] || line.match_status)}</span>
            <span>${display(line.standard_process_name || line.process_token)}</span>
            <span>${display(line.process_qty)} × ${money(line.unit_price)}</span>
            <span>${money(line.line_fee)}</span>
        </div>
    `).join('');
    const body = `
        ${weld.weld_info_raw ? `<blockquote class="quote-block">${display(weld.weld_info_raw)}</blockquote>` : ''}
        <div class="facts">${fact('焊装合计', money(weld.final_welding_fee))}</div>
        ${lines ? opsTable(lines) : ''}
    `;
    return { title: '焊装', inner: body };
}

function indirectHtml(row) {
    if (row.view === 'procurement') return null;
    const lines = row.indirects || [];
    if (!lines.length) {
        return { title: '摊入费用', inner: '<p class="quiet">无摊入费用</p>' };
    }
    const body = `
        <div class="ledger-head">
            <span>项目</span><span class="num">计入方式</span><span class="num">金额</span><span></span>
        </div>
        ${lines.map((line) => `
        <div class="id-row">
            <div class="label">${display(line.label)}${line.note ? `<div class="node-full">${display(line.note)}</div>` : ''}</div>
            <div class="num">${line.kind === 'direct' ? '按件计入' : '按比例摊入'}</div>
            <div class="num">${money(line.amount)}</div>
            <div></div>
        </div>`).join('')}
    `;
    return { title: '摊入费用', inner: body };
}

function documentsHtml(row) {
    const docs = row.documents || [];
    if (!docs.length) return null;
    const body = `<ol class="refs">${docs.map((doc) => {
        const cat = display(doc.file_category_label || '资料');
        const rowNo = doc.excel_row ? `，第 ${display(doc.excel_row)} 行` : '';
        const cites = (doc.cited_short_codes || []).length
            ? `（${display((doc.cited_short_codes || []).join('、'))}）`
            : '';
        return `<li><span class="refs-cat">${cat}</span> ${display(doc.filename)}${rowNo}${cites}</li>`;
    }).join('')}</ol>`;
    return { title: '资料来源', inner: body, kind: 'refs' };
}

function paintChapter(no, title, inner, kind) {
    if (kind === 'refs') {
        return `
            <section class="chapter refs-chapter">
                <h2 class="refs-title">${display(title)}</h2>
                ${inner}
            </section>
        `;
    }
    return `
        <section class="chapter">
            <header class="chap-head">
                <p class="chap-no">${display(no)}</p>
                <h2 class="chap-title">${display(title)}</h2>
            </header>
            ${inner}
        </section>
    `;
}

function render(root, row) {
    setTabTitle(row);
    const blocks = [
        exceptionsHtml(row),
        identityHtml(row),
        waterfallHtml(row),
        nodesHtml(row),
        weldingHtml(row),
        indirectHtml(row),
        documentsHtml(row),
    ].filter(Boolean);
    let seq = 1;
    const chapters = blocks.map((block) => {
        if (block.kind === 'refs') {
            return paintChapter('', block.title, block.inner, 'refs');
        }
        const no = String(seq).padStart(2, '0');
        seq += 1;
        return paintChapter(no, block.title, block.inner);
    });
    root.innerHTML = coverHtml(row) + chapters.join('') + signOffHtml(row);
    root.addEventListener('click', (event) => {
        if (event.target.closest('.node-open')) {
            event.stopPropagation();
        }
    }, true);
}

async function boot() {
    paintWatermark();
    const root = document.getElementById('reportRoot');
    const params = paramsFromUrl();
    const hasKeys = Boolean(params.year && params.month && params.part_number);
    const hasId = Number.isFinite(params.id) && params.id > 0;
    if (!hasKeys && !hasId) {
        root.innerHTML = '<div class="state error">缺少年度、月份、零件号。</div>';
        return;
    }
    try {
        const row = await loadRestore(params);
        render(root, row);
    } catch (error) {
        const message = error && error.status === 401
            ? '请先登录核价台后再打开'
            : (error && error.message) || '加载失败';
        root.innerHTML = `<div class="state error">${display(message)}</div>`;
    }
}

boot();

window.addEventListener('beforeprint', () => {
    const stamp = document.querySelector('.print-date');
    if (stamp) stamp.textContent = `打印 ${printDateText()}`;
    paintWatermark();
});
