# Revalidación: valores de referencia y criterio de comparación

## Propósito
Este documento fija los valores canónicos que deben usarse para comparar una regeneración completa del pipeline contra el estado actualmente documentado del proyecto.

Su objetivo es servir como hoja de control para una revalidación técnica del pipeline público.

## Fuentes canónicas usadas
- `data/outputs/transformer_baseline_selection_latest.json`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/manifest.json`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/tabla_experimentos_dev_cierre.csv`
- `data/outputs/comparacion_backbones_hibrido_latest.json`
- `data/outputs/cierre_modelos_dev_20260401_114409/decision_modelo_final.json`
- `data/outputs/results_20260401_112536/tabla_comparativa_modelos.csv`

## Actualización de cierre dev
El cierre de referencia vigente queda actualizado al ensamble por ramas con `max_length=512`.

La configuración anterior basada en híbrido tabular se conserva como referencia histórica/comparativa. No debe borrarse ni sobrescribirse, pero ya no representa el mejor modelo global en `dev`.

## Advertencia importante antes de limpiar `data/`
Si se conserva **solo** `data/ips_raw.csv`, puede regenerarse el flujo activo del pipeline, pero hay dos matices que conviene fijar desde el inicio.

### Motivo
La regeneración del estado vigente no depende únicamente del corpus bruto. También hay pasos que usan insumos adicionales:
- `data/processed/gemini_extraction.json`: opcional para `06`, pero relevante para variantes del barrido híbrido con `llm1`.
- la validación clínica externa con IPS es una instancia cualitativa ya enviada y no forma parte del rerun técnico estándar.

### Implicación práctica
- Si regenerás `gemini_extraction.json`, las variantes con LLM pueden cambiar aunque el resto del pipeline se mantenga estable.
- Si vaciás `data/` hasta dejar solo `ips_raw.csv`, vas a poder reconstruir el flujo activo `01`-`09`; la revisión clínica externa queda fuera del rerun técnico principal.

## Qué debería coincidir exactamente
Estos valores deberían volver a salir si se ejecuta el pipeline sobre el mismo código, submódulo, insumo base y seeds:

### Corpus y splits
| Elemento | Valor canónico |
|---|---:|
| Registros originales (`ips_raw`) | `3155` |
| Pacientes originales | `90` |
| Registros tras deduplicación (`dataset_base`) | `3143` |
| Pacientes tras deduplicación | `90` |
| `ansiedad` en `dataset_base` | `925` |
| `depresion` en `dataset_base` | `2218` |
| Registros finales modelados (`dataset_denoised`) | `1835` |
| Pacientes finales modelados | `90` |
| `ansiedad` en `dataset_denoised` | `556` |
| `depresion` en `dataset_denoised` | `1279` |
| `train` registros | `1107` |
| `train` pacientes únicos | `54` |
| `train`: `ansiedad` | `358` |
| `train`: `depresion` | `749` |
| `dev` registros | `343` |
| `dev` pacientes únicos | `18` |
| `dev`: `ansiedad` | `100` |
| `dev`: `depresion` | `243` |
| `test` registros | `385` |
| `test` pacientes únicos | `18` |
| `test`: `ansiedad` | `98` |
| `test`: `depresion` | `287` |

### Longitud de texto por split
| Split | Media | Mediana |
|---|---:|---:|
| `dataset_base` | `138.86859688195992` | `65.0` |
| `train` | `226.91237579042456` | `153.0` |
| `dev` | `198.90379008746356` | `126.0` |
| `test` | `209.37142857142857` | `152.0` |

## Resultados de referencia en `dev`

### Baselines
| Modelo | Macro F1 | Precision macro | Recall macro | Accuracy |
|---|---:|---:|---:|---:|
| `DUMMY` | `0.4942373085372092` | `0.4947659374264879` | `0.4945061728395061` | `0.5714285714285714` |
| `TF-IDF` | `0.7405642538385901` | `0.7322895093908448` | `0.767716049382716` | `0.7667638483965015` |
| `BETO` | `0.7350522620828567` | `0.7271533613445378` | `0.7491769547325102` | `0.7696793002915452` |
| `ROBERTA_CLINICAL` | `0.7410776566366946` | `0.7322864594653337` | `0.7638888888888888` | `0.7696793002915452` |
| `ROBERTA_BIOMEDICAL` | `0.722793714143178` | `0.7173617583100342` | `0.7303497942386832` | `0.7638483965014577` |

### Comparación controlada de backbone del híbrido
| Backbone | Modelo | Macro F1 | Balanced accuracy | F1 ansiedad | F1 depresión | n features |
|---|---|---:|---:|---:|---:|---:|
| `beto` | `BETO` | `0.7288943006066821` | `0.7212139917695473` | `0.6063829787234043` | `0.8514056224899599` | `861` |
| `roberta_clinical` | `ROBERTA_CLINICAL` | `0.7243149400405088` | `0.7162139917695474` | `0.5989304812834224` | `0.8496993987975952` | `861` |

### Híbrido final cerrado en `dev`
| Campo | Valor |
|---|---|
| Modelo final vigente | Ensamble weighted soft `ROBERTA_CLINICAL 512 + simbólico py RF + simbólico core RF late fusion LLM` |
| Split | `dev` |
| `n_eval` | `343` |
| `macro_f1_dev` | `0.7492497114274721` |
| `balanced_accuracy_dev` | `0.7700617283950617` |
| `weighted_f1_dev` | `0.7849091992098328` |
| `f1_ansiedad_dev` | `0.663716814159292` |
| `f1_depresion_dev` | `0.8347826086956521` |
| Estado | `nuevo cierre dev recomendado; TEST_VIRGEN` |

### Mejor híbrido tabular alineado a 512
| Campo | Valor |
|---|---|
| Modelo | `Híbrido tabular 512 py XGB` |
| Feature run | `fe_20260512_161646` |
| Train run | `train_20260512_165340` |
| `context_max_length` | `512` |
| `macro_f1_dev` | `0.7233870967741935` |
| `balanced_accuracy_dev` | `0.7170987654320987` |
| `weighted_f1_dev` | `0.7748283645255337` |
| `f1_ansiedad_dev` | `0.600000` |
| `f1_depresion_dev` | `0.846774193548387` |

### Híbrido tabular histórico
| Campo | Valor |
|---|---|
| Modelo histórico | `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication|py|XGB` |
| Lectura | referencia histórica/comparativa, no mejor modelo global vigente |

## Decisiones metodológicas que deberían mantenerse
| Decisión | Valor canónico |
|---|---|
| Baseline fuerte simple | `TF-IDF` |
| Mejor transformer standalone | `ROBERTA_CLINICAL` |
| Mejor backbone del híbrido | `BETO` |
| Mejor híbrido tabular 512 | `py XGB` |
| Mejor modelo global en `dev` | ensamble weighted soft 512 |
| `test` | reservado metodológicamente; auditoría formal `auditoria_test_*.md` pendiente |
| XAI | fuera del cierre técnico actual; integración formal final pendiente |
| Estado de fase | `CIERRE_DEV_ENSAMBLE_512_RECOMENDADO` |
| `transformer` standalone y backbone del híbrido | `NO COINCIDEN` |
| Freeze léxico preliminar | `freeze_lexico_20260401_114408` |
| Split de decisión | `dev` |

## Lista corta que pasa a `test`
Según el cierre vigente, la shortlist metodológica es:
- `TF-IDF`
- `ROBERTA_CLINICAL`
- ensamble weighted soft 512
- híbrido tabular 512 `py XGB` como comparador clínico-tabular

## Qué puede variar sin invalidar la revalidación
### 1. Timestamps y nombres de carpetas
No deben compararse literalmente:
- `data/outputs/train_<timestamp>`
- `data/outputs/results_<timestamp>`
- `data/outputs/cierre_modelos_dev_<timestamp>`
- `data/processed/fe_<timestamp>_*`

### 2. Artefactos LLM si regenerás `gemini_extraction.json`
Si actualizás `data/processed/gemini_extraction.json`, no corresponde exigir identidad exacta en:
- variantes del barrido con `llm1`;
- algunas métricas del híbrido si esas variantes vuelven a influir en el ranking;
- comparaciones finas que dependan de la normalización semántica del LLM.

### 3. Transformers
Aunque se mantengan seeds y datos, una rerun de `04c` puede mostrar pequeñas variaciones numéricas por entorno, librerías o entrenamiento. La expectativa razonable no es identidad decimal perfecta, sino:
- mismo orden metodológico principal;
- misma selección de `ROBERTA_CLINICAL` como mejor transformer standalone;
- misma lectura general del cierre.

## Qué sería una señal de divergencia seria
Debe auditarse si cambia cualquiera de estos puntos:
- `3155 -> 3143 -> 1835`
- `1107 / 343 / 385`
- distribución por clase en `train/dev/test`
- mejor transformer standalone
- mejor backbone del híbrido
- modelo final cerrado en `dev`
- shortlist que pasa a `test`

## Recomendación operativa para la revalidación
### Opción segura
Conservar al menos:
- `data/ips_raw.csv`
- el commit actual del repo
- el commit actual del submódulo

### Si insistís en conservar solo `ips_raw.csv`
Podrás regenerar el flujo activo del pipeline y reconstruir de nuevo los artefactos técnicos principales. Los puntos que quedan fuera de esa lógica son:
- la validación clínica externa ya enviada;
- y cualquier diferencia derivada de volver a generar `gemini_extraction.json`.

En ese escenario, la comparación correcta sería:
- corpus y splits: sí
- baselines y líneas principales de `dev`: sí
- freeze léxico actual: sí
- frente IPS actual: se mantiene como material externo ya cerrado; no es el foco del rerun técnico
- variantes LLM actualizadas con nuevo `gemini_extraction.json`: no necesariamente

## Checklist mínimo de comparación post-rerun
1. Verificar `n` del corpus en cada etapa.
2. Verificar distribución por clase en `dataset_base` y `dataset_denoised`.
3. Verificar `train/dev/test` y pacientes únicos por split.
4. Verificar mejor transformer standalone.
5. Verificar comparación controlada de backbones.
6. Verificar híbrido final cerrado en `dev`.
7. Verificar shortlist para `test`.
8. Verificar que `test` siga sin abrirse.
9. Verificar si el nuevo `gemini_extraction.json` cambió variantes `llm1` y documentarlo explícitamente.
