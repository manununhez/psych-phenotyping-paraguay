#!/usr/bin/env python3
"""
Punto de entrada estable para cierre formal de modelos en dev.

Este wrapper delega la ejecución al script operativo ubicado en:
  scripts/audit/cerrar_modelos_dev.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    target = Path(__file__).resolve().parent / "audit" / "cerrar_modelos_dev.py"
    if not target.exists():
        raise SystemExit(f"No se encontró el script operativo: {target}")
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
