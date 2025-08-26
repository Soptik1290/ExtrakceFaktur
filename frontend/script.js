
let lastData = null;

async function extract() {
  const file = document.getElementById('file').files[0];
  const method = document.getElementById('method').value;
  if (!file) { alert('Select a file first.'); return; }

  const fd = new FormData();
  fd.append('file', file);

  const res = await fetch(`/api/extract?method=${encodeURIComponent(method)}`, {
    method: 'POST',
    body: fd
  });
  if (!res.ok) { alert('Extraction failed.'); return; }
  const data = await res.json();
  lastData = data;  // keep for export
  document.getElementById('result').classList.remove('hidden');

  // JSON out
  const pretty = JSON.stringify(data, null, 2);
  document.getElementById('jsonOut').textContent = pretty;

  // Table
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  const d = data.data || {};
  const sup = d.dodavatel || {};
  const rows = [
    ['Variabilní symbol', d.variabilni_symbol],
    ['Datum vystavení', d.datum_vystaveni],
    ['Splatnost', d.datum_splatnosti],
    ['DUZP', d.duzp],
    ['Částka bez DPH', d.castka_bez_dph],
    ['DPH', d.dph],
    ['Částka s DPH', d.castka_s_dph],
    ['Měna', d.mena],
    ['Dodavatel – název', sup.nazev],
    ['Dodavatel – IČO', sup.ico],
    ['Dodavatel – DIČ', sup.dic],
    ['Dodavatel – adresa', sup.adresa],
    ['Confidence', d.confidence],
    ['Template', d._template || '']
  ];
  rows.forEach(([k,v]) => {
    const tr = document.createElement('tr');
    const td1 = document.createElement('td'); td1.textContent = k;
    const td2 = document.createElement('td'); td2.textContent = (v ?? '').toString();
    tr.appendChild(td1); tr.appendChild(td2); tbody.appendChild(tr);
  });

  // Validations
  const valUl = document.getElementById('valid');
  valUl.innerHTML = '';
  const v = data.validations || {};
  const items = [
    ['Variabilní symbol', v.variabilni_symbol],
    ['IČO checksum', v.ico],
    ['DIČ pattern', v.dic],
    ['Součet (bezDPH + DPH = s DPH)', v.sum_check]
  ];
  items.forEach(([label, ok]) => {
    const li = document.createElement('li');
    li.innerHTML = ok === true ? `✅ <span class="ok">${label}</span>` :
                 ok === false ? `⚠️ <span class="bad">${label}</span>` :
                 `ℹ️ ${label}: (nelze ověřit)`;
    valUl.appendChild(li);
  });
}

async function doExport() {
  if (!lastData) { alert('Nejdřív vytěž fakturu.'); return; }
  const fmt = document.getElementById('exportFmt').value;
  const name = document.getElementById('exportName').value || 'invoice_export';
  const payload = {
    format: fmt,
    data: lastData.data || {},
    filename: name
  };
  const res = await fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) { alert('Export failed.'); return; }
  const blob = await res.blob();
  // guess extension by fmt
  const ext = fmt === 'xlsx' ? 'xlsx' : (fmt === 'csv' ? 'csv' : (fmt === 'txt' ? 'txt' : 'json'));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${name}.${ext}`;
  a.click();
}

document.getElementById('go').addEventListener('click', extract);
document.getElementById('doExport').addEventListener('click', doExport);
