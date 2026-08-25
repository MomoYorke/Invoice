/* Logica pagina "Nuova fattura" */
(function () {
  const form = document.getElementById('invoice-form');
  if (!form) return;

  const itemsBox = document.getElementById('items');
  const totalEl = document.getElementById('total-preview');
  const clientSel = document.getElementById('client-select');
  const addrBox = document.getElementById('client-addr');
  const sugBox = document.getElementById('running-suggestion');
  const sugTesto = document.getElementById('running-suggestion-testo');
  const newToggle = document.getElementById('new-client-toggle');
  const newFields = document.getElementById('new-client-fields');
  let rowCount = 0;

  // Le frasi che questo file scrive nella pagina. Le manda nuova.html gia'
  // tradotte; l'italiano qui sotto e' la rete di sicurezza, come nel resto
  // dell'app: se una manca si legge in italiano, non si legge il vuoto.
  const T = Object.assign({
    descrizione: 'Descrizione del servizio',
    rimuovi: 'Rimuovi',
    periodo: "Periodo proposto in automatico (mese successivo all'ultima " +
             'fattura: {periodo}). Controlla le date e correggi se serve.',
    intestata: 'La fattura sarà intestata a {chi}, non a {cliente}.'
  }, window.TESTI || {});

  function riempi(frase, valori) {
    return frase.replace(/\{(\w+)\}/g, (tutto, nome) =>
      nome in valori ? valori[nome] : tutto);
  }
  function alSicuro(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  }

  // ---- parsing importi (specchio di money.py; il server ricalcola comunque) ----
  function parseAmount(s) {
    if (!s) return null;
    let t = String(s).toUpperCase().replace(/CHF|FR\./g, '');
    t = t.replace(/\.\s*[-–—]\s*$/, '');
    t = t.replace(/[–—'  ]/g, '');
    if (!/\d/.test(t)) return null;
    if (t.includes(',') && t.includes('.')) {
      if (t.lastIndexOf(',') > t.lastIndexOf('.')) t = t.replace(/\./g, '').replace(',', '.');
      else t = t.replace(/,/g, '');
    } else if (t.includes(',')) {
      t = /,\d{1,2}$/.test(t) ? t.replace(',', '.') : t.replace(/,/g, '');
    } else if ((t.match(/\./g) || []).length > 1) {
      const p = t.split('.');
      t = p.slice(0, -1).join('') + '.' + p[p.length - 1];
    }
    if (/^\d{1,3}\.\d{3}$/.test(t)) t = t.replace('.', '');
    t = t.replace(/[^0-9.]/g, '');
    if (!t || t === '.') return null;
    return Math.round(parseFloat(t) * 100);
  }
  function fmtChf(c) {
    const fr = Math.floor(Math.abs(c) / 100), ct = Math.abs(c) % 100;
    return fr.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'") + '.' + String(ct).padStart(2, '0') + ' CHF';
  }

  function addRow(desc, qty, unit, tot) {
    const i = rowCount++;
    const div = document.createElement('div');
    div.className = 'item-row';
    div.innerHTML =
      `<input type="text" name="qty_${i}" value="${qty || '1'}">` +
      `<input type="text" name="desc_${i}" value="${desc || ''}" placeholder="${T.descrizione}">` +
      `<input type="text" name="unit_${i}" value="${unit || ''}" placeholder="110.-">` +
      `<input type="text" name="tot_${i}" value="${tot || ''}" placeholder="auto">` +
      `<button type="button" class="remove-row" title="${T.rimuovi}">✕</button>`;
    div.querySelector('.remove-row').onclick = () => { div.remove(); updateTotal(); };
    div.querySelectorAll('input').forEach(el => el.addEventListener('input', updateTotal));
    itemsBox.appendChild(div);
    updateTotal();
    return div;
  }

  function rowTotal(div) {
    const [qtyEl, , unitEl, totEl] = div.querySelectorAll('input');
    const explicit = parseAmount(totEl.value);
    if (explicit !== null) return explicit;
    const unit = parseAmount(unitEl.value);
    if (unit === null) return null;
    const qty = parseFloat(String(qtyEl.value).replace(',', '.')) || 1;
    return Math.round(qty * unit);
  }

  function updateTotal() {
    let sum = 0;
    itemsBox.querySelectorAll('.item-row').forEach(div => {
      const t = rowTotal(div);
      if (t !== null) sum += t;
    });
    totalEl.textContent = fmtChf(sum);
  }

  document.getElementById('add-row').onclick = () => addRow();
  addRow(); // prima riga

  // ---- preset servizi ----
  document.querySelectorAll('.preset').forEach(btn => {
    btn.onclick = async () => {
      const desc = btn.dataset.desc;
      const firstRow = itemsBox.querySelector('.item-row') || addRow();
      const inputs = firstRow.querySelectorAll('input');
      // se questo servizio e' gia' stato fatturato a questo cliente con un
      // periodo dentro, il server lo ripropone con le date del mese dopo
      let ripreso = false;
      if (clientSel.value) {
        const r = await fetch('/api/periodo-successivo?client_id=' + clientSel.value +
                              '&servizio=' + encodeURIComponent(desc)).then(r => r.json());
        if (r.found && r.description) {
          ripreso = true;
          inputs[1].value = r.description;
          if (r.unit) inputs[2].value = r.unit;
          if (r.advanced) {
            sugBox.style.display = 'block';
            sugTesto.innerHTML = riempi(alSicuro(T.periodo),
                     { periodo: '<em>' + alSicuro(r.previous) + '</em>' });
          } else {
            sugBox.style.display = 'none';
          }
        }
      }
      if (!ripreso) {
        inputs[1].value = desc;
        sugBox.style.display = 'none';
      }
      updateTotal();
      inputs[2].focus();
    };
  });

  // ---- cliente: indirizzo + toggle nuovo ----
  clientSel.addEventListener('change', async () => {
    sugBox.style.display = 'none';
    if (!clientSel.value) { addrBox.textContent = ''; return; }
    const c = await fetch('/api/client/' + clientSel.value).then(r => r.json());
    const indirizzo = [c.address1, (c.address2 || '').replace('\n', ', ')].filter(Boolean).join(', ');
    addrBox.textContent = indirizzo;
    // chi si allena e chi riceve la fattura possono essere persone diverse
    if (c.intestatario) {
      const avviso = document.createElement('div');
      avviso.style.marginTop = '4px';
      avviso.innerHTML = '\u270D\uFE0F ' + riempi(alSicuro(T.intestata), {
        chi: '<strong>' + alSicuro(c.intestatario) + '</strong>',
        cliente: alSicuro(c.name)
      });
      addrBox.appendChild(avviso);
    }
  });
  newToggle.addEventListener('change', () => {
    newFields.style.display = newToggle.checked ? 'block' : 'none';
    clientSel.disabled = newToggle.checked;
  });
})();
