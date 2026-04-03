# Spanish_Psych_Phenotyping_PY: Esquema Clínico Curado

## Propósito de este documento
Este documento explica qué es el submódulo `Spanish_Psych_Phenotyping_PY/`, de dónde viene, qué aporta al pipeline principal y cómo se organiza su esquema clínico curado.

Su objetivo es evitar que el submódulo se lea como una simple carpeta de patrones. En este proyecto funciona como dependencia clínica versionada y como base real de:

- denoising clínico;
- extracción rule-based de fenotipos;
- negación;
- perfiles `co`, `core` y `py`;
- parte de la interpretabilidad del híbrido.

## Qué es el submódulo
`Spanish_Psych_Phenotyping_PY/` es un fork clínico y reproducible basado en el proyecto original `Spanish_Psych_Phenotyping`, citado en el propio submódulo como baseline histórico de Colombia.

En el contexto de este repositorio, el submódulo se usa para pasar de un fenotipado histórico publicado a una arquitectura por capas:

- `Concept_CO`: baseline histórico colombiano;
- `Concept_Core`: núcleo clínico depurado y portable;
- `Concept_PY`: capa de adaptación regional paraguaya.

No es un recurso decorativo ni un backup del paper original. Es la base clínica operativa del proyecto.

## Qué aporta al proyecto principal
El submódulo aporta cuatro cosas centrales.

### 1. Reglas clínicas explícitas
Define patrones `TargetRule` para síntomas, contexto y medicación. Esos patrones alimentan columnas como:

- `rule_*`
- `niega_*`
- `rule_medication_*`

### 2. Soporte al denoising
`03_denoising_reglas_core.ipynb` usa esta capa para decidir qué notas conservan suficiente densidad clínica para la tarea diferencial actual.

### 3. Perfiles comparables
Permite comparar de forma controlada:

- `co`
- `core`
- `py`

sin reescribir el pipeline clínico en cada iteración.

### 4. Auditabilidad
Vuelve trazable qué categorías clínicas estaban activas cuando se congeló una corrida. Por eso el proyecto genera además un freeze léxico separado.

## Cómo se carga técnicamente
La carga principal está implementada en:

- `Spanish_Psych_Phenotyping_PY/cli.py`
- `Spanish_Psych_Phenotyping_PY/escribe/default_nlp.py`

### Componentes base
El pipeline usa:

- `spaCy`
- `medSpaCy`
- `ConText_ES.json`
- `RuSH_ES.tsv`

`default_nlp.py` construye un pipeline base en español y reemplaza:

- segmentación (`medspacy_pyrush`)
- target matcher
- contexto clínico

### Carga por capas
`cli.py` implementa `build_pipeline(profile, ...)` y carga una o más capas definidas en `configs/*_config.yml`.

La lógica es:

- primera capa: resetea el target matcher;
- capas siguientes: se cargan encima sin reset.

Eso permite que `Concept_PY` se aplique como extensión de `Concept_Core` y no como reemplazo.

## Configuración activa
Archivos principales:

- `configs/fenotipos.yml`
- `configs/co_config.yml`
- `configs/core_config.yml`
- `configs/py_config.yml`

### `fenotipos.yml`
Define los folders conceptuales activos para el proyecto:

- `Ansiedad`
- `Depresion`
- `Contexto`

### Perfiles operativos
- `co`: `Concept_CO`
- `core`: `Concept_Core`
- `py`: `Concept_Core + Concept_PY`

## Estructura del recurso clínico
Directorio principal:
- `Spanish_Psych_Phenotyping_PY/escribe/patterns/`

Capas:
- `Concept_CO/`
- `Concept_Core/`
- `Concept_PY/`

Folders clínicos:
- `Ansiedad/`
- `Depresion/`
- `Contexto/`

Cada archivo `.json` representa un conjunto de reglas clínicas. En la mayoría de los casos, la `category` emitida por esas reglas termina convertida en columnas `rule_<categoria>`; en algunos bloques de contexto, el detalle adicional puede quedar en `literal` o en categorías auxiliares específicas según la capa activa.

## Esquema clínico curado por capa

### `Concept_CO`
Es el baseline histórico del proyecto original colombiano.

En el snapshot actual contiene:
- `Ansiedad`: `18` archivos JSON
- `Depresion`: `33` archivos JSON
- `Contexto`: no aparece como carpeta versionada en el árbol actual

Rol metodológico:
- baseline histórico para comparación;
- no es la capa operativa principal del híbrido vigente.

### `Concept_Core`
Es el núcleo clínico depurado que el proyecto toma como base portable.

En el snapshot actual contiene:
- `Ansiedad`: `18` archivos JSON
- `Depresion`: `34` archivos JSON
- `Contexto`: `3` archivos JSON

Rol metodológico:
- corregir y estabilizar la capa clínica general;
- separar mejoras técnicas generales de las adaptaciones regionales paraguayas;
- servir como base del perfil `core` y del perfil `py`.

### `Concept_PY`
Es la capa regional paraguaya cargada encima de `Concept_Core`.

En el snapshot actual contiene:
- `Ansiedad`: `8` archivos JSON
- `Depresion`: `13` archivos JSON
- `Contexto`: `2` archivos JSON

Rol metodológico:
- añadir variantes paraguayas, jopará, abreviaturas locales e institucionales;
- ampliar cobertura clínica del core sin redefinir la tarea supervisada principal;
- poder introducir también categorías auxiliares de contexto regional como `Alcohol` o `UsoSustancias`;
- mejorar cobertura sin cambiar los labels finales `ansiedad` y `depresion`.

## Qué define cada fenotipo en la práctica
El submódulo no define los fenotipos como una única tabla plana. Los define como archivos JSON agrupados por carpeta clínica. Cada archivo aporta reglas para una categoría canónica concreta.

### Ansiedad (`Concept_Core/Ansiedad`)
IDs canónicos activos en el snapshot actual:

- `Agitacinpsicomotora`
- `AngustiaMiedoTemor`
- `Ansiedad`
- `Bajaconcentracin`
- `Compulsiones`
- `DespersonalizacinDesrealizacin`
- `Fatiga`
- `Ideacinpersecutoria`
- `Irritabilidad`
- `Obsesiones`
- `Paranoia`
- `Pnico`
- `Sntomasansiososgenerales`
- `SntomassomticosEjemplos`
- `SueoAlterado`
- `SueoInsomnio`
- `SueoPesadillas`
- `medication_anxiety`

Interpretación:
- cubre ansiedad general, pánico, somatización, insomnio, disociación, obsesividad y ciertos fenómenos limítrofes de activación o ideación persecutoria;
- `medication_anxiety` representa evidencia farmacológica separada, no señal diagnóstica fusionada.

### Depresión (`Concept_Core/Depresion`)
IDs canónicos activos en el snapshot actual:

- `Abulia`
- `Anhedonia`
- `Animodeprimido`
- `Apata`
- `Apetitoaumentode`
- `Apetitodisminucinde`
- `Autolesin`
- `Bajaconcentracin`
- `Bajaenerga`
- `Culpa`
- `Desesperanza`
- `Disforia`
- `Fatiga`
- `Hipotimia`
- `Ideacinsuicida`
- `Ideasdemuerte`
- `Intentosuicida`
- `Irritabilidad`
- `Labilidademocional`
- `Llantofcil`
- `Minusvala`
- `PesoIncremento`
- `PesoPrdida`
- `Prospeccindesesperanzada`
- `RetraimientosocialAislamiento`
- `Retrasopsicomotor`
- `Rumiacin`
- `Sntomasdepresivosgenerales`
- `Soledad`
- `SueoAlterado`
- `SueoDespertartemprano`
- `SueoHipersomnio`
- `SueoInsomnio`
- `medication_depression`

Interpretación:
- cubre ánimo deprimido, anhedonia, culpa, desesperanza, rumiación, enlentecimiento, aislamiento y suicidabilidad;
- `medication_depression` vuelve a marcar un espacio terapéutico separado.

### Contexto (`Concept_Core/Contexto`)
IDs activos en el snapshot actual:

- `Agresividad`
- `Alcohol`
- `Usodesustancias`

Interpretación:
- no son target principal del clasificador binario;
- funcionan como contexto clínico auxiliar y como posible fuente de confusión o enriquecimiento semántico.

## Qué agrega específicamente `Concept_PY`
`Concept_PY` no crea un nuevo sistema de categorías. Reutiliza categorías canónicas del core y les añade variantes lingüísticas paraguayas.

### Ejemplos de aportes visibles
Según `lexicon_manifest.csv`, la capa paraguaya añade variantes como:

- `Ndavy'ái`
- `Vy'a'ỹ`
- `Tekorei`
- `Kaigue`
- `No da gusto`
- `No se halla`
- `Ataque de nervios`
- `Macoña`
- `OH`, `OH+`
- `SPA`

Y las mapea a categorías ya existentes, por ejemplo:

- `Animodeprimido`
- `Anhedonia`
- `Abulia`
- `Fatiga`
- `Rumiacin`
- `SntomassomticosEjemplos`
- `Pnico`
- `Alcohol`
- `UsoSustancias`

Esto es importante: la adaptación paraguaya no rompe el espacio de salida. Aumenta cobertura manteniendo auditabilidad.

## Qué relación tiene con medicación
Los archivos:

- `medication_anxiety.json`
- `medication_depression.json`

viven dentro del recurso clínico, pero el pipeline principal no los fusiona como diagnóstico vía LLM. En `06` se preservan como:

- `rule_medication_*`

Su rol es:
- evidencia terapéutica;
- señal útil para ablación;
- fuente potencial de riesgo metodológico si el cierre depende demasiado de ellas.

## Qué relación tiene con negación
El submódulo no solo detecta categorías. También, junto con `ConText_ES.json` y la lógica del proyecto principal, permite distinguir entidades negadas o matizadas por el contexto clínico.

Eso alimenta columnas como:
- `niega_*`
- `feat_niega_*`

Y es una razón central por la cual el recurso no debe leerse como un simple diccionario plano.

## Cómo se integra al pipeline principal

### En `03`
Se usa para:
- apoyar denoising clínico;
- definir qué notas tienen señal suficiente para seguir en el problema modelado.

### En `05`
Se usa para:
- justificar la comparación entre `Concept_CO`, `Concept_Core` y `Concept_PY`.

### En `06`
Se usa para:
- construir `rule_*`;
- construir `niega_*`;
- servir de base para `feat_*` tras `late fusion` con LLM.

### En `07`, barrido y cierre
Se usa indirectamente porque:
- toda la matriz híbrida depende de esas categorías;
- la parsimonia, auditabilidad y freeze final dependen del recurso clínico efectivamente cargado.

## Qué no hace el submódulo por sí solo
No hace estas cosas de manera autónoma:

- no entrena el clasificador híbrido;
- no decide el mejor backbone contextual;
- no decide el mejor híbrido final;
- no resuelve el cierre en `dev`;
- no reemplaza el denoising, la ablación o la rúbrica de cierre.

Su rol es clínico-estructural: define la base de extracción y la ontología operativa sobre la que luego trabajan `06`, `07`, el barrido y `09b`.

## Lectura correcta dentro del proyecto
La forma correcta de leer `Spanish_Psych_Phenotyping_PY/` dentro de este repositorio es:

- baseline clínico histórico (`Concept_CO`);
- núcleo clínico depurado (`Concept_Core`);
- adaptación regional paraguaya (`Concept_PY`);
- esquema clínico curado que soporta denoising, extracción, negación, perfiles y trazabilidad.

No es una carpeta auxiliar. Es la dependencia clínica principal del pipeline.
