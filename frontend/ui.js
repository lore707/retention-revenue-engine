const $ = (selector) => document.querySelector(selector);
const pageFactories = new Map(), pageDocuments = new Map(), pageScripts = new Map();
const pagePaths = {overview: '/', retention: '/retention', rules: '/rules'};
const pageLocations = new Map();
let activePage, activePageName, navigationSequence = 0;

function mountPage(name) {
  const cleanup = [];
  const lifecycle = {
    listen(target, type, listener) {
      const guarded = event => {if (location.pathname === pagePaths[name]) listener(event);};
      target.addEventListener(type, guarded);
      cleanup.push(() => target.removeEventListener(type, guarded));
    },
    interval(callback, delay) {const timer = setInterval(callback, delay); cleanup.push(() => clearInterval(timer));}
  };
  const controller = pageFactories.get(name)(document.body, lifecycle);
  activePageName = name;
  activePage = {...controller, dispose() {controller.dispose(); cleanup.forEach(dispose => dispose());}};
  $('#detail-back')?.addEventListener('click', closePlan);
  $('#outcome-dialog')?.addEventListener('close', () => $('#outcome-content').replaceChildren());
}
function registerPage(name, factory) {
  pageFactories.set(name, factory);
  if (!activePage && document.body.dataset.page === name) mountPage(name);
}
async function navigatePage(url, push = true, restoreFilters = false) {
  const name = Object.keys(pagePaths).find(key => pagePaths[key] === url.pathname);
  if (restoreFilters && !url.search && !url.hash && pageLocations.has(name)) url = new URL(pageLocations.get(name));
  if (push && activePageName) pageLocations.set(activePageName, location.href);
  const sequence = ++navigationSequence;
  document.documentElement.setAttribute('aria-busy', 'true');
  try {
    if (!pageDocuments.has(name)) {
      const response = await fetch(url.pathname);
      if (!response.ok) throw new Error('Pagina non disponibile');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (parsed.body.dataset.page !== name) throw new Error('Pagina non valida');
      pageDocuments.set(name, parsed);
    }
    const parsed = pageDocuments.get(name);
    await Promise.all([...parsed.querySelectorAll('link[rel="stylesheet"]')].map(link => {
      if ([...document.querySelectorAll('link[rel="stylesheet"]')].some(current => current.href === link.href)) return;
      return new Promise((resolve, reject) => {
        const style = link.cloneNode(); style.onload = resolve; style.onerror = reject; document.head.append(style);
      });
    }));
    if (!pageFactories.has(name)) {
      if (!pageScripts.has(name)) pageScripts.set(name, new Promise((resolve, reject) => {
        const script = element('script'); script.src = `/${name}.js`; script.onload = resolve;
        script.onerror = () => {pageScripts.delete(name); script.remove(); reject(new Error('Script non disponibile'));};
        document.head.append(script);
      }));
      await pageScripts.get(name);
    }
    if (sequence !== navigationSequence) return;
    openFloatingSelect?.close(); ++detailRequest;
    activePage?.dispose(); activePage = null;
    document.body.replaceWith(parsed.body.cloneNode(true));
    document.body.dataset.page = name; document.title = parsed.title;
    if (push) history.pushState(null, '', url.pathname + url.search + url.hash);
    mountPage(name);
    window.scrollTo(0, 0);
    const heading = $('.workspace > main h1');
    if (heading) {heading.tabIndex = -1; heading.focus({preventScroll: true});}
  } catch {
    if (sequence === navigationSequence) {if (push) location.assign(url.href); else location.reload();}
  } finally {if (sequence === navigationSequence) document.documentElement.removeAttribute('aria-busy');}
}
document.addEventListener('click', event => {
  const link = event.target.closest?.('a[href]');
  if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
  const url = new URL(link.href, location.href);
  if (url.origin !== location.origin || !Object.values(pagePaths).includes(url.pathname)) return;
  event.preventDefault(); navigatePage(url, true, Boolean(link.closest('.sidebar')));
});
window.addEventListener('popstate', () => {
  if (pagePaths[activePageName] !== location.pathname) navigatePage(new URL(location.href), false);
  else {++navigationSequence; document.documentElement.removeAttribute('aria-busy');}
});
const money = (minor) => `€ ${(minor / 100).toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
const dateLabel = (value, year = false) => new Intl.DateTimeFormat('it-IT', {day: '2-digit', month: 'short', ...(year ? {year: 'numeric'} : {}), timeZone: 'UTC'}).format(new Date(`${value}T12:00:00Z`));
function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}

const commercialCategoryPresentation = {
  targeted: {icon: 'target', tone: 'green'}, test: {icon: 'flask', tone: 'purple'}, none: {icon: 'clock', tone: 'slate'}
};
const filterIconPaths = {
  message: 'M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-3 3V11.5A8.5 8.5 0 0 1 9.5 3h3a8.5 8.5 0 0 1 8.5 8.5Z',
  send: 'm22 2-7 20-4-9-9-4 20-7ZM22 2 11 13',
  archive: 'M3 3h18v5H3V3Zm1 5v13h16V8M9 12h6',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  target: 'M21 12a9 9 0 1 1-9-9m5 9a5 5 0 1 1-5-5m0 5 9-9m-5 0h5v5',
  flask: 'M9 3h6m-5 0v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-10V3M8 15h8',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0M12 7v5l3 2',
  list: 'M9 6h12M9 12h12M9 18h12M3 6h1M3 12h1M3 18h1',
  play: 'm7 3 14 9-14 9V3Z', activity: 'M20 7a9 9 0 1 0 1 9M20 3v5h-5',
  check: 'm5 12 4 4L19 6', pause: 'M9 5v14M15 5v14',
  grid: 'M3 3h6v6H3V3Zm12 0h6v6h-6V3ZM3 15h6v6H3v-6Zm12 0h6v6h-6v-6Z',
  puzzle: 'M8 3H3v5a3 3 0 1 1 0 6v7h7a3 3 0 1 1 6 0h5v-7a3 3 0 1 0 0-6V3h-7a3 3 0 1 1-6 0Z',
  box: 'm12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10v9M3 8l9 5 9-5M7 5.8l9 5',
  bars: 'M4 14h3v7H4v-7Zm7-6h3v13h-3V8Zm7-5h3v18h-3V3Z',
  repeat: 'M3 10a9 9 0 0 1 15-6l3 3M21 2v5h-5M21 14A9 9 0 0 1 6 20l-3-3M3 22v-5h5',
  arrow: 'M12 21V3m-7 7 7-7 7 7', star: 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z',
  bolt: 'm13 2-9 12h7l-1 8 10-12h-7l1-8Z', briefcase: 'M9 6V3h6v3M3 6h18v15H3V6Zm0 6a22 22 0 0 0 18 0M12 11v4',
  gem: 'M3 8 7 3h10l4 5-9 13L3 8Zm0 0h18M7 3l5 18 5-18'
};
function filterIcon(name, tone) {
  const wrap = element('span', undefined, `filter-option-icon filter-tone-${tone}`);
  wrap.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '1.7');
  svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', filterIconPaths[name]); svg.append(path); wrap.append(svg); return wrap;
}
let openFloatingSelect, floatingSelectEventsReady = false;
function createFloatingSelect({id, search, describeOption}) {
  bindFloatingSelectEvents();
  const select = $(`#${id}`), label = $(`#${id}-label`);
  const trigger = element('button', undefined, 'floating-filter-trigger'); trigger.type = 'button'; trigger.id = `${select.id}-trigger`;
  trigger.setAttribute('aria-haspopup', 'dialog'); trigger.setAttribute('aria-expanded', 'false');
  const valueId = `${select.id}-value`;
  trigger.setAttribute('aria-labelledby', `${label.id} ${valueId}`);
  trigger.setAttribute('aria-describedby', `${select.id}-description`);
  const popup = element('div', undefined, 'floating-filter-popup'); popup.id = `${select.id}-popup`; popup.hidden = true;
  popup.setAttribute('role', 'dialog'); popup.setAttribute('aria-labelledby', label.id);
  trigger.setAttribute('aria-controls', popup.id);
  const searchWrap = element('div', undefined, 'floating-filter-search');
  const searchIcon = element('img'); searchIcon.src = '/assets/retention-search.svg'; searchIcon.alt = '';
  const input = element('input'); input.type = 'search'; input.autocomplete = 'off'; input.placeholder = search;
  input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list'); input.setAttribute('aria-expanded', 'false');
  input.setAttribute('aria-label', search.replace('…', ''));
  const list = element('div', undefined, 'floating-filter-options'); list.id = `${select.id}-options`;
  list.setAttribute('role', 'listbox'); list.setAttribute('aria-labelledby', label.id); input.setAttribute('aria-controls', list.id);
  const status = element('p', undefined, 'floating-filter-status'); status.setAttribute('role', 'status');
  searchWrap.append(searchIcon, input); popup.append(searchWrap, list, status);
  select.after(trigger, popup); select.hidden = true; label.htmlFor = trigger.id;
  let isOpen = false, closeTimer, activeIndex = -1, visibleOptions = [];

  function setActive(index, scroll = false) {
    activeIndex = index;
    [...list.children].forEach((node, i) => node.classList.toggle('is-active', i === index));
    if (index < 0) input.removeAttribute('aria-activedescendant');
    else {input.setAttribute('aria-activedescendant', list.children[index].id); if (scroll) list.children[index].scrollIntoView({block: 'nearest'});}
  }
  function renderOptions() {
    const query = input.value.trim().toLocaleLowerCase('it');
    visibleOptions = [...select.options].map(option => describeOption(option))
      .filter(option => `${option.title} ${option.description}`.toLocaleLowerCase('it').includes(query));
    list.replaceChildren(...visibleOptions.map((option, i) => {
      const row = element('div', undefined, 'floating-filter-option'); row.id = `${select.id}-option-${i}`;
      row.setAttribute('role', 'option'); row.setAttribute('aria-selected', String(option.value === select.value));
      if (option.disabled) row.setAttribute('aria-disabled', 'true');
      const copy = element('span', undefined, 'filter-option-copy');
      copy.append(element('span', option.title, 'filter-option-title'), element('span', option.description, 'filter-option-description'));
      row.append(filterIcon(option.icon, option.tone), copy);
      if (option.count !== undefined) {
        const count = element('span', option.count.toLocaleString('it-IT'), 'filter-option-count');
        count.setAttribute('aria-label', `${option.count} ${option.countHint || ''}`.trim()); count.title = option.countHint || ''; row.append(count);
      }
      const check = element('span', option.value === select.value ? '✓' : '', 'filter-option-check'); check.setAttribute('aria-hidden', 'true'); row.append(check);
      row.addEventListener('pointerdown', event => event.preventDefault());
      row.addEventListener('pointermove', () => {if (!option.disabled) setActive(i);});
      row.addEventListener('click', () => choose(i)); return row;
    }));
    status.hidden = visibleOptions.length > 0; status.textContent = visibleOptions.length ? '' : 'Nessuna opzione trovata';
    let index = visibleOptions.findIndex(option => option.value === select.value && !option.disabled);
    if (index < 0) index = visibleOptions.findIndex(option => !option.disabled);
    setActive(index);
  }
  function position() {
    if (!isOpen) return;
    const rect = trigger.getBoundingClientRect(), viewport = window.visualViewport;
    const left = viewport?.offsetLeft || 0, top = viewport?.offsetTop || 0;
    const width = viewport?.width || document.documentElement.clientWidth, height = viewport?.height || window.innerHeight;
    if (rect.bottom <= top || rect.top >= top + height) {close(); return;}
    const below = Math.max(0, top + height - rect.bottom - 16), above = Math.max(0, rect.top - top - 16);
    const flip = below < 360 && above > below;
    // With a short viewport (e.g. a mobile keyboard), allow overlap with the anchor.
    const available = Math.max(above, below) < 180 ? height - 24 : flip ? above : below;
    popup.style.width = `${Math.min(Math.max(rect.width, 320), width - 24)}px`;
    popup.style.maxHeight = `${Math.min(480, available)}px`;
    popup.style.left = `${Math.max(left + 12, Math.min(rect.left, left + width - popup.offsetWidth - 12))}px`;
    const popupTop = flip ? rect.top - popup.offsetHeight - 8 : rect.bottom + 8;
    popup.style.top = `${Math.max(top + 12, Math.min(popupTop, top + height - popup.offsetHeight - 12))}px`;
    popup.classList.toggle('opens-above', flip);
  }
  function close(restoreFocus = false) {
    if (!isOpen) return;
    isOpen = false; if (openFloatingSelect === control) openFloatingSelect = null;
    trigger.setAttribute('aria-expanded', 'false'); input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
    popup.classList.remove('is-open'); popup.inert = true; popup.setAttribute('aria-hidden', 'true');
    closeTimer = setTimeout(() => {popup.hidden = true;}, 160);
    if (restoreFocus) trigger.focus({preventScroll: true});
  }
  function open() {
    if (isOpen) return;
    openFloatingSelect?.close(); clearTimeout(closeTimer); openFloatingSelect = control; isOpen = true;
    input.value = ''; popup.hidden = false; popup.inert = false; popup.removeAttribute('aria-hidden');
    trigger.setAttribute('aria-expanded', 'true'); input.setAttribute('aria-expanded', 'true');
    renderOptions(); position();
    // Commit the collapsed style before transitioning; also works when reopening during close.
    void popup.offsetHeight; popup.classList.add('is-open'); input.focus({preventScroll: true});
  }
  function choose(index) {
    const option = visibleOptions[index]; if (!option || option.disabled) return;
    select.value = option.value; close(true); update(); select.dispatchEvent(new Event('change', {bubbles: true}));
  }
  function update() {
    const option = describeOption(select.selectedOptions[0]);
    const copy = element('span', undefined, 'filter-option-copy'), title = element('span', option.title, 'filter-option-title'); title.id = valueId;
    const description = element('span', option.summary || option.description, 'filter-option-description');
    description.id = `${select.id}-description`; copy.append(title, description);
    const chevron = element('span', undefined, 'filter-trigger-chevron'); chevron.setAttribute('aria-hidden', 'true');
    trigger.replaceChildren(filterIcon(option.icon, option.tone), copy, chevron);
    if (isOpen) {renderOptions(); position();}
  }
  trigger.addEventListener('click', () => isOpen ? close(true) : open());
  trigger.addEventListener('keydown', event => {
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) {event.preventDefault(); open(); if (event.key === 'ArrowUp') setActive(visibleOptions.findLastIndex(option => !option.disabled), true);}
    else if (event.key.length === 1 && event.key !== ' ' && !event.ctrlKey && !event.metaKey && !event.altKey) {event.preventDefault(); open(); input.value = event.key; renderOptions(); position();}
  });
  input.addEventListener('input', () => {renderOptions(); position();});
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape') {event.preventDefault(); event.stopPropagation(); close(true);}
    else if (event.key === 'Tab') {close(true); if (event.shiftKey) event.preventDefault();}
    else if (event.key === 'Enter') {event.preventDefault(); choose(activeIndex);}
    else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault(); const step = event.key === 'ArrowDown' ? 1 : -1;
      let next = activeIndex; do {next += step;} while (visibleOptions[next]?.disabled);
      if (visibleOptions[next]) setActive(next, true);
    }
  });
  const control = {select, trigger, popup, update, close, position}; update(); return control;
}
function bindFloatingSelectEvents() {
  if (floatingSelectEventsReady) return;
  floatingSelectEventsReady = true;
  document.addEventListener('pointerdown', event => {if (openFloatingSelect && !openFloatingSelect.popup.contains(event.target) && !openFloatingSelect.trigger.contains(event.target)) openFloatingSelect.close();});
  document.addEventListener('focusin', event => {if (openFloatingSelect && !openFloatingSelect.popup.contains(event.target) && !openFloatingSelect.trigger.contains(event.target)) openFloatingSelect.close();});
  window.addEventListener('resize', () => openFloatingSelect?.position());
  window.addEventListener('scroll', () => openFloatingSelect?.position(), true);
  window.visualViewport?.addEventListener('resize', () => openFloatingSelect?.position());
  window.visualViewport?.addEventListener('scroll', () => openFloatingSelect?.position());
}

function productThumbnail(image) {
  if (!image) return null;
  const node = element('img', undefined, 'product-thumbnail');
  node.src = image.src; node.alt = image.alt; node.width = 36; node.height = 36;
  node.loading = 'lazy'; node.decoding = 'async';
  node.addEventListener('error', () => node.remove(), {once: true});
  return node;
}

function attachProductImage(container, image) {
  const thumbnail = productThumbnail(image);
  if (!thumbnail) return;
  const row = element('span', undefined, 'product-with-image'), text = element('span', undefined, 'product-copy');
  text.append(...container.childNodes); row.append(thumbnail, text); container.append(row);
}

const profilePresentation = {
  first_purchase: {label: 'Primo acquisto', tone: 'neutral', icon: 'profile-first.svg', note: '1 ordine valido'},
  recurring: {label: 'Ricorrenti', tone: 'green', icon: 'profile-recurring.svg', note: 'Almeno 2 ordini'},
  recent_activity: {label: 'Alta attività', tone: 'blue', icon: 'profile-activity.svg', note: '3 ordini in 90 giorni'},
  multicategory: {label: 'Multicategoria', tone: 'purple', icon: 'profile-multicategory.svg', note: '2 categorie principali'},
  possible_b2b: {label: 'Possibili B2B', tone: 'amber', icon: 'profile-b2b.svg', note: 'Non valutabile'},
  high_historical_value: {label: 'Alto valore', tone: 'rose', icon: 'profile-value.svg', note: 'Spesa netta mancante'},
};

function profileBadge(signal, detail = false) {
  const presentation = profilePresentation[signal.key];
  const badge = element('span', undefined, `profile-badge tone-${presentation.tone}`);
  const emoji = {recurring: '🔁', multicategory: '🏷️'}[signal.key];
  const icon = detail && emoji ? element('span', emoji, 'profile-emoji') : element('img');
  if (icon.tagName === 'IMG') { icon.src = `/assets/${presentation.icon}`; icon.alt = ''; icon.width = 14; icon.height = 14; }
  else icon.setAttribute('aria-hidden', 'true');
  badge.append(icon, element('span', signal.label)); return badge;
}

function profileBadges(profile, detail = false) {
  const badges = element('div', undefined, 'profile-badges');
  for (const signal of profile.signals) badges.append(profileBadge(signal, detail));
  if (!profile.signals.length) badges.append(element('small', 'Nessun segnale qualificato'));
  return badges;
}

function customerQualification(profile, compact = false) {
  const block = element('section', undefined, compact ? 'quick-profile' : 'card customer-profile');
  block.append(compact ? element('h2', 'Profilo cliente · storico osservato') : customerHeading('Profilo cliente', 'profile'), profileBadges(profile, !compact));
  block.append(element('p', `${profile.valid_orders} ordini interamente validi · ${profile.recent_valid_orders} negli ultimi 90 giorni (dal ${dateLabel(profile.recent_starts_on, true)})`, 'customer-small'));
  block.append(element('p', `Categorie principali: ${profile.main_categories.join(' · ') || 'Nessuna osservata'}. Gli accessori non aggiungono categorie.`, 'customer-small'));
  if (profile.uncertain_orders) block.append(element('p', `${profile.uncertain_orders} ordini con righe incerte: i conteggi non rappresentano lo storico completo.`, 'customer-small'));
  const other = compact ? block : element('details', undefined, 'customer-extra');
  if (!compact) other.append(customerSummary('Altri dati'));
  for (const signal of profile.unavailable_signals) {
    if (!compact) { other.append(element('p', `${signal.label}: ${signal.reason}`, 'customer-small')); continue; }
    const row = element('div', undefined, 'profile-unavailable');
    row.append(profileBadge({...signal, label: `${signal.label} · non valutabile`}), element('p', signal.reason, 'customer-small'));
    block.append(row);
  }
  if (!compact) {
    other.append(element('p', 'I segnali descrivono gli acquisti importati; non dimostrano il bisogno di un prodotto e non modificano le priorità commerciali.', 'customer-small'));
    block.append(other);
  }
  return block;
}

async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Impossibile caricare i dati.');
  return data;
}

const eventLabels = {
  contact: 'Email già inviata', reply: 'Risposta ricevuta', product_interest: 'Interesse per un prodotto',
  product_rejection: 'Rifiuto di un prodotto', plan_rejection: 'Rifiuto dell’intera proposta',
  rejection: 'Rifiuto della proposta', conversation_closed: 'Conversazione gestita',
  verified_purchase: 'Acquisto verificato in Shopify', revenue_correction: 'Correzione del ricavo',
};
let detailRequest = 0;
let detailOrigin, detailScroll = 0, detailBreadcrumb = '';

function closePlan() {
  ++detailRequest;
  $('#outcome-dialog').close();
  $('#outcome-content').replaceChildren();
  $('#detail').hidden = true;
  $('#detail-content').replaceChildren();
  $('.workspace > main').hidden = false;
  $('.topbar > span').textContent = detailBreadcrumb;
  window.scrollTo(0, detailScroll);
  if (detailOrigin?.isConnected) detailOrigin.focus({preventScroll: true});
  else { const heading = $('.workspace > main h1'); heading.tabIndex = -1; heading.focus({preventScroll: true}); }
}


async function openPlan(row, savedMessage = '') {
  const request = ++detailRequest;
  if ($('#detail').hidden) {
    detailOrigin = document.activeElement;
    detailScroll = window.scrollY;
    detailBreadcrumb = $('.topbar > span').textContent;
  }
  $('#outcome-dialog').close();
  $('#detail-title').textContent = `Cliente · ${row.customer_id}`;
  $('#detail-back').textContent = document.body.dataset.page === 'retention' ? '← Retention' : '← Overview';
  $('.workspace > main').hidden = true;
  $('#detail').hidden = false;
  $('.topbar > span').textContent = `${detailBreadcrumb} / Cliente`;
  $('#detail-content').replaceChildren(element('p', 'Caricamento…'));
  window.scrollTo(0, 0);
  try {
    const data = await api(`/api/plan?customer=${encodeURIComponent(row.customer_id)}&plan=${encodeURIComponent(JSON.stringify(row.plan_key))}`);
    if (request !== detailRequest || $('#detail').hidden) return;
    const content = $('#detail-content');
    content.replaceChildren();
    if (savedMessage) { const status = element('p', savedMessage, 'save-success'); status.setAttribute('role', 'status'); content.append(status); }
    const columns = element('div', undefined, 'customer-columns');
    const primaryColumn = element('div', undefined, 'customer-main-column'), sideColumn = element('div', undefined, 'customer-side-column');
    const header = customerHeader(data), title = header.querySelector('h1');
    primaryColumn.append(header);
    if (!data.active || data.review_reasons.length) primaryColumn.append(element('p', !data.active
      ? 'Storico non attivo: nessun contatto lavorabile.' : 'Dati da verificare: il contatto è sospeso.', 'detail-note save-success'));
    const primary = data.proposals.find(product => product.role === 'primary') || data.proposals[0];
    primaryColumn.append(customerProposal(data, primary));
    const alternatives = data.proposals.filter(product => product !== primary);
    if (alternatives.length) {
      const section = element('section', undefined, 'card customer-alternatives');
      const heading = customerHeading('Alternative compatibili', 'box');
      heading.append(element('small', 'Opzioni nella stessa email', 'customer-small'));
      const list = element('div', undefined, 'customer-alternative-list');
      for (const product of alternatives) list.append(customerAlternative(data, product));
      section.append(heading, list);
      if (data.presentation) section.append(element('p', data.presentation.instruction, 'customer-small'));
      primaryColumn.append(section);
    }
    const future = nextOpportunities(data);
    if (future) primaryColumn.append(future);
    primaryColumn.append(customerHistory(data), planLogic(data));
    sideColumn.append(customerQualification(data.customer_profile), nextAction(data, row));
    columns.append(primaryColumn, sideColumn); content.append(columns);
    content.append(element('p', `${data.demo ? 'Demo · dati sintetici. ' : ''}Valutazione: ${dateLabel(data.date, true)} · solo storico importato.`, 'customer-small'));
    if (!savedMessage) title.focus({preventScroll: true});
  } catch (error) {
    if (request === detailRequest) $('#detail-content').replaceChildren(element('p', `${savedMessage ? savedMessage + ' ' : ''}Impossibile aggiornare il dettaglio: ${error.message}`));
  }
}

function customerIcon(name) {
  const sizes = {user: 32, profile: 24, mail: 20, target: 26, check: 22, document: 22,
    clock: 22, info: 20, box: 24, future: 24, calendar: 18, chevron: 16, cart: 24,
    'detail-chevron': 18, send: 24, contact: 20, consent: 20, date: 20, 'action-info': 20,
    'contact-clock': 20, 'contact-calendar': 20};
  const image = element('img', undefined, 'customer-icon');
  image.src = `/assets/customer-${name}.svg`; image.alt = ''; image.width = sizes[name]; image.height = sizes[name];
  return image;
}

function customerHeading(title, icon, tag = 'h2') {
  const heading = element('div', undefined, 'customer-section-heading');
  heading.append(customerIcon(icon), element(tag, title)); return heading;
}

function customerSummary(title, icon = 'detail-chevron') {
  const summary = element('summary', undefined, 'customer-summary');
  summary.append(element('span', title), customerIcon(icon)); return summary;
}

function customerBadge(label, tone = 'blue') {
  return element('span', label, `customer-badge tone-${tone}`);
}

function customerHeader(data) {
  const header = element('section', undefined, 'card customer-header'), identity = element('div', undefined, 'customer-identity');
  const avatar = element('span', undefined, 'customer-avatar'); avatar.append(customerIcon('user'));
  const copy = element('div', undefined, 'customer-identity-copy'), title = element('h1', data.customer_id); title.tabIndex = -1;
  const count = new Set(data.purchases.map(purchase => purchase.order_id)).size;
  const last = data.purchases[0]?.date;
  copy.append(title, element('p', `${count} ordini importati · ${data.customer_profile.main_categories.length} categorie${last ? ` · Ultimo acquisto ${dateLabel(last, true)}` : ''}`, 'customer-small'));
  const badges = element('div', undefined, 'customer-header-badges');
  const closedLabels = {verified_purchase: 'Acquisto verificato', plan_rejection: 'Rifiuto del piano', attempts_exhausted: 'Tentativi esauriti', not_eligible: 'Non più proponibile'};
  const state = data.event_templates.contact ? 'Contattabile' : data.tracked_plan?.state === 'closed'
    ? closedLabels[data.tracked_plan.outcome] || 'Piano concluso' : data.tracked_plan ? 'In corso' : 'In attesa';
  const consent = {subscribed: 'Consenso valido', unsubscribed: 'Non iscritto', unknown: 'Consenso da verificare'}[data.contact_permission.consent_status] || 'Consenso da verificare';
  badges.append(customerBadge(state, data.event_templates.contact ? 'green' : 'blue'), customerBadge(consent, data.contact_permission.allowed ? 'green' : 'neutral'), customerBadge('Canale: email'));
  copy.append(badges); identity.append(avatar, copy, contactAddress(data)); header.append(identity); return header;
}

function productOptions(data, product) {
  if (product.options.length < 2) return null;
  const details = element('details', undefined, 'product-options'); details.append(customerSummary('Varianti disponibili'));
  const list = element('ul');
  for (const option of product.options) {
    const row = element('li', [option.product_name, option.material, option.color, option.sku].filter(Boolean).join(' · '));
    attachProductImage(row, data.product_images[option.sku]); list.append(row);
  }
  details.append(list); return details;
}

function customerProposal(data, product) {
  const section = element('section', undefined, 'card customer-proposal');
  const heading = customerHeading(product ? data.contacts.length ? 'Proposta principale presentata' : 'Proposta principale consigliata' : 'Proposte presentate', 'target');
  if (product) heading.append(customerBadge(product.commercial_category === 'targeted' ? 'Opportunità mirata' : 'Opportunità da testare'));
  section.append(heading);
  if (!product) {
    for (const name of [...new Set(data.contacts.flatMap(contact => contact.proposal_names))]) section.append(element('p', name));
    section.append(element('p', data.contacts.length ? 'Prezzo storico non registrato. Gli importi verificati restano nello storico degli esiti.' : 'Nessuna proposta attiva. Consulta gli acquisti e le condizioni del cliente.', 'customer-small'));
    return section;
  }
  const hero = element('div', undefined, 'customer-hero'), image = productThumbnail(data.product_images[product.sku]);
  if (image) { image.width = 166; image.height = 166; hero.append(image); }
  else hero.classList.add('without-photo');
  const copy = element('div', undefined, 'customer-product-copy'), name = element('div', undefined, 'customer-product-top');
  name.append(element('h3', product.name), element('strong', money(product.value_minor), 'customer-price'));
  copy.append(name, element('p', product.description, 'customer-product-description'), element('h4', 'Perché questa proposta?'));
  const reasons = element('div', undefined, 'customer-reasons');
  for (const reason of product.reasons) {
    const item = element('div', undefined, `customer-reason tone-${reason.tone}`), text = element('div');
    text.append(element('span', reason.label), element('small', reason.date ? `dal ${dateLabel(reason.date, true)}` : reason.detail, 'customer-small'));
    item.append(customerIcon(reason.icon), text); reasons.append(item);
  }
  copy.append(reasons); hero.append(copy); section.append(hero);
  const variants = productOptions(data, product); if (variants) section.append(variants);
  const note = element('p', undefined, 'customer-info-band'); note.append(customerIcon('info'), element('span', product.promotion_active
    ? 'Promozione pianificata: verificare attivazione, disponibilità e prezzo prima dell’invio.'
    : 'Verificare disponibilità e prezzo aggiornato prima dell’invio.'));
  section.append(note); return section;
}

function customerAlternative(data, product) {
  const article = element('article', undefined, 'customer-alternative'), image = productThumbnail(data.product_images[product.sku]);
  if (image) { image.width = 100; image.height = 100; article.append(image); }
  else article.classList.add('without-photo');
  const copy = element('div', undefined, 'customer-product-copy'), price = element('div', undefined, 'customer-alternative-price');
  copy.append(element('h3', product.name)); price.append(customerBadge(product.commercial_category === 'targeted' ? 'Mirata' : 'Da testare'), element('strong', money(product.value_minor)));
  copy.append(price, element('p', product.benefit, 'customer-small')); const variants = productOptions(data, product); if (variants) copy.append(variants);
  article.append(copy); return article;
}

function nextOpportunities(data) {
  const plans = data.operator_timeline.filter(plan => JSON.stringify(plan.plan_key) !== JSON.stringify(data.plan_key));
  if (!plans.length) return null;
  const section = element('section', undefined, 'card customer-future'), heading = customerHeading('Prossime opportunità', 'future');
  const blocking = plans.filter(plan => plan.blocking_plan_keys.some(key => JSON.stringify(key) === JSON.stringify(data.plan_key)));
  heading.append(element('small', blocking.length ? `${blocking.length} in attesa del piano attuale` : `${plans.length} piani successivi`, 'customer-small')); section.append(heading);
  const states = {contact_review: 'Da contattare', queued: 'In attesa', deferred: 'Attesa temporale', blocked_consent: 'Consenso mancante', operator_response: 'Risposta da gestire'};
  for (const plan of plans) {
    const details = element('details', undefined, 'customer-next-plan'), summary = element('summary', undefined, 'customer-next-summary');
    const product = plan.proposals.find(product => product.role === 'primary') || plan.proposals[0];
    const image = productThumbnail(data.product_images[product?.target_sku]); if (image) summary.append(image);
    summary.append(element('span', [...new Set(plan.proposals.map(product => product.target_product_name))].join(' / '), 'customer-next-name'), customerBadge(states[plan.state] || plan.state));
    const timing = element('span', undefined, 'customer-next-date'); timing.append(customerIcon('calendar'), element('span', dateLabel(plan.eligible_from_date, true))); summary.append(timing, customerIcon('chevron'));
    details.append(summary, element('p', plan.reason, 'customer-small'), element('p', `Ordine ${plan.order_number} · Maturazione ${dateLabel(plan.eligible_from_date, true)}`, 'customer-small'));
    details.append(element('p', plan.next_contact_date ? `Contatto non prima del ${dateLabel(plan.next_contact_date, true)}, da rivalutare.` : 'Data di contatto da rivalutare dopo la gestione dei piani precedenti.', 'customer-small'));
    if (plan.blocking_plan_keys.length) {
      const names = plan.blocking_plan_keys.map(key => { const blocker = data.operator_timeline.find(other => JSON.stringify(other.plan_key) === JSON.stringify(key)); return blocker ? [...new Set(blocker.proposals.map(product => product.target_product_name))].join(' / ') : key[0]; });
      details.append(element('p', `Piani da chiudere: ${names.join('; ')}.`, 'customer-small'));
    }
    section.append(details);
  }
  return section;
}

function contactAddress(data) {
  const block = element('div', undefined, 'customer-address');
  if (!data.contact_email) { block.append(element('p', 'Recapito non disponibile', 'customer-small')); return block; }
  const reveal = element('button', undefined, 'button customer-email-button'), label = element('span', 'Mostra email'); reveal.append(customerIcon('mail'), label); reveal.type = 'button'; reveal.setAttribute('aria-expanded', 'false');
  const address = element('div', undefined, 'customer-email'); address.hidden = true;
  const text = element('span', data.contact_email);
  const copy = element('button', 'Copia', 'button customer-link'); copy.type = 'button';
  copy.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(data.contact_email); copy.textContent = 'Copiata'; }
    catch { copy.textContent = 'Seleziona l’indirizzo per copiarlo'; }
  });
  address.append(text, copy); block.append(reveal, address);
  reveal.addEventListener('click', () => { address.hidden = !address.hidden; label.textContent = address.hidden ? 'Mostra email' : 'Nascondi email'; reveal.setAttribute('aria-expanded', String(!address.hidden)); });
  return block;
}

function planLogic(data) {
  const details = element('details', undefined, 'customer-logic');
  details.append(customerSummary('Regole e dettagli della raccomandazione'), element('p', data.reason, 'customer-small'));
  const source = data.source_purchase;
  if (source) details.append(element('p', `Acquisto di origine · ${[source.product_name, source.configuration, data.order_number, dateLabel(source.date, true)].filter(Boolean).join(' · ')}`, 'customer-small'));
  if (data.source) details.append(element('p', `${data.source.elapsed_days} giorni trascorsi · maturazione ${dateLabel(data.source.eligible_from_date, true)}.`, 'customer-small'));
  if (data.presentation) details.append(element('p', `Proposta principale: ${data.presentation.primary_selection_reason}`, 'customer-small'));
  const checks = [...new Set(data.proposals.flatMap(product => product.operator_checks))];
  if (checks.length) { const list = element('ul'); for (const check of checks) list.append(element('li', check)); details.append(list); }
  for (const reason of data.review_reasons) details.append(element('p', reason, 'customer-small'));
  return details;
}

function nextAction(data, row) {
  const section = element('aside', undefined, 'card customer-action');
  section.append(customerHeading('Prossimo passo', 'send'));
  const body = element('div', undefined, 'customer-action-body'); section.append(body);
  const count = data.tracked_plan?.contact_count ?? data.current_plan?.contact_count ?? 0;
  const last = data.tracked_plan?.last_contact_date;
  if (data.event_templates.contact) {
    body.append(element('h3', 'Contatta il cliente via email', 'customer-instruction'), element('p', 'Dopo l’invio, registra qui il contatto effettuato.', 'customer-small'));
  } else {
    body.append(element('h3', data.tracked_plan?.state === 'closed' ? 'Piano concluso' : data.contacts.length ? 'Gestisci il contatto in corso' : 'Attendi la prossima azione', 'customer-instruction'));
  }
  const stats = element('div', undefined, 'customer-contact-stats'), counter = element('span', undefined, 'customer-contact-count');
  counter.append(customerIcon('contact'), element('span', `${data.event_templates.contact ? count === 0 ? 'Primo contatto' : 'Secondo contatto' : 'Contatti registrati'} · ${count} / ${data.maximum_contacts}`));
  const consent = element('span', undefined, `customer-consent tone-${data.contact_permission.allowed ? 'green' : 'neutral'}`);
  if (data.contact_permission.allowed) consent.append(customerIcon('consent'));
  consent.append(element('span', {subscribed: 'Consenso valido', unsubscribed: 'Non iscritto', unknown: 'Consenso da verificare'}[data.contact_permission.consent_status] || 'Consenso da verificare'));
  stats.append(counter, consent); body.append(stats);
  if (data.event_templates.contact) {
    body.append(eventForm(data, row, ['contact']));
    const note = element('p', undefined, 'customer-action-note'); note.append(customerIcon('action-info'), element('span', 'L’email viene inviata fuori dal sistema.')); body.append(note);
  } else {
    const next = data.current_plan?.plan_next_contact_date;
    if (last || next) {
      const dates = element('div', undefined, 'customer-contact-dates');
      for (const [value, label, icon] of [[last, 'Ultimo contatto', 'contact-calendar'], [next, 'Nuovo contatto non prima del', 'contact-clock']]) {
        if (!value) continue;
        const item = element('div', undefined, 'customer-contact-date'), copy = element('div');
        copy.append(element('small', label, 'customer-small'), element('strong', dateLabel(value, true))); item.append(customerIcon(icon), copy); dates.append(item);
      }
      if (next) dates.append(element('p', 'Solo se il piano resta lavorabile.', 'customer-small'));
      body.append(dates);
    }
    if (!data.contacts.length || !next || data.current_plan?.raw_status === 'operator_response' || !data.contact_permission.allowed) body.append(element('p', data.reason, 'customer-small'));
  }
  const actions = Object.keys(data.event_templates).filter(kind => kind !== 'contact');
  if (actions.length) {
    const update = element('button', 'Aggiorna esito', 'button primary'); update.type = 'button';
    update.addEventListener('click', () => { $('#outcome-content').replaceChildren(eventForm(data, row, actions)); $('#outcome-dialog').showModal(); });
    if (!data.event_templates.contact) body.append(element('p', 'Quando arriva una risposta o un risultato, registralo con “Aggiorna esito”.', 'customer-small'));
    body.append(update);
  }
  if (data.sales.length) body.append(element('small', 'Ricavo attribuito · verificato dall’operatore'), element('strong', money(data.attributed_revenue_minor), 'customer-revenue'));
  if (data.contacts.length) { const note = element('p', undefined, 'customer-action-note'); note.append(customerIcon('action-info'), element('span', 'Risposta e interesse richiedono gestione manuale. Il ricavo si registra solo per un acquisto verificato.')); body.append(note); }
  return section;
}

function customerHistory(data) {
  const section = element('section', undefined, 'card customer-history'), heading = customerHeading('Storico acquisti', 'cart');
  const count = new Set(data.purchases.map(purchase => purchase.order_id)).size;
  heading.append(element('small', `${count} ${count === 1 ? 'ordine importato' : 'ordini importati'}`, 'customer-small')); section.append(heading);
  const scroll = element('div', undefined, 'table-scroll'), table = element('table'), head = element('thead'), headings = element('tr');
  table.setAttribute('role', 'table');
  for (const label of ['Data', 'Ordine', 'Prodotto acquistato', 'Quantità · Stato']) headings.append(element('th', label));
  head.append(headings); const body = element('tbody');
  const validities = {valid: 'Riga valida', unknown: 'Da verificare', cancelled: 'Annullata', returned: 'Resa'};
  for (const purchase of data.purchases) {
    const row = element('tr');
    row.append(element('td', dateLabel(purchase.date, true)), element('td', purchase.order_number));
    const product = element('td', [purchase.product_name, purchase.configuration, purchase.color].filter(Boolean).join(' · '));
    product.append(element('small', purchase.sku)); attachProductImage(product, data.product_images[purchase.sku]);
    const status = element('td'), label = element('span', `${purchase.quantity ?? '—'} · ${validities[purchase.validity] || purchase.validity}`, `customer-purchase-status${purchase.validity === 'valid' ? ' tone-green' : ''}`);
    status.append(label); row.append(product, status);
    [...row.children].forEach((cell, index) => {cell.dataset.label = ['Data', 'Ordine', 'Prodotto acquistato', 'Quantità · Stato'][index];});
    body.append(row);
  }
  table.append(head, body); scroll.append(table); section.append(scroll);
  const events = element('details', undefined, 'customer-extra'); events.append(customerSummary('Contatti ed esiti'));
  if (!data.customer_events.length) events.append(element('p', 'Nessun contatto o esito registrato per questo cliente.', 'customer-small'));
  for (const event of data.customer_events) {
    const item = element('article', undefined, 'customer-event');
    item.append(element('p', `${dateLabel(event.date, true)} · ${eventLabels[event.type] || event.type}`));
    const order = data.purchases.find(purchase => purchase.order_id === event.plan_key[0]);
    item.append(element('small', `Piano dell’ordine ${order?.order_number || event.plan_key[0]}`));
    if (event.proposal_names) item.append(element('small', `Proposte registrate: ${event.proposal_names.join(', ')}`));
    if (event.product_name) item.append(element('small', event.product_name));
    if (event.shopify_order_id) item.append(element('small', `Ordine Shopify ${event.shopify_order_id} · ${event.purchased_sku}`));
    if (event.amount_minor !== undefined) item.append(element('small', `${money(event.amount_minor)}${event.type === 'revenue_correction' ? ' · importo corretto' : ' · importo registrato'}`));
    if (event.reason || event.notes) item.append(element('small', event.reason || event.notes));
    events.append(item);
  }
  section.append(events, element('p', 'Lo storico comprende solo gli acquisti importati.', 'customer-small')); return section;
}


function eventForm(data, row, kinds) {
  const ownerRequest = detailRequest;
  const form = element('form', undefined, 'event-form');
  function field(parent, labelText, name, type = 'text', options = []) {
    const label = element('label', labelText);
    const input = element(type === 'select' ? 'select' : type === 'textarea' ? 'textarea' : 'input');
    input.name = name;
    if (input.tagName === 'INPUT') input.type = type;
    if (type === 'select') input.append(...options.map(([value, label]) => new Option(label, value)));
    input.required = name !== 'notes';
    label.append(input); parent.append(label); return input;
  }
  const action = field(form, 'Attività', 'action', 'select', kinds.map(kind => [kind, eventLabels[kind]]));
  if (kinds.length === 1) action.parentElement.hidden = true;
  const dateInput = field(form, kinds[0] === 'contact' ? 'Data contatto' : 'Data dell’attività', 'date', 'date');
  dateInput.value = data.date; dateInput.max = data.date; dateInput.min = data.minimum_event_date || '';
  if (kinds[0] === 'contact') {
    const label = dateInput.parentElement, wrapper = element('span', undefined, 'customer-date-field');
    wrapper.append(customerIcon('date'), dateInput); label.append(wrapper);
  }
  const fields = element('div', undefined, 'event-fields'); form.append(fields);
  const notes = field(form, 'Note operative (facoltative)', 'notes', 'textarea'); notes.rows = 2;
  const message = element('p', '', 'form-status'); message.setAttribute('role', 'status'); form.append(message);
  const submit = element('button', undefined, 'button primary'); submit.type = 'submit';
  if (kinds[0] === 'contact') submit.append(customerIcon('send'));
  submit.append(element('span', kinds[0] === 'contact' ? 'Salva contatto' : 'Salva esito')); form.append(submit);
  let pendingKey, pendingId;
  function updateFields() {
    fields.replaceChildren(); message.textContent = '';
    if (action.value === 'contact') {
      const products = element('section', undefined, 'customer-presented-products'); products.append(element('p', 'Prodotti presentati · piano corrente', 'customer-small'));
      for (const product of data.proposals) {
        const item = element('div', undefined, 'customer-presented-product'), image = productThumbnail(data.product_images[product.sku]);
        if (image) { image.width = 32; image.height = 32; item.append(image); }
        item.append(element('span', product.name), element('strong', money(product.value_minor))); products.append(item);
      }
      fields.append(products);
    }
    if (action.value === 'product_interest' || action.value === 'product_rejection') {
      field(fields, 'Prodotto presentato', 'product_key', 'select', data.products.map(p => [p.key, p.label]));
    }
    if (action.value === 'plan_rejection') fields.append(element('p', 'Chiude il piano: il cliente ha rifiutato l’intera proposta.', 'detail-note'));
    if (action.value === 'conversation_closed') fields.append(element('p', 'Segna la risposta come gestita. Il motore rivaluta le prossime azioni mantenendo i tentativi già effettuati.', 'detail-note'));
    if (action.value === 'verified_purchase') {
      const contact = field(fields, 'Contatto a cui attribuire l’acquisto', 'contact_event_id', 'select', data.contacts.map(c => [c.id, `${dateLabel(c.date, true)} · ${c.id}`]));
      const sku = field(fields, 'Prodotto / SKU acquistato', 'purchased_sku', 'select');
      const updateProducts = () => sku.replaceChildren(...data.contacts.find(c => c.id === contact.value).products.map(p => new Option(p.label, p.sku)));
      contact.addEventListener('change', updateProducts); updateProducts();
      field(fields, 'ID ordine Shopify', 'shopify_order_id');
      const purchase = field(fields, 'Data dell’acquisto', 'purchase_date', 'date'); purchase.value = data.date; purchase.max = data.date;
    }
    if (action.value === 'revenue_correction') {
      field(fields, 'Vendita da correggere', 'verified_purchase_event_id', 'select', data.sales.map(s => [s.id, `Ordine ${s.order_id}`]));
      field(fields, 'Motivo della correzione', 'reason');
    }
    if (action.value === 'verified_purchase' || action.value === 'revenue_correction') {
      const amount = field(fields, action.value === 'revenue_correction' ? 'Nuovo importo totale attribuito (€)' : 'Importo attribuito verificato (€)', 'amount', 'text');
      amount.inputMode = 'decimal'; amount.placeholder = '29,99'; amount.pattern = '[0-9]+([.,][0-9]{1,2})?';
      field(fields, 'Confermo la verifica dell’ordine e dell’importo in Shopify.', 'verified_in_shopify', 'checkbox');
    }
  }
  action.addEventListener('change', updateFields); updateFields();
  if (kinds.includes('contact')) {
    const confirmation = field(form, 'Confermo l’invio dell’email e la verifica di recapito, consenso, disponibilità e prezzi.', 'confirmed', 'checkbox');
    form.insertBefore(confirmation.parentElement, message);
  }
  form.addEventListener('submit', async e => {
    e.preventDefault(); if (submit.disabled) return;
    const values = new FormData(form);
    const event = {...data.event_templates[action.value], date: values.get('date')};
    if (values.get('notes').trim()) event.notes = values.get('notes').trim();
    for (const name of ['product_key', 'contact_event_id', 'purchased_sku', 'shopify_order_id', 'purchase_date', 'verified_purchase_event_id', 'reason']) {
      if (values.has(name)) event[name] = values.get(name).trim();
    }
    if (values.has('amount')) {
      const [whole, fraction = ''] = values.get('amount').replace(',', '.').split('.');
      event.amount_minor = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
      event.verified_in_shopify = values.get('verified_in_shopify') === 'on';
    }
    const key = JSON.stringify(event);
    if (key !== pendingKey) { pendingKey = key; pendingId = crypto.randomUUID(); }
    event.id = pendingId;
    submit.disabled = true; message.textContent = 'Salvataggio…';
    try {
      await api('/api/events', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({customer_id: data.customer_id, event})});
      message.textContent = 'Attività salvata.';
      await activePage.refresh?.();
      if (!$('#detail').hidden && detailRequest === ownerRequest) await openPlan(row, 'Attività salvata. Coda e risultati aggiornati.');
    } catch (error) { message.textContent = error.message; }
    finally { submit.disabled = false; }
  });
  return form;
}
