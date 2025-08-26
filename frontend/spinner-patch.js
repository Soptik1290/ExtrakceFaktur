// Spinner helpers
function showLoading() { 
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    // Aktualizovat text podle akce
    const loadingText = overlay.querySelector('.loading-text');
    if (loadingText) {
      loadingText.textContent = 'Zpracovávám fakturu...';
    }
  }
}

function hideLoading() { 
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) {
    overlay.classList.add('hidden');
  }
}

// Wrap existing actions if available
(function patchButtons(){
  const go = document.getElementById('go');
  if (go && !go.dataset.patched) {
    go.dataset.patched = '1';
    go.addEventListener('click', async (e) => {
      showLoading();
      try { 
        await (window.extract ? window.extract() : (() => {})()); 
      } catch (error) {
        console.error('Chyba při extrakci:', error);
        toast('❌ Nastala chyba při zpracování faktury', 'error');
      } finally { 
        hideLoading(); 
      }
    }, { once: false });
  }
  
  const dl = document.getElementById('doExport');
  if (dl && !dl.dataset.patched) {
    dl.dataset.patched = '1';
    dl.addEventListener('click', async (e) => {
      const loadingText = document.querySelector('.loading-text');
      if (loadingText) loadingText.textContent = 'Připravuji export...';
      
      showLoading();
      try { 
        await (window.doExport ? window.doExport() : (() => {})()); 
      } catch (error) {
        console.error('Chyba při exportu:', error);
        toast('❌ Nastala chyba při exportu dat', 'error');
      } finally { 
        hideLoading(); 
      }
    }, { once: false });
  }
})();