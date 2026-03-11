# Metodología experimental (fase de desarrollo)

## Tarea y alcance
- Tarea actual: clasificación probabilística binaria entre `ansiedad` y `depresion`.
- En esta fase no existe clase explícita de comorbilidad.
- El objetivo de esta etapa es cerrar decisiones en `dev` sin usar `test`.

## Rol de cada split

### `train`
- Ajuste de modelos y entrenamiento de variantes.
- No se usa para comparaciones finales.

### `dev`
- Comparación de líneas base.
- Barridos y ablaciones del híbrido.
- Selección formal del modelo final de desarrollo.
- Definición de lista corta para fase final.

### `test`
- Hold-out final para evaluación única post-freeze.
- No debe intervenir en selección ni ajuste durante desarrollo.

## Estado actual respecto a `test`
- Auditoría completada: `TEST_VIRGEN` en el estado de cierre actual.
- En esta etapa no se ejecuta evaluación final en `test`.
- El notebook final de `test` será integrado manualmente en la fase final.

## Freeze metodológico previo a test

### Freeze léxico/reglas
- Se congela la versión vigente de:
  - `Concept_CO`,
  - `Concept_PY`,
  - `Concept_PY_Lexicon`.
- Artefacto: `data/outputs/freeze_lexico_<timestamp>/`.

### Freeze de selección de modelo en dev
- Se congela:
  - variante híbrida final,
  - lista corta de modelos que pasan a `test`,
  - criterios multicriterio usados para decidir.
- Artefacto: `data/outputs/cierre_modelos_dev_<timestamp>/`.

## Regla de selección en dev
- `macro_f1` como criterio principal dentro de una rúbrica multicriterio.
- Desempates: `balanced_accuracy`, estabilidad por seeds y balance por clase (`f1_ansiedad`, `f1_depresion`).
- Criterios metodológicos adicionales:
  - parsimonia,
  - auditabilidad clínica,
  - trazabilidad de señales.
- Penalizaciones explícitas para configuraciones con dependencia metodológicamente riesgosa:
  - template,
  - medicación como proxy diagnóstica,
  - LLM sin evidencia robusta.

## Principio de cierre
A partir del cierre formal en `dev`, no se deben cambiar reglas, features ni configuración en función de resultados de `test`.
