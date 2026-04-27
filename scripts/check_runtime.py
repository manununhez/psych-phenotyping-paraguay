#!/usr/bin/env python3
"""
Chequeo rápido del entorno reproducible del proyecto.

No ejecuta el pipeline. Verifica:
- imports críticos;
- presencia del submódulo clínico;
- disponibilidad de modelo spaCy en español;
- existencia opcional de datos locales esperados.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


RUNTIME_MODULES = [
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "transformers",
    "torch",
    "spacy",
    "medspacy",
    "xgboost",
    "shap",
    "google.genai",
]


def check_imports() -> list[str]:
    missing: list[str] = []
    print("== Imports críticos ==")
    for name in RUNTIME_MODULES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", None)
            print(f"[OK] {name} ({version})")
        except Exception as exc:
            print(f"[FAIL] {name}: {exc.__class__.__name__}: {exc}")
            missing.append(name)
    return missing


def check_submodule() -> bool:
    print("\n== Submódulo clínico ==")
    target = REPO_ROOT / "Spanish_Psych_Phenotyping_PY" / "escribe" / "default_nlp.py"
    if target.exists():
        print(f"[OK] {target.relative_to(REPO_ROOT)}")
        return True
    print(f"[FAIL] Falta {target.relative_to(REPO_ROOT)}")
    return False


def check_spacy_model() -> bool:
    print("\n== Modelo spaCy español ==")
    for candidate in ("es_core_news_md", "es_core_news_sm"):
        try:
            mod = importlib.import_module(candidate)
            version = getattr(mod, "__version__", None)
            print(f"[OK] {candidate} ({version})")
            return True
        except Exception:
            continue
    print("[FAIL] No se encontró ni `es_core_news_md` ni `es_core_news_sm`.")
    return False


def check_data(expect_raw: bool) -> bool:
    print("\n== Datos locales ==")
    raw_file = REPO_ROOT / "data" / "ips_raw.csv"
    if raw_file.exists():
        print(f"[OK] {raw_file.relative_to(REPO_ROOT)}")
        return True
    if expect_raw:
        print(f"[FAIL] Falta {raw_file.relative_to(REPO_ROOT)}")
        return False
    print(f"[WARN] {raw_file.relative_to(REPO_ROOT)} no está disponible. Esto es aceptable para una validación de entorno sin datos.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-raw-data", action="store_true")
    args = parser.parse_args()

    missing_imports = check_imports()
    ok_submodule = check_submodule()
    ok_spacy = check_spacy_model()
    ok_data = check_data(expect_raw=args.expect_raw_data)

    failed = bool(missing_imports) or (not ok_submodule) or (not ok_spacy) or (not ok_data)
    print("\n== Resultado ==")
    if failed:
        print("Chequeo incompleto o fallido.")
        return 1
    print("Chequeo OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
