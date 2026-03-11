# Guía de ejecución (fase de desarrollo)

Esta guía cubre únicamente la regeneración hasta el cierre actual en `dev`.

No incluye:
- evaluación final en `test` (pendiente);
- notebook final de xAI/explicabilidad (pendiente).

## Opción recomendada: script único

```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
```

Wrapper bash opcional:

```bash
bash scripts/run_regeneracion_desarrollo.sh --dry-run
bash scripts/run_regeneracion_desarrollo.sh
```

## Ejecución parcial

```bash
python scripts/regenerar_pipeline_desarrollo.py --desde 06_ingenieria_features_hibridas --hasta 09b_cierre_modelos_dev
```

## Limpieza controlada de outputs

```bash
python scripts/regenerar_pipeline_desarrollo.py \
  --limpiar-outputs \
  --confirmar-limpieza \
  --dry-run
```

Para ejecutar limpieza real, quitar `--dry-run`.

## Salidas de la regeneración
Cada corrida deja:
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.md`
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.json`
- logs por paso en `data/outputs/regeneracion_desarrollo_<timestamp>/logs/`.

## Orden operativo cubierto por la regeneración
1. `01_datos_eda_limpieza`
2. `02_patient_level_split`
3. `03_denoising_reglas_core`
4. `04a_linea_base_dummy`
5. `04b_linea_base_tfidf`
6. `04c_linea_base_transformers`
7. `05_brecha_lexica_co_core_py`
8. `06_ingenieria_features_hibridas`
9. `07_entrenamiento_modelos_hibridos`
10. `comparacion_backbones_hibrido` (si se activa `--incluir-comparacion-backbones`)
11. `08_resultados_hibrido_vs_lineas_base`
12. `barrido_hibrido_dev`
13. `freeze_lexico_preliminar`
14. `manifiesto_artefactos_backbone`
15. `09b_cierre_modelos_dev`
16. `09_analisis_errores_hibrido`

## Nota específica sobre backbone
- `04c` define y exporta la selección del baseline Transformer.
- `06+` consume esa selección por defecto y permite override explícito por entorno.
- `09b` utiliza la selección de `04c` y la comparación controlada de backbones (si existe artefacto válido) para fundamentar la decisión final en `dev`.

Cadena operativa recomendada:
`04c` -> `06` -> `07` -> `scripts/comparar_backbones_hibrido.py` -> `scripts/audit/registrar_artefactos_backbone.py` -> `09b`.

## Nota metodológica
La regeneración está diseñada para reproducir el estado de desarrollo y su documentación de cierre en `dev`, sin mezclar decisiones de la fase final.
