# Baseline Crudo Vs Filtrado

## Uso recomendado
Este contraste conviene tratarlo como material metodológico secundario.

No debería reemplazar:
- la tabla principal de baselines en `dev`;
- la comparación canónica entre `DUMMY`, `TF-IDF`, `BETO`, `ROBERTA_CLINICAL`, `ROBERTA_BIOMEDICAL` y el híbrido;
- ni el cierre formal del sistema en `09b`.

Sí puede servir como:
- apoyo para justificar el denoising;
- evidencia de que la limpieza del universo modelado no fue cosmética;
- material breve de apéndice o nota metodológica.

## Fuente actual
Resultados tomados de:

- `data/outputs/ips_cierre_final_smoke_10_publico/baseline_crudo_vs_filtrado.csv`
- `data/outputs/ips_cierre_final_smoke_10_publico/baseline_crudo_vs_filtrado.md`

Este contraste pertenece al frente secundario de revisión clínica externa y no al pipeline canónico `04a-09`.

## Resultados actuales
| configuracion | train_universo | eval_universo | macro_f1 | balanced_accuracy | f1_ansiedad | f1_depresion | n_eval | n_train |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `train_base→dev_base` | `train_base` | `dev_base` | `0.682764` | `0.688849` | `0.575064` | `0.790464` | `595` | `1911` |
| `train_base→dev_denoised` | `train_base` | `dev_denoised` | `0.763774` | `0.800658` | `0.694215` | `0.833333` | `343` | `1911` |
| `train_denoised→dev_base` | `train_denoised` | `dev_base` | `0.673228` | `0.668579` | `0.539773` | `0.806683` | `595` | `1107` |
| `train_denoised→dev_denoised` | `train_denoised` | `dev_denoised` | `0.754539` | `0.784774` | `0.677966` | `0.831111` | `343` | `1107` |

## Lectura metodológica
- `train_base→dev_base` muestra el comportamiento de una configuración simple sobre un universo todavía mezclado con seguimiento, reposición y ruido administrativo.
- `train_base→dev_denoised` funciona como control: el modelo se entrena con más volumen, pero se evalúa sobre un universo clínicamente más coherente.
- `train_denoised→dev_denoised` es el contraste filtrado equivalente bajo la misma lógica simple.
- El punto no es demostrar que el universo crudo sea inútil en términos absolutos, sino mostrar que el denoising ayudó a delimitar un espacio experimental más consistente para una tarea diferencial entre ansiedad y depresión.

## Resultado redactado
El contraste auxiliar entre universo base y universo filtrado muestra que la interpretación del denoising no debe reducirse a una lectura simplista de "mejora" o "empeora" la métrica. Cuando la línea base textual simple se entrena y evalúa sobre el universo previo al filtrado (`train_base→dev_base`), alcanza una `macro_f1=0.6828` y una `balanced_accuracy=0.6888`. En cambio, al mantener el entrenamiento sobre ese universo más amplio pero evaluar sobre el conjunto clínicamente más coherente (`train_base→dev_denoised`), los valores suben a `macro_f1=0.7638` y `balanced_accuracy=0.8007`. El contraste estrictamente filtrado (`train_denoised→dev_denoised`) queda en `macro_f1=0.7545` y `balanced_accuracy=0.7848`, mientras que la combinación `train_denoised→dev_base` desciende a `macro_f1=0.6732` y `balanced_accuracy=0.6686`.

Leído correctamente, este resultado no pretende demostrar que el universo base sea inútil ni que el denoising se justifique solo por una ganancia métrica automática. Lo que muestra es que el universo evaluado cambia de naturaleza cuando se separan notas de seguimiento, reposición o baja densidad fenomenológica de aquellas que aportan señal clínica más útil para la tarea diferencial. Por eso, el valor principal de este contraste es metodológico: ayuda a justificar que la comparación canónica entre modelos se haya fijado sobre el universo `denoised`, no porque el corpus previo carezca por completo de información, sino porque el filtrado vuelve más coherente el espacio experimental y más defendible la interpretación de los resultados.

## Recomendación de uso en el documento
Si se incorpora, conviene hacerlo como:
- subapartado corto de apoyo metodológico; o
- apéndice breve.

No conviene usarlo como resultado central, porque:
- no forma parte de la comparación canónica del pipeline;
- mezcla universos distintos;
- y su valor principal es justificar el recorte metodológico, no redefinir el ranking de modelos.

## Párrafo sugerido
Se realizó además un contraste auxiliar entre una línea base textual simple entrenada sobre el universo previo al denoising y su equivalente sobre el universo filtrado. Este ejercicio no se incorporó a la comparación canónica de modelos, ya que no opera exactamente sobre el mismo espacio experimental que el cierre principal. Su utilidad fue metodológica: mostrar que el denoising no respondió solo a una búsqueda de mejora métrica, sino a la necesidad de separar notas clínicamente informativas de registros de seguimiento, trámite o baja densidad fenomenológica.

## Versión más corta
Como apoyo metodológico adicional, se ensayó un contraste auxiliar entre un baseline textual simple sobre el universo previo al denoising y su equivalente sobre el universo filtrado. Este ejercicio no redefine la comparación principal de modelos, pero sí ayuda a mostrar que la limpieza del corpus no fue cosmética, sino una forma de delimitar un universo clínicamente más coherente para la tarea diferencial.
