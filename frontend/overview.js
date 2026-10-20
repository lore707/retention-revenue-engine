registerPage('overview', (root, lifecycle) => {
const $ = selector => root.querySelector(selector);
let disposed = false;
let overview, period = '30d', expanded = false, requestSequence = 0;
const periodSelect = $('#period-filter');
function restoreOverviewPeriod() {
  const requested = new URLSearchParams(location.search).get('period');
  period = [...periodSelect.options].some(option => option.value === requested) ? requested : '30d';
  periodSelect.value = period;
}
restoreOverviewPeriod();
const periodPicker = createFloatingSelect({id: 'period-filter', search: 'Cerca un periodo…', describeOption: option => ({
  value: option.value, title: option.textContent, disabled: option.disabled, icon: 'clock', tone: 'blue',
  description: option.value.endsWith('m') ? 'Ricavi aggregati per mese' : 'Ricavi giornalieri'
})});
document.querySelectorAll('.overview-metric-heading').forEach(heading => heading.append(filterIcon(heading.dataset.icon, heading.dataset.tone)));
$('#chart-heading-icon').append(filterIcon('bars', 'green'));

async function loadOverview() {
  if (disposed) return;
  const sequence = ++requestSequence;
  $('.revenue-chart').setAttribute('aria-busy', 'true');
  if (!overview) {
    $('#notice').hidden = false;
    $('#notice').textContent = 'Caricamento dello storico e valutazione delle opportunità in corso…';
  }
  try {
    const data = await api(`/api/overview?period=${period}`);
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
    renderOperationalViews(data.activity_views, data.analyzed_customers);
    $('#retention-base-other').hidden = !data.activity_unassigned_customers;
    $('#retention-base-other').textContent = `${data.activity_unassigned_customers} altri clienti: piani futuri, verifiche o nessuna proposta attuale. Consultabili in Retention.`;
    renderRows();
  } catch (error) {
    if (sequence === requestSequence) {$('#notice').textContent = error.message; $('#notice').hidden = false;}
  } finally {if (sequence === requestSequence) $('.revenue-chart').removeAttribute('aria-busy');}
}

function renderOperationalViews(views, analyzedCustomers) {
  $('#operational-views').replaceChildren();
  for (const view of views) {
    const presentation = {
      today: {icon: 'message', tone: 'rose', action: 'Apri in Retention'},
      opportunities: {icon: 'target', tone: 'blue', action: 'Esplora opportunità'},
      working: {icon: 'send', tone: 'green', action: 'Visualizza piani'},
      history: {icon: 'archive', tone: 'slate', action: 'Esamina storico'}
    }[view.key];
    const card = element('a', undefined, `card operational-card filter-tone-${presentation.tone}`);
    card.href = `/retention?activity=${encodeURIComponent(view.key)}`;
    const heading = element('div', undefined, 'overview-category-heading'); heading.append(filterIcon(presentation.icon, presentation.tone), element('h3', view.label));
    const count = element('strong', view.count.toLocaleString('it-IT'), 'overview-category-count');
    card.append(heading, count, element('p', view.description, 'small'), element('span', `${presentation.action} →`, 'operational-link'));
    $('#operational-views').append(card);
  }
  $('#operational-note').textContent = `${analyzedCustomers.toLocaleString('it-IT')} clienti con consenso email valido`;
  $('#retention-base-icon').replaceChildren(filterIcon('users', 'slate'));
}

function renderRows() {
  const rows = expanded ? overview.rows : overview.rows.slice(0, 4);
  $('#queue-title').textContent = `Priorità Retention · ${overview.rows.length} clienti`;
  $('#show-all').textContent = expanded ? 'Mostra meno' : `Vedi tutti i ${overview.rows.length} clienti`;
  $('#show-all').hidden = overview.rows.length <= 4;
  $('#customers').replaceChildren();
  if (!rows.length) {
    const row = element('tr');
    const cell = element('td', 'Nessun cliente con consenso valido nello storico.', 'empty');
    cell.colSpan = 8;
    row.append(cell); $('#customers').append(row);
  }
  for (const item of rows) {
    const row = element('tr', undefined, `urgency-row filter-tone-${item.urgency.tone}`);
    const cells = [
      [item.customer_id, `${item.contact_count} contatti registrati`],
      null,
      [`${item.source_product.replace(/^Laifen /, '')} · ${dateLabel(item.source_date)}`],
      [item.proposal, item.contactable ? 'Attuabile oggi' : item.status_label],
      [item.strategy_label],
      [item.reason],
      [item.value_minor == null ? '—' : money(item.value_minor), 'Valore nominale'],
    ];
    cells.forEach((values, index) => {
      const cell = element('td', undefined, index === 6 ? 'numeric' : '');
      cell.dataset.label = ['Cliente / urgenza', 'Profilo e comportamento', 'Acquisto fonte', 'Proposta principale', 'Strategia', 'Prossimo passo', 'Valore'][index];
      if (index === 1) { cell.append(profileBadges(item.customer_profile)); row.append(cell); return; }
      const [primary, secondary] = values;
      const title = element('span', primary, 'primary-text'); title.title = primary;
      if (index === 4) title.classList.add('strategy-badge', `strategy-${item.strategy}`);
      cell.append(title);
      if (index === 0) {
        cell.append(urgencyBadge(item.urgency));
        if (item.urgency.date) cell.append(element('small', `${item.urgency.date_label} ${dateLabel(item.urgency.date)}`));
        if (item.urgency.mixed_plan) cell.append(element('small', 'Mirate e Da testare nella stessa mail', 'mixed-plan-note'));
      }
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
  $('#table-summary').textContent = `Mostrati ${rows.length} di ${overview.rows.length} clienti · stesso ordine di Retention: risposte, follow-up, primi contatti e attese. Filtri completi in Retention.`;
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
  const params = new URLSearchParams(location.search); params.set('period', period);
  history.replaceState(null, '', `${location.pathname}?${params}${location.hash}`); loadOverview();
});
lifecycle.listen(window, 'popstate', () => {periodPicker.close(); restoreOverviewPeriod(); periodPicker.update(); loadOverview();});
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
lifecycle.interval(() => {if (!document.hidden) loadOverview();}, 60000);

return {refresh: loadOverview, controls: [periodPicker], dispose() {disposed = true; ++requestSequence;}};
});
