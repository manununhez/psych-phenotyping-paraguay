# Directorio de Datos

> [WARNING] **IMPORTANTE**: Este directorio NO está versionado en GitHub por privacidad de datos clínicos.

---

## Contenido del Directorio

### Archivos de Entrada (debes proveer)

#### `ips_raw.csv` (REQUERIDO)
- **Descripción**: Dataset original con notas clínicas sin procesar
- **Formato**: CSV con columnas:
 - `Motivo Consulta`: Texto de la nota clínica
 - `Tipo`: Etiqueta (Ansiedad/Depresión/Depresivo)
 - Otras columnas: metadata (fecha, paciente, etc.)
- **Tamaño esperado**: ~3000-5000 registros
- **Fuente**: Sistema IPS o fuente clínica local
- **Privacidad**: NUNCA subir a git (protegido por .gitignore)

**Cómo obtenerlo**:
```bash
# Copiar tu dataset local
cp /path/to/your/ips_raw.csv data/ips_raw.csv
```

---

### Archivos Generados (automáticamente por notebooks)

#### `ips_clean.csv` (generado por `01_eda_understanding.ipynb`)
- **Descripción**: Dataset limpio con preprocesamiento ligero
- **Formato**: CSV con columnas:
 - `id_paciente`: ID único del paciente
 - `fecha`: Fecha de la consulta
 - `texto`: Texto limpio (colapso de alargamientos, normalización de espacios)
 - `etiqueta`: Etiqueta normalizada (`ansiedad` o `depresion`)
- **Preprocesamiento aplicado**:
 - ✅ Normalización Unicode (NFC)
 - ✅ Normalización de etiquetas (`Depresivo` → `depresion`)
 - ✅ Colapso de alargamientos (`holaaa` → `holaa`)
 - ✅ Normalización de espacios
 - ✅ **NUEVO**: Remoción de oraciones duplicadas DENTRO de cada texto
 - ✅ Eliminación de textos duplicados completos
 - ❌ NO lowercase (preserva tildes y mayúsculas)
 - ❌ NO elimina puntuación
- **Tamaño**: ~3125 registros únicos (después de deduplicación)
- **Uso**: Entrada para `02_create_splits.ipynb` y TODOS los baselines
- **⚠️ IMPORTANTE**: Si modificas la limpieza en `01_eda_understanding.ipynb`, 
  debes RE-EJECUTAR todos los notebooks de baselines para mantener comparabilidad

---

#### `splits/` (generado por `02_create_splits.ipynb`)

Directorio con splits unificados para todos los baselines, con estrategia metodológica 60/20/20:

##### **Estrategia de Split 60/20/20 + Cross-Validation**

Split a nivel de **paciente** (no de casos) para eliminar data leakage:

| Conjunto | Casos | Pacientes | Propósito |
|----------|-------|-----------|-----------|
| **Train** | 1,849 (59.1%) | 54 | Entrenamiento modelos |
| **Dev** | 641 (20.5%) | 18 | Validación single (contexto adicional) |
| **Test** | 637 (20.4%) | 18 | Evaluación final ciega (reservado) |
| **CV 5-Fold** | 2,490 (79.6%) | 72 | **Métrica principal** (Train+Dev combinados) |

**Características del split:**
- ✅ **Zero leakage**: Un paciente solo aparece en UN conjunto (train, dev o test)
- ✅ **Estratificado**: Por clase mayoritaria del paciente
- ✅ **Reproducible**: Seed fijo 42
- ✅ **CV patient-level stratified**: 5 folds en Train+Dev combinados

**Estrategia de evaluación:**
1. **Cross-Validation 5-fold** (PRINCIPAL):
   - Usa Train+Dev combinados (2,490 casos, 72 pacientes)
   - Patient-level stratified, ~2,501 train / ~625 test por fold
   - Cada paciente evaluado exactamente 1 vez
   - IC95% bootstrapped (10,000 iteraciones) para significancia estadística
   - **Métrica para paper/tesis:** F1 Macro (CV) ± std con IC95%

2. **Single dev evaluation** (CONTEXTO):
   - Validación en dev set (641 casos, 18 pacientes)
   - Útil para comparar consistencia con CV
   - Si dev ∈ IC95% de CV → split representativo ✅

3. **Test set hold-out** (RESERVADO):
   - Evaluación final ciega (637 casos, 18 pacientes)
   - Solo usar para evaluación final de mejor modelo
   - NO tocar hasta evaluación final

**Justificación metodológica:**
- **CV 5-fold es estándar** para datasets pequeños (maximiza uso de datos)
- El **dev set** permite validar consistencia (todos los modelos caen dentro IC95%)
- El **test set** se reserva ciego para evaluación final contra baselines
- Split patient-level evita que textos del mismo paciente aparezcan en train y dev/test
- **IC95% de CV** cuantifica incertidumbre real del modelo (critical para paper/tesis)

##### `splits/train_indices.csv`
- **Descripción**: Índices (row_id) del conjunto de entrenamiento
- **Formato**: CSV con una columna `row_id`
- **Tamaño**: 1,863 índices (60%)
- **Uso**: Entrenar modelos ML y explorar vocabulario para Concept_PY

##### `splits/dev_indices.csv`
- **Descripción**: Índices (row_id) del conjunto de desarrollo/validación
- **Formato**: CSV con una columna `row_id`
- **Tamaño**: 646 índices (20%)
- **Uso**: Validación iterativa durante desarrollo de Concept_PY, ajuste de hiperparámetros

##### `splits/test_indices.csv`
- **Descripción**: Índices (row_id) del conjunto de test (reservado)
- **Formato**: CSV con una columna `row_id`
- **Tamaño**: 646 índices (20%)
- **Uso**: Evaluación final ciega de Concept_PY vs baselines (NO USAR hasta evaluación final)

**¿Por qué separar dataset e índices?**
- [OK] Permite que cada baseline aplique su propio preprocesamiento
- [OK] Un único dataset maestro garantiza consistencia
- [OK] Índices ligeros (solo IDs) facilitan reproducibilidad

---

#### Archivos de Resultados (generados por `02_baseline_*.ipynb`)

Cada baseline genera 4 archivos:

##### `{baseline}_predictions.csv`
- **Contenido**: Predicciones por ejemplo
- **Columnas**: `row_id`, `texto`, `true_label`, `pred_label`
- **Uso**: Análisis de errores

##### `{baseline}_eval.csv`
- **Contenido**: Métricas macro agregadas
- **Columnas**: `macro_f1`, `macro_precision`, `macro_recall`, `n`
- **Uso**: Comparación rápida entre baselines

##### `{baseline}_classification_report.csv`
- **Contenido**: Reporte detallado por clase
- **Columnas**: `precision`, `recall`, `f1-score`, `support` por clase
- **Uso**: Análisis por clase (Depresión vs Ansiedad)

##### `{baseline}_confusion_matrix.csv`
- **Contenido**: Matriz de confusión
- **Formato**: Filas = true, Columnas = pred
- **Uso**: Visualización de errores

**Baselines que generan estos archivos**:
- `rule_based_*.csv`
- `tfidf_*.csv`
- `beto_*.csv`

---

#### Archivos de EDA (generados por `01_eda_understanding.ipynb`)

##### Análisis de n-gramas:
- `eda_top_unigrams.csv`: Top 20 palabras más frecuentes
- `eda_top_bigrams.csv`: Top 20 bigramas más frecuentes
- `eda_top_trigrams.csv`: Top 20 trigramas más frecuentes
- `eda_ans_unigrams.csv`: Unigramas específicos de Ansiedad
- `eda_ans_bigrams.csv`: Bigramas específicos de Ansiedad
- `eda_dep_unigrams.csv`: Unigramas específicos de Depresión
- `eda_dep_bigrams.csv`: Bigramas específicos de Depresión

##### Análisis de ruido:
- `eda_noise_stats_overall.csv`: Estadísticas de ruido general
- `eda_noise_stats_by_class.csv`: Estadísticas de ruido por clase

---

#### `figs/` (generado por notebooks con visualizaciones)

Directorio con figuras generadas:
- Distribuciones de clases
- Wordclouds
- Gráficos de comparación de baselines
- Matrices de confusión visualizadas

---

## Flujo de Datos

```

 ips_raw.csv (entrada manual)

 01_eda_understanding.ipynb
 ↓

ips_clean.csv (limpieza ligera)

 02_create_splits.ipynb
 ↓

 splits/ 
 dataset_base.csv 
 train_indices.csv
 val_indices.csv 

 02_baseline_*.ipynb
 ↓

 Resultados por baseline
 predictions.csv 
 eval.csv 
 report.csv 
 confusion_matrix.csv

```

---

## Tamaños Esperados

| Archivo | Tamaño Aproximado | Registros |
|---------|-------------------|-----------|
| `ips_raw.csv` | ~2-5 MB | ~3000-5000 |
| `ips_clean.csv` | ~1-3 MB | ~3125 |
| `splits/dataset_base.csv` | ~1-3 MB | 3125 |
| `splits/train_indices.csv` | ~50 KB | 2500 |
| `splits/val_indices.csv` | ~15 KB | 625 |
| `*_predictions.csv` | ~500 KB | 625 (val) |
| `*_eval.csv` | ~1 KB | 1 fila |

---

## 🔍 Problemas de Calidad del Dataset Identificados

Durante el desarrollo del proyecto, se identificaron dos problemas críticos de calidad de datos que afectan significativamente los resultados:

### **1. Problema: Oraciones Duplicadas Intra-Texto (40.3% del corpus)**

**Descripción**: El dataset original (`ips_raw.csv`) contenía 43,938 oraciones duplicadas **dentro del mismo texto**, resultado de:
- Errores de transcripción (copiar-pegar repetido)
- Campos de formulario duplicados
- Artefactos del sistema IPS

**Impacto**:
- ❌ Sobre-representación artificial de ciertos patrones
- ❌ Bias en métricas de vocabulario (TF-IDF inflado)
- ❌ Modelos aprendiendo a detectar duplicados en lugar de síntomas

**Solución**: 
- ✅ Implementada en `01_eda_understanding.ipynb`
- ✅ Deduplicación de oraciones intra-texto (preservando estructura)
- ✅ Dataset limpio: `ips_clean.csv` (3,127 casos vs 3,155 originales)
- ✅ 43,938 oraciones duplicadas removidas (40.3% del corpus de oraciones)

**Resultados**:
- Modelos entrenados con `ips_clean.csv` muestran métricas más realistas
- Vocabulario ahora refleja diversidad real del dataset

---

### **2. Problema: Artifact de Muestreo en Validación (Sampling Variance)**

**Descripción**: Al cambiar de split 80/20 a 60/20/20, se observó una mejora "sospechosa" de +14.6% en F1:
- Val 80/20: F1 = 0.755 (27 pacientes)
- Dev 60/20/20: F1 = 0.866 (18 pacientes)

**Investigación**:
- ✅ Análisis de overlap de pacientes: Solo **11.1% compartidos** (3 de 27 pacientes)
- ✅ 24 pacientes solo en val 80/20, 15 pacientes solo en dev 60/20/20
- ✅ Evaluación en **test set** (hold-out final): F1 = 0.786

**Conclusión**:
- ❌ La mejora +14.6% fue un **artifact de muestreo**, no mejora real
- ✅ Los 15 pacientes en dev 60/20/20 eran más fáciles por azar (ratio D/A más balanceado: 1.84 vs 2.75)
- ✅ F1 real del modelo está en rango **0.75-0.80** (confirmado por test set)

**Lecciones aprendidas**:
- ⚠️ Con **solo 90 pacientes totales**, hay alta varianza por muestreo
- ⚠️ Diferentes pacientes en validación pueden dar ±10-15% de F1 por azar
- ✅ **Test set evaluation** es crítico para validar resultados
- ✅ Recomendación: Cross-validation para estimar F1 con intervalos de confianza

**Evidencia documentada**:
- Análisis completo en notebooks
- Comparación de características de pacientes únicos por split
- Evaluación en 3 conjuntos: val 80/20, dev 60/20/20, test 60/20/20

---

### **Recomendaciones para Futuros Trabajos**

1. **Expansión del dataset**: 
   - Objetivo: 200-300 pacientes para reducir varianza
   - Priorizar balance Depresión/Ansiedad (actualmente 70/30)

2. **Validación robusta**:
   - Usar **cross-validation 5-fold** a nivel de pacientes
   - Reportar F1 con IC95% en lugar de punto único
   - Siempre validar en test set hold-out antes de conclusiones

3. **Calidad de datos**:
   - Auditoría de textos cortos (<200 chars): 1.9-2.5% de casos
   - Revisión con psiquiatras de casos ambiguos
   - Verificación manual de etiquetas en casos limítrofes

---

## Privacidad y Seguridad

### [OK] Archivos Protegidos (NO se suben a git):

Todos los archivos `.csv`, `.xlsx`, `.json` en este directorio están protegidos por `.gitignore`:

```gitignore
data/*.csv
data/*.xlsx
data/*.json
data/splits/
data/figs/
```

### [X] NUNCA subir a git:
- ips_raw.csv (datos originales)
- ips_clean.csv (datos procesados)
- Cualquier archivo con información de pacientes

### [OK] SÍ se versiona:
- Este README.md (documentación)

---

## Setup para Google Colab

Si trabajas en Google Colab:

```python
from google.colab import drive
drive.mount('/content/drive')

# Apuntar DATA_PATH a tu Drive
DATA_PATH = Path("/content/drive/MyDrive/psych-data")
```

---

## FAQ

### ¿Qué pasa si no tengo ips_raw.csv?

Ejecuta `00_setup.ipynb` y verás un error claro:
```
[X] Falta archivo crítico:
 - Colocar ips_raw.csv en data/
```

### ¿Puedo usar otro nombre para el archivo de entrada?

Sí, pero necesitas modificar `01_eda_understanding.ipynb`:
```python
INPUT_FILE = DATA_PATH / "tu_archivo.csv"
```

### ¿Cómo regenero ips_clean.csv si lo borré?

Ejecuta `01_eda_understanding.ipynb` de nuevo.

### ¿Cómo regenero los splits?

Ejecuta `02_create_splits.ipynb` de nuevo. Los índices serán los mismos (seed=42).

### ¿Puedo cambiar el split 80/20?

Sí, modifica en `02_create_splits.ipynb`:
```python
TEST_SIZE = 0.3 # Para split 70/30
```

### ¿Los datos están balanceados?

No. La distribución natural es:
- Depresión: ~70% (2200 ejemplos en train)
- Ansiedad: ~30% (925 ejemplos en train)

Los baselines usan `class_weight='balanced'` para compensar.

---

## Soporte

Si tienes problemas con los datos:

1. Verifica que `ips_raw.csv` existe: `ls -lh data/ips_raw.csv`
2. Ejecuta `00_setup.ipynb` para diagnóstico completo
3. Revisa logs de errores en los notebooks
4. Abre un issue en GitHub (sin incluir datos sensibles)

---

**Última actualización**: Noviembre 2025