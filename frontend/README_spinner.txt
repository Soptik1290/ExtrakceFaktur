Add the following to your frontend:

1) In index.html, just before </body>, insert:
----------------------------------------------------------------
<!-- Loading overlay -->
<div id="loadingOverlay" class="loading hidden">
  <div class="spinner"></div>
  <div class="loading-text">Zpracovávám…</div>
</div>
<script src="/spinner-patch.js"></script>
----------------------------------------------------------------

2) In style.css, append at the end:
----------------------------------------------------------------
/* Loading overlay */
.loading { position: fixed; inset: 0; background: rgba(15,23,42,0.75); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.loading.hidden { display: none; }
.spinner { width: 48px; height: 48px; border: 6px solid #1f2937; border-top-color: #60a5fa; border-radius: 50%; animation: spin 0.8s linear infinite; }
.loading-text { margin-top: 12px; color: #e5e7eb; font-weight: 600; text-align: center; }
@keyframes spin { to { transform: rotate(360deg);} }
----------------------------------------------------------------

3) Create file frontend/spinner-patch.js with:
----------------------------------------------------------------
// Spinner helpers
function showLoading() { document.getElementById('loadingOverlay')?.classList.remove('hidden'); }
function hideLoading() { document.getElementById('loadingOverlay')?.classList.add('hidden'); }

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
----------------------------------------------------------------
