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
        // Uložíme původní funkci toast
        const originalToast = window.toast;
        let extractionSuccessful = false;
        
        // Dočasně přepíšeme funkci toast, abychom mohli zachytit úspěšnou extrakci
        window.toast = function(msg, type) {
          if (msg === '✅ Extrakce dokončena úspěšně') {
            extractionSuccessful = true;
          }
          // Voláme původní funkci toast
          originalToast(msg, type);
        };
        
        // Voláme funkci extract
        await (window.extract ? window.extract() : (() => {})()); 
        
        // Obnovíme původní funkci toast
        window.toast = originalToast;
      } catch (error) {
        console.error('Chyba při extrakci:', error);
        // Zobrazíme chybovou hlášku pouze pokud extrakce nebyla úspěšná
        if (!extractionSuccessful) {
          toast('❌ Nastala chyba při zpracování faktury', 'error');
        }
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
        // Uložíme původní funkci toast
        const originalToast = window.toast;
        let exportSuccessful = false;
        
        // Dočasně přepíšeme funkci toast, abychom mohli zachytit úspěšný export
        window.toast = function(msg, type) {
          if (msg === '💾 Soubor byl stažen') {
            exportSuccessful = true;
          }
          // Voláme původní funkci toast
          originalToast(msg, type);
        };
        
        // Voláme funkci doExport
        await (window.doExport ? window.doExport() : (() => {})()); 
        
        // Obnovíme původní funkci toast
        window.toast = originalToast;
      } catch (error) {
        console.error('Chyba při exportu:', error);
        // Zobrazíme chybovou hlášku pouze pokud export nebyl úspěšný
        if (!exportSuccessful) {
          toast('❌ Nastala chyba při exportu dat', 'error');
        }
      } finally { 
        hideLoading(); 
      }
    }, { once: false });
  }
})();