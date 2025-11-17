# Notebooks

Notebooks reproducibles para el proyecto de fenotipado psicológico en Paraguay.

---

## Orden de Ejecución

Los notebooks deben ejecutarse en este orden específico:

```
00_setup.ipynb
 ↓
01_eda_understanding.ipynb
 ↓
02_create_splits.ipynb
 ↓

 
02_baseline_ 02_baseline_ 02_baseline_
rule_based.ipynb tfidf.ipynb transformer_beto.ipynb
 

 ↓
02_comparacion_resultados.ipynb
 ↓
03_preparacion_validacion_psiquiatras.ipynb
```

---

## Descripción de Notebooks

### `00_setup.ipynb` - Configuración Inicial

**Propósito**: Validar que el entorno está correctamente configurado.

**Qué hace**:
- [OK] Detecta entorno (Local vs Google Colab)
- [OK] Configura paths usando `utils_shared.py`
- [OK] Verifica estructura de carpetas
- [OK] Valida dependencias instaladas
- [OK] Verifica archivos de datos
- [OK] Muestra próximos pasos

**Cuándo ejecutar**:
- Primera vez que clonas el repositorio
- Después de cambios en la estructura
- Para verificar que todo está bien instalado

**Salida**: Ninguna (solo validación y mensajes)

**Tiempo estimado**: < 1 minuto

---

### `01_eda_understanding.ipynb` - EDA, Limpieza y Calidad

**Propósito**: Análisis exploratorio, limpieza y análisis de calidad de datos.

**Qué hace**:
- **Análisis Exploratorio:**
  - Carga `ips_raw.csv`
  - Distribución de clases, longitud de textos
  - Análisis de ruido (mayúsculas, puntuación, espacios)
  - Análisis de n-gramas (unigrams, bigrams, trigrams)
- **Limpieza LIGERA:**
  - Normaliza etiquetas (`Depresivo` → `depresion`)
  - Colapsa alargamientos (`holaaa` → `holaa`)
  - Normaliza espacios
  - **Preserva** tildes, mayúsculas, puntuación
- **Análisis de Calidad (Sección 4):**
  - Textos cortos (<200 chars)
  - Detección de repeticiones anómalas
  - Visualización de distribución de longitudes
  - Resumen por paciente
  - Flags de calidad: `es_texto_corto`, `es_muy_corto`, `es_repeticion`
- Exporta `ips_clean.csv` con flags de calidad
- Genera CSVs de análisis (n-gramas, estadísticas)

**Entrada**: `data/ips_raw.csv`

**Salida**: 
- `data/ips_clean.csv` (con flags de calidad)
- `data/eda_*.csv` (análisis)
- `data/figs/calidad_distribucion_longitudes.png`

**Tiempo estimado**: 3-7 minutos

**Decisión clave**: Limpieza conservadora + flags de calidad para análisis posterior.

---

### `02_create_splits.ipynb` - Splits Unificados

**Propósito**: Crear splits train/dev/test reproducibles para todos los baselines con split metodológico 60/20/20.

**Qué hace**:
- Carga `ips_clean.csv`
- Split estratificado 60/20/20 a nivel de **paciente** (zero leakage):
 - Train: 1,849 casos (54 pacientes) - Para entrenamiento
 - Dev: 641 casos (18 pacientes) - Para validación single (contexto)
 - Test: 637 casos (18 pacientes) - Para evaluación final ciega
 - Estratificación por clase mayoritaria del paciente
 - Seed fijo: 42 (reproducibilidad)
- Exporta 3 archivos:
 - `splits/train_indices.csv`: Índices de entrenamiento
 - `splits/dev_indices.csv`: Índices de desarrollo
 - `splits/test_indices.csv`: Índices de test (reservado)

**Entrada**: `data/ips_clean.csv`

**Salida**: `data/splits/*.csv`

**Tiempo estimado**: < 1 minuto

**Decisión clave**: 
- Split 60/20/20 permite **Cross-Validation 5-fold** en Train+Dev combinados (métrica principal)
- Dev set independiente permite validar consistencia (dev ∈ IC95% de CV?)
- Test ciego se reserva para evaluación final
- Split patient-level elimina 100% de leakage entre conjuntos

---

### `02_baseline_rule_based.ipynb` - Baseline con Patrones

**Propósito**: Baseline rule-based usando el fork colombiano.

**Estrategia**: Patrones JSON + ConText para negación

**Preprocesamiento**: LIGERO
- [OK] Preserva tildes y mayúsculas (los patrones los necesitan)
- [OK] Colapsa alargamientos
- [X] NO lowercase
- [X] NO elimina puntuación

**Qué hace**:
- Carga splits desde `data/splits/`
- Configura fork colombiano (solo Ansiedad/Depresión)
- Ejecuta pipeline de patrones
- Evalúa en val set
- Exporta resultados:
 - `data/rule_based_predictions.csv`
 - `data/rule_based_eval.csv`
 - `data/rule_based_classification_report.csv`
 - `data/rule_based_confusion_matrix.csv`

**Entrada**: `data/splits/*.csv` + `Spanish_Psych_Phenotyping_PY/`

**Salida**: `data/rule_based_*.csv`

**Tiempo estimado**: 5-10 minutos

**Pros**: Interpretable, rápido, no requiere entrenamiento 
**Contras**: Requiere fork y mantenimiento manual de patrones

---

### `02_baseline_tfidf.ipynb` - Baseline con Char TF-IDF

**Propósito**: Baseline clásico robusto a typos con char n-grams.

**Estrategia**: Char-level TF-IDF (3-5) + LinearSVC con class_weight='balanced'

**Preprocesamiento**: AGRESIVO
- [OK] Lowercase completo
- [OK] Elimina tildes (robustez ante errores)
- [OK] Marca negaciones ("no tengo" → "no_tengo")
- [OK] Elimina símbolos especiales

**Qué hace**:
- Carga splits desde `data/splits/`
- Aplica preprocesamiento agresivo
- Extrae char n-grams (3-5)
- Entrena LinearSVC con class_weight='balanced'
- Evalúa en val set
- Exporta resultados:
 - `data/tfidf_predictions.csv`
 - `data/tfidf_eval.csv`
 - `data/tfidf_classification_report.csv`
 - `data/tfidf_confusion_matrix.csv`

**Entrada**: `data/splits/*.csv`

**Salida**: `data/tfidf_*.csv`

**Tiempo estimado**: 2-3 minutos

**Pros**: Robusto a typos ("deprecion" ≈ "depresion"), rápido, no requiere GPU 
**Contras**: No captura semántica compleja

---

### `02_baseline_transformer_beto.ipynb` - Baseline con BETO

**Propósito**: Baseline state-of-the-art con transformer en español.

**Estrategia**: Fine-tuning de BETO-base (dccuchile/bert-base-spanish-wwm-cased)

**Preprocesamiento**: CONSERVADOR
- [OK] Preserva tildes, mayúsculas, puntuación
- [OK] Solo colapsa alargamientos
- [X] NO lowercase (el modelo lo maneja)
- [X] NO marca negaciones (BETO las capta)

**Qué hace**:
- Carga splits desde `data/splits/`
- Aplica preprocesamiento conservador
- Carga BETO desde HuggingFace
- Fine-tuning (3 epochs, lr=2e-5)
- Evalúa en val set
- Exporta resultados:
 - `data/beto_predictions.csv`
 - `data/beto_eval.csv`
 - `data/beto_classification_report.csv`
 - `data/beto_confusion_matrix.csv`

**Entrada**: `data/splits/*.csv`

**Salida**: `data/beto_*.csv` + checkpoints en `data/beto_ckpt/`

**Tiempo estimado**: 
- Con GPU: 5-10 minutos
- Sin GPU: 30-60 minutos

**Pros**: Captura contexto y semántica, state-of-the-art 
**Contras**: Requiere GPU, más lento, más pesado

---

### `02_comparacion_resultados.ipynb` - Comparación de Baselines

**Propósito**: Comparar los 3 baselines con Cross-Validation 5-fold, visualizaciones y análisis de significancia.

**Qué hace**:
- **Sección 1-3:** Dummy baselines (stratified, majority) para validar calidad
- **Sección 4:** Carga resultados single dev de los 3 modelos principales
- **Sección 5:** Cross-Validation 5-fold patient-level stratified en Train+Dev:
  - Combina train + dev (2,490 casos, 72 pacientes)
  - 5 folds patient-level, ~2,501 train / ~625 test por fold
  - Calcula F1 Macro mean ± std
  - IC95% bootstrapped (10,000 iteraciones)
- **Sección 6-7:** Análisis de consistencia dev vs CV:
  - Verifica si single dev cae dentro IC95% de CV
  - Análisis de significancia estadística (IC95% solapan?)
  - Análisis de varianza (CV%)
- **Sección 8-9:** Visualizaciones y tabla consolidada:
  - Gráficos comparativos CV vs single dev
  - Tabla resumen con IC95% y significancia
- **Sección 10:** Exporta resultados:
  - `data/02_baselines_comparacion_cv.csv` (tabla consolidada CV)
  - `data/cv_results/*.csv` (resultados por fold de cada modelo)

**Entrada**: 
- `data/{rule_based,tfidf,beto}_*.csv` (single dev)
- `data/splits/*.csv` (para CV)

**Salida**: 
- `data/02_baselines_comparacion_cv.csv` (métrica principal)
- `data/cv_results/*.csv` (detalles CV por modelo)
- Visualizaciones en notebook

**Tiempo estimado**: 5-10 minutos (por re-entrenamiento en CV)

**Nota**: 
- Requiere que los 3 baselines hayan sido ejecutados en single dev
- CV es la **métrica principal para paper/tesis**
- Single dev es contexto adicional para validar consistencia

---

## `utils_shared.py` - Utilidades Compartidas

**Propósito**: Módulo con funciones comunes para evitar duplicación.

**Funciones principales**:

### `setup_paths()`
Detecta y configura paths del proyecto automáticamente.
```python
paths = setup_paths()
DATA_PATH = paths['DATA_PATH']
```

### `guess_text_col(df)`
Detecta automáticamente la columna de texto en un DataFrame.
```python
text_col = guess_text_col(df) # → 'texto'
```

### `guess_label_col(df)`
Detecta automáticamente la columna de etiquetas.
```python
label_col = guess_label_col(df) # → 'etiqueta'
```

### `normalize_label(s)`
Normaliza etiquetas a formato estándar.
```python
normalize_label("Depresivo") # → "depresion"
normalize_label("ANSIEDAD") # → "ansiedad"
```

### `validate_splits_exist(splits_path)`
Valida que los splits existen antes de cargarlos.

### `load_splits(splits_path)`
Carga los 3 archivos de splits en un diccionario.
```python
splits = load_splits(SPLITS_PATH)
train_idx = splits['train_indices']
```

**Uso**: Todos los notebooks importan este módulo con fallback:
```python
try:
 from utils_shared import setup_paths, ...
 print("[OK] Utilizando utils_shared.py")
except ImportError:
 print("[WARNING] utils_shared.py no encontrado, usando funciones locales")
 # Funciones de fallback...
```

**Beneficio**: Elimina ~150 líneas de código duplicado.

---

## Estrategias de Preprocesamiento

### Resumen Comparativo:

| Aspecto | Rule-Based | TF-IDF | BETO |
|---------|------------|--------|------|
| **Filosofía** | Conservador | Agresivo | Conservador |
| **Lowercase** | [X] No | [OK] Sí | [X] No |
| **Tildes** | [OK] Preserva | [X] Elimina | [OK] Preserva |
| **Puntuación** | [OK] Preserva | [X] Elimina parcial | [OK] Preserva |
| **Negaciones** | ConText | Marca "no_X" | Aprende solo |
| **Alargamientos** | [OK] Colapsa | [OK] Colapsa | [OK] Colapsa |
| **Justificación** | Patrones lo necesitan | Reduce vocab | Distribución pretraining |

### ¿Por qué diferentes?

**Decisión**: Cada arquitectura beneficia de un preprocesamiento adaptado.

- **Rule-Based**: Necesita texto original para matching de patrones JSON
- **TF-IDF**: Beneficia de normalización agresiva para reducir vocabulario sparse
- **BETO**: Necesita texto similar al pretraining para funcionar óptimamente

**Alternativa rechazada**: Normalización única para todos → perjudica a rule-based y BETO.

---

## Dependencias

Principales librerías utilizadas:

```python
# Core
pandas>=1.5.0
numpy>=1.23.0

# Machine Learning
scikit-learn>=1.2.0
transformers>=4.30.0
torch>=2.0.0

# Visualización
matplotlib>=3.6.0
seaborn>=0.12.0

# Utilidades
pyyaml>=6.0
tqdm>=4.65.0
```

Ver `requirements.txt` completo en raíz del proyecto.

---

## Uso Rápido

### Flujo Completo (desde cero):

```bash
# 1. Validar setup
jupyter notebook 00_setup.ipynb

# 2. EDA y limpieza
jupyter notebook 01_eda_understanding.ipynb

# 3. Crear splits
jupyter notebook 02_create_splits.ipynb

# 4. Entrenar baselines (en paralelo si tienes GPU)
jupyter notebook 02_baseline_rule_based.ipynb
jupyter notebook 02_baseline_tfidf.ipynb
jupyter notebook 02_baseline_transformer_beto.ipynb

# 5. Comparar
jupyter notebook 02_comparacion_resultados.ipynb

# 6. Preparar validación con psiquiatras
jupyter notebook 03_preparacion_validacion_psiquiatras.ipynb
```

### Solo Comparación (si ya tienes splits y predicciones):

```bash
jupyter notebook 02_comparacion_resultados.ipynb
jupyter notebook 03_preparacion_validacion_psiquiatras.ipynb
```

---

## `03_preparacion_validacion_psiquiatras.ipynb` - Validación con Expertos

**Propósito**: Identificar casos problemáticos para validación con profesionales psiquiatras.

**Estado**: ⏳ EN DESARROLLO - Estructura inicial creada

**Alcance:**
- Analizar TODOS los casos conflictivos
- FN para TODAS las clases (ansiedad, depresión, neutral)
- Detectar vocabulario regional paraguayo (español + posible guaraní)
- Identificar casos administrativos, textos cortos, ambiguos

**Qué hace (planificado):**
1. **Setup y Carga:** Predicciones de 3 modelos + dataset con flags de calidad
2. **Análisis Exhaustivo:**
   - Casos donde TODOS los modelos fallan
   - FN_Ansiedad (vocabulario paraguayo)
   - FN_Depresión (clase mayoritaria)
   - FP_Neutral / Casos neutrales (filosofía de etiquetado)
   - Análisis de idioma (guaraní/español)
   - Textos cortos y repeticiones
   - Casos administrativos
3. **Selección Estratégica:** 25 casos representativos para reunión
4. **Generación de Excel:**
   - Hoja 1: Casos_Validacion (25 casos seleccionados)
   - Hoja 2: Instrucciones (cómo completar)
   - Hoja 3: Resumen_Completo (estadísticas + justificación)
5. **Visualizaciones:** Matrices confusión, distribución de errores
6. **Resumen Ejecutivo:** Recomendaciones priorizadas

**Justificaciones incluidas:**
- ✓ Por qué FN_Ansiedad Y FN_Depresión (ambas clases importantes)
- ✓ Por qué casos neutrales (validar filosofía de etiquetado)
- ✓ Por qué análisis de idioma (vocabulario paraguayo/guaraní)

**Entrada**: 
- `data/ips_clean.csv` (con flags de calidad)
- `data/*_predictions.csv` (3 modelos)

**Salida esperada**: 
- `data/analisis/todos_fallan_completo.csv`
- `data/analisis/fn_{clase}_completo.csv` (por cada clase)
- `data/analisis/textos_cortos_completo.csv`
- `data/analisis/casos_administrativos.csv`
- `data/VALIDACION_PSIQUIATRAS_25_CASOS.xlsx` (muestra para reunión)

**Tiempo estimado**: 10-15 minutos (cuando esté completo)

**Parámetros configurables:**
- `N_CASOS_REUNION = 25`
- `UMBRAL_TEXTO_CORTO = 200`
- Distribución de muestra por grupo

**Siguiente paso:** Completar secciones 3-7 del notebook

---

### Solo Comparación (si ya tienes splits):

```bash
jupyter notebook 02_baseline_*.ipynb
jupyter notebook 02_comparacion_resultados.ipynb
```

### Solo Comparación (si ya tienes splits y predicciones):

---

## Troubleshooting

### Error: "ips_raw.csv no encontrado"
**Solución**: Coloca tu dataset en `data/ips_raw.csv`

### Error: "Splits no encontrados"
**Solución**: Ejecuta `02_create_splits.ipynb` primero

### Error: "utils_shared.py no encontrado"
**Solución**: Los notebooks tienen fallback automático, pero verifica que estás en el directorio correcto

### Error: "Spanish_Psych_Phenotyping_PY no encontrado"
**Solución**: Solo necesario para rule-based. Clona el fork:
```bash
git clone https://github.com/clarafrydman/Spanish_Psych_Phenotyping.git Spanish_Psych_Phenotyping_PY
```

### Warning: "CUDA not available"
**Solución**: BETO funcionará pero será más lento. Usa Google Colab con GPU gratis.

---

## Outputs Esperados

### Por Baseline:

Cada baseline genera 4 archivos en `data/`:
- `{baseline}_predictions.csv` (~500 KB)
- `{baseline}_eval.csv` (~1 KB)
- `{baseline}_classification_report.csv` (~1 KB)
- `{baseline}_confusion_matrix.csv` (~1 KB)

### Comparación:

- `data/02_baselines_comparacion.csv`: Tabla resumen (~1 KB)
- Visualizaciones en notebook (no guardadas por defecto)

---

## Para Aprender Más

### Comentarios Extensos en Notebooks:

Cada notebook tiene 50-80 líneas de comentarios explicativos sobre:
- **Por qué** se tomó cada decisión
- **Qué alternativas** se consideraron
- **Cuándo usar** cada enfoque
- **Limitaciones** conocidas

### Documentación de Código:

`utils_shared.py` tiene docstrings completas con ejemplos.

### Referencias:

- **Spanish Psych Phenotyping**: [GitHub](https://github.com/clarafrydman/Spanish_Psych_Phenotyping)
- **BETO**: [HuggingFace](https://huggingface.co/dccuchile/bert-base-spanish-wwm-cased)
- **TF-IDF**: [Scikit-learn docs](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)

---

## Contribuir

Para agregar un nuevo baseline:

1. Crea `02_baseline_tu_modelo.ipynb`
2. Importa `utils_shared.py`
3. Carga splits con `load_splits()`
4. Aplica tu preprocesamiento (documenta el "por qué")
5. Exporta los 4 archivos estándar
6. Actualiza `02_comparacion_resultados.ipynb`

---

**Última actualización**: Noviembre 2025
