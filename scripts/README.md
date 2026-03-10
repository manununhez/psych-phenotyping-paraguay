# Guía de Scripts

Scripts activos de soporte al pipeline.

## Estructura
```text
scripts/
  llm/
    run_gemini_constrained.py
  audit/
    audit_core.py
    diff_meds_excel_repo.py
    freeze_core_from_excel.py
  export/
    export_project_chats_md.py
  devtools/
    split_batches.py
```

## Uso
```bash
python scripts/llm/run_gemini_constrained.py
python scripts/audit/audit_core.py --patterns_root Spanish_Psych_Phenotyping_PY/escribe/patterns --co Concept_CO --core Concept_PY --lexicon Concept_PY_Lexicon
python scripts/audit/diff_meds_excel_repo.py
python scripts/audit/freeze_core_from_excel.py
python scripts/export/export_project_chats_md.py <archivo.json> -o salidas_md
python scripts/devtools/split_batches.py --batch-size 10
```

Estos scripts no modifican la arquitectura científica congelada; solo apoyan extracción, auditoría y trazabilidad.
