registerPage('analysis', (root, lifecycle) => {
  const $ = selector => root.querySelector(selector);
  const period = $('#analysis-period');
  let request = 0;

  function table(container, title, rows) {
    container.replaceChildren();
    if (!rows.length) {container.append(element('p', 'Nessun piano avviato in questo gruppo nel periodo.', 'analysis-empty')); return;}
    const table = element('table', undefined, 'analysis-table');
    table.append(element('caption', title));
    const head = element('thead'), heading = element('tr');
    for (const label of [title.includes('contatto') ? 'Tentativo' : 'Gruppo', 'Piani', 'Clienti', 'Con risposta', 'Acquirenti verificati', 'Ricavi attribuiti']) heading.append(element('th', label));
    head.append(heading); table.append(head);
    const body = element('tbody');
    for (const row of rows) {
      const tr = element('tr');
      for (const value of [row.label, row.plans, row.customers, row.replies, row.buyers, money(row.revenue_minor)]) tr.append(element('td', String(value)));
      body.append(tr);
    }
    table.append(body); container.append(table);
  }

  function timingCard(label, data, detail) {
    const card = element('article', undefined, 'card');
    card.append(element('span', label), element('strong', data.median_days === null ? '—' : `${data.median_days} giorni`),
      element('small', `${data.cases} ${data.cases === 1 ? 'caso osservato' : 'casi osservati'} · ${detail}`));
    return card;
  }

  async function load() {
    const current = ++request;
    $('#analysis-notice').hidden = false;
    $('#analysis-notice').textContent = 'Caricamento dell’analisi…';
    try {
      const data = await api(`/api/analysis?period=${encodeURIComponent(period.value)}`);
      if (current !== request) return;
      $('#mode').textContent = data.demo ? 'Simulazione · dati sintetici' : 'Dati operativi';
      $('#evaluation-date').textContent = dateLabel(data.date, true);
      $('#workspace-mode').textContent = data.demo ? 'Laifen · Workspace demo' : 'Laifen · Workspace operativo';
      $('#analysis-scope').textContent = `${data.plans} ${data.plans === 1 ? 'piano avviato' : 'piani avviati'} · ${data.customers} ${data.customers === 1 ? 'cliente' : 'clienti'} · ${data.starts_on ? `dal ${dateLabel(data.starts_on, true)} al ${dateLabel(data.date, true)}` : `fino al ${dateLabel(data.date, true)}`}`;
      table($('#strategy-table'), 'Strategia della proposta principale', data.groups.strategy);
      table($('#product-table'), 'Prodotto della proposta principale', data.groups.product);
      table($('#attempt-table'), 'Risultati per contatto', data.groups.attempt);
      table($('#profile-table'), 'Profilo cliente al primo contatto', data.groups.profile);
      table($('#path-table'), 'Anzianità del piano al primo contatto', data.groups.path);
      $('#timing-cards').replaceChildren(
        timingCard('Dall’acquisto fonte al primo contatto', data.timing.purchase_to_contact, 'solo piani con ordine fonte'),
        timingCard('Dal contatto all’acquisto verificato', data.timing.contact_to_purchase, 'solo acquisti collegati a un contatto'));
      $('#analysis-content').hidden = false;
      $('#analysis-notice').hidden = true;
    } catch (error) {
      if (current !== request) return;
      $('#analysis-notice').textContent = error.message || 'Analisi non disponibile.';
    }
  }

  lifecycle.listen(period, 'change', load);
  load();
  return {dispose() {++request;}};
});
