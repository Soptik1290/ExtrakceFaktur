
# Hotové úpravy
- Oprava nekonečné animace načítání (spinner) – overlay se vždy schová (`try/finally`).
- Zobrazení názvu nahraného souboru u inputu (vč. velikosti).
- Success toast „Hotovo – faktura zpracována“ (krátké potvrzení po dokončení).
- Backend endpoint `GET /api/templates` – vrací dostupné šablony.

## Nasazení
1. Nahraj tyto soubory do svého GitHub repozitáře (nahraď původní).
2. Spusť aplikaci jako obvykle (`uvicorn backend.app:app --reload` nebo přes Docker).
3. Otestuj: nahraj fakturu → spinner se ukáže → po dokončení zmizí a uvidíš ✅ toast.

### Docker (pokud používáš)
```
docker build -t extrakce_faktur .
docker run --rm -p 8000:8000 extrakce_faktur
```

## Volitelné
- Toast text můžeš změnit v `frontend/script.js` ve funkci `showSuccessToast(...)`.
- Délku zobrazení upravíš v `setTimeout(...)` (aktuálně ~1.6 s + 0.4 s fade-out).
