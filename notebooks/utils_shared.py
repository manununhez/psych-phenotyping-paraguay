"""
Utilidades compartidas para notebooks de fenotipado psicológico en Paraguay.

Este módulo centraliza funciones comunes para evitar duplicación de código
y garantizar consistencia entre notebooks.

Autor: Proyecto Psych-Phenotyping Paraguay
Fecha: 2025-11
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
    - notebooks/ (detecta y sube un nivel)
    - raíz del proyecto
    
    Returns:
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
    BASE_PATH = Path.cwd()
    
    # Si estamos en notebooks/, subir un nivel
    if BASE_PATH.name == "notebooks":
        BASE_PATH = BASE_PATH.parent
    
    paths = {
        'BASE_PATH': BASE_PATH,
        'DATA_PATH': BASE_PATH / "data",
        'FORK_PATH': BASE_PATH / "Spanish_Psych_Phenotyping_PY",
        'SPLITS_PATH': BASE_PATH / "data" / "splits",
        'FIGS_PATH': BASE_PATH / "data" / "figs"
    }
    
    # Crear directorios si no existen (solo data-related)
    paths['DATA_PATH'].mkdir(exist_ok=True)
    paths['SPLITS_PATH'].mkdir(exist_ok=True)
    paths['FIGS_PATH'].mkdir(exist_ok=True)
    
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
    
    Args:
        df (pd.DataFrame): Dataset a analizar
    
    Returns:
        str: Nombre de la columna de texto
    
    Raises:
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
        f"❌ No se encontró columna de texto en el dataset.\n"
        f"   Columnas disponibles: {list(df.columns)}"
    )


def guess_label_col(df):
    """
    Detecta automáticamente la columna de etiquetas en el dataset.
    
    Estrategia de búsqueda (en orden de prioridad):
    1. Nombres conocidos: etiqueta, Tipo, label, target, etc.
    2. None si no se encuentra (algunos datasets no tienen labels)
    
    Args:
        df (pd.DataFrame): Dataset a analizar
    
    Returns:
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
    
    Args:
        s (str or Any): Etiqueta a normalizar
    
    Returns:
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
    
    Args:
        splits_path (Path): Ruta a la carpeta de splits
    
    Raises:
        FileNotFoundError: Si falta algún archivo requerido
    
    Ejemplo:
        >>> validate_splits_exist(Path('data/splits'))
        # Si falta algún archivo, lanza error con mensaje claro
    """
    required_files = ['dataset_base.csv', 'train_indices.csv', 'val_indices.csv']
    missing = [f for f in required_files if not (splits_path / f).exists()]
    
    if missing:
        raise FileNotFoundError(
            f"❌ Faltan archivos de splits en {splits_path}:\n"
            f"   Faltantes: {missing}\n"
            f"   Solución: Ejecuta 02_create_splits.ipynb primero."
        )


def validate_dataset_columns(df, required_cols):
    """
    Verifica que el dataset tenga las columnas requeridas.
    
    Args:
        df (pd.DataFrame): Dataset a validar
        required_cols (list): Lista de columnas requeridas
    
    Raises:
        ValueError: Si falta alguna columna requerida
    
    Ejemplo:
        >>> validate_dataset_columns(df, ['texto', 'etiqueta'])
        # Si falta 'texto', lanza error descriptivo
    """
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        raise ValueError(
            f"❌ Dataset no tiene columnas requeridas: {missing}\n"
            f"   Columnas disponibles: {list(df.columns)}\n"
            f"   Verifica que estés usando el dataset correcto."
        )


def validate_file_exists(filepath, error_message=None):
    """
    Verifica que un archivo exista, con mensaje de error personalizable.
    
    Args:
        filepath (Path): Ruta al archivo
        error_message (str, optional): Mensaje de error customizado
    
    Raises:
        FileNotFoundError: Si el archivo no existe
    
    Ejemplo:
        >>> validate_file_exists(
        >>>     Path('data/ips_clean.csv'),
        >>>     "Ejecuta 01_eda_preprocessing.ipynb primero"
        >>> )
    """
    if not filepath.exists():
        msg = error_message or f"No se encontró el archivo: {filepath}"
        raise FileNotFoundError(f"❌ {msg}")


# ============================================================
# HELPERS DE CARGA
# ============================================================

def load_splits(splits_path):
    """
    Carga los 3 archivos de splits de una vez.
    
    Args:
        splits_path (Path): Ruta a la carpeta de splits
    
    Returns:
        tuple: (dataset_base, train_indices, val_indices)
            - dataset_base: DataFrame completo con row_id
            - train_indices: Array de row_ids para train
            - val_indices: Array de row_ids para val
    
    Ejemplo:
        >>> ds_base, train_ids, val_ids = load_splits(SPLITS_PATH)
        >>> df_train = ds_base[ds_base['row_id'].isin(train_ids)]
    """
    # Validar que existan
    validate_splits_exist(splits_path)
    
    # Cargar archivos
    dataset_base = pd.read_csv(splits_path / 'dataset_base.csv')
    train_indices = pd.read_csv(splits_path / 'train_indices.csv')['row_id'].values
    val_indices = pd.read_csv(splits_path / 'val_indices.csv')['row_id'].values
    
    return dataset_base, train_indices, val_indices


# ============================================================
# INFORMACIÓN DEL MÓDULO
# ============================================================

def print_module_info():
    """
    Imprime información sobre las funciones disponibles en este módulo.
    Útil para debugging y documentación rápida.
    """
    print("📚 Módulo: utils_shared.py")
    print("\n🔧 Funciones disponibles:")
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
    print("    - load_splits(path): Carga splits de una vez")
    print("\n💡 Uso:")
    print("    from utils_shared import setup_paths, load_splits")
    print("    paths = setup_paths()")
    print("    dataset, train_ids, val_ids = load_splits(paths['SPLITS_PATH'])")


if __name__ == "__main__":
    # Si se ejecuta directamente, mostrar info
    print_module_info()
