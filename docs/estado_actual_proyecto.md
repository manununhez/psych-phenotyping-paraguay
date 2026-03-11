# Estado actual del proyecto

## Resumen ejecutivo
El proyecto está cerrado metodológicamente en fase de desarrollo (`dev`) y preparado para pasar a evaluación final en `test`, con controles de freeze y trazabilidad.

## Qué está cerrado
1. Pipeline de desarrollo reproducible hasta análisis de errores.
2. Barrido/ablación híbrida en `dev`.
3. Freeze léxico preliminar.
4. Cierre formal de selección de modelos en `dev` integrado como etapa `09b`.
5. Lista corta de modelos para `test`.
6. Auditoría de split con estado `TEST_VIRGEN`.

## Artefactos clave ya generados
- Auditoría de test:
  - `data/outputs/auditoria_test_20260310_213839.md`
  - `data/outputs/auditoria_test_20260310_213839.csv`
- Barrido amplio de híbridos:
  - `data/outputs/barridos_hibridos/20260310_202656/`
- Freeze léxico preliminar vigente:
  - `data/outputs/freeze_lexico_20260310_232420/`
- Cierre formal de modelos en `dev`:
  - `data/outputs/cierre_modelos_dev_20260310_233211/`

## Qué está pendiente (fase final)
1. Integrar y ejecutar notebook final de evaluación en `test` (única pasada post-freeze).
2. Integrar notebook final de xAI/explicabilidad.
3. Consolidar acta final post-test para cierre de tesis/paper.
4. Incorporar validación externa IPS final al freeze oficial definitivo.

## Riesgos y advertencias
- El mejor desempeño absoluto en `dev` sigue en baselines textuales fuertes; la narrativa del híbrido debe sostenerse en trazabilidad y diseño, no en sobreafirmación de métricas.
- Cambios en reglas/features antes de `test` invalidan el cierre formal en `dev`.
- La evidencia actual corresponde a desarrollo; no debe comunicarse como evaluación final externa.

## Próximo paso recomendado
Ejecutar la regeneración limpia de desarrollo y, sobre ese estado congelado, preparar la corrida final en `test` con lista corta fija y sin ajustes posteriores.
