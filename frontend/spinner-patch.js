// Spinner helpers
function showLoading() { document.getElementById('loadingOverlay')?.classList.remove('hidden'); }
function hideLoading() { document.getElementById('loadingOverlay')?.classList.add('hidden'); }

// Wrap existing actions if available
(function patchButtons(){
  const go = document.getElementById('go');
  if (go && !go.dataset.patched) {
    const orig = go.onclick || (()=>{});
    go.dataset.patched = '1';
    go.addEventListener('click', async (e) => {
      showLoading();
      try { await (window.extract ? window.extract() : orig(e)); }
      finally { hideLoading(); }
    }, { once: false });
  }
  const dl = document.getElementById('doExport');
  if (dl && !dl.dataset.patched) {
    const orig2 = dl.onclick || (()=>{});
    dl.dataset.patched = '1';
    dl.addEventListener('click', async (e) => {
      showLoading();
      try { await (window.doExport ? window.doExport() : orig2(e)); }
      finally { hideLoading(); }
    }, { once: false });
  }
})();