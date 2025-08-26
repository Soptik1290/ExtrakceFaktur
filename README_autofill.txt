Backend:
- Přidej soubor: backend/extractors/postprocess.py
- V app.py importuj: from .extractors.postprocess import autofill_amounts
- Po výpočtu `result` (před validate_extraction) zavolej: result = autofill_amounts(result)

Frontend (volitelné):
- Pokud chceš u dopočítaných hodnot zobrazit štítek „(počítáno)“, využij skriptový snippet (viz script_snippet_autofill.txt)
  – uprav funkci pro rendrování řádků a předávej computed flagy z `data._computed`.
