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
  if (!res.ok) {
    alert('Extraction failed.'); return;
  }
  const data = await res.json();
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
    ['Confidence', d.confidence]
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

  // Download JSON
  const btn = document.getElementById('downloadJson');
  btn.onclick = () => {
    const blob = new Blob([JSON.stringify(d, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (file.name.replace(/\.[^.]+$/,'') || 'invoice') + '.json';
    a.click();
  };
}

document.getElementById('go').addEventListener('click', extract);
