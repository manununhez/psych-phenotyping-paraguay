# Fenotipado Psiquiátrico Paraguay

Repositorio de investigación para clasificación de notas clínicas psiquiátricas del IPS (Paraguay) entre `ansiedad` y `depresion`. La unidad principal es la nota; la partición separa pacientes. No es un sistema de diagnóstico autónomo ni de screening y no incluye controles ni una tercera clase de comorbilidad.

## Estado del experimento
El cierre reproducible vigente es el ensamble ponderado de probabilidades:

- RoBERTa clínico ajustado, `max_length=512`: peso 0.65.
- Random Forest regionalizado `py` (Core + PY), sin LLM: peso 0.15.
- Random Forest `core` con unión binaria de síntomas de reglas y LLM: peso 0.20.

Los pesos se seleccionaron en desarrollo entre 231 combinaciones. El notebook `10` comprobó la reproducción en `dev` y ejecutó inferencia final `predict-only` en prueba el 6 de junio de 2026, sin reentrenar ni reajustar. La configuración de mayo con pesos `0.80 / 0.10 / 0.10` es histórica: no se recuperó su checkpoint contextual exacto.

| Configuración | Macro-F1 en desarrollo | Macro-F1 en prueba |
|---|---:|---:|
| Ensamble 512 recongelado | 0.757017 | 0.555807 |
| RoBERTa clínico 512 aislado | 0.747232 | 0.540702 |
| TF-IDF + LinearSVC | 0.740564 | 0.584478 |
| Híbrido completo PY XGBoost 512 | 0.723387 | 0.506520 |

El ensamble fue el mejor en desarrollo; TF-IDF + LinearSVC obtuvo el mayor valor puntual en prueba. TF-IDF y el híbrido se compararon posteriormente mediante ajuste solo en entrenamiento e inferencia del modelo conservado, respectivamente. No todas las cifras proceden de la ejecución final del ensamble. No se usa prueba para cambiar reglas, modelos, pesos o umbrales.

Resultados de las ramas, métricas por clase, matriz de confusión y procedencia: [Revalidación y valores de referencia](docs/REVALIDACION_RESULTADOS_REFERENCIA.md). El valor puntual no demuestra superioridad estadística. La explicabilidad del ensamble y la revisión clínica completa siguen pendientes; materiales de revisión y SHAP del híbrido histórico no equivalen a esas validaciones.

## Datos y EDA
El flujo conserva `3155 -> 3143 -> 1835` notas: original, base limpia y denoised, con 90 pacientes. El universo denoised contiene 556 notas de ansiedad y 1279 de depresión.

| Conjunto denoised | Pacientes | Notas |
|---|---:|---:|
| Entrenamiento | 54 | 1107 |
| Validación | 18 | 343 |
| Prueba | 18 | 385 |

Todo el EDA está en [01_datos_eda_limpieza.ipynb](notebooks/pipeline/01_datos_eda_limpieza.ipynb): distribución global y por partición, clases, consultas por paciente, sexo, edad con histogramas e intervalos por clase, longitudes, tokens, vocabulario, duplicados, retención y truncamiento potencial. Genera el reporte y sus recursos sin scripts de EDA.

Su análisis principal usa denoised y contrasta la retención con la base limpia. Excluir notas sin entidades aceptadas no prueba ausencia de información clínica ni mejora causal del rendimiento. La partición por paciente tampoco elimina textos idénticos entre conjuntos. Véase [Limitaciones](docs/LIMITACIONES.md).

La ejecución completa de `01` requiere artefactos de `02`/`03` y el tokenizer local de RoBERTa. En una primera ejecución se prepara primero la limpieza y se vuelve al EDA cuando existen esos insumos; el detalle está en la [Guía de ejecución](docs/GUIA_EJECUCION.md).

## Recursos clínicos y LLM
`Spanish_Psych_Phenotyping_PY/` es un submódulo versionado, no contenido accidental del árbol. Inicializarlo en un clon limpio:

```bash
git submodule update --init --recursive
```

Se mantienen las capas y perfiles congelados:

- `Concept_CO`: base histórica; `co = Concept_CO`.
- `Concept_Core`: núcleo depurado; `core = Concept_Core`.
- `Concept_PY`: adaptación regional; `py = Concept_Core + Concept_PY`.

El denoising emplea `core` y una política explícita de aseveración. El LLM apoya revisión léxica y normalización semántica de síntomas dentro de categorías definidas; no clasifica clínicamente ni expande libremente la ontología. La integración sintomática es `feat_X = max(rule_X, llm_X)`; `rule_medication_*` conserva evidencia terapéutica separada.

La extracción conservada incluye las notas de los tres conjuntos, sin proporcionar etiquetas de referencia. Aplicar esa transformación a prueba es distinto de usarla para selección. Su trazabilidad y el resguardo del uso de una API externa se delimitan en [Metodología](docs/METODOLOGIA.md) y [Limitaciones](docs/LIMITACIONES.md).

## Flujo experimental principal
1. [01: limpieza y EDA](notebooks/pipeline/01_datos_eda_limpieza.ipynb).
2. [02: partición por paciente](notebooks/pipeline/02_patient_level_split.ipynb).
3. [03: denoising con Core](notebooks/pipeline/03_denoising_reglas_core.ipynb).
4. [04a: Dummy](notebooks/pipeline/04a_linea_base_dummy.ipynb).
5. [04b: TF-IDF + LinearSVC](notebooks/pipeline/04b_linea_base_tfidf.ipynb).
6. [04c: Transformers standalone](notebooks/pipeline/04c_linea_base_transformers.ipynb).
7. [05: cobertura CO/Core/PY en desarrollo](notebooks/analysis/05_brecha_lexica_co_core_py.ipynb).
8. [06: matriz híbrida](notebooks/pipeline/06_ingenieria_features_hibridas.ipynb).
9. [07: RF y XGBoost](notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb).
10. [Comparación controlada de backbone](scripts/comparar_backbones_hibrido.py).
11. [08: consolidación de resultados](notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb).
12. [09b: cierre multicriterio histórico en desarrollo](notebooks/pipeline/09b_cierre_modelos_dev.ipynb).
13. [09: errores asociados al cierre histórico](notebooks/analysis/09_analisis_errores_hibrido.ipynb).
14. [10: verificación del recongelado e inferencia final](notebooks/pipeline/10_cierre_final_test_ensamble.ipynb).

Análisis secundarios, fuera de la selección principal:

- [09c: auditoría histórica en desarrollo](notebooks/analysis/09c_auditoria_validacion_secundaria_dev.ipynb), con métricas por paciente y SHAP del híbrido reducido.
- [10 de análisis: materiales para revisión clínica externa](notebooks/analysis/10_validacion_clinica_ips.ipynb), no una validación clínica completada.

`04c` selecciona el mejor Transformer standalone (RoBERTa clínico). La comparación controlada del híbrido retuvo BETO en una variante reducida de 861 variables; el híbrido completo 512 tiene 958. Por eso `06` usa BETO por defecto; `FE_TEXT_BACKBONE=auto` hereda explícitamente la selección standalone. TF-IDF no alimenta ese bloque. El ensamble combina predicciones de ramas independientes, no embeddings concatenados.

## Ejecución y reproducibilidad
Consultar los requisitos antes de regenerar:

```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
```

El orquestador regenera desarrollo; no ejecuta el cierre final de prueba ni garantiza recuperar los artefactos originales. Una reproducción exacta necesita los modelos, checkpoints, extracción LLM, índices y manifiestos conservados. Usar identificadores explícitos para el cierre histórico; `latest` es una comodidad operativa, no una identidad congelada.

Opción por contenedor:

```bash
bash scripts/docker_build.sh
bash scripts/docker_up.sh
CONTAINER_MODE=snapshot bash scripts/docker_up.sh
bash scripts/docker_smoke_test.sh
```

El modo `dev` monta el código local; `snapshot` usa el código de la imagen. Datos, credenciales, checkpoints y descargas externas no quedan preservados automáticamente por Docker.

## Salidas y documentación
`data/` y `reports/` contienen datos y artefactos locales excluidos del repositorio público. No subir textos clínicos, predicciones individuales, credenciales ni informes internos.

- EDA: `reports/eda_audit_20260619/reporte_auditoria_eda.md`, tablas y figuras.
- Desarrollo vigente: `data/outputs/cierre_dev_recongelado_roberta_512_20260606_160946/`.
- Prueba vigente: `data/outputs/cierre_final_test_ensamble_512_20260606_1640/`.
- Reporte consolidado: `python scripts/reportes/generar_reporte_estado_actual.py --verbose`.

El [índice documental](docs/README.md) organiza el frente público. Puntos de entrada: [Metodología](docs/METODOLOGIA.md), [Guía de ejecución](docs/GUIA_EJECUCION.md), [Decisiones](docs/DECISIONES_METODOLOGICAS_CLAVE.md), [Revalidación](docs/REVALIDACION_RESULTADOS_REFERENCIA.md), [Limitaciones](docs/LIMITACIONES.md), [Validación clínica](docs/ESTRATEGIA_VALIDACION.md), [notebooks](notebooks/README.md) y [scripts](scripts/README.md).
