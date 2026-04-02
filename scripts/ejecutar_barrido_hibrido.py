#!/usr/bin/env python3
"""
Wrapper de compatibilidad para el barrido/ablación híbrida.

El nombre canónico del script operativo es:
  scripts/ejecutar_barrido_ablacion_hibrido.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    target = Path(__file__).resolve().parent / "ejecutar_barrido_ablacion_hibrido.py"
    if not target.exists():
        raise SystemExit(f"No se encontró el script operativo: {target}")
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
