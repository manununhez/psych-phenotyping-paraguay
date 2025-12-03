# Guía de Ejecución del Pipeline

Este documento detalla el orden correcto de ejecución de los notebooks para reproducir el pipeline de fenotipado psiquiátrico.

## Orden de Ejecución

### 1. Configuración y Preparación
*   **`00_setup.ipynb`**
    *   **Propósito:** Verifica dependencias y configura el entorno.
    *   **Output:** Ninguno (solo validación).

*   **`01_eda.ipynb`**
    *   **Propósito:** Análisis exploratorio y limpieza inicial.
    *   **Input:** Datos crudos (`data/ips.csv` o similar).
    *   **Output:** `data/ips_clean.csv` (Dataset limpio para splits).

*   **`02_create_splits.ipynb`**
    *   **Propósito:** División train/dev/test a nivel paciente (sin leakage).
    *   **Input:** `data/ips_clean.csv`.
    *   **Output:** 
        *   `data/splits/dataset_base.csv`
        *   `data/splits/train_indices.csv`
        *   `data/splits/dev_indices.csv`
        *   `data/splits/test_indices.csv`

### 2. Procesamiento y Denoising
*   **`03_rule_based_denoising.ipynb`**
    *   **Propósito:** Filtrado de ruido administrativo usando reglas NLP (Weak Supervision).
    *   **Input:** `data/splits/dataset_base.csv` y splits.
    *   **Output:** `data/splits/train_denoised.csv` (Dataset de entrenamiento limpio).

*   **`03_preparacion_validacion_psiquiatras.ipynb`** (Opcional para el flujo ML)
    *   **Propósito:** Selección de casos para validación humana.
    *   **Input:** `data/splits/dataset_base.csv`.
    *   **Output:** Archivos Excel para psiquiatras.

### 3. Modelado (Baselines y Modelos)
*   **`04_baseline_dummy.ipynb`**
    *   **Propósito:** Baselines triviales (Majority, Stratified).
    *   **Input:** Splits y `dataset_base.csv`.
    *   **Output:** `data/dummy_*_eval.csv`.

*   **`04_baseline_tfidf.ipynb`**
    *   **Propósito:** Modelo ML clásico (TF-IDF + LinearSVC).
    *   **Input:** `train_denoised.csv` (Train) y `dataset_base.csv` (Dev).
    *   **Output:** `data/tfidf_eval.csv`.

*   **`04_baseline_transformers.ipynb`**
    *   **Propósito:** Modelos Deep Learning (BETO, RoBERTa).
    *   **Input:** `train_denoised.csv` (Train) y `dataset_base.csv` (Dev).
    *   **Output:** `data/{model}_eval.csv` y checkpoints.
    *   **Nota:** Requiere GPU/MPS para ejecución rápida.

### 4. Evaluación y Comparación
*   **`05_comparacion_resultados.ipynb`**
    *   **Propósito:** Consolidación de métricas y gráficos comparativos.
    *   **Input:** Todos los archivos `*_eval.csv` generados anteriormente.
    *   **Output:** `data/comparacion_modelos_consolidada.csv` y gráficos en `data/figs/`.

## Comandos Rápidos (Terminal)

Si deseas ejecutar todo el pipeline secuencialmente desde la terminal:

```bash
# 1. Setup & Data
jupyter nbconvert --to notebook --execute notebooks/00_setup.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/02_create_splits.ipynb --inplace

# 2. Denoising
jupyter nbconvert --to notebook --execute notebooks/03_rule_based_denoising.ipynb --inplace

# 3. Models
jupyter nbconvert --to notebook --execute notebooks/04_baseline_dummy.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/04_baseline_tfidf.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/04_baseline_transformers.ipynb --inplace

# 4. Comparison
jupyter nbconvert --to notebook --execute notebooks/05_comparacion_resultados.ipynb --inplace
```
