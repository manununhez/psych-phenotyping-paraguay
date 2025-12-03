# Notebooks del Proyecto

Este directorio contiene los notebooks Jupyter para el pipeline de fenotipado psiquiátrico.

## 📋 Orden de Ejecución

Siga este orden secuencial para reproducir los resultados:

| # | Notebook | Propósito |
|---|----------|-----------|
| 1 | `00_setup.ipynb` | Configuración inicial del entorno y verificación de dependencias. |
| 2 | `01_eda.ipynb` | Análisis Exploratorio de Datos (EDA) y limpieza inicial. |
| 3 | `02_create_splits.ipynb` | Creación de particiones Train/Dev/Test a nivel de paciente (60/20/20). |
| 4 | `03_rule_based_denoising.ipynb` | Pipeline de limpieza y filtrado de ruido administrativo. |
| 5 | `03_preparacion_validacion_psiquiatras.ipynb` | Selección de casos para validación clínica post-denoising. |
| 6 | `04_baseline_dummy.ipynb` | Baselines triviales (Majority/Stratified) para sanity checks. |
| 7 | `04_baseline_tfidf.ipynb` | Modelo ML tradicional (TF-IDF + LinearSVC). |
| 8 | `04_baseline_transformers.ipynb` | Modelos Deep Learning (BETO, RoBERTa). |
| 9 | `05_comparacion_resultados.ipynb` | Comparación consolidada de todos los modelos y análisis estadístico. |

## 🛠️ Utilidades Compartidas

*   **`utils_shared.py`**: Módulo con funciones comunes para carga de datos, configuración de paths y métricas. Evita la duplicación de código entre notebooks.

## 📝 Notas Importantes

*   **Reproducibilidad:** Todos los notebooks usan `seed=42` para garantizar resultados consistentes.
*   **Datos:** Los notebooks esperan que los datos estén en `../data/`.
*   **Dependencias:** Asegúrese de instalar las dependencias listadas en `../requirements.txt`.
