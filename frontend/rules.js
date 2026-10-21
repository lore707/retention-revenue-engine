registerPage('rules', (root, lifecycle) => {
const $ = selector => root.querySelector(selector);
let disposed = false;
let rulebook, selectedFlow = 'hair_dryer';
const rulePickers = [
  {id: 'rule-strategy', icon: 'grid', tone: 'purple', search: 'Cerca una strategia…'},
  {id: 'rule-source', icon: 'box', tone: 'blue', search: 'Cerca un acquisto iniziale…'},
  {id: 'rule-target', icon: 'target', tone: 'green', search: 'Cerca un prodotto proposto…'}
].map(config => createFloatingSelect({...config, describeOption: option => ({value: option.value,
  title: option.textContent, icon: config.icon, tone: config.tone, disabled: option.disabled,
  description: option.value ? 'Restringi le regole del percorso' : 'Mostra tutte le regole del percorso'})}));

function rulesBadge(label, tone) {return element('span', label, `rules-badge rules-tone-${tone}`);}
function rulesTable(headers, label) {
  const scroll = element('div', undefined, 'rules-table-scroll'); scroll.tabIndex = 0;
  scroll.setAttribute('role', 'region'); scroll.setAttribute('aria-label', label);
  const table = element('table', undefined, 'rules-table'), caption = element('caption', label, 'sr-only');
  table.setAttribute('role', 'table');
  const head = element('thead'), row = element('tr'), body = element('tbody');
  for (const title of headers) {const th = element('th', title); th.scope = 'col'; row.append(th);}
  head.append(row); table.append(caption, head, body); scroll.append(table); return {scroll, body};
}
function rulesDetails(label, items) {
  const details = element('details', undefined, 'rules-details'); details.append(element('summary', label));
  const list = element('ul'); for (const item of items) list.append(element('li', item)); details.append(list); return details;
}
function renderRules() {
  if (!rulebook) return;
  const flow = rulebook.flows.find(item => item.id === selectedFlow);
  const rows = rulebook.rules.filter(rule => flow.rule_ids.includes(rule.id) && (!$('#rule-strategy').value || rule.strategy === $('#rule-strategy').value)
    && (!$('#rule-source').value || rule.sources.some(source => source.product === $('#rule-source').value))
    && (!$('#rule-target').value || rule.targets.some(target => target.name === $('#rule-target').value)));
  $('#rule-count').textContent = `${rows.length} di ${flow.rule_ids.length} regole del percorso`;
  $('#flow-title').textContent = flow.label;
  $('#flow-models').textContent = flow.models.join(' · ');
  $('#flow-limit').hidden = !flow.models_without_rules.length;
  $('#flow-limit').textContent = `Nessun percorso commerciale attivo per: ${flow.models_without_rules.join(' · ')}. Il prodotto è riconosciuto nello storico.`;
  for (const button of $('#rule-flow-tabs').children) button.setAttribute('aria-pressed', String(button.dataset.flow === selectedFlow));
  const list = $('#rule-list'); list.replaceChildren();
  for (const [index, stage] of flow.stages.entries()) {
    const group = rows.filter(rule => stage.rule_ids.includes(rule.id)); if (!group.length) continue;
    const section = element('section', undefined, `card rules-group rules-flow-stage${stage.seasonal ? ' rules-flow-seasonal' : ''}`);
    const heading = element('div', undefined, 'rules-group-heading');
    heading.append(element('span', stage.seasonal ? '↗' : String(index + 1), 'rules-stage-number'),
      element('strong', stage.when, 'rules-stage-when'), element('h3', stage.label),
      rulesBadge(stage.seasonal ? 'Percorso parallelo' : 'Piano separato dalle altre fasi', stage.seasonal ? 'amber' : 'blue'));
    section.append(heading);
    section.append(element('p', stage.description, 'rules-stage-description'));
    const {scroll, body} = rulesTable(['Modello acquistato', 'Prodotto da proporre', 'Perché / strategia', 'Condizioni e dettagli'], `${flow.label} · ${stage.when} · ${stage.label}`);
    for (const rule of group) {
      const row = element('tr'), source = element('th'); source.scope = 'row';
      source.append(element('strong', [...new Set(rule.sources.map(item => item.product.replace(/^Laifen /, '')))].join(' · ')));
      source.append(rulesDetails('Configurazioni ammesse', rule.sources.map(item => `${item.product} · ${item.configuration}`)));
      const target = element('td'), names = [...new Map(rule.targets.map(item => [item.name, item])).values()];
      for (const item of names) {
        const product = element('div', undefined, 'rules-product');
        if (item.image) {const img = element('img'); img.src = item.image.src; img.alt = ''; img.loading = 'lazy'; product.append(img);}
        product.append(element('strong', item.name)); target.append(product);
      }
      target.append(rulesDetails('Varianti, SKU e prezzi', rule.targets.map(item => [item.variant_label, item.sku, money(item.value_minor)].filter(Boolean).join(' · '))));
      const why = element('td'); why.append(rulesBadge(rule.category === 'targeted' ? 'Mirata' : 'Da testare', rule.category === 'targeted' ? 'green' : 'purple'), element('p', rule.rationale));
      const conditions = element('td');
      if (rule.wait_for_rules.length) conditions.append(rulesBadge('Attende le fasi precedenti', 'amber'));
      const details = [rule.timing, ...rule.exclusions, ...rule.compatibility];
      if (rule.wait_for_rules.length) details.push('Attende la conclusione delle fasi precedenti applicabili dello stesso ordine, anche in promozione. Non è obbligatorio un acquisto.');
      conditions.append(rulesDetails('Esclusioni, compatibilità e tempi', details));
      conditions.append(element('small', rule.id, 'rules-reference'));
      [source, target, why, conditions].forEach((cell, index) => {cell.dataset.label = ['Modello acquistato', 'Prodotto da proporre', 'Perché / strategia', 'Condizioni e dettagli'][index]; row.append(cell);}); body.append(row);
    }
    section.append(scroll); list.append(section);
  }
  if (!rows.length) list.append(element('p', 'Nessuna regola corrisponde ai filtri. Prova ad azzerarli.', 'card rules-empty'));
}
function renderStrategies() {
  const headers = ['Strategia', 'Significato semplice', 'Esempi presenti nel sistema', 'Categoria'];
  const {scroll, body} = rulesTable(headers, 'Le cinque strategie commerciali'); scroll.classList.add('rules-strategy-table');
  for (const strategy of rulebook.strategies) {
    const row = element('tr'), title = element('th'); title.scope = 'row'; title.dataset.label = headers[0];
    title.append(element('strong', strategy.label)); row.append(title);
    for (const [index, text] of [strategy.meaning, strategy.examples].entries()) {
      const cell = element('td', text); cell.dataset.label = headers[index + 1]; row.append(cell);
    }
    const category = element('td'); category.dataset.label = headers[3];
    category.append(rulesBadge(strategy.category === 'targeted' ? 'Mirata' : 'Da testare', strategy.category === 'targeted' ? 'green' : 'purple'));
    row.append(category); body.append(row);
  }
  $('#strategy-table').replaceChildren(scroll);
  const note = rulebook.proposal_change, title = element('h3', note.title); title.id = 'proposal-change-title';
  $('#proposal-change').replaceChildren(title, element('p', note.description), element('strong', note.caveat));
}
function renderProfiles() {
  const headers = ['Profilo', 'Come viene identificato'];
  const {scroll, body} = rulesTable(headers, 'I profili cliente'); scroll.classList.add('rules-profile-table');
  for (const profile of rulebook.profiles) {
    const row = element('tr'), title = element('th'); title.scope = 'row'; title.dataset.label = headers[0];
    title.append(element('strong', profile.label));
    const criterion = element('td', profile.criterion); criterion.dataset.label = headers[1];
    row.append(title, criterion); body.append(row);
  }
  $('#profile-table').replaceChildren(scroll);
  $('#profile-note').textContent = rulebook.profile_note;
}
function renderCalendar() {
  const headers = ['Fase', 'Percorso standard', 'Primo contatto in ritardo / ordine vecchio'];
  const {scroll, body} = rulesTable(headers, 'Calendario standard e recupero ordini'); scroll.classList.add('rules-calendar-table');
  for (const phase of rulebook.contact_calendar.rows) {
    const row = element('tr'), title = element('th'); title.scope = 'row'; title.dataset.label = headers[0];
    title.append(element('strong', phase.label)); row.append(title);
    for (const [index, text] of [phase.standard, phase.delayed].entries()) {
      const cell = element('td', text); cell.dataset.label = headers[index + 1]; row.append(cell);
    }
    body.append(row);
  }
  $('#calendar-table').replaceChildren(scroll);
  $('#calendar-note').textContent = rulebook.contact_calendar.note;
}
async function loadRules() {
  try {
    const data = await api('/api/rules');
    if (disposed) return;
    rulebook = data;
    $('#notice').hidden = true; $('#mode').textContent = 'Consultazione'; $('#evaluation-date').textContent = `Versione ${rulebook.version}`;
    const stats = $('#rule-stats'); stats.replaceChildren();
    for (const [value, title, detail] of [[rulebook.rules.length, 'Regole commerciali', 'Prodotti e tempi di maturazione'],
      [new Set(rulebook.rules.map(rule => rule.strategy)).size, 'Strategie', 'Dai completamenti ai ricambi'],
      [rulebook.flows.length, 'Percorsi di retention', 'Asciugacapelli, rasoi e spazzolini']]) {
      const card = element('div', undefined, 'card rules-stat'), copy = element('div', undefined, 'rules-stat-copy');
      copy.append(element('span', title), element('small', detail)); card.append(element('strong', String(value)), copy); stats.append(card);
    }
    for (const [value, label] of new Map(rulebook.rules.map(rule => [rule.strategy, rule.strategy_label]))) $('#rule-strategy').append(new Option(label, value));
    for (const name of [...new Set(rulebook.rules.flatMap(rule => rule.sources.map(source => source.product)))].sort()) $('#rule-source').append(new Option(name, name));
    for (const name of [...new Set(rulebook.rules.flatMap(rule => rule.targets.map(target => target.name)))].sort()) $('#rule-target').append(new Option(name, name));
    for (const flow of rulebook.flows) {
      const button = element('button', undefined, 'rules-flow-button'); button.type = 'button'; button.dataset.flow = flow.id;
      button.append(filterIcon('box', 'blue'), element('strong', flow.label), element('small', `${flow.rule_ids.length} regole`));
      button.addEventListener('click', () => {
        selectedFlow = flow.id; openFloatingSelect?.close();
        rulePickers.forEach(picker => {picker.select.value = ''; picker.update();}); renderRules();
      }); $('#rule-flow-tabs').append(button);
    }
    rulePickers.forEach(picker => picker.update()); renderStrategies(); renderProfiles(); renderCalendar(); renderRules();
  } catch (error) {if (disposed) return; $('#notice').hidden = false; $('#notice').textContent = error.message;}
}
$('#rule-filters').addEventListener('submit', event => event.preventDefault());
$('#rule-filters').addEventListener('change', () => {
  const source = $('#rule-source').value;
  if (source) selectedFlow = rulebook.flows.find(flow => flow.models.includes(source)).id;
  rulePickers.forEach(picker => picker.update()); renderRules();
});
$('#rule-filters').addEventListener('reset', event => {
  event.preventDefault(); openFloatingSelect?.close();
  rulePickers.forEach(picker => {picker.select.value = ''; picker.update();}); renderRules();
});
loadRules();

return {refresh: loadRules, controls: rulePickers, dispose() {disposed = true;}};
});
