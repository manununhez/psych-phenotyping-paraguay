# Revalidación: resultados y procedencia

## Qué se reproduce
Se distingue **reproducción de inferencia congelada** de **regeneración con nuevos entrenamientos**. La primera usa los artefactos originales; la segunda produce una nueva corrida y puede cambiar resultados o selección. Mantener código y seeds no obliga a recuperar el mismo ranking.

Estos valores describen el cierre reproducible del 6 de junio de 2026 y sus comparadores posteriores, sin alterar cifras, pesos ni particiones.

## Corpus de referencia
| Universo | Pacientes | Notas | Ansiedad | Depresión |
|---|---:|---:|---:|---:|
| Base limpia | 90 | 3143 | 925 | 2218 |
| Denoised | 90 | 1835 | 556 | 1279 |
| Entrenamiento denoised | 54 | 1107 | 358 | 749 |
| Validación denoised | 18 | 343 | 100 | 243 |
| Prueba denoised | 18 | 385 | 98 | 287 |

El original contiene 3155 notas de 90 pacientes. La retención frente a la base limpia es 58.38%. Los conjuntos previos al filtro tienen 1911, 595 y 637 notas. La pertenencia de pacientes se fija antes del filtro y no debe modificarse para obtener otras distribuciones.

## Comparación vigente
Macro-F1 a nivel nota, sobre 343 notas de desarrollo y 385 de prueba:

| Configuración | Desarrollo | Prueba | Procedencia |
|---|---:|---:|---|
| Ensamble 512, pesos 0.65/0.15/0.20 | 0.757017 | 0.555807 | Cierre congelado |
| RoBERTa clínico 512 aislado | 0.747232 | 0.540702 | Rama contextual del cierre |
| TF-IDF + LinearSVC | 0.740564 | 0.584478 | Reproducción posterior, ajuste solo en entrenamiento |
| Híbrido completo PY XGBoost 512 | 0.723387 | 0.506520 | Inferencia posterior del modelo conservado |
| Random Forest Core + PY, sin LLM | 0.632684 | 0.545550 | Rama local del cierre |
| Random Forest Core + LLM | 0.640838 | 0.581889 | Rama Core/LLM del cierre |

El ensamble fue el mejor valor en desarrollo; TF-IDF fue el mejor valor puntual en prueba. Las ramas aisladas comparan desempeño, no aporte causal ni ganancia específica de PY. No hay una prueba pareada de superioridad estadística.

La corrida final del ensamble fue `predict-only`. TF-IDF y el híbrido se compararon posteriormente, sin selección con prueba. No todas las cifras de esta tabla salieron de la ejecución final del notebook `10`.

## Resultado final del ensamble
| Métrica | Desarrollo | Prueba |
|---|---:|---:|
| Macro-F1 | 0.757017 | 0.555807 |
| Balanced accuracy | 0.765638 | 0.553883 |
| Weighted-F1 | 0.796002 | 0.671349 |
| F1 ansiedad | 0.663507 | 0.320442 |
| F1 depresión | 0.850526 | 0.791171 |

Matriz de confusión final; filas = referencia, columnas = predicción:

| Referencia | Ansiedad predicha | Depresión predicha |
|---|---:|---:|
| Ansiedad | 29 | 69 |
| Depresión | 54 | 233 |

Son 262 aciertos y 123 errores. La recuperación de ansiedad es 29/98 (29.59%); la de depresión, 233/287 (81.18%). Accuracy 68.05% no resume esta asimetría. El bootstrap de 1000 remuestreos por paciente, semilla 42, da un intervalo percentil del 95% de Macro-F1 aproximado `[0.453942, 0.661296]`. Es incertidumbre del ensamble sobre 18 pacientes, no de la diferencia frente a TF-IDF o RoBERTa.

## Referencias históricas separadas
| Experimento | Macro-F1 en desarrollo | Alcance |
|---|---:|---|
| Dummy estratificado | 0.494237 | Referencia trivial |
| Backbone BETO en híbrido reducido | 0.728894 | Comparación controlada, 861 variables |
| Backbone RoBERTa clínico en híbrido reducido | 0.724315 | Misma variante de 861 variables |
| Ensamble de mayo, pesos 0.80/0.10/0.10 | 0.749250 | Checkpoint contextual exacto no recuperado |

El híbrido reducido y el completo 512 de 958 variables no son el mismo modelo. Las métricas por paciente y SHAP históricos de `09c` no se trasladan al comparador completo ni al ensamble. `09b` conserva la rúbrica y shortlist históricas; los pesos vigentes provienen de 231 ternas evaluadas en desarrollo durante el recongelado.

## Fuentes de las cifras
Los artefactos locales no se publican con el repositorio:

- Desarrollo: `data/outputs/cierre_dev_recongelado_roberta_512_20260606_160946/`, con `manifest.json` y `metricas_globales_por_rama_dev.csv`.
- Prueba: `data/outputs/cierre_final_test_ensamble_512_20260606_1640/`, con `manifest.json`, `metricas_test.csv` y `metricas_globales_por_rama_test.csv`.
- Comparadores posteriores: `reports/qa_numerica_anteproyecto_20260728/dev_test_comparators.csv`, con procedencia por fila. TF-IDF y XGBoost remiten a `reports/pipeline_audit_20260622/tables/dev_test_comparators.csv`.
- Híbrido completo: features `fe_20260512_161646` y entrenamiento `train_20260512_165340`.
- Backbone controlado: manifiesto de la corrida referida por `data/outputs/comparacion_backbones_hibrido_latest.json`; verificar identidad antes de comparar.
- EDA: `reports/eda_audit_20260619/reporte_auditoria_eda.md`, tablas, figuras y `execution_manifest.json`, generados en `01`.

La fecha del nombre de carpeta no basta para fechar la ejecución: consultar el manifiesto. `latest` facilita operación corriente, pero no sustituye identificadores y hashes de una referencia congelada.

## Material para reproducción exacta
Conservar commits del repositorio y submódulo, entorno, corpus e índices, snapshot de reglas, extracción LLM conservada, columnas, tokenizer, checkpoints, modelos, pesos y predicciones de referencia. Verificar integridad y compatibilidad.

No basta con `ips_raw.csv`. Una nueva llamada LLM genera otro artefacto; otro entrenamiento puede cambiar probabilidades o selección. No se debe sobrescribir evidencia ni presentar una nueva corrida como recuperación exacta de un checkpoint ausente.

## Verificación operativa
1. Comprobar conteos, etiquetas, índices y separación de pacientes.
2. Verificar identidad de reglas, extracción, columnas, modelos y tokenizer con los manifiestos.
3. Usar rutas explícitas del cierre, no resolver sin control otra corrida mediante `latest`.
4. Ejecutar `10` en modo `dev`, en carpeta nueva, y comparar `row_id`, clases, probabilidades y predicciones. La tolerancia contextual predeterminada es `1e-5`; diferencias aceptables en probabilidades no autorizan cambios silenciosos de etiquetas predichas.
5. Comparar métricas recalculadas desde predicciones congeladas, distinguiendo redondeo de diferencias reales.
6. Mantener prueba fuera de selección y documentar por separado las auditorías posteriores.

La [Guía de ejecución](GUIA_EJECUCION.md) describe requisitos del EDA, regeneración ordinaria y comprobación en desarrollo sin sobrescribir el cierre.
