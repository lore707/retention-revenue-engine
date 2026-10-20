// Dependency-free interaction checks. Geometry is simulated; these do not replace browser visual QA.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const frontend = path.join(__dirname, '..', 'frontend');

function harness(search = '', page = 'retention') {
  let document;
  class UIEvent {
    constructor(type, options = {}) {Object.assign(this, {type, bubbles: true}, options);}
    preventDefault() {this.defaultPrevented = true;}
    stopPropagation() {this.stopped = true;}
  }
  class Node {
    constructor(tag) {
      this.tagName = tag.toUpperCase(); this.childNodes = []; this.events = {}; this.attributes = {};
      this.className = ''; this.style = {}; this.dataset = {}; this._text = ''; this.hidden = false; this.disabled = false;
      this.classList = {
        add: (...names) => {this.className = [...new Set([...this.className.split(' '), ...names])].join(' ');},
        remove: name => {this.className = this.className.split(' ').filter(value => value !== name).join(' ');},
        toggle: (name, enabled) => enabled ? this.classList.add(name) : this.classList.remove(name)
      };
    }
    get children() {return this.childNodes.filter(node => node.tagName !== '#TEXT');}
    get options() {return this.children;}
    get selectedOptions() {return this.options.filter(option => option.value === this.value);}
    get value() {return this._value ?? (this.tagName === 'SELECT' ? this.options[0]?.value ?? '' : '');}
    set value(value) {this._value = this.tagName === 'SELECT' && !this.options.some(option => option.value === value) ? '' : String(value);}
    get textContent() {return this._text + this.childNodes.map(node => node.textContent).join('');}
    set textContent(value) {this._text = String(value); this.childNodes = [];}
    get offsetWidth() {return parseFloat(this.style.width) || 320;}
    get offsetHeight() {return Math.min(450, parseFloat(this.style.maxHeight) || 450);}
    get isConnected() {return true;}
    get parentElement() {return this.parent;}
    append(...nodes) {
      for (let node of nodes) {
        if (typeof node !== 'object') {const text = new Node('#text'); text.textContent = node; node = text;}
        node.parent = this; this.childNodes.push(node);
      }
    }
    replaceChildren(...nodes) {this.childNodes = []; this._text = ''; this.append(...nodes);}
    replaceWith(node) {
      const index = this.parent.childNodes.indexOf(this); this.parent.childNodes[index] = node; node.parent = this.parent;
      if (this === document.body) document.body = node;
    }
    after(...nodes) {const index = this.parent.childNodes.indexOf(this); for (const node of nodes) node.parent = this.parent; this.parent.childNodes.splice(index + 1, 0, ...nodes);}
    setAttribute(name, value) {this.attributes[name] = String(value); if (name === 'class') this.className = String(value);}
    removeAttribute(name) {delete this.attributes[name];}
    hasAttribute(name) {return Object.hasOwn(this.attributes, name);}
    addEventListener(type, listener) {(this.events[type] ||= []).push(listener);}
    removeEventListener(type, listener) {this.events[type] = (this.events[type] || []).filter(item => item !== listener);}
    cloneNode(deep = false) {
      const copy = new Node(this.tagName); Object.assign(copy, {attributes: {...this.attributes}, dataset: {...this.dataset}, className: this.className, _text: this._text});
      for (const key of ['id', 'href', 'src', 'rel', 'hidden', 'disabled', '_value', 'type']) if (this[key] !== undefined) copy[key] = this[key];
      if (deep) copy.append(...this.childNodes.map(node => node.cloneNode(true)));
      return copy;
    }
    closest(selector) {return this.matches(selector) ? this : this.parent?.closest(selector);}
    dispatchEvent(event) {
      event.target ||= this;
      for (const listener of this.events[event.type] || []) listener(event);
      if (event.bubbles && !event.stopped) this.parent?.dispatchEvent(event);
      return !event.defaultPrevented;
    }
    contains(node) {return this.all().includes(node);}
    all() {return [this, ...this.childNodes.flatMap(node => node.all())];}
    matches(selector) {
      const attribute = selector.match(/^([\w-]+)\[([\w-]+)(?:="([^"]*)")?\]$/);
      if (attribute) return this.tagName === attribute[1].toUpperCase() && this.hasAttribute(attribute[2]) && (attribute[3] === undefined || this[attribute[2]] === attribute[3]);
      return selector[0] === '#' ? this.id === selector.slice(1) : selector[0] === '.' ? this.className.split(' ').includes(selector.slice(1)) : this.tagName === selector.toUpperCase();
    }
    querySelectorAll(selector) {return this.all().filter(node => node.matches(selector));}
    querySelector(selector) {return this.querySelectorAll(selector)[0] || null;}
    focus() {document.activeElement = this; this.dispatchEvent(new UIEvent('focusin'));}
    scrollIntoView() {this.scrolled = true;}
    getBoundingClientRect() {return this.rect || {left: 280, top: 220, bottom: 284, width: 240};}
    close() {this.open = false;}
    showModal() {this.open = true;}
  }
  class Option extends Node {
    constructor(title, value) {super('option'); this.textContent = title; this.value = value;}
  }
  function parseHTML(html) {
  const root = new Node('html'), stack = [root];
  for (const part of html.match(/<[^>]*>|[^<]+/g)) {
    if (part.startsWith('<!')) continue;
    if (part.startsWith('</')) {stack.pop(); continue;}
    if (!part.startsWith('<')) {if (part.trim()) stack.at(-1).append(part.trim()); continue;}
    const match = part.match(/^<([\w-]+)([\s\S]*?)>$/); if (!match) continue;
    const node = new Node(match[1]);
    for (const attribute of match[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g)) {
      const [ , name, value] = attribute; node.attributes[name] = value ?? '';
      if (name === 'class') node.className = value;
      else if (['hidden', 'disabled'].includes(name)) node[name] = true;
      else if (name.startsWith('data-')) node.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = value;
      else node[name] = value;
    }
    stack.at(-1).append(node);
    if (!['input', 'img', 'meta', 'link', 'br'].includes(match[1])) stack.push(node);
  }
  root.body = root.querySelector('body'); root.title = root.querySelector('title').textContent;
  return root;
  }
  const root = parseHTML(fs.readFileSync(path.join(frontend, `${page}.html`), 'utf8'));
  root.clientWidth = 1440;
  document = new Node('document'); document.append(root); document.body = root.querySelector('body'); document.head = root.querySelector('head'); document.documentElement = root;
  // The styles are already available in the simulated browser; actual loading is tested through server MIME tests.
  for (const name of ['retention', 'rules']) {const style = new Node('link'); style.rel = 'stylesheet'; style.href = `/${name}.css`; style.setAttribute('rel', 'stylesheet'); document.head.append(style);}
  document.createElement = tag => new Node(tag); document.createElementNS = (_, tag) => new Node(tag);
  const location = new URL(`http://localhost/${page === 'overview' ? '' : page}${search}`), calls = [], timers = new Map(); let timerId = 0;
  const data = {active: true, demo: true, date: '2026-10-15', analyzed_customers: 13,
    urgency_legend: [
      {rank: 1, label: 'Risposta da gestire', tone: 'rose'}, {rank: 2, label: 'Follow-up dovuto', tone: 'amber'},
      {rank: 3, label: 'Primo contatto · Mirata', tone: 'blue'}, {rank: 4, label: 'Primo contatto · Da testare', tone: 'purple'},
      {rank: 5, label: 'Nessuna azione oggi', tone: 'slate'}],
    purchased_product_options: [{value: 'synthetic_product', label: 'Prodotto acquistato sintetico'}],
    activity_views: [
      {key: 'today', label: 'Da gestire oggi', description: 'Risposte e follow-up dovuti', count: 2},
      {key: 'opportunities', label: 'Nuove opportunità', description: 'Clienti pronti da contattare', count: 4},
      {key: 'working', label: 'In lavorazione', description: 'Piani commerciali già avviati', count: 3},
      {key: 'history', label: 'Storico da recuperare', description: 'Clienti ancora da rivalutare', count: 1}],
    activity_unassigned_customers: 3,
    metrics: {ready_customers: 8}, unassigned_review_orders: 0, rows: [], product_images: {},
    operational_views: [
      {key: 'targeted', label: 'Opportunità mirate', description: 'Descrizione ricevuta dal backend', tone: 'blue', count: 5},
      {key: 'test', label: 'Opportunità da testare', description: 'Proposte da sperimentare', tone: 'purple', count: 3},
      {key: 'none', label: 'Nessuna azione immediata', description: 'Attese o blocchi', tone: 'amber', count: 5}
    ]};
  if (page === 'overview') {
    Object.assign(data.metrics, {potential_value_minor: 14995, registered_contacts: 6, attributed_revenue_minor: 2400, verified_orders: 1});
    Object.assign(data, {period: '30d', starts_on: '2026-09-16', chart: {attributed_revenue_minor: 2400, verified_orders: 1,
      series: [{date: '2026-09-16', amount_minor: 0}, {date: '2026-10-15', amount_minor: 2400}]}});
  }
  if (page === 'rules') Object.assign(data, JSON.parse(execFileSync('python', ['-c',
    'import json; from src.customer_profiles import rules_summary; print(json.dumps(rules_summary()))'],
    {cwd: path.join(__dirname, '..'), encoding: 'utf8'})));
  const window = new Node('window'); window.innerHeight = 900;
  const state = {data, calls, fail: false, pending: null, importResult: {active: true, imported_files: 1}};
  const updateURL = (_, __, url) => {location.href = new URL(url, location).href;};
  window.scrollTo = () => {};
  const context = vm.createContext({document, window, Option, Event: UIEvent, URL, URLSearchParams, Intl, Date, JSON, Set, Map,
    DOMParser: class {parseFromString(html) {return parseHTML(html);}},
    location, history: {replaceState: updateURL, pushState: updateURL}, console, encodeURIComponent,
    FormData: class {constructor(form) {this.form = form;}},
    setInterval() {}, clearInterval() {}, setTimeout: callback => {timers.set(++timerId, callback); return timerId;}, clearTimeout: id => timers.delete(id),
    fetch: async url => {
      if (!url.startsWith('/api/')) {calls.push(url); return {ok: true, text: async () => fs.readFileSync(path.join(frontend, `${url === '/' ? 'overview' : url.slice(1)}.html`), 'utf8')};}
      calls.push(url); const responseData = structuredClone(state.fail ? {error: 'Errore sintetico'} : url === '/api/import' ? state.importResult : state.data);
      const response = {ok: !state.fail, json: async () => responseData};
      return state.pending ? await new Promise(resolve => state.pending.push(() => resolve(response))) : response;
    }});
  vm.runInContext(fs.readFileSync(path.join(frontend, 'ui.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(frontend, `${page}.js`), 'utf8'), context);
  const $ = selector => document.querySelector(selector);
  const fire = (node, type, options) => node.dispatchEvent(new UIEvent(type, options));
  const controls = () => vm.runInContext('activePage.controls', context);
  const settle = () => new Promise(setImmediate);
  return {...state, state, $, fire, controls, document, window, location, context, settle,
    flush: async () => {for (const [id, callback] of [...timers]) {timers.delete(id); await callback();} await settle();}};
}

test('single-select filters use backend priority counts, descriptions and disabled profile choices', async () => {
  const h = harness(); await h.settle();
  assert.equal(h.controls().length, 6);
  for (const control of h.controls()) {
    assert.equal(control.select.hidden, true);
    assert.equal(control.trigger.attributes['aria-expanded'], 'false');
    assert.equal(control.trigger.attributes['aria-haspopup'], 'dialog');
    assert.equal(h.$(`#${control.select.id}-label`).htmlFor, control.trigger.id);
    h.fire(control.trigger, 'click');
    assert.equal(h.document.activeElement, control.popup.querySelector('input'));
    assert.equal(control.popup.hidden, false);
  }
  const category = h.controls()[0]; h.fire(category.trigger, 'click');
  assert.equal(category.popup.querySelectorAll('.filter-option-count').map(node => node.textContent).join(','), '13,5,3,5');
  assert(category.popup.textContent.includes('Descrizione ricevuta dal backend'));
  for (const control of h.controls().slice(1)) assert.equal(control.popup.querySelectorAll('.filter-option-count').length, 0);
  const profile = h.controls()[3]; h.fire(profile.trigger, 'click');
  const disabled = profile.popup.querySelectorAll('.floating-filter-option').filter(node => node.attributes['aria-disabled'] === 'true');
  assert.equal(disabled.length, 2);
  h.fire(disabled[0], 'click'); assert.equal(profile.select.value, '');
  assert.equal(profile.trigger.attributes['aria-expanded'], 'true');
  assert.equal(profile.popup.querySelector('[aria-multiselectable]'), null);
});

test('search, arrow keys, Enter, Escape, Tab, outside click and one popup at a time', async () => {
  const h = harness(); await h.settle(); const [category, state] = h.controls();
  h.fire(category.trigger, 'keydown', {key: 'ArrowDown'});
  let input = category.popup.querySelector('input');
  h.fire(input, 'keydown', {key: 'ArrowDown'}); h.fire(input, 'keydown', {key: 'Enter'}); await h.settle();
  assert.equal(category.select.value, 'targeted'); assert.equal(h.document.activeElement, category.trigger);
  assert.equal(new URLSearchParams(h.calls.at(-1).split('?')[1]).get('category'), 'targeted');
  h.fire(category.trigger, 'click'); input.value = 'da testare'; h.fire(input, 'input');
  assert.equal(category.popup.querySelectorAll('.floating-filter-option').length, 1);
  h.fire(input, 'keydown', {key: 'Escape'}); assert.equal(category.select.value, 'targeted');
  h.fire(category.trigger, 'click'); input.value = 'inesistente'; h.fire(input, 'input');
  assert.equal(category.popup.querySelector('.floating-filter-status').hidden, false);
  h.fire(input, 'keydown', {key: 'Enter'}); assert.equal(category.select.value, 'targeted');
  h.fire(state.trigger, 'click'); assert.equal(category.trigger.attributes['aria-expanded'], 'false');
  h.fire(state.popup.querySelector('input'), 'keydown', {key: 'Tab'});
  assert.equal(state.trigger.attributes['aria-expanded'], 'false'); assert.equal(h.document.activeElement, state.trigger);
  h.fire(category.trigger, 'click'); h.fire(h.$('#search'), 'pointerdown');
  assert.equal(category.trigger.attributes['aria-expanded'], 'false');
  h.fire(category.trigger, 'click'); h.$('#search').focus();
  assert.equal(category.trigger.attributes['aria-expanded'], 'false');
  await h.flush(); assert.equal(category.popup.hidden, true);
});

test('all filters round-trip through URL, chip removal and reset preserve unrelated parameters', async () => {
  const h = harness('?view=targeted&state=open&strategy=complement&profile=recurring&search=ordine&source=overview#lista'); await h.settle();
  for (const [index, value] of ['targeted', 'open', 'complement', 'recurring'].entries()) assert.equal(h.controls()[index].select.value, value);
  assert.equal(h.$('#search').value, 'ordine');
  const request = new URLSearchParams(h.calls[0].split('?')[1]);
  assert.equal(request.get('profile'), 'recurring'); assert.equal(request.get('strategy'), 'complement');
  assert.equal(h.$('#filter-chips').querySelectorAll('.retention-filter-chip').length, 5);
  h.fire(h.$('#filter-chips').querySelector('.retention-filter-chip'), 'click'); await h.settle();
  assert.equal(h.controls()[0].select.value, ''); assert.equal(h.location.searchParams.get('view'), null);
  assert.equal(h.location.searchParams.get('state'), 'open'); assert.equal(h.location.searchParams.get('source'), 'overview');
  h.fire(h.$('#filters'), 'reset'); await h.settle();
  assert.equal(h.$('#filter-chips').hidden, true); assert.equal(h.$('#search').value, '');
  assert.equal(h.location.search, '?source=overview'); assert.equal(h.location.hash, '#lista');
  h.location.search = '?view=test&state=closed&profile=first_purchase&source=overview'; h.fire(h.window, 'popstate'); await h.settle();
  assert.equal(h.controls()[0].select.value, 'test'); assert.equal(h.controls()[1].select.value, 'closed');
  assert.equal(h.controls()[3].select.value, 'first_purchase');
});

test('invalid and unavailable URL values do not become selected; legacy category links still work', async () => {
  const h = harness('?category=none&profile=possible_b2b&state=invalid'); await h.settle();
  assert.equal(h.controls()[0].select.value, 'none'); assert.equal(h.controls()[3].select.value, '');
  assert.equal(h.controls()[1].select.value, '');
  const request = new URLSearchParams(h.calls[0].split('?')[1]); assert.equal(request.get('profile'), ''); assert.equal(request.get('state'), '');
});

test('popup geometry stays inside a narrow viewport and flips above when needed', async () => {
  const h = harness(); await h.settle(); const control = h.controls()[0];
  h.document.documentElement.clientWidth = 375; h.window.innerHeight = 400;
  control.trigger.rect = {left: 290, top: 320, bottom: 384, width: 240}; h.fire(control.trigger, 'click');
  const popup = control.popup;
  assert(popup.className.includes('opens-above'));
  assert(parseFloat(popup.style.left) >= 12);
  assert(parseFloat(popup.style.left) + popup.offsetWidth <= 363);
  assert(parseFloat(popup.style.top) >= 8);
  assert(parseFloat(popup.style.top) + popup.offsetHeight < control.trigger.rect.top);
  h.window.innerHeight = 200;
  control.trigger.rect = {left: 290, top: 80, bottom: 136, width: 240}; control.position();
  assert(parseFloat(popup.style.top) >= 12);
  assert(parseFloat(popup.style.top) + popup.offsetHeight <= 188);
  control.trigger.rect = {left: 290, top: -80, bottom: -24, width: 240}; control.position();
  assert.equal(control.trigger.attributes['aria-expanded'], 'false');
});

test('keyboard skips unavailable profile options and refresh preserves focused chips', async () => {
  const h = harness('?profile=recurring'); await h.settle(); const profile = h.controls()[3];
  h.fire(profile.trigger, 'keydown', {key: 'ArrowUp'});
  const input = profile.popup.querySelector('input');
  const activeId = input.attributes['aria-activedescendant'];
  assert.equal(h.$('#' + activeId).attributes['aria-disabled'], undefined);
  h.fire(input, 'keydown', {key: 'ArrowDown'});
  assert.equal(input.attributes['aria-activedescendant'], activeId);
  h.fire(input, 'keydown', {key: 'Escape'});
  const chip = h.$('#filter-chips').querySelector('.retention-filter-chip'); chip.focus();
  await vm.runInContext('activePage.refresh()', h.context);
  assert.equal(h.$('#filter-chips').querySelector('.retention-filter-chip'), chip);
  assert.equal(h.document.activeElement, chip);
  h.fire(profile.trigger, 'click'); h.fire(input, 'keydown', {key: 'Tab', shiftKey: true});
  assert.equal(h.document.activeElement, profile.trigger);
});

test('floating filters fit smartphone widths, landscape and the visual viewport above the keyboard', async () => {
  for (const page of ['overview', 'retention', 'rules']) {
    const h = harness('', page); await h.settle();
    const control = h.controls()[0];
    for (const [width, height, offsetTop] of [[320, 568, 0], [375, 667, 0], [430, 932, 0], [667, 320, 0], [320, 240, 120]]) {
      h.document.documentElement.clientWidth = width; h.window.innerHeight = height;
      h.window.visualViewport = {width, height, offsetTop, offsetLeft: 0};
      control.trigger.rect = {left: 14, top: offsetTop + 30, bottom: offsetTop + 86, width: width - 28};
      h.fire(control.trigger, 'click'); control.position();
      const popup = control.popup, left = parseFloat(popup.style.left), top = parseFloat(popup.style.top);
      assert(left >= 12 && left + popup.offsetWidth <= width - 12, `${page}: horizontal ${width}`);
      assert(top >= offsetTop + 12 && top + popup.offsetHeight <= offsetTop + height - 12, `${page}: vertical ${height}`);
      h.fire(popup.querySelector('input'), 'keydown', {key: 'Escape'});
      assert.equal(control.trigger.attributes['aria-expanded'], 'false');
    }
  }
});

test('debounced search, API errors and stale-response guard remain functional', async () => {
  const h = harness(); await h.settle();
  h.$('#search').value = 'prima'; h.fire(h.$('#search'), 'input');
  h.$('#search').value = 'dopo'; h.fire(h.$('#search'), 'input'); await h.flush();
  assert.equal(h.calls.length, 2); assert.equal(h.location.searchParams.get('search'), 'dopo');
  h.state.fail = true; await vm.runInContext('activePage.refresh()', h.context);
  assert.equal(h.$('#notice').textContent, 'Errore sintetico'); h.state.fail = false;
  h.state.pending = []; const old = vm.runInContext('activePage.refresh()', h.context);
  h.state.data = {...h.data, analyzed_customers: 21}; const latest = vm.runInContext('activePage.refresh()', h.context);
  h.state.pending[1](); await latest; h.state.pending[0](); await old;
  assert(h.controls()[0].trigger.textContent.includes('21 clienti'));
});

test('filtered backend rows keep their main proposal, client action and pagination', async () => {
  const h = harness('?strategy=complement&state=open'); await h.settle();
  const row = {customer_id: 'SYNTHETIC_UI_001', category: 'targeted', customer_profile: {signals: []},
    urgency: {key: 'first_targeted', rank: 3, label: 'Primo contatto · Mirata', tone: 'blue', date: '2026-08-16', date_label: 'Maturo dal', mixed_plan: true},
    source_product: 'Prodotto fonte sintetico', order_number: '#SYNTHETIC', source_date: '2026-08-01',
    proposal: 'Proposta principale dal backend', contactable: true, strategy_label: 'Completamenti funzionali',
    strategy: 'completion', target_sku: 'SYNTHETIC_SKU', value_minor: 2400, reason: 'Motivazione dal backend',
    plan_key: ['synthetic', 'accessories'], plans: [], matching_plans: [
      {state: 'open', opportunities: [{proposal: 'Alternativa corrispondente', strategy_label: 'Complementi d’uso'}]}
    ]};
  h.state.data = {...h.data, rows: Array.from({length: 26}, (_, index) => ({...row, customer_id: `SYNTHETIC_UI_${index}`}))};
  await vm.runInContext('activePage.refresh()', h.context);
  assert.equal(h.$('#customers').children.length, 25);
  assert.deepEqual(h.$('#customers').children[0].children.slice(0, 7).map(cell => cell.dataset.label),
    ['Cliente / urgenza', 'Profilo', 'Acquisto fonte', 'Raccomandazione principale', 'Strategia', 'Corrispondenze / motivo', 'Valore']);
  assert.equal(h.$('#urgency-legend').children.length, 5);
  assert(h.$('#customers').children[0].textContent.includes('3 · Primo contatto · Mirata'));
  assert(h.$('#customers').children[0].textContent.includes('Mirate e Da testare nella stessa mail'));
  assert(h.$('#customers').children[0].className.includes('filter-tone-blue'));
  assert(h.$('#customers').children[0].textContent.includes('Proposta principale dal backend'));
  assert(h.$('#customers').children[0].textContent.includes('Alternativa corrispondente'));
  let opened; h.context.recordOpen = item => {opened = item;}; vm.runInContext('openPlan = recordOpen;', h.context);
  h.fire(h.$('#customers').querySelector('.open-button'), 'click');
  assert.equal(opened.customer_id, 'SYNTHETIC_UI_0');
  assert.equal(opened.proposal, 'Proposta principale dal backend');
  h.fire(h.$('#next'), 'click'); assert.equal(h.$('#customers').children.length, 1);
  assert.equal(h.$('#page-label').textContent, '26–26 di 26');
});

test('Retention matches activity cards and advanced controls, preserving product and scope in URLs and reset', async () => {
  const h = harness('?activity=history&product=synthetic_product&strategy=completion&scope=all_plans&state=closed&source=overview#lista'); await h.settle();
  const tabs = h.$('#activity-tabs').children;
  assert.equal(tabs.length, 4);
  assert.equal(tabs.map(tab => tab.querySelector('strong').textContent).join(','), 'Da gestire,Nuove opportunità,Storico da recuperare,Tutti i clienti');
  assert.equal(tabs.map(tab => tab.querySelector('small').textContent).join(','), '2 clienti,4 clienti,1 cliente,13 clienti');
  assert.equal(tabs.map(tab => tab.attributes['aria-pressed']).join(','), 'false,false,true,false');
  assert.equal(h.$('#advanced-filters').hidden, false);
  assert.equal(h.$('#advanced-toggle').attributes['aria-expanded'], 'true');
  const request = new URLSearchParams(h.calls[0].split('?')[1]);
  assert.equal(request.get('product'), 'synthetic_product'); assert.equal(request.get('scope'), 'all_plans');
  assert(h.$('#filter-chips').textContent.includes('Prodotto acquistato sintetico'));
  h.fire(h.$('#advanced-toggle'), 'click'); assert.equal(h.$('#advanced-filters').hidden, true);
  assert.equal(h.controls()[1].select.value, 'closed');
  h.fire(h.$('#activity-tabs').children[0], 'click'); await h.settle();
  assert.equal(h.location.searchParams.get('activity'), 'today');
  assert.equal(h.location.searchParams.get('product'), 'synthetic_product');
  assert.equal(h.location.searchParams.get('source'), 'overview'); assert.equal(h.location.hash, '#lista');
  h.fire(h.$('#activity-tabs').children[3], 'click'); await h.settle();
  assert.equal(h.location.searchParams.get('activity'), null);
  assert.equal(h.$('#activity-tabs').children[3].attributes['aria-pressed'], 'true');
  h.fire(h.$('#filters'), 'reset'); await h.settle();
  assert.equal(h.location.searchParams.get('scope'), null); assert.equal(h.location.searchParams.get('product'), null);
  assert.equal(h.$('#advanced-filters').hidden, true); assert(h.controls().every(control => control.select.value === ''));
  h.location.search = '?product=synthetic_product&scope=all_plans'; h.fire(h.window, 'popstate'); await h.settle();
  assert.equal(h.controls()[4].select.value, 'synthetic_product'); assert.equal(h.controls()[5].select.value, 'all_plans');
  assert.equal(h.$('#advanced-filters').hidden, false);
});

test('Overview displays backend KPI, four activity cards, consent base and chart values', async () => {
  const h = harness('', 'overview'); await h.settle();
  assert.equal(h.calls[0], '/api/overview?period=30d');
  assert.equal(h.$('#ready-count').textContent, '8'); assert.equal(h.$('#potential').textContent, '€ 149,95');
  assert.equal(h.$('#contacts').textContent, '6'); assert.equal(h.$('#revenue').textContent, '€ 24,00');
  assert.equal(h.$('#chart-total').textContent, '€ 24,00');
  const cards = h.$('#operational-views').children;
  assert.equal(cards.map(card => card.href).join(','), '/retention?activity=today,/retention?activity=opportunities,/retention?activity=working,/retention?activity=history');
  assert.equal(cards.map(card => card.querySelector('strong').textContent).join(','), '2,4,3,1');
  assert.equal(h.$('#operational-note').textContent, '13 clienti con consenso email valido');
  assert(h.$('#retention-base-other').textContent.includes('3 altri clienti'));
  assert.equal(h.$('#customers').children[0].children[0].colSpan, 8);
  const points = h.$('#chart').querySelectorAll('.hit'); assert.equal(points.length, 2);
  h.fire(points[1], 'focus'); assert(h.$('#chart-tooltip').textContent.includes('€ 24,00'));
  h.fire(points[1], 'blur'); assert.equal(h.$('#chart-tooltip').hidden, true);
  h.fire(points[1], 'click'); assert.equal(h.$('#chart-tooltip').hidden, false);
});

test('Overview activity links remain visible and removable when combining Retention filters and navigating back', async () => {
  const h = harness('?activity=history&view=targeted&source=overview#lista'); await h.settle();
  assert.equal(new URLSearchParams(h.calls[0].split('?')[1]).get('activity'), 'history');
  assert(h.$('#active-filters').textContent.includes('Storico da recuperare'));
  const chip = h.$('#filter-chips').querySelectorAll('.retention-filter-chip').find(node => node.textContent.includes('Storico'));
  assert(chip); h.controls()[2].select.value = 'completion'; h.fire(h.controls()[2].select, 'change'); await h.settle();
  assert.equal(h.location.searchParams.get('activity'), 'history');
  h.fire(h.$('#filter-chips').querySelectorAll('.retention-filter-chip').find(node => node.textContent.includes('Storico')), 'click'); await h.settle();
  assert.equal(h.location.searchParams.get('activity'), null);
  assert.equal(h.location.searchParams.get('view'), 'targeted'); assert.equal(h.location.searchParams.get('source'), 'overview');
  h.location.search = '?activity=working'; h.fire(h.window, 'popstate'); await h.settle();
  assert(h.$('#active-filters').textContent.includes('In lavorazione'));
  h.fire(h.$('#filters'), 'reset'); await h.settle(); assert.equal(h.location.searchParams.get('activity'), null);
  h.location.search = '?activity=invalid'; h.fire(h.window, 'popstate'); await h.settle();
  assert.equal(h.location.searchParams.get('activity'), null);
});

test('Overview period popup searches and selects by keyboard while preserving KPI and URL context', async () => {
  const h = harness('?period=6m&source=bookmark#ricavi', 'overview'); await h.settle();
  const picker = h.controls()[0]; assert.equal(picker.select.value, '6m');
  assert.equal(h.calls[0], '/api/overview?period=6m');
  h.fire(picker.trigger, 'click'); const input = picker.popup.querySelector('input');
  input.value = '90 giorni'; h.fire(input, 'input'); assert.equal(picker.popup.querySelectorAll('.floating-filter-option').length, 1);
  h.fire(input, 'keydown', {key: 'Enter'}); await h.settle();
  assert.equal(picker.select.value, '90d'); assert.equal(h.calls.at(-1), '/api/overview?period=90d');
  assert.equal(h.location.searchParams.get('period'), '90d'); assert.equal(h.location.searchParams.get('source'), 'bookmark');
  assert.equal(h.location.hash, '#ricavi'); assert.equal(h.$('#ready-count').textContent, '8');
  h.location.search = '?period=12m'; h.fire(h.window, 'popstate'); await h.settle();
  assert.equal(picker.select.value, '12m'); assert.equal(h.calls.at(-1), '/api/overview?period=12m');
  h.fire(picker.trigger, 'click'); h.fire(input, 'keydown', {key: 'Escape'});
  assert.equal(picker.select.value, '12m'); assert.equal(h.document.activeElement, picker.trigger);
});

test('Overview validates periods and ignores stale errors from older requests', async () => {
  const h = harness('?period=unsupported', 'overview'); await h.settle();
  assert.equal(h.controls()[0].select.value, '30d'); assert.equal(h.calls[0], '/api/overview?period=30d');
  h.state.pending = []; h.state.fail = true; const older = vm.runInContext('activePage.refresh()', h.context);
  h.state.fail = false; const latest = vm.runInContext('activePage.refresh()', h.context);
  h.state.pending[1](); await latest; h.state.pending[0](); await older;
  assert.equal(h.$('#notice').hidden, true); assert.equal(h.$('.revenue-chart').attributes['aria-busy'], undefined);
  h.state.pending = null; h.state.fail = true; await vm.runInContext('activePage.refresh()', h.context);
  assert.equal(h.$('#notice').textContent, 'Errore sintetico'); assert.equal(h.$('#notice').hidden, false);
});

test('Overview preserves CSV dialog, demo restrictions and import refresh', async () => {
  const h = harness('', 'overview'); await h.settle();
  h.fire(h.$('#upload'), 'click'); assert.equal(h.$('#import-dialog').open, true);
  assert.equal(h.$('#import-form').hidden, true); assert(h.$('#import-help').textContent.includes('dati sintetici'));
  h.state.data = {...h.data, demo: false}; await vm.runInContext('activePage.refresh()', h.context);
  h.fire(h.$('#upload'), 'click'); assert.equal(h.$('#import-form').hidden, false);
  h.fire(h.$('#import-form'), 'submit'); await h.settle();
  assert(h.calls.includes('/api/import')); assert.equal(h.calls.at(-1), '/api/overview?period=30d');
  assert.equal(h.$('#import-submit').disabled, false); assert.equal(h.$('#import-status').textContent, 'Importati 1 file.');
});

test('Overview still opens client detail and expands the backend queue', async () => {
  const h = harness('', 'overview'); await h.settle();
  const row = {customer_id: 'SYNTHETIC_OVERVIEW', contact_count: 0, customer_profile: {signals: []},
    source_product: 'Laifen Fonte sintetica', source_date: '2026-08-01', elapsed_days: 75,
    proposal: 'Proposta canonica', alternatives_count: 2, strategy_label: 'Completamenti funzionali',
    strategy: 'completion', eligible_from_date: '2026-08-16', reason: 'Motivazione ricevuta', value_minor: 2400,
    target_sku: 'SYNTHETIC_SKU', plan_key: ['synthetic', 'accessories']};
  h.state.data = {...h.data, rows: Array.from({length: 5}, (_, index) => ({...row, customer_id: `${row.customer_id}_${index}`}))};
  await vm.runInContext('activePage.refresh()', h.context);
  assert.equal(h.$('#customers').children.length, 4);
  assert.equal(h.$('#customers').children[0].children[3].dataset.label, 'Proposta principale');
  assert.equal(h.$('#customers').children[0].children[6].dataset.label, 'Valore');
  h.fire(h.$('#show-all'), 'click'); assert.equal(h.$('#customers').children.length, 5);
  let opened; h.context.recordOpen = item => {opened = item;}; vm.runInContext('openPlan = recordOpen;', h.context);
  h.fire(h.$('#customers').querySelector('.open-button'), 'click'); assert.equal(opened.customer_id, 'SYNTHETIC_OVERVIEW_0');
  assert.equal(opened.proposal, row.proposal);
  h.fire(h.$('#show-all'), 'click'); assert.equal(h.$('#customers').children.length, 4);
});

test('Rules renders all backend relations and guides as accessible tables without old cards', async () => {
  const h = harness('', 'rules'); await h.settle();
  assert.equal(h.$('#notice').hidden, true);
  const seen = new Set();
  for (const flow of h.data.flows) {
    h.fire(h.$('#rule-flow-tabs').children.find(button => button.dataset.flow === flow.id), 'click');
    assert.equal(h.$('#rule-count').textContent, `${flow.rule_ids.length} di ${flow.rule_ids.length} regole del percorso`);
    assert.equal(h.$('#rule-list').querySelectorAll('tbody').reduce((n, body) => n + body.children.length, 0), flow.rule_ids.length);
    for (const id of flow.rule_ids) {
      const rule = h.data.rules.find(item => item.id === id); seen.add(id);
      assert(h.$('#rule-list').textContent.includes(rule.id));
      assert(h.$('#rule-list').textContent.includes(rule.timing));
      for (const target of rule.targets) assert(h.$('#rule-list').textContent.includes(target.sku));
    }
  }
  assert.equal(seen.size, 15);
  assert.equal(h.$('#rule-list').querySelectorAll('.rule-card').length, 0);
  const guideCount = ['retention', 'plans', 'contacts'].reduce((n, id) => n + h.$(`#${id}-tables`).children.length, 0);
  assert.equal(guideCount, h.data.guides.length);
  for (const table of h.document.querySelectorAll('.rules-table')) {
    assert(table.querySelector('caption').textContent.length);
    assert(table.querySelectorAll('th').every(th => ['col', 'row'].includes(th.scope)));
    const labels = table.querySelector('thead').querySelectorAll('th').map(cell => cell.textContent);
    for (const row of table.querySelector('tbody').children) {
      assert.deepEqual(row.children.map(cell => cell.dataset.label), labels);
    }
  }
  assert(h.$('#retention-tables').textContent.includes('stato e strategia sullo stesso piano'));
  assert(h.$('#contacts-tables').textContent.includes('15 giorni'));
});

test('Rules combines product and strategy filters, reports empty results and resets shared popovers', async () => {
  const h = harness('', 'rules'); await h.settle();
  h.$('#rule-source').value = h.data.rules.flatMap(rule => rule.sources).find(source => source.product.startsWith('Laifen P3 -')).product;
  h.fire(h.$('#rule-source'), 'change');
  assert.equal(h.$('#rule-count').textContent, '1 di 2 regole del percorso');
  assert(h.$('#rule-list').textContent.includes('p3_travel_case_cross_sell'));
  assert(!h.$('#rule-list').textContent.includes('p3_pro_head_replenishment'));
  h.$('#rule-strategy').value = 'replenishment'; h.fire(h.$('#rule-strategy'), 'change');
  assert.equal(h.$('#rule-count').textContent, '0 di 2 regole del percorso');
  assert(h.$('#rule-list').textContent.includes('Nessuna regola'));
  const picker = h.controls()[0]; h.fire(picker.trigger, 'click');
  h.fire(h.$('#rule-filters'), 'reset');
  assert.equal(h.$('#rule-count').textContent, '2 di 2 regole del percorso');
  assert(h.controls().every(control => control.select.value === ''));
  assert.equal(picker.trigger.attributes['aria-expanded'], 'false');
  assert.equal(h.calls.filter(url => url === '/api/rules').length, 1);
});

test('Retention flows distinguish timed phases, seasonal branch, repeated cycles and unsupported models', async () => {
  const h = harness('', 'rules'); await h.settle();
  assert.equal(h.$('#flow-title').textContent, 'Asciugacapelli');
  assert.equal(h.$('#rule-list').querySelectorAll('.rules-flow-stage').length, 4);
  const hair = h.$('#rule-list').querySelectorAll('.rules-flow-stage');
  assert(hair[0].textContent.includes('Da 15 giorni'));
  assert(hair[1].textContent.includes('Da 45 giorni'));
  assert(hair[1].textContent.includes('autocurl_cross_sell'));
  assert(!hair[1].textContent.includes('hair_dryer_to_wave_pro_category_expansion'));
  assert(hair[2].textContent.includes('Da 75 giorni'));
  assert(hair[3].textContent.includes('Percorso parallelo'));
  assert.equal(h.$('#rule-flow-tabs').children[0].attributes['aria-pressed'], 'true');
  h.fire(h.$('#rule-flow-tabs').children[1], 'click');
  assert(h.$('#flow-limit').textContent.includes('T1 Pro'));
  assert.equal(h.$('#flow-limit').hidden, false);
  assert(h.$('#rule-list').textContent.includes('180 giorni'));
  h.fire(h.$('#rule-flow-tabs').children[2], 'click');
  assert.equal(h.$('#flow-limit').hidden, true);
  assert(h.$('#rule-list').textContent.includes('240 giorni'));
  assert.equal(h.$('#rule-flow-tabs').children.filter(button => button.attributes['aria-pressed'] === 'true').length, 1);
  assert.equal(h.calls.filter(url => url === '/api/rules').length, 1);
});


test('internal navigation reuses the document, restores URLs on Back and cleans page listeners', async () => {
  const h = harness('?strategy=completion'); await h.settle();
  const originalDocument = h.document;
  vm.runInContext(fs.readFileSync(path.join(frontend, 'rules.js'), 'utf8'), h.context);
  const rules = JSON.parse(execFileSync('python', ['-c', 'import json; from src.customer_profiles import rules_summary; print(json.dumps(rules_summary()))'], {encoding: 'utf8'}));
  h.state.data = rules;
  const sidebarLink = h.$('.sidebar').querySelectorAll('a').find(link => link.href === '/rules');
  const clicked = new h.context.Event('click', {button: 0}); sidebarLink.dispatchEvent(clicked);
  await h.settle(); await h.settle();
  assert.equal(clicked.defaultPrevented, true);
  assert.equal(h.document, originalDocument);
  assert.equal(h.document.body.dataset.page, 'rules');
  assert.equal(h.location.pathname, '/rules');
  assert.equal(h.window.events.popstate.length, 1);
  assert.equal(h.document.events.keydown.length, 0);
  h.state.data = h.data;
  h.location.href = 'http://localhost/retention?strategy=completion';
  h.fire(h.window, 'popstate'); await h.settle(); await h.settle();
  assert.equal(h.document.body.dataset.page, 'retention');
  assert.equal(h.controls()[2].select.value, 'completion');
  assert.equal(h.window.events.popstate.length, 2);
  assert.equal(h.document.events.keydown.length, 1);
  const retained = h.$('#customers');
  h.state.data = rules;
  await vm.runInContext("navigatePage(new URL('http://localhost/rules'))", h.context); await h.settle();
  assert.notEqual(h.$('#customers'), retained);
  assert.equal(h.calls.filter(url => url === '/rules').length, 1);
  const requests = h.calls.length;
  const modified = new h.context.Event('click', {button: 0, ctrlKey: true});
  h.$('.brand').dispatchEvent(modified); await h.settle();
  assert.equal(modified.defaultPrevented, undefined); assert.equal(h.calls.length, requests);
  h.state.data = h.data;
  h.fire(h.$('.sidebar').querySelectorAll('a').find(link => link.href === '/retention'), 'click', {button: 0});
  await h.settle(); await h.settle();
  assert.equal(h.document.body.dataset.page, 'retention');
  assert.equal(h.controls()[2].select.value, 'completion');
  assert.equal(h.location.searchParams.get('strategy'), 'completion');
  assert.equal(h.document.events.keydown.length, 1);
});

test('leaving a page ignores outstanding responses and disposes repeated refreshes', async () => {
  const h = harness(); await h.settle();
  h.state.pending = [];
  const pending = vm.runInContext('activePage.refresh()', h.context);
  const oldPage = vm.runInContext('activePage', h.context);
  oldPage.dispose();
  h.state.pending[0](); await pending;
  assert.equal(h.$('#customers').attributes['aria-busy'], 'true');
  const count = h.calls.length; await oldPage.refresh();
  assert.equal(h.calls.length, count);
});
