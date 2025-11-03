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
 - [OK] Normalización de etiquetas (`Depresivo` → `depresion`)
 - [OK] Colapso de alargamientos (`holaaa` → `holaa`)
 - [OK] Normalización de espacios
 - [X] NO lowercase (preserva tildes y mayúsculas)
 - [X] NO elimina puntuación
- **Tamaño**: ~3125 registros únicos (después de deduplicación)
- **Uso**: Entrada para `02_create_splits.ipynb`

---

#### `splits/` (generado por `02_create_splits.ipynb`)

Directorio con splits unificados para todos los baselines:

##### `splits/dataset_base.csv`
- **Descripción**: Dataset maestro con row_id único
- **Columnas**:
 - `row_id`: ID único de fila (0-3124)
 - `texto`: Texto original de `ips_clean.csv`
 - `etiqueta`: Etiqueta normalizada
- **Tamaño**: 3125 registros
- **Uso**: Todos los baselines cargan este archivo

##### `splits/train_indices.csv`
- **Descripción**: Índices (row_id) del conjunto de entrenamiento
- **Formato**: CSV con una columna `row_id`
- **Tamaño**: 2500 índices (80%)
- **Split**: Estratificado (mantiene proporción 70% depresión, 30% ansiedad)
- **Seed**: 42 (reproducibilidad)

##### `splits/val_indices.csv`
- **Descripción**: Índices (row_id) del conjunto de validación
- **Formato**: CSV con una columna `row_id`
- **Tamaño**: 625 índices (20%)
- **Split**: Estratificado

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