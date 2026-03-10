"""
Utilidades compartidas para notebooks de fenotipado psicológico en Paraguay.

Este módulo centraliza funciones comunes para evitar duplicación de código
y garantizar consistencia entre notebooks.
"""

from pathlib import Path
import pandas as pd
import unicodedata


# ============================================================
# CONFIGURACIÓN DE PATHS
# ============================================================

def setup_paths():
    """
    Detecta y configura paths del proyecto automáticamente.
    
    Funciona correctamente si se ejecuta desde:
    - raíz del proyecto
    - notebooks/
    - notebooks/pipeline, notebooks/analysis o notebooks/appendix
    - raíz del proyecto
    
    Retorna:
        dict: Diccionario con paths clave del proyecto:
            - BASE_PATH: Raíz del proyecto
            - DATA_PATH: Carpeta de datos
            - FORK_PATH: Fork del proyecto colombiano
            - SPLITS_PATH: Splits de train/val
            - FIGS_PATH: Figuras y visualizaciones
    
    Ejemplo:
        >>> paths = setup_paths()
        >>> DATA_PATH = paths['DATA_PATH']
    """
    BASE_PATH = Path.cwd().resolve()

    # Resolver raíz del repositorio aun si estamos dentro de subcarpetas de notebooks/
    if not ((BASE_PATH / "data").exists() and (BASE_PATH / "notebooks").exists()):
        for parent in [BASE_PATH, *BASE_PATH.parents]:
            if (parent / "data").exists() and (parent / "notebooks").exists():
                BASE_PATH = parent
                break

    paths = {
        'BASE_PATH': BASE_PATH,
        'DATA_PATH': BASE_PATH / "data",
        'FORK_PATH': BASE_PATH / "Spanish_Psych_Phenotyping_PY",
        'SPLITS_PATH': BASE_PATH / "data" / "splits",
        'FIGS_PATH': BASE_PATH / "data" / "figs",
        'PROCESSED_PATH': BASE_PATH / "data" / "processed",
        'OUTPUTS_PATH': BASE_PATH / "data" / "outputs",
        'CHECKPOINTS_PATH': BASE_PATH / "data" / "checkpoints",
        'LOGS_PATH': BASE_PATH / "data" / "logs",
    }
    
    # Crear directorios si no existen (solo data-related)
    paths['DATA_PATH'].mkdir(exist_ok=True)
    paths['SPLITS_PATH'].mkdir(exist_ok=True)
    paths['FIGS_PATH'].mkdir(exist_ok=True)
    paths['PROCESSED_PATH'].mkdir(exist_ok=True)
    paths['OUTPUTS_PATH'].mkdir(exist_ok=True)
    paths['CHECKPOINTS_PATH'].mkdir(exist_ok=True)
    paths['LOGS_PATH'].mkdir(exist_ok=True)
    
    return paths


# ============================================================
# DETECCIÓN AUTOMÁTICA DE COLUMNAS
# ============================================================

def guess_text_col(df):
    """
    Detecta automáticamente la columna de texto en el dataset.
    
    Estrategia de búsqueda (en orden de prioridad):
    1. Nombres conocidos: texto, Motivo Consulta, text, etc.
    2. Primera columna de tipo string (object)
    
    Parámetros:
        df (pd.DataFrame): Dataset a analizar
    
    Retorna:
        str: Nombre de la columna de texto
    
    Lanza:
        ValueError: Si no se encuentra ninguna columna de texto
    
    Ejemplo:
        >>> text_col = guess_text_col(df)
        >>> texts = df[text_col]
    """
    # Prioridad 1: Nombres conocidos
    known_names = ['texto', 'Motivo Consulta', 'original_motivo_consulta', 'text']
    for col in known_names:
        if col in df.columns:
            return col
    
    # Prioridad 2: Primera columna tipo object (string)
    for col in df.columns:
        if df[col].dtype == 'O':
            return col
    
    raise ValueError(
        f"Error: no se encontró una columna de texto en el dataset.\n"
        f"Columnas disponibles: {list(df.columns)}"
    )


def guess_label_col(df):
    """
    Detecta automáticamente la columna de etiquetas en el dataset.
    
    Estrategia de búsqueda (en orden de prioridad):
    1. Nombres conocidos: etiqueta, Tipo, label, target, etc.
    2. None si no se encuentra (algunos datasets no tienen labels)
    
    Parámetros:
        df (pd.DataFrame): Dataset a analizar
    
    Retorna:
        str or None: Nombre de la columna de etiquetas, o None si no existe
    
    Ejemplo:
        >>> label_col = guess_label_col(df)
        >>> if label_col:
        >>>     labels = df[label_col]
    """
    known_names = ['etiqueta', 'Tipo', 'label', 'target', 'y', 'clase']
    for col in known_names:
        if col in df.columns:
            return col
    return None


def guess_patient_id_col(df):
    """
    Detecta automáticamente la columna de identificador de paciente.

    Retorna:
        str or None: nombre de columna de paciente si existe.
    """
    known_names = ['patient_id', 'id_paciente', 'paciente', 'prontuario', 'idpaciente']
    cols_lower = {str(c).lower(): c for c in df.columns}
    for key in known_names:
        if key in cols_lower:
            return cols_lower[key]
    return None


# ============================================================
# NORMALIZACIÓN DE ETIQUETAS
# ============================================================

def normalize_label(s):
    """
    Normaliza etiquetas a formato estándar para clasificación binaria A/D.
    
    Transformaciones aplicadas:
    1. Conversión a minúsculas
    2. Remoción de acentos (normalización NFD → ASCII)
    3. Corrección de variantes conocidas:
       - "depresivo" → "depresion"
       - (agregar más según sea necesario)
    
    Parámetros:
        s (str or Any): Etiqueta a normalizar
    
    Retorna:
        str: Etiqueta normalizada ("ansiedad" o "depresion" típicamente)
    
    Ejemplo:
        >>> normalize_label("Depresión")
        'depresion'
        >>> normalize_label("ANSIEDAD")
        'ansiedad'
        >>> normalize_label("Depresivo")
        'depresion'
    """
    if pd.isna(s):
        return ""
    
    # Convertir a string y limpiar
    s = str(s).strip().lower()
    
    # Remover acentos (normalización Unicode)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    
    # Corrección de variantes conocidas
    variants = {
        'depresivo': 'depresion',
        'depresiva': 'depresion',
        # Agregar más variantes aquí si aparecen en los datos
    }
    
    return variants.get(s, s)


# ============================================================
# VALIDACIONES
# ============================================================

def validate_splits_exist(splits_path):
    """
    Verifica que los archivos de splits necesarios existan.
    
    Archivos requeridos:
    - dataset_base.csv: Dataset base con row_id
    - train_indices.csv: Índices para entrenamiento (80%)
    - val_indices.csv: Índices para validación (20%)
    
    Parámetros:
        splits_path (Path): Ruta a la carpeta de splits
    
    Lanza:
        FileNotFoundError: Si falta algún archivo requerido
    
    Ejemplo:
        >>> validate_splits_exist(Path('data/splits'))
        # Si falta algún archivo, lanza error con mensaje claro
    """
    required_files = ['dataset_base.csv', 'train_indices.csv', 'dev_indices.csv', 'test_indices.csv']
    missing = [f for f in required_files if not (splits_path / f).exists()]
    
    if missing:
        raise FileNotFoundError(
            f"Error: faltan archivos de índices en {splits_path}:\n"
            f"Faltantes: {missing}\n"
            f"Sugerencia: ejecuta notebooks/pipeline/02_patient_level_split.ipynb primero."
        )


def validate_dataset_columns(df, required_cols):
    """
    Verifica que el dataset tenga las columnas requeridas.
    
    Parámetros:
        df (pd.DataFrame): Dataset a validar
        required_cols (list): Lista de columnas requeridas
    
    Lanza:
        ValueError: Si falta alguna columna requerida
    
    Ejemplo:
        >>> validate_dataset_columns(df, ['texto', 'etiqueta'])
        # Si falta 'texto', lanza error descriptivo
    """
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        raise ValueError(
            f"Error: el dataset no contiene las columnas requeridas: {missing}\n"
            f"Columnas disponibles: {list(df.columns)}\n"
            f"Verifica que estés usando el dataset correcto."
        )


def validate_file_exists(filepath, error_message=None):
    """
    Verifica que un archivo exista, con mensaje de error personalizable.
    
    Parámetros:
        filepath (Path): Ruta al archivo
        error_message (str, optional): Mensaje de error customizado
    
    Lanza:
        FileNotFoundError: Si el archivo no existe
    
    Ejemplo:
        >>> validate_file_exists(
        >>>     Path('data/ips_clean.csv'),
        >>>     "Ejecuta notebooks/pipeline/01_datos_eda_limpieza.ipynb primero"
        >>> )
    """
    if not filepath.exists():
        msg = error_message or f"No se encontró el archivo: {filepath}"
        raise FileNotFoundError(f"Error: {msg}")


def ensure_dir(path_like):
    """
    Crea un directorio si no existe y devuelve Path.
    """
    p = Path(path_like)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================
# HELPERS DE CARGA
# ============================================================

def load_splits(splits_path):
    """
    Carga los 4 archivos de índices en una sola llamada (train/dev/test).
    
    Parámetros:
        splits_path (Path): Ruta a la carpeta de splits
    
    Retorna:
        tuple: (dataset_base, train_indices, dev_indices, test_indices)
            - dataset_base: DataFrame completo con row_id
            - train_indices: Array de row_ids para train
            - dev_indices: Array de row_ids para dev
            - test_indices: Array de row_ids para test
    
    Ejemplo:
        >>> ds_base, train_ids, dev_ids, test_ids = load_splits(SPLITS_PATH)
        >>> df_train = ds_base[ds_base['row_id'].isin(train_ids)]
    """
    # Validar que existan
    validate_splits_exist(splits_path)
    
    # Cargar archivos
    dataset_base = pd.read_csv(splits_path / 'dataset_base.csv')
    train_indices = pd.read_csv(splits_path / 'train_indices.csv')['row_id'].values
    dev_indices = pd.read_csv(splits_path / 'dev_indices.csv')['row_id'].values
    test_indices = pd.read_csv(splits_path / 'test_indices.csv')['row_id'].values
    
    return dataset_base, train_indices, dev_indices, test_indices


# ============================================================
# METRICAS Y EVALUACION
# ============================================================

from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def get_cv_splitter(n_splits=5, random_state=42):
    """
    Retorna el particionador estándar para validación cruzada.
    Usa StratifiedGroupKFold para respetar la estructura de pacientes.
    
    Parámetros:
        n_splits (int): Número de folds (por defecto=5)
        random_state (int): Semilla aleatoria (por defecto=42)
        
    Retorna:
        StratifiedGroupKFold: Particionador configurado
    """
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

def calculate_metrics(y_true, y_pred, labels=['ansiedad', 'depresion']):
    """
    Calcula métricas clave para evaluación.
    
    Parámetros:
        y_true (list/array): Etiquetas reales
        y_pred (list/array): Etiquetas predichas
        labels (list): Lista de etiquetas esperadas
        
    Retorna:
        dict: Diccionario con métricas (f1, precision, recall, report)
    """
    metrics = {
        'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
        'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
        'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0),
        'accuracy': accuracy_score(y_true, y_pred),
        'report': classification_report(y_true, y_pred, zero_division=0),
        'report_dict': classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    }
    return metrics

def plot_confusion_matrix(y_true, y_pred, labels=['ansiedad', 'depresion'], title="Matriz de Confusión", save_path=None):
    """
    Grafica y guarda la matriz de confusión.
    
    Parámetros:
        y_true (list/array): Etiquetas reales
        y_pred (list/array): Etiquetas predichas
        labels (list): Lista de etiquetas para los ejes
        title (str): Título del gráfico
        save_path (Path, optional): Ruta para guardar la imagen
    """
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.ylabel('Real')
    plt.xlabel('Predicho')
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        print(f"Gráfico guardado en: {save_path}")
    
    plt.show()
    plt.close()


# ============================================================
# INFORMACIÓN DEL MÓDULO
# ============================================================

def print_module_info():
    """
    Imprime información sobre las funciones disponibles en este módulo.
    """
    print(" Módulo: utils_shared.py")
    print("\n Funciones disponibles:")
    print("  Paths:")
    print("    - setup_paths(): Configura rutas del proyecto")
    print("\n  Detección de columnas:")
    print("    - guess_text_col(df): Detecta columna de texto")
    print("    - guess_label_col(df): Detecta columna de etiquetas")
    print("\n  Normalización:")
    print("    - normalize_label(s): Normaliza etiquetas a formato estándar")
    print("\n  Validaciones:")
    print("    - validate_splits_exist(path): Verifica splits")
    print("    - validate_dataset_columns(df, cols): Verifica columnas")
    print("    - validate_file_exists(path): Verifica archivo")
    print("\n  Carga:")
    print("    - load_splits(path): Carga índices (train/dev/test)")
    print("\n  Métricas y Visualización:")
    print("    - calculate_metrics(y_true, y_pred): Calcula F1, Precision, Recall")
    print("    - plot_confusion_matrix(y_true, y_pred): Grafica matriz de confusión")
    print("\nUso:")
    print("    from utils_shared import setup_paths, load_splits, calculate_metrics")
    print("    paths = setup_paths()")
    print("    ds, train_ids, dev_ids, test_ids = load_splits(paths['SPLITS_PATH'])")


if __name__ == "__main__":
    # Si se ejecuta directamente, mostrar info
    print_module_info()


# ============================================================
# OUTPUTS VERSIONADOS (para comparar perfiles sin pisar archivos)
# ============================================================

import json
from datetime import datetime

def make_run_id(prefix: str = None) -> str:
    """Crea un run_id reproducible (fecha-hora)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}" if prefix else ts

def get_output_dir(base_path: Path, profile: str, run_id: str) -> Path:
    """Devuelve y crea el directorio de salida versionado."""
    out_dir = base_path / "data" / "outputs" / f"{run_id}_{profile}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def export_fp_fn_candidates(df_text: pd.DataFrame,
                            df_rules: pd.DataFrame,
                            gemini_json_path: Path,
                            out_dir: Path,
                            text_col: str = "texto",
                            row_id_col: str = "row_id"):
    """Exporta candidatos a FP/FN para auditoría, usando Gemini como referencia externa.

    - FP candidato: alguna regla dispara y Gemini no extrae síntomas.
    - FN candidato: Gemini extrae síntomas y ninguna regla dispara.

    Nota: esto NO es 'verdad clínica'. Es un set de casos para revisión y refinamiento.
    """
    if not gemini_json_path.exists():
        print(f"Aviso: no existe Gemini JSON en {gemini_json_path}. No se exportan FP/FN.")
        return None, None

    with open(gemini_json_path, "r", encoding="utf-8") as f:
        gemini = json.load(f)

    df_g = pd.DataFrame([{
        row_id_col: int(x.get(row_id_col)),
        "gemini_symptoms": x.get("sintomas", []) or [],
        "gemini_meds": x.get("medicamentos", []) or []
    } for x in gemini])

    # Merge mínimo
    dfm = df_text[[row_id_col, text_col]].merge(df_rules, on=row_id_col, how="left").merge(df_g, on=row_id_col, how="left")
    dfm["gemini_symptoms"] = dfm["gemini_symptoms"].apply(lambda x: x if isinstance(x, list) else [])
    rule_cols = [c for c in df_rules.columns if c.startswith("rule_")]
    dfm["rules_fired"] = dfm[rule_cols].apply(lambda r: [c.replace("rule_","") for c,v in r.items() if int(v)==1], axis=1)
    dfm["n_rules"] = dfm["rules_fired"].apply(len)

    fp = dfm[(dfm["n_rules"]>0) & (dfm["gemini_symptoms"].apply(len)==0)].copy()
    fn = dfm[(dfm["n_rules"]==0) & (dfm["gemini_symptoms"].apply(len)>0)].copy()

    fp_out = fp[[row_id_col, text_col, "rules_fired", "gemini_symptoms"]].to_dict(orient="records")
    fn_out = fn[[row_id_col, text_col, "rules_fired", "gemini_symptoms"]].to_dict(orient="records")

    save_json(fp_out, out_dir / "false_positives_candidates.json")
    save_json(fn_out, out_dir / "false_negatives_candidates.json")

    print(f"FP candidatos: {len(fp_out)} → {out_dir/'false_positives_candidates.json'}")
    print(f"FN candidatos: {len(fn_out)} → {out_dir/'false_negatives_candidates.json'}")

    return fp_out, fn_out

# ============================================================
# CLINICAL ASSERTION FILTER (keep_entity)
# Fuente única de verdad para 03 / 07 / 09 (MCP)
# ============================================================
# Propósito (auditable):
#   En EHR es común encontrar menciones de síntomas en contextos no-actuales o no-paciente
#   (plantillas, checklist, antecedentes, hipótesis). Esto genera falsos positivos si se
#   toman literalmente como evidencia clínica.
#
# keep_entity implementa un filtro de “aseveración clínica”:
#   1) DESCARTA menciones en contexto: histórico / hipotético / familiar.
#   2) Si la mención está NEGADA:
#        - conserva SOLO si la negación es atribuida al PACIENTE (p. ej. “Paciente niega…”),
#          porque es señal fenomenológica relevante (estado subjetivo, defensas, insight).
#        - descarta si la negación es del MÉDICO/plantilla (p. ej. “Sin síntomas…”),
#          porque suele ser ruido administrativo que diluye la señal.
#
# Contrato de consistencia:
#   - 03_denoising: has_clinical_signal se calcula SOLO con entidades que pasan keep_entity.
#   - 07_feature_engineering: rule_* y niega_* se basan SOLO en keep_entity.
#   - 06_brecha_lexica_co_core_py: la auditoría de reglas usa keep_entity para no comparar peras con manzanas.
#
# Nota metodológica:
#   Esto es *data cleaning / normalización del formato de nota*, NO “decisión clínica”.
#   El objetivo es reducir ruido sistemático del EHR y mejorar precisión/recall de extracción.
#
import re

# Regex robusto para detectar negación atribuida al paciente (IPS/Paraguay)
PATIENT_NEG_RE = re.compile(
    r"("
    r"paciente\s+niega|"
    r"refiere\s+que\s+no|"
    r"dice\s+que\s+no|"
    r"manifiesta\s+que\s+no|"
    r"no\s+refiere|"
    r"no\s+manifiesta|"
    r"niega\s+(tener|sentir|presentar|haber|haber\s+tenido)"
    r")",
    re.I
)

def is_patient_negation(ent, doc, window_tokens: int = 12) -> bool:
    """
    Detecta si una negación (is_negated=True) proviene explícitamente del paciente.

    Estrategia:
      - Buscar triggers de negación del paciente en un contexto a la izquierda de la entidad.
      - Por defecto window_tokens=12 para cubrir oraciones médicas largas (IPS).

    Parámetros:
        ent: spaCy Span (entidad detectada por TargetMatcher)
        doc: spaCy Doc
        window_tokens: cantidad de tokens a la izquierda a inspeccionar

    Retorna:
        bool: True si la negación parece atribuida al paciente, False si es del médico/plantilla.
    """
    start = max(0, ent.start - int(window_tokens))
    left = doc[start:ent.start].text
    # Si hay segmentación por oraciones disponible, podemos reforzar buscando en ent.sent
    # pero evitamos depender de sentencizer; usamos lo robusto: ventana izquierda.
    return bool(PATIENT_NEG_RE.search(left))


def keep_entity(ent, doc, window_tokens: int = 12) -> tuple[bool, bool]:
    """
    Decide si una entidad debe contarse como evidencia clínica válida.

    Retorna:
        (keep, is_patient_neg):
          - keep: si la entidad se conserva como señal para has_clinical_signal / rule features
          - is_patient_neg: True si la entidad está negada y la fuente es el paciente
                            (sirve para feature niega_*)

    Política (MCP):
      1) Ruido por contexto: descartar si es histórico / hipotético / familiar.
      2) Negación:
         - Si NO está negada => conservar.
         - Si está negada:
             - conservar SOLO si es negación del paciente (patient-negation).
             - descartar si es negación del médico/plantilla.

    Requiere:
      - medspacy_context para atributos como is_historical/is_hypothetical/is_family/is_negated.
        Si no existen, se asume False (no descarta por falta de anotación).

    Parámetros:
        ent: spaCy Span
        doc: spaCy Doc
        window_tokens: ventana para detectar negación del paciente

    """
    ext = getattr(ent, "_", None)

    # 1) Contextos a descartar
    is_hist = bool(getattr(ext, "is_historical", False))
    is_hyp = bool(getattr(ext, "is_hypothetical", False))
    is_fam = bool(getattr(ext, "is_family", False))
    if is_hist or is_hyp or is_fam:
        return (False, False)

    # 2) Negación
    is_neg = bool(getattr(ext, "is_negated", False))
    if not is_neg:
        return (True, False)

    # Negada: conservar SOLO si es negación del paciente
    pat_neg = is_patient_negation(ent, doc, window_tokens=window_tokens)
    if pat_neg:
        return (True, True)

    return (False, False)
