let retention, page = 0, retentionRequest = 0, quickRequest = 0, quickOrigin, refreshTimer;
let selectedView = '', selectedActivity = '';
const pageSize = 25;
const stateLabels = {open: 'Aperto — da lavorare', in_progress: 'In corso', closed: 'Chiuso', suspended: 'In attesa / sospeso'};

// Presentation only: values and filtering continue to use the existing selects and API.
const filterDefinitions = [
  {id: 'operational-filter', param: 'view', icon: 'users', tone: 'green', hint: 'Panoramica completa', search: 'Cerca nella categoria…', options: commercialCategoryPresentation},
  {id: 'state-filter', param: 'state', icon: 'list', tone: 'blue', hint: 'Tutti i piani', search: 'Cerca nello stato…', options: {
    open: {title: 'Aperti', description: 'Da lavorare', icon: 'play', tone: 'green'},
    in_progress: {description: 'Contatto già avviato', icon: 'activity', tone: 'amber'},
    closed: {description: 'Piani conclusi', icon: 'check', tone: 'slate'},
    suspended: {title: 'In attesa / sospesi', description: 'Non ancora attuabili o bloccati', icon: 'pause', tone: 'rose'}}},
  {id: 'strategy', param: 'strategy', icon: 'grid', tone: 'purple', hint: 'Tutte le proposte', search: 'Cerca nella strategia…', options: {
    completion: {description: 'Accessori di completamento', icon: 'puzzle', tone: 'green'},
    complement: {description: 'Complementi per l’esperienza d’uso', icon: 'box', tone: 'blue'},
    expansion: {description: 'Prodotti di un’altra categoria', icon: 'bars', tone: 'purple'},
    replenishment: {description: 'Consumabili e parti di ricambio', icon: 'repeat', tone: 'amber'},
    replacement: {description: 'Nuove versioni o modelli', icon: 'arrow', tone: 'rose'}}},
  {id: 'profile-filter', param: 'profile', icon: 'users', tone: 'slate', hint: 'Un segnale alla volta', search: 'Cerca nel profilo…', options: {
    first_purchase: {description: 'Primo ordine valido osservato', icon: 'star', tone: 'amber'},
    recurring: {description: 'Acquisti ripetuti osservati', icon: 'repeat', tone: 'green'},
    recent_activity: {description: 'Frequenza d’acquisto recente', icon: 'bolt', tone: 'amber'},
    multicategory: {description: 'Acquisti in più categorie principali', icon: 'grid', tone: 'blue'},
    possible_b2b: {title: 'Possibile B2B', description: 'Non valutabile: criteri da definire', icon: 'briefcase', tone: 'slate'},
    high_historical_value: {title: 'Alto valore storico', description: 'Non valutabile: spesa netta non disponibile', icon: 'gem', tone: 'slate'}}}
];
function filterOption(definition, option) {
  const presentation = definition.options[option.value] || {};
  const category = definition.param === 'view' ? retention?.operational_views.find(view => view.key === option.value) : null;
  const count = definition.param === 'view' ? (option.value ? category?.count : retention?.analyzed_customers) : undefined;
  return {value: option.value, disabled: option.disabled, title: presentation.title || option.textContent,
    description: category?.description || presentation.description || definition.hint,
    icon: presentation.icon || definition.icon, tone: presentation.tone || definition.tone,
    count, countHint: 'clienti prima degli altri filtri',
    summary: count === undefined ? undefined : `${count.toLocaleString('it-IT')} clienti ${option.value ? 'nella categoria' : 'con consenso valido'}`};
}

const floatingFilters = filterDefinitions.map(definition => ({definition, ...createFloatingSelect({
  id: definition.id, search: definition.search, describeOption: option => filterOption(definition, option)
})}));

function syncRetentionUrl() {
  const params = new URLSearchParams(location.search); params.delete('category');
  if (selectedActivity) params.set('activity', selectedActivity); else params.delete('activity');
  for (const filter of floatingFilters) {
    const value = filter.definition.param === 'view' ? selectedView : filter.select.value;
    if (value) params.set(filter.definition.param, value); else params.delete(filter.definition.param);
  }
  const search = $('#search').value.trim(); if (search) params.set('search', search); else params.delete('search');
  history.replaceState(null, '', `${location.pathname}${params.size ? '?' + params : ''}${location.hash}`);
}
function restoreRetentionFilters() {
  const params = new URLSearchParams(location.search);
  selectedView = params.get('view') || params.get('category') || '';
  selectedActivity = params.get('activity') || '';
  for (const filter of floatingFilters) {
    const value = params.get(filter.definition.param) || '';
    filter.select.value = [...filter.select.options].some(option => option.value === value && !option.disabled) ? value : '';
    filter.update();
  }
  $('#search').value = params.get('search') || ''; renderFilterChips();
}
function renderFilterChips() {
  const chips = $('#filter-chips'), nodes = [];
  const activity = retention?.activity_views?.find(view => view.key === selectedActivity);
  const signature = JSON.stringify([selectedActivity, activity?.label, ...floatingFilters.map(filter => filter.select.value), $('#search').value.trim()]);
  if (chips.dataset.signature === signature) return;
  chips.dataset.signature = signature;
  if (activity) {
    const chip = element('button', `${activity.label} ×`, 'retention-filter-chip filter-tone-blue'); chip.type = 'button';
    chip.setAttribute('aria-label', `Rimuovi filtro ${activity.label}`);
    chip.addEventListener('click', () => {selectedActivity = ''; $('.retention-reset').focus(); applyRetentionFilters();}); nodes.push(chip);
  }
  for (const filter of floatingFilters) {
    if (!filter.select.value) continue;
    const option = filterOption(filter.definition, filter.select.selectedOptions[0]);
    const chip = element('button', undefined, `retention-filter-chip filter-tone-${option.tone}`); chip.type = 'button';
    chip.setAttribute('aria-label', `Rimuovi filtro ${$(`#${filter.select.id}-label`).textContent}: ${option.title}`);
    const remove = element('span', '×', 'filter-chip-remove'); remove.setAttribute('aria-hidden', 'true');
    chip.append(filterIcon(option.icon, option.tone), element('span', option.title), remove);
    chip.addEventListener('click', () => {filter.select.value = ''; filter.trigger.focus(); filter.select.dispatchEvent(new Event('change', {bubbles: true}));}); nodes.push(chip);
  }
  if ($('#search').value.trim()) {
    const chip = element('button', `Ricerca: ${$('#search').value.trim()} ×`, 'retention-filter-chip filter-tone-slate'); chip.type = 'button';
    chip.setAttribute('aria-label', 'Rimuovi filtro di ricerca'); chip.addEventListener('click', () => {$('#search').value = ''; $('#search').focus(); applyRetentionFilters();}); nodes.push(chip);
  }
  chips.hidden = nodes.length === 0;
  if (nodes.length) {
    const clear = element('button', 'Azzera tutti', 'retention-clear-all'); clear.type = 'reset';
    chips.replaceChildren(element('span', 'Filtri attivi:', 'filter-chips-label'), ...nodes, clear);
  } else chips.replaceChildren();
}
function applyRetentionFilters() {
  clearTimeout(refreshTimer); selectedView = $('#operational-filter').value; page = 0;
  floatingFilters.forEach(filter => filter.update()); renderFilterChips(); syncRetentionUrl(); loadRetention();
}
window.addEventListener('popstate', () => {clearTimeout(refreshTimer); openFloatingSelect?.close(); restoreRetentionFilters(); page = 0; loadRetention();});
document.addEventListener('keydown', event => {if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && $('#detail').hidden) {event.preventDefault(); openFloatingSelect?.close(); $('#search').focus();}});
restoreRetentionFilters();

async function loadRetention() {
  const request = ++retentionRequest;
  const params = new URLSearchParams({category: selectedView, state: $('#state-filter').value,
    strategy: $('#strategy').value, profile: $('#profile-filter').value, search: $('#search').value.trim(), activity: selectedActivity});
  try {
    $('#customers').setAttribute('aria-busy', 'true');
    const data = await api(`/api/retention?${params}`);
    if (request !== retentionRequest) return;
    retention = data;
    if (selectedActivity && !data.activity_views.some(view => view.key === selectedActivity)) {selectedActivity = ''; syncRetentionUrl();}
    if (!data.operational_views.some(view => view.key === selectedView)) selectedView = '';
    $('#operational-filter').replaceChildren(new Option('Tutti i clienti', ''), ...data.operational_views.map(view => new Option(view.label, view.key)));
    $('#operational-filter').value = selectedView;
    floatingFilters.forEach(filter => filter.update()); renderFilterChips();
    $('#mode').textContent = data.demo ? 'Simulazione · dati sintetici' : 'Dati locali';
    $('#workspace-mode').textContent = data.demo ? 'Laifen · Workspace demo' : 'Laifen · Workspace locale';
    $('#data-scope').textContent = 'Storico ordini disponibile';
    $('#evaluation-date').textContent = dateLabel(data.date, true);
    $('#freshness').textContent = `Valutazione · ${dateLabel(data.date, true)}`;
    $('#customer-scope').textContent = `${data.analyzed_customers.toLocaleString('it-IT')} clienti con consenso email valido · ${data.metrics.ready_customers.toLocaleString('it-IT')} contattabili oggi. Ogni cliente appartiene a una sola categoria.`;
    $('#notice').hidden = data.active;
    $('#notice').textContent = 'Lo storico non è ancora attivo. Nessun piano è lavorabile.';
    closeQuickDetail(false); renderRetention();
  } catch (error) { if (request === retentionRequest) {$('#notice').hidden = false; $('#notice').textContent = error.message;} }
  finally { if (request === retentionRequest) $('#customers').removeAttribute('aria-busy'); }
}

function renderRetention() {
  const rows = retention.rows;
  const view = retention.operational_views.find(view => view.key === selectedView);
  const activity = retention.activity_views.find(view => view.key === selectedActivity);
  $('#view-description').textContent = (activity?.description || view?.description || 'Ogni cliente compare una sola volta. La categoria descrive la situazione attuale, lo stato riguarda i singoli piani.') + (retention.unassigned_review_orders ? ` ${retention.unassigned_review_orders} ordini senza email non sono ancora attribuiti a clienti.` : '');
  const active = ['#operational-filter', '#state-filter', '#strategy', '#profile-filter'].map(id => $(id)).filter(select => select.value).map(select => select.selectedOptions[0].textContent);
  $('#active-filters').textContent = `Ricerca attiva: ${[activity?.label, ...active].filter(Boolean).join(' · ') || 'Tutti i clienti'}${$('#search').value ? ' · ' + $('#search').value : ''}`;
  $('#queue-title').textContent = `${rows.length} clienti corrispondenti`;
  page = Math.min(page, Math.max(0, Math.ceil(rows.length / pageSize) - 1));
  renderRetentionRows(rows.slice(page * pageSize, (page + 1) * pageSize));
  $('#page-label').textContent = rows.length ? `${page * pageSize + 1}–${Math.min((page + 1) * pageSize, rows.length)} di ${rows.length}` : 'Nessun cliente';
  $('#previous').disabled = page === 0; $('#next').disabled = (page + 1) * pageSize >= rows.length;
  $('.pagination').hidden = rows.length <= pageSize;
}

function closeQuickDetail(restoreFocus = true) {
  ++quickRequest;
  $('#quick-detail').hidden = true;
  $('#quick-content').replaceChildren();
  $('#customers').querySelectorAll('.selected-row').forEach(row => row.classList.remove('selected-row'));
  if (restoreFocus && quickOrigin?.isConnected) quickOrigin.focus();
}

async function previewPlan(item, row, origin) {
  const request = ++quickRequest;
  quickOrigin = origin;
  $('#customers').querySelectorAll('.selected-row').forEach(row => row.classList.remove('selected-row'));
  row.classList.add('selected-row');
  const aside = $('#quick-detail'), content = $('#quick-content'); aside.hidden = false;
  content.replaceChildren(element('p', 'Caricamento del profilo e del piano…', 'small'));
  try {
    const data = await api(`/api/plan?customer=${encodeURIComponent(item.customer_id)}&plan=${encodeURIComponent(JSON.stringify(item.plan_key))}`);
    if (request !== quickRequest) return;
    const title = element('h2', data.customer_id); title.id = 'quick-title';
    content.replaceChildren(title, element('p', data.reason, 'small'), customerQualification(data.customer_profile, true));
    if (data.order_number) content.append(element('p', `Ordine di origine: ${data.order_number}`, 'small'));
    const action = element('section', undefined, 'quick-action');
    action.append(element('h3', 'Prossima azione suggerita'), element('p', data.event_templates.contact ? 'Contatta il cliente via email' : 'Apri la scheda per verificare il prossimo passo.'));
    action.append(element('p', data.event_templates.contact ? 'Verifica prezzo, disponibilità e consenso. Dopo l’invio registra il contatto.' : data.reason, 'small'));
    const open = element('button', data.event_templates.contact ? 'Apri scheda e registra contatto' : 'Apri scheda cliente', 'button primary');
    open.addEventListener('click', () => { closeQuickDetail(false); openPlan(item); }); action.append(open); content.append(action);
    content.append(element('h3', 'Opportunità del piano'));
    for (const product of data.proposals) {
      const card = element('article', undefined, 'quick-product');
      card.append(element('h4', product.name), element('p', `${money(product.value_minor)} · ${product.role === 'primary' ? 'Proposta principale' : 'Opzione del piano'}`, 'small'), element('p', `${product.commercial_category === 'targeted' ? 'Mirata' : 'Da testare'} · ${product.rationale}`, 'small')); content.append(card);
      attachProductImage(card, data.product_images[product.sku]);
    }
    if (data.presentation) content.append(element('p', data.presentation.instruction, 'small'));
    content.append(element('h3', 'Altri piani e corrispondenze ai filtri'));
    for (const plan of item.plans) {
      const card = element('article', undefined, 'quick-product');
      if (item.matching_plans.some(match => JSON.stringify(match.plan_key) === JSON.stringify(plan.plan_key))) card.append(element('strong', 'Corrisponde ai filtri'));
      card.append(element('p', `${stateLabels[plan.state]} · ${plan.reason}`, 'small'));
      for (const op of plan.opportunities) card.append(element('p', `${op.proposal} · ${op.strategy_label} · ${op.commercial_category === 'targeted' ? 'Mirata' : 'Da testare'}`, 'small'));
      const inspect = element('button', plan.is_primary ? 'Apri piano consigliato' : 'Consulta piano e storico', 'button subtle');
      inspect.addEventListener('click', () => { closeQuickDetail(false); openPlan({customer_id: item.customer_id, plan_key: plan.plan_key}); });
      card.append(inspect); content.append(card);
    }
    const history = element('button', 'Vedi storico completo', 'button subtle');
    history.addEventListener('click', () => { closeQuickDetail(false); openPlan(item); }); content.append(history);
    $('#quick-close').focus({preventScroll: true});
  } catch (error) { if (request === quickRequest) content.replaceChildren(element('p', error.message)); }
}

function renderRetentionRows(rows) {
  $('#columns').replaceChildren(...['Cliente / categoria', 'Profilo', 'Acquisto fonte', 'Raccomandazione principale', 'Strategia', 'Corrispondenze / motivo', 'Valore', 'Azione'].map((label, i) => {
    const heading = element('th', undefined, i === 6 ? 'numeric' : i === 7 ? 'action' : ''); heading.scope = 'col';
    heading.append(element('span', label, i === 7 ? 'sr-only' : '')); return heading;
  }));
  $('#customers').replaceChildren();
  if (!rows.length) {const row = element('tr'), cell = element('td', 'Nessun cliente corrisponde alla combinazione di filtri.', 'empty'); cell.colSpan = 8; row.append(cell); $('#customers').append(row); return;}
  for (const item of rows) {
    const row = element('tr');
    const category = retention.operational_views.find(view => view.key === item.category);
    const matches = item.matching_plans.flatMap(plan => plan.opportunities.map(op => `${op.proposal} · ${stateLabels[plan.state]}`));
    const filtered = $('#strategy').value || $('#state-filter').value;
    const cells = [[item.customer_id, category.label], null,
      [item.source_product, `${item.order_number || ''} · ${dateLabel(item.source_date, true)}`],
      [item.proposal, item.contactable ? 'Attuabile oggi' : item.status_label], [item.strategy_label],
      [filtered ? matches.join(' / ') : item.reason, filtered ? 'Corrispondenze al filtro; raccomandazione globale invariata' : null],
      [item.value_minor == null ?  '—' : money(item.value_minor), 'Valore nominale']];
    cells.forEach((values, index) => {
      const cell = element('td', undefined, index === 6 ? 'numeric' : '');
      cell.dataset.label = ['Cliente / categoria', 'Profilo', 'Acquisto fonte', 'Raccomandazione principale', 'Strategia', 'Corrispondenze / motivo', 'Valore'][index];
      if (index === 1) {
        const badges = profileBadges(item.customer_profile);
        item.customer_profile.signals.forEach((signal, i) => {
          const name = {first_purchase: 'first', recurring: 'recurring', multicategory: 'multicategory'}[signal.key];
          if (name) badges.children[i].querySelector('img').src = `/assets/retention-${name}.svg`;
        });
        cell.append(badges);
      }
      else {const label = element('span', values[0], 'primary-text'); label.title = values[0]; cell.append(label);
        if (index === 4) label.classList.add('strategy-badge', `strategy-${item.strategy}`);
        if (values[1]) cell.append(element('small', values[1], index === 0 ? `tone-${category.tone}` : ''));
      }
      if (index === 3) attachProductImage(cell, retention.product_images[item.target_sku]);
      if (index === 5 && item.plans.length) {
        const plans = element('button', `${item.plans.length} ${item.plans.length === 1 ? 'piano consultabile' : 'piani consultabili'}`, 'retention-plans');
        plans.type = 'button'; plans.setAttribute('aria-label', `Consulta i piani di ${item.customer_id}`);
        plans.addEventListener('click', () => previewPlan(item, row, plans)); cell.append(plans);
      }
      row.append(cell);
    });
    const action = element('td', undefined, 'action'), open = element('button', undefined, 'open-button'); open.type = 'button';
    open.append(element('span', 'Apri'));
    const iconSlot = element('span', undefined, 'retention-icon-slot'), icon = element('img');
    icon.src = '/assets/retention-open.svg'; icon.alt = ''; iconSlot.append(icon); open.append(iconSlot);
    open.setAttribute('aria-label', `Apri la scheda di ${item.customer_id}`);
    open.addEventListener('click', () => {closeQuickDetail(false); openPlan(item);}); action.append(open); row.append(action); $('#customers').append(row);
  }
}

$('#filters').addEventListener('submit', event => event.preventDefault());
$('#filters').addEventListener('change', event => {if (floatingFilters.some(filter => filter.select === event.target)) applyRetentionFilters();});
$('#search').addEventListener('input', () => {clearTimeout(refreshTimer); refreshTimer = setTimeout(applyRetentionFilters, 350);});
$('#filters').addEventListener('reset', () => {
  clearTimeout(refreshTimer); openFloatingSelect?.close();
  selectedActivity = '';
  // Clear explicitly so hidden select state, triggers, chips and URL change together.
  floatingFilters.forEach(filter => {filter.select.value = '';}); $('#search').value = '';
  $('.retention-reset').focus(); applyRetentionFilters();
});
$('#quick-close').addEventListener('click', () => closeQuickDetail());
$('#quick-detail').addEventListener('keydown', event => {if (event.key === 'Escape') {event.preventDefault(); closeQuickDetail();}});
$('#previous').addEventListener('click', () => {page--; closeQuickDetail(false); renderRetention();});
$('#next').addEventListener('click', () => {page++; closeQuickDetail(false); renderRetention();});
loadRetention();
setInterval(() => {if (!document.hidden && $('#quick-detail').hidden && $('#detail').hidden) loadRetention();}, 60000);
