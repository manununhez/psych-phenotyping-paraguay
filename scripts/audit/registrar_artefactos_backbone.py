#!/usr/bin/env python3
"""
Registra estado de artefactos de backbone Transformer sin borrar salidas previas.

Salida:
  data/outputs/backbone_artifacts_manifest_<timestamp>.json
  data/outputs/backbone_artifacts_manifest_latest.json
  data/outputs/backbone_artifacts_manifest_latest.md
  data/outputs/comparacion_backbones_hibrido_latest.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


VALID_BACKBONES = {"beto", "roberta_clinical", "roberta_biomedical"}
BACKBONE_TO_MODEL = {
    "beto": "BETO",
    "roberta_clinical": "ROBERTA_CLINICAL",
    "roberta_biomedical": "ROBERTA_BIOMEDICAL",
}


def _safe_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        if not path.exists():
            return None, "no_existe"
        if path.stat().st_size == 0:
            return None, "vacio"
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"json_invalido: {e}"


def _ts(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def _validar_seleccion(path: Path) -> dict[str, Any]:
    payload, err = _safe_json(path)
    status = "INVALIDO"
    motivo = err or ""
    modelo = None
    eval_split = None
    n_modelos = 0

    if payload is not None:
        modelo = str(
            ((payload.get("mejor_transformer_baseline", {}) or {}).get("modelo") or "")
        ).strip()
        eval_split = str(payload.get("eval_split", "")).strip().lower()
        modelos = payload.get("modelos_comparados", [])
        n_modelos = len(modelos) if isinstance(modelos, list) else 0
        if modelo and n_modelos > 0 and eval_split in {"dev", "test"}:
            status = "VALIDO"
            motivo = ""
        else:
            status = "INCOMPLETO"
            motivo = "faltan campos de selección (modelo/eval_split/modelos_comparados)"

    return {
        "tipo": "seleccion_transformer_04c",
        "ruta": str(path),
        "archivo": path.name,
        "fecha_modificacion": _ts(path),
        "status": status,
        "motivo": motivo,
        "eval_split": eval_split,
        "modelo": modelo,
        "n_modelos_comparados": int(n_modelos),
    }


def _validar_comparacion_dir(path: Path) -> dict[str, Any]:
    csv_path = path / "comparacion_backbones_hibrido.csv"
    json_path = path / "comparacion_backbones_hibrido.json"

    status = "INCOMPLETO"
    motivo = ""
    n_rows = 0
    best_backbone = None
    best_macro = None
    delta_vs_beto = None
    ok_corridas = 0
    n_corridas = 0

    if not csv_path.exists() or not json_path.exists():
        status = "INCOMPLETO"
        motivo = "faltan csv/json de comparación"
    else:
        try:
            df = pd.read_csv(csv_path)
            n_rows = int(len(df))
            if n_rows > 0 and {"backbone", "macro_f1"}.issubset(df.columns):
                dff = df.copy()
                dff["backbone"] = dff["backbone"].astype(str).str.lower()
                dff["macro_f1"] = pd.to_numeric(dff["macro_f1"], errors="coerce")
                dff = dff[dff["backbone"].isin(VALID_BACKBONES)].copy()
                if not dff.empty:
                    top = dff.sort_values("macro_f1", ascending=False).iloc[0]
                    best_backbone = str(top["backbone"])
                    best_macro = (
                        float(top["macro_f1"]) if pd.notna(top["macro_f1"]) else None
                    )
                    if (dff["backbone"] == "beto").any() and best_macro is not None:
                        m_beto = float(
                            dff.loc[dff["backbone"] == "beto", "macro_f1"].iloc[0]
                        )
                        delta_vs_beto = best_macro - m_beto
            else:
                status = "INCOMPLETO"
                motivo = "csv sin filas comparables"
        except Exception as e:
            status = "INVALIDO"
            motivo = f"csv_invalido: {e}"

        payload, err = _safe_json(json_path)
        if err and status != "INVALIDO":
            status = "INVALIDO"
            motivo = err
        if payload:
            corridas = payload.get("corridas", [])
            if isinstance(corridas, list):
                n_corridas = len(corridas)
                ok_corridas = int(sum(1 for c in corridas if bool(c.get("ok"))))

        if status != "INVALIDO":
            if n_rows <= 0:
                status = "FALLIDO"
                motivo = "comparación sin filas válidas"
            elif not best_backbone:
                status = "INCOMPLETO"
                motivo = "no se pudo inferir backbone ganador"
            else:
                status = "VALIDO"
                motivo = ""

    return {
        "tipo": "comparacion_backbones_hibrido",
        "ruta": str(path),
        "archivo": path.name,
        "fecha_modificacion": _ts(path),
        "status": status,
        "motivo": motivo,
        "n_filas_csv": int(n_rows),
        "n_corridas": int(n_corridas),
        "n_corridas_ok": int(ok_corridas),
        "best_backbone": best_backbone,
        "best_backbone_modelo": BACKBONE_TO_MODEL.get(best_backbone) if best_backbone else None,
        "best_macro_f1": best_macro,
        "delta_vs_beto": delta_vs_beto,
    }


def _latest_valid(items: list[dict[str, Any]], key_filter: str) -> dict[str, Any] | None:
    valid = [x for x in items if x.get("tipo") == key_filter and x.get("status") == "VALIDO"]
    if not valid:
        return None
    valid.sort(key=lambda x: x.get("fecha_modificacion", ""))
    return valid[-1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Registra y clasifica artefactos de backbone (sin borrar archivos)."
    )
    parser.add_argument(
        "--outputs-dir",
        default="data/outputs",
        help="Directorio de outputs del proyecto.",
    )
    parser.add_argument(
        "--actualizar-latest-selection",
        action="store_true",
        help="Si hay selección válida, actualiza transformer_baseline_selection_latest.json.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    outputs_dir = (repo / args.outputs_dir).resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []

    for p in sorted(outputs_dir.glob("transformer_baseline_selection_*.json")):
        if p.name == "transformer_baseline_selection_latest.json":
            continue
        items.append(_validar_seleccion(p))

    for p in sorted(outputs_dir.glob("comparacion_backbones_hibrido_*")):
        if p.is_dir():
            items.append(_validar_comparacion_dir(p))

    latest_sel = _latest_valid(items, "seleccion_transformer_04c")
    latest_cmp = _latest_valid(items, "comparacion_backbones_hibrido")

    if args.actualizar_latest_selection and latest_sel:
        sel_path = Path(latest_sel["ruta"])
        latest_path = outputs_dir / "transformer_baseline_selection_latest.json"
        shutil.copy2(sel_path, latest_path)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"backbone_artifacts_manifest_{ts}"
    manifest_path = outputs_dir / f"{run_id}.json"
    latest_manifest_json = outputs_dir / "backbone_artifacts_manifest_latest.json"
    latest_manifest_md = outputs_dir / "backbone_artifacts_manifest_latest.md"
    latest_cmp_json = outputs_dir / "comparacion_backbones_hibrido_latest.json"

    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "outputs_dir": str(outputs_dir),
        "totales": {
            "artefactos": len(items),
            "validos": sum(1 for x in items if x["status"] == "VALIDO"),
            "incompletos": sum(1 for x in items if x["status"] == "INCOMPLETO"),
            "fallidos": sum(1 for x in items if x["status"] == "FALLIDO"),
            "invalidos": sum(1 for x in items if x["status"] == "INVALIDO"),
        },
        "latest_valid_selection": latest_sel,
        "latest_valid_backbone_comparison": latest_cmp,
        "artefactos": items,
        "politica_consumo": {
            "seleccion_transformer": "usar exclusivamente latest_valid_selection o fallback por validación interna",
            "comparacion_backbones": "usar exclusivamente latest_valid_backbone_comparison para decisión formal",
            "nota": "no se eliminan artefactos históricos; se clasifican por estado para trazabilidad",
        },
    }

    manifest_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    latest_manifest_json.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    cmp_pointer = {
        "fecha": resumen["fecha"],
        "latest_valid_backbone_comparison": latest_cmp,
    }
    latest_cmp_json.write_text(
        json.dumps(cmp_pointer, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = []
    md.append("# Manifiesto de artefactos de backbone")
    md.append("")
    md.append(f"- Fecha: {resumen['fecha']}")
    md.append(f"- Artefactos analizados: {resumen['totales']['artefactos']}")
    md.append(f"- Válidos: {resumen['totales']['validos']}")
    md.append(f"- Incompletos: {resumen['totales']['incompletos']}")
    md.append(f"- Fallidos: {resumen['totales']['fallidos']}")
    md.append(f"- Inválidos: {resumen['totales']['invalidos']}")
    md.append("")
    md.append("## Selección Transformer válida para consumo")
    if latest_sel:
        md.append(f"- Archivo: `{latest_sel['ruta']}`")
        md.append(f"- Modelo seleccionado: `{latest_sel.get('modelo')}`")
        md.append(f"- Split: `{latest_sel.get('eval_split')}`")
    else:
        md.append("- No se encontró artefacto válido de selección Transformer.")
    md.append("")
    md.append("## Comparación controlada válida para consumo")
    if latest_cmp:
        md.append(f"- Directorio: `{latest_cmp['ruta']}`")
        md.append(f"- Backbone ganador: `{latest_cmp.get('best_backbone')}`")
        md.append(f"- Macro-F1: `{latest_cmp.get('best_macro_f1')}`")
        md.append(f"- Delta vs BETO: `{latest_cmp.get('delta_vs_beto')}`")
    else:
        md.append("- No se encontró comparación controlada válida.")
    md.append("")
    md.append("## Criterio operativo")
    md.append("- No se borran artefactos históricos.")
    md.append(
        "- Los artefactos con estado distinto de `VALIDO` quedan fuera del consumo automático en cierre metodológico."
    )
    latest_manifest_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(latest_manifest_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
