let overview, period = '30d', expanded = false, requestSequence = 0;
let work = '', searchTimer;
const overviewFilterDefinitions = [
  {key: 'category', all: 'Tutte le categorie', icon: 'target', tone: 'green'},
  {key: 'product', all: 'Tutti i prodotti', icon: 'box', tone: 'blue'},
  {key: 'strategy', all: 'Tutte le strategie', icon: 'grid', tone: 'purple'},
  {key: 'profile', all: 'Tutti i profili', icon: 'users', tone: 'slate'},
  {key: 'order', icon: 'bars', tone: 'blue'},
];
const overviewFilters = overviewFilterDefinitions.map(definition => {
  const control = createFloatingSelect({id: `overview-${definition.key}`, search: 'Cerca…', describeOption: option => ({
    value: option.value, title: option.textContent, disabled: option.disabled,
    icon: definition.icon, tone: definition.tone,
    description: definition.key === 'order' ? (option.value === 'product' ? 'Clienti raggruppati per proposta' : 'Priorità e alternanza dei prodotti') : 'Filtra la proposta principale del piano',
  })});
  control.definition = definition;
  control.select.addEventListener('change', applyOverviewFilters);
  return control;
});
const periodSelect = $('#period-filter');
function restoreOverviewPeriod() {
  const params = new URLSearchParams(location.search), requested = params.get('period');
  period = [...periodSelect.options].some(option => option.value === requested) ? requested : '30d';
  periodSelect.value = period;
  work = params.get('work') || '';
  for (const control of overviewFilters) {
    const value = params.get(control.definition.key) || (control.definition.key === 'order' ? 'recommended' : '');
    if (![...control.select.options].some(option => option.value === value)) control.select.append(new Option(value, value));
    control.select.value = value; control.update();
  }
  $('#overview-search').value = params.get('search') || '';
}
restoreOverviewPeriod();
const periodPicker = createFloatingSelect({id: 'period-filter', search: 'Cerca un periodo…', describeOption: option => ({
  value: option.value, title: option.textContent, disabled: option.disabled, icon: 'clock', tone: 'blue',
  description: option.value.endsWith('m') ? 'Ricavi aggregati per mese' : 'Ricavi giornalieri'
})});
document.querySelectorAll('.overview-metric-heading').forEach(heading => heading.append(filterIcon(heading.dataset.icon, heading.dataset.tone)));
$('#chart-heading-icon').append(filterIcon('bars', 'green'));

async function loadOverview() {
  const sequence = ++requestSequence;
  $('.revenue-chart').setAttribute('aria-busy', 'true');
  $('#customers').setAttribute('aria-busy', 'true');
  if (!overview) {
    $('#notice').hidden = false;
    $('#notice').textContent = 'Caricamento dello storico e valutazione delle opportunità in corso…';
  }
  try {
    const params = overviewParams();
    const data = await api(`/api/overview?${params}`);
    if (sequence !== requestSequence) return;
    overview = data;
    $('#mode').textContent = data.demo ? 'Dati demo' : 'Dati locali';
    $('#workspace-mode').textContent = data.demo ? 'Laifen · Workspace demo' : 'Laifen · Workspace locale';
    $('#data-scope').textContent = data.demo ? 'Profili e ordini sintetici' : 'Storico ordini disponibile';
    $('#evaluation-date').textContent = dateLabel(data.date, true);
    $('#privacy-label').textContent = data.demo ? 'Dati demo · nessun cliente reale' : 'Dati locali · storico disponibile';
    $('#freshness').textContent = `Valutazione: ${dateLabel(data.date, true)} · storico disponibile`;
    $('#ready-count').textContent = data.metrics.ready_customers.toLocaleString('it-IT');
    $('#potential').textContent = money(data.metrics.potential_value_minor);
    $('#potential-note').textContent = `${data.metrics.ready_customers} proposte principali · non ricavi`;
    $('#contacts').textContent = data.metrics.registered_contacts.toLocaleString('it-IT');
    $('#revenue').textContent = money(data.metrics.attributed_revenue_minor);
    $('#verified-note').textContent = `${data.metrics.verified_orders} ordini verificati · clienti con consenso valido`;
    $('#notice').hidden = data.active;
    $('#notice').textContent = 'Lo storico non è ancora attivato: nessun cliente è lavorabile.';
    renderChart(data);
    updateOverviewFilters(data);
    renderOperationalViews(data.work_views);
    renderRows();
  } catch (error) {
    if (sequence === requestSequence) {$('#notice').textContent = error.message; $('#notice').hidden = false;}
  } finally {if (sequence === requestSequence) {$('.revenue-chart').removeAttribute('aria-busy'); $('#customers').removeAttribute('aria-busy');}}
}

function overviewParams() {
  const params = new URLSearchParams({period});
  if (work) params.set('work', work);
  for (const control of overviewFilters) {
    if (control.select.value && !(control.definition.key === 'order' && control.select.value === 'recommended')) params.set(control.definition.key, control.select.value);
  }
  const search = $('#overview-search').value.trim(); if (search) params.set('search', search);
  return params;
}
function syncOverviewUrl() {
  const params = new URLSearchParams(location.search), current = overviewParams();
  for (const key of ['period', 'work', 'category', 'product', 'strategy', 'profile', 'search', 'order']) {
    if (current.has(key)) params.set(key, current.get(key)); else params.delete(key);
  }
  history.replaceState(null, '', `${location.pathname}?${params}${location.hash}`);
}
function applyOverviewFilters() {
  clearTimeout(searchTimer); expanded = false;
  overviewFilters.forEach(control => control.update());
  syncOverviewUrl(); renderOverviewChips(); loadOverview();
}
function updateOverviewFilters(data) {
  if (work) work = data.work_group;
  for (const control of overviewFilters) {
    const key = control.definition.key;
    if (key !== 'order') control.select.replaceChildren(new Option(control.definition.all, ''), ...data.filter_options[key].map(option => new Option(option.label, option.value)));
    control.select.value = data.filters[key];
    control.trigger.disabled = key === 'order' && data.work_group === 'follow_up';
    control.update();
  }
  $('#overview-search').value = data.filters.search;
  renderOverviewChips(); syncOverviewUrl();
  $('#overview-order-note').textContent = data.work_group === 'follow_up'
    ? 'Prima le risposte da gestire, poi i follow-up consentiti, dal più vecchio. Filtri sulla proposta principale.'
    : data.filters.order === 'product' ? 'Prima le mirate, poi i test. Stesso prodotto insieme, dal piano più vecchio. Filtri sulla proposta principale.'
    : 'Prima le mirate, poi i test. I prodotti si alternano; per ogni prodotto, prima i piani più vecchi. Filtri sulla proposta principale.';
}
function renderOverviewChips() {
  const chips = $('#overview-chips');
  const signature = JSON.stringify([...overviewFilters.map(control => control.select.value), $('#overview-search').value.trim()]);
  if (chips.dataset.signature === signature) return;
  chips.dataset.signature = signature;
  const nodes = [];
  for (const control of overviewFilters) {
    if (control.definition.key === 'order' || !control.select.value) continue;
    const chip = element('button', `${control.select.selectedOptions[0].textContent} ×`, `overview-chip filter-tone-${control.definition.tone}`); chip.type = 'button';
    chip.setAttribute('aria-label', `Rimuovi filtro ${control.select.selectedOptions[0].textContent}`);
    chip.addEventListener('click', () => {control.select.value = ''; control.trigger.focus(); applyOverviewFilters();}); nodes.push(chip);
  }
  if ($('#overview-search').value.trim()) {
    const chip = element('button', `Ricerca: ${$('#overview-search').value.trim()} ×`, 'overview-chip filter-tone-slate'); chip.type = 'button';
    chip.setAttribute('aria-label', 'Rimuovi filtro di ricerca');
    chip.addEventListener('click', () => {$('#overview-search').value = ''; $('#overview-search').focus(); applyOverviewFilters();}); nodes.push(chip);
  }
  chips.hidden = nodes.length === 0; chips.replaceChildren(...nodes);
}
function renderOperationalViews(views) {
  const signature = JSON.stringify([views, overview.work_group]);
  if ($('#operational-views').dataset.signature === signature) return;
  const focusedWork = [...$('#operational-views').children].find(card => card === document.activeElement)?.dataset.work;
  $('#operational-views').dataset.signature = signature;
  $('#operational-views').replaceChildren();
  for (const view of views) {
    const presentation = {follow_up: {icon: 'repeat', tone: 'blue'}, recent: {icon: 'target', tone: 'green'}, backlog: {icon: 'clock', tone: 'amber'}}[view.key];
    const card = element('button', undefined, `card operational-card filter-tone-${presentation.tone}`); card.type = 'button';
    card.dataset.work = view.key;
    card.setAttribute('aria-pressed', String(view.key === overview.work_group));
    card.setAttribute('aria-controls', 'customers');
    card.addEventListener('click', () => {work = view.key; applyOverviewFilters();});
    const heading = element('div', undefined, 'overview-category-heading'); heading.append(filterIcon(presentation.icon, presentation.tone), element('h3', view.label));
    const count = element('div', undefined, 'overview-category-count'); count.append(element('strong', view.count.toLocaleString('it-IT')), element('span', 'clienti', 'small'));
    card.append(heading, count, element('p', view.description, 'small'), element('span', view.key === overview.work_group ? 'Lista selezionata' : 'Mostra clienti →', 'operational-link'));
    $('#operational-views').append(card);
    if (view.key === focusedWork) card.focus({preventScroll: true});
  }
  $('#operational-note').textContent = 'Gruppi esclusivi sul piano attuale, prima dei filtri. Solo azioni consentite oggi e clienti con consenso valido. Piani futuri e attese restano in Retention.';
}

function renderRows() {
  const rows = expanded ? overview.rows : overview.rows.slice(0, 4);
  $('#queue-title').textContent = `${overview.work_views.find(view => view.key === overview.work_group).label} · ${overview.rows.length} clienti`;
  $('#show-all').textContent = expanded ? 'Mostra meno' : `Vedi tutti i ${overview.rows.length} clienti`;
  $('#show-all').hidden = overview.rows.length <= 4;
  $('#customers').replaceChildren();
  if (!rows.length) {
    const row = element('tr');
    const cell = element('td', 'Nessun cliente corrisponde a questo gruppo e ai filtri selezionati.', 'empty');
    cell.colSpan = 8;
    row.append(cell); $('#customers').append(row);
  }
  for (const item of rows) {
    const row = element('tr');
    const cells = [
      [item.customer_id, `${item.contact_count} contatti registrati`],
      null,
      [`${item.source_product.replace(/^Laifen /, '')} · ${dateLabel(item.source_date)}`, `${item.elapsed_days} giorni dall’acquisto`],
      [item.proposal, item.alternatives_count ? `+ ${item.alternatives_count} opzioni compatibili` : 'Proposta del piano'],
      [item.strategy_label],
      [item.work_action === 'reply' ? 'Gestisci la risposta' : item.work_action === 'follow_up' ? `Follow-up dal ${dateLabel(item.work_date)}` : `Primo contatto · maturo dal ${dateLabel(item.eligible_from_date)}`, item.reason],
      [money(item.value_minor), 'Valore nominale'],
    ];
    cells.forEach((values, index) => {
      const cell = element('td', undefined, index === 6 ? 'numeric' : '');
      cell.dataset.label = ['Cliente', 'Profilo e comportamento', 'Acquisto fonte', 'Proposta principale', 'Strategia', 'Prossimo passo', 'Valore'][index];
      if (index === 1) { cell.append(profileBadges(item.customer_profile)); row.append(cell); return; }
      const [primary, secondary] = values;
      const title = element('span', primary, 'primary-text'); title.title = primary;
      if (index === 4) title.classList.add('strategy-badge', `strategy-${item.strategy}`);
      cell.append(title);
      if (secondary) { const note = element('small', secondary); note.title = secondary; cell.append(note); }
      if (index === 2 && item.order_number) cell.append(element('small', item.order_number));
      if (index === 3) attachProductImage(cell, overview.product_images[item.target_sku]);
      row.append(cell);
    });
    const cell = element('td', undefined, 'action');
    const open = element('button', 'Apri', 'open-button');
    const arrow = element('img'); arrow.src = '/assets/retention-open.svg'; arrow.alt = ''; open.append(arrow);
    open.setAttribute('aria-label', `Apri il piano di ${item.customer_id}`);
    open.addEventListener('click', () => openPlan(item));
    cell.append(open); row.append(cell); $('#customers').append(row);
  }
  $('#table-summary').textContent = `Mostrati ${rows.length} di ${overview.rows.length} clienti · una proposta principale per cliente · alternative nel dettaglio.`;
}

function renderChart(data) {
  $('#chart-total').textContent = money(data.chart.attributed_revenue_minor);
  $('#chart-range').textContent = `${dateLabel(data.starts_on)} – ${dateLabel(data.date, true)} · ${data.chart.verified_orders} acquisti verificati · clienti con consenso valido`;
  $('#chart-caption').textContent = data.chart.verified_orders === 0
    ? 'Nessun acquisto verificato nel periodo. Il grafico si aggiornerà dopo la registrazione degli acquisti.'
    : `Ricavi ${period.endsWith('m') ? 'mensili' : 'giornalieri'} · solo acquisti verificati${data.demo ? ' · dati demo' : ''}`;
  const svg = $('#chart'), points = data.chart.series;
  svg.replaceChildren(); $('#chart-tooltip').hidden = true;
  const namespace = 'http://www.w3.org/2000/svg';
  const node = (tag, attrs, text) => {
    const child = document.createElementNS(namespace, tag);
    Object.entries(attrs).forEach(([key, value]) => child.setAttribute(key, value));
    if (text !== undefined) child.textContent = text;
    svg.append(child); return child;
  };
  const max = Math.max(4000, Math.ceil(Math.max(...points.map(p => p.amount_minor)) / 2000) * 2000);
  [max, max / 2, 0].forEach((value, i) => {
    const y = 4 + i * 48;
    node('line', {x1: 48, x2: 1104, y1: y, y2: y, class: 'grid'});
    node('text', {x: 0, y: y + 5}, `€ ${Math.round(value / 100)}`);
  });
  const coords = points.map((point, i) => ({x: 48 + i * 1056 / Math.max(1, points.length - 1), y: 100 - point.amount_minor / max * 96}));
  const line = coords.map((p, i) => `${i ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ');
  node('path', {d: `${line} L 1104 100 L 48 100 Z`, class: 'area'});
  node('path', {d: line, class: 'line'});
  const indices = [...new Set([0, Math.round((points.length - 1) / 4), Math.round((points.length - 1) / 2), Math.round((points.length - 1) * 3 / 4), points.length - 1])];
  indices.forEach(index => node('text', {x: coords[index].x, y: 123, 'text-anchor': index === points.length - 1 ? 'end' : 'start'}, period.endsWith('m') ? points[index].date.slice(0, 7) : dateLabel(points[index].date)));
  points.forEach((point, i) => {
    const hit = node('rect', {x: Math.max(48, coords[i].x - 528 / points.length), y: 0, width: Math.max(8, 1056 / points.length), height: 104, class: 'hit', tabindex: 0, 'aria-label': `${dateLabel(point.date, true)}: ${money(point.amount_minor)}`});
    const show = () => {
      const tooltip = $('#chart-tooltip');
      tooltip.textContent = `${dateLabel(point.date, true)} · ${money(point.amount_minor)}`;
      tooltip.style.left = `${Math.min(80, Math.max(4, coords[i].x / 1120 * 100))}%`; tooltip.hidden = false;
    };
    hit.addEventListener('mouseenter', show); hit.addEventListener('focus', show);
    hit.addEventListener('click', show);
    hit.addEventListener('mouseleave', () => $('#chart-tooltip').hidden = true);
    hit.addEventListener('blur', () => $('#chart-tooltip').hidden = true);
  });
}

periodSelect.addEventListener('change', () => {
  period = periodSelect.value; periodPicker.update();
  syncOverviewUrl(); loadOverview();
});
window.addEventListener('popstate', () => {clearTimeout(searchTimer); openFloatingSelect?.close(); restoreOverviewPeriod(); periodPicker.update(); expanded = false; loadOverview();});
$('#overview-filters').addEventListener('submit', event => {event.preventDefault(); applyOverviewFilters();});
$('#overview-filters').addEventListener('reset', event => {
  event.preventDefault(); overviewFilters.forEach(control => {control.select.value = control.definition.key === 'order' ? 'recommended' : '';});
  $('#overview-search').value = ''; applyOverviewFilters();
});
$('#overview-search').addEventListener('input', () => {++requestSequence; clearTimeout(searchTimer); searchTimer = setTimeout(applyOverviewFilters, 300);});
document.addEventListener('keydown', event => {if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && $('#detail').hidden) {event.preventDefault(); openFloatingSelect?.close(); $('#overview-search').focus();}});
$('#show-all').addEventListener('click', () => {expanded = !expanded; renderRows();});
$('#upload').addEventListener('click', () => {
  const demo = overview?.demo;
  $('#import-help').textContent = demo ? 'Stai visualizzando dati sintetici. Per importare ordini avvia la pagina con il database locale.' : 'Gli export vengono ridotti localmente e uniti allo storico esistente, senza duplicare gli ordini.';
  $('#import-form').hidden = demo;
  $('#import-status').textContent = '';
  $('#import-dialog').showModal();
});
$('#import-form').addEventListener('submit', async (event) => {
  event.preventDefault(); $('#import-submit').disabled = true;
  try {
    const result = await api('/api/import', {method: 'POST', body: new FormData(event.target)});
    $('#import-status').textContent = `Importati ${result.imported_files} file.${result.active ? '' : ' Lo storico richiede l’attivazione tramite il comando activate.'}`;
    await loadOverview();
  } catch (error) { $('#import-status').textContent = error.message; }
  finally { $('#import-submit').disabled = false; }
});
loadOverview();
setInterval(() => {if (!document.hidden) loadOverview();}, 60000);
