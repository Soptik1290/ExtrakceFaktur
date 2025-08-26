
// --- Global state
let lastData = null;

// Toast helper
function toast(msg, type = 'success') {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className = `toast show ${type}`;
  
  // Automaticky skrýt po 3 sekundách
  setTimeout(() => { el.classList.remove('show'); }, 1300);
}

// Success overlay helper
function showSuccessOverlay() {
  // Vytvoříme success overlay
  let successOverlay = document.getElementById('successOverlay');
  if (!successOverlay) {
    successOverlay = document.createElement('div');
    successOverlay.id = 'successOverlay';
    successOverlay.className = 'success-overlay';
    successOverlay.innerHTML = `
      <div class="success-content">
        <div class="success-icon">✅</div>
        <div class="success-text">Zpracování dokončeno!</div>
      </div>
    `;
    document.body.appendChild(successOverlay);
  }
  
  // Zobrazíme overlay
  successOverlay.classList.add('show');
  
  // Automaticky skryjeme po 2 sekundách s fade-out efektem
  setTimeout(() => {
    successOverlay.classList.remove('show');
  }, 2000);
}

// Copy helper
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text ?? '');
    toast('Zkopírováno');
  } catch (e) {
    console.error(e);
    toast('Kopírování selhalo');
  }
}

// Build a table row with a copy button
function rowWithCopy(label, value, computed) {
  if (value == null || value === '') return null;
  const tr = document.createElement('tr');
  const td1 = document.createElement('td'); td1.textContent = label;
  const td2 = document.createElement('td');
  const span = document.createElement('span'); span.className = 'val'; span.textContent = (value ?? '').toString();
  if (computed) {
    const small = document.createElement('small');
    small.className = 'computed-badge';
    small.style.cssText = 'color: #28a745; font-weight: 600; margin-left: 0.5rem;';
    small.textContent = ' (počítáno)';
    span.appendChild(small);
  }
  const btn = document.createElement('button'); btn.className = 'copybtn'; btn.title = 'Kopírovat';
  btn.innerHTML = '📋';
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    copyText((value ?? '').toString());
  });
  td2.appendChild(span); td2.appendChild(btn);
  tr.appendChild(td1); tr.appendChild(td2);
  return tr;
}

async function extract() {
  const file = document.getElementById('file').files[0];
  const method = document.getElementById('method').value;
  if (!file) { 
    toast('⚠️ Nejdříve vyberte soubor s fakturou');
    return; 
  }
  
  // Zobrazení informací o souboru (pro případ, že by uživatel kliknul na tlačítko bez předchozího výběru souboru)
  displayFileInfo(file);

  // Zobrazíme loading overlay
  const loadingOverlay = document.getElementById('loadingOverlay');
  if (loadingOverlay) {
    loadingOverlay.classList.remove('hidden');
  }

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await fetch(`/api/extract?method=${encodeURIComponent(method)}`, {
      method: 'POST',
      body: fd
    });
    if (!res.ok) { 
      toast('❌ Extrakce se nezdařila');
      return; 
    }
    const data = await res.json();
    lastData = data;
    document.getElementById('result').classList.remove('hidden');

    // JSON out + Copy JSON
    const pretty = JSON.stringify(data, null, 2);
    document.getElementById('jsonOut').textContent = pretty;
    const copyJsonBtn = document.getElementById('copyJson');
    if (copyJsonBtn) copyJsonBtn.onclick = () => copyText(pretty);

    // Table
    const tbody = document.querySelector('#tbl tbody'); tbody.innerHTML = '';
    const d = data.data || {}; const sup = d.dodavatel || {};
    const computed = d._computed || {};
    const rows = [
      ['Variabilní symbol', d.variabilni_symbol, null],
      ['Datum vystavení', d.datum_vystaveni, null],
      ['Splatnost', d.datum_splatnosti, null],
      ['DUZP', d.duzp, null],
      ['Částka bez DPH', d.castka_bez_dph, 'castka_bez_dph'],
      ['DPH', d.dph, 'dph'],
      ['Částka s DPH', d.castka_s_dph, 'castka_s_dph'],
      ['Měna', d.mena, null],
      ['Dodavatel – název', sup.nazev, null],
      ['Dodavatel – IČO', sup.ico, null],
      ['Dodavatel – DIČ', sup.dic, null],
      ['Dodavatel – adresa', sup.adresa, null],
      ['Způsob úhrady', d.platba_zpusob, null],
      ['Banka příjemce', d.banka_prijemce, null],
      ['Číslo účtu příjemce', d.ucet_prijemce, null],
      ['Důvěryhodnost', d.confidence != null ? Math.round(d.confidence * 100) + ' %' : null, null],
      // Template only if non-empty
      d._template ? ['Použitá šablona', d._template, null] : null,
    ];
    rows.forEach(([k,v,key]) => {
      const row = rowWithCopy(k,v, computed[key]);
      if (row) tbody.appendChild(row);
    });

    // Validations
    const valUl = document.getElementById('valid'); valUl.innerHTML = '';
    const v = data.validations || {};
    const items = [
      ['Variabilní symbol', v.variabilni_symbol, 'Kontrola formátu variabilního symbolu'],
      ['IČO checksum', v.ico, 'Ověření kontrolního součtu IČO'],
      ['DIČ pattern', v.dic, 'Kontrola formátu DIČ'],
      ['Součet (bezDPH + DPH = s DPH)', v.sum_check, 'Ověření matematické správnosti částek']
    ];
    items.forEach(([label, ok, description]) => {
      const li = document.createElement('li');
      if (ok === true) {
        li.className = 'ok';
        li.innerHTML = `<div class="validation-item"><div class="validation-header">✅ ${label}</div><div class="validation-description">${description}</div></div>`;
      } else if (ok === false) {
        li.className = 'bad';
        li.innerHTML = `<div class="validation-item"><div class="validation-header">❌ ${label}</div><div class="validation-description">${description}</div></div>`;
      } else {
        li.className = 'info';
        li.innerHTML = `<div class="validation-item"><div class="validation-header">ℹ️ ${label}</div><div class="validation-description">${description} (nelze ověřit)</div></div>`;
      }
      valUl.appendChild(li);
    });
    
    // Explicitně zobrazíme hlášku o úspěšné extrakci
    toast('✅ Extrakce dokončena úspěšně');
    
    // Zobrazíme success overlay s fade-out efektem
    showSuccessOverlay();
    
  } catch (error) {
    console.error('Chyba při extrakci:', error);
    toast('❌ Nastala chyba při zpracování faktury', 'error');
  } finally {
    // Skryjeme loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add('hidden');
    }
  }
}

async function doExport() {
  if (!lastData) { 
    toast('⚠️ Nejdříve proveďte extrakci dat');
    return; 
  }
  
  // Zobrazíme loading overlay
  const loadingOverlay = document.getElementById('loadingOverlay');
  if (loadingOverlay) {
    loadingOverlay.classList.remove('hidden');
    // Změníme text pro export
    const loadingText = loadingOverlay.querySelector('.loading-text');
    if (loadingText) {
      loadingText.textContent = 'Připravuji export...';
    }
  }
  
  try {
    const fmt = document.getElementById('exportFmt').value;
    const name = document.getElementById('exportName').value || 'invoice_export';
    const payload = { format: fmt, data: (lastData.data || {}), filename: name };
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) { 
      toast('❌ Export se nezdařil');
      return; 
    }
    const blob = await res.blob();
    const ext = fmt === 'xlsx' ? 'xlsx' : (fmt === 'csv' ? 'csv' : (fmt === 'txt' ? 'txt' : 'json'));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `${name}.${ext}`; a.click();
    toast('💾 Soubor byl stažen');
    
    // Zobrazíme success overlay
    showSuccessOverlay();
    
  } catch (error) {
    console.error('Chyba při exportu:', error);
    toast('❌ Nastala chyba při exportu dat', 'error');
  } finally {
    // Skryjeme loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add('hidden');
      // Vrátíme původní text
      const loadingText = loadingOverlay.querySelector('.loading-text');
      if (loadingText) {
        loadingText.textContent = 'Probíhá zpracování dokumentu...';
      }
    }
  }
}

window.extract = extract;
window.doExport = doExport;

// Funkce pro zobrazení informací o souboru
function displayFileInfo(file) {
  if (!file) return;
  
  const fileInfoEl = document.getElementById('file-info');
  const fileNameEl = document.getElementById('file-name');
  const fileSizeEl = document.getElementById('file-size');
  
  // Zobrazení názvu souboru
  fileNameEl.textContent = `📄 Název: ${file.name}`;
  
  // Zobrazení velikosti souboru v KB nebo MB
  const sizeInKB = file.size / 1024;
  let sizeText = '';
  
  if (sizeInKB < 1024) {
    sizeText = `📊 Velikost: ${sizeInKB.toFixed(2)} KB`;
  } else {
    const sizeInMB = sizeInKB / 1024;
    sizeText = `📊 Velikost: ${sizeInMB.toFixed(2)} MB`;
  }
  
  fileSizeEl.textContent = sizeText;
  fileInfoEl.classList.remove('hidden');
}

// Hook buttons
document.getElementById('go')?.addEventListener('click', extract);
document.getElementById('doExport')?.addEventListener('click', doExport);
document.getElementById('copyJson')?.addEventListener('click', () => {
  const pretty = document.getElementById('jsonOut').textContent || '';
  copyText(pretty);
});

// Přidání event listeneru pro změnu souboru
document.getElementById('file')?.addEventListener('change', (e) => {
  const file = e.target.files[0];
  displayFileInfo(file);
});
