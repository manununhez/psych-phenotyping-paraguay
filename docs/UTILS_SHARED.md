# `notebooks/utils_shared.py`: utilidades compartidas, contratos y reglas transversales

## Propósito de este documento

Este documento explica qué contiene `notebooks/utils_shared.py`, por qué existe y qué lógica del proyecto depende de ese módulo.

El objetivo es evitar una lectura equivocada del archivo como si fuera solo una colección de helpers menores. En realidad mezcla tres capas distintas:

- utilidades técnicas de notebook;
- resolución operativa de artefactos versionados;
- reglas metodológicas transversales de filtrado clínico.

## Por qué existe

El pipeline usa notebooks como interfaz principal, pero necesita compartir funciones estables sin duplicarlas entre `pipeline/` y `analysis/`. `utils_shared.py` centraliza ese contrato común.

Sin este módulo, el riesgo real sería:

- duplicar lógica entre notebooks;
- resolver corridas por orden alfabético y no por validez real;
- introducir versiones inconsistentes del filtro clínico;
- producir resultados distintos según qué notebook copie qué helper.

## Qué tipos de lógica contiene

## 1. Helpers puros de notebook

Funciones de conveniencia que pueden quedarse en `utils_shared.py` sin problema:

- `setup_paths()`
- `guess_text_col()`
- `guess_label_col()`
- `guess_patient_id_col()`
- `normalize_label()`
- `validate_splits_exist()`
- `validate_dataset_columns()`
- `validate_file_exists()`
- `ensure_dir()`
- `load_splits()`
- `get_cv_splitter()`
- `calculate_metrics()`
- `plot_confusion_matrix()`
- `make_run_id()`
- `get_output_dir()`
- `save_json()`

Estas funciones no contienen decisiones metodológicas sensibles. Son infraestructura local para ejecutar notebooks con menos duplicación.

## 2. Contratos operativos del pipeline

Aquí vive lógica importante de reproducibilidad. No es solo helper cosmético.

Funciones clave:

- `latest_feature_base()`
- `resolve_feature_run_ids()`
- `latest_train_run()`
- `extract_feature_base_from_train_dir()`
- `latest_matching_barrido()`
- `latest_freeze_dir()`

### Qué resuelven

Estas funciones definen cómo el pipeline encuentra artefactos válidos cuando hay múltiples corridas coexistiendo.

Ejemplos:

- una corrida de `06` solo es válida si existe el par completo:
  - `<base>_core`
  - `<base>_py`
- una corrida de `07` no debe elegirse por orden alfabético, sino por corridas completas y usables;
- un barrido solo debe reutilizarse si coincide con:
  - `ref_train_run`
  - y/o `feature_run_base`.

### Por qué esto es importante

El proyecto ya tuvo una desalineación real cuando `07` resolvía corridas de features por orden alfabético de nombres y no por una corrida completa reciente. Esa clase de error no cambia el código del modelo, pero sí puede cambiar el cierre metodológico.

Por eso esta lógica:

- sí debe estar documentada;
- sí debe tratarse como contrato del pipeline;
- no debe duplicarse ad hoc en cada notebook.

## 3. Reglas metodológicas transversales

La parte más sensible del archivo está al final:

- `is_patient_negation()`
- `keep_entity()`

Estas funciones no son utilidades neutras. Implementan política clínica de extracción.

## Filtro de aseveración clínica

`keep_entity()` define cuándo una entidad detectada por reglas cuenta como evidencia clínica válida.

Política vigente:

1. descartar menciones en contexto:
   - histórico;
   - hipotético;
   - familiar.
2. si la entidad no está negada:
   - conservar.
3. si está negada:
   - conservar solo si la negación se atribuye al paciente;
   - descartar si la negación parece provenir del médico o de una plantilla administrativa.

`is_patient_negation()` implementa esa detección con un patrón lingüístico explícito sobre la ventana izquierda de la entidad.

## Dónde impacta esto

Este filtro afecta directamente:

- `03_denoising_reglas_core.ipynb`
- `05_brecha_lexica_co_core_py.ipynb`
- `06_ingenieria_features_hibridas.ipynb`

Por eso debe leerse como regla metodológica compartida, no como helper decorativo.

## Debe extraerse a un script aparte

La recomendación actual es:

- no extraer todo `utils_shared.py` a scripts separados;
- mantenerlo como módulo compartido de notebooks;
- documentar explícitamente qué partes son contrato operativo y qué partes son política metodológica.

### Razón

Extraer todos los helpers a scripts o CLIs no mejoraría la claridad. Haría el flujo más fragmentado sin aportar evidencia nueva. El problema no es la ubicación del código, sino que su rol quede explícito.

## Cuándo sí convendría extraer lógica

Solo si aparece alguno de estos casos:

1. la misma lógica empieza a ser consumida fuera de notebooks y fuera de scripts ya existentes;
2. se vuelve necesario testear de forma aislada la resolución de artefactos;
3. el filtro clínico necesita evolución independiente, con validación propia.

En ese caso, el candidato natural a extraer sería la capa de resolución de artefactos versionados, no todo el archivo.

## Qué no debería entrar en `utils_shared.py`

No conviene agregar allí:

- lógica ad hoc de un notebook concreto;
- reglas experimentales de una sola corrida;
- decisiones de cierre formal;
- transformaciones que produzcan artefactos canónicos por sí solas;
- análisis narrativo o visualización demasiado específica.

## Resumen práctico

`utils_shared.py` puede quedarse donde está si se respetan tres condiciones:

1. documentar qué contiene;
2. no esconder decisiones metodológicas nuevas allí sin trazabilidad;
3. mantener separadas las decisiones de cierre formal, que deben vivir en notebooks o scripts explícitos del pipeline.

En el estado actual del proyecto, esa estrategia es suficiente y más clara que fragmentarlo artificialmente.
