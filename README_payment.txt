
Payment fields patch
--------------------
Backend:
- Replace or merge:
  - backend/extractors/heuristics.py   (adds: platba_zpusob, banka_prijemce, ucet_prijemce)
  - backend/extractors/llm.py          (schema extended + parsing)
  - backend/templates/tpl_alza.json    (regex for payment method / bank / account)
  - backend/templates/tpl_vocaskova.json

Frontend:
- In your extract() table builder, append three rows (see frontend/script_snippet_payment.txt).
  If you use my rowWithCopy(), the copy buttons will be there automatically.

Export:
- /api/export already flattens arbitrary keys → works out of the box.
