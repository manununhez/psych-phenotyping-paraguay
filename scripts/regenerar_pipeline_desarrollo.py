#!/usr/bin/env python3
"""
Regenera el pipeline de desarrollo hasta el estado actual en dev.

No ejecuta:
- evaluación final en test;
- notebook final de xAI/explicabilidad.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Step:
    step_id: str
    tipo: str  # notebook | script
    path: str
    descripcion: str
    expected_outputs: tuple[str, ...]


STEPS: tuple[Step, ...] = (
    Step(
        "01_datos_eda_limpieza",
        "notebook",
        "notebooks/pipeline/01_datos_eda_limpieza.ipynb",
        "Limpieza inicial y EDA.",
        (),
    ),
    Step(
        "02_patient_level_split",
        "notebook",
        "notebooks/pipeline/02_patient_level_split.ipynb",
        "Split por paciente.",
        (),
    ),
    Step(
        "03_denoising_reglas_core",
        "notebook",
        "notebooks/pipeline/03_denoising_reglas_core.ipynb",
        "Denoising clínico con reglas.",
        (),
    ),
    Step(
        "04a_linea_base_dummy",
        "notebook",
        "notebooks/pipeline/04a_linea_base_dummy.ipynb",
        "Baseline dummy.",
        (),
    ),
    Step(
        "04b_linea_base_tfidf",
        "notebook",
        "notebooks/pipeline/04b_linea_base_tfidf.ipynb",
        "Baseline TF-IDF.",
        (),
    ),
    Step(
        "04c_linea_base_transformers",
        "notebook",
        "notebooks/pipeline/04c_linea_base_transformers.ipynb",
        "Baselines Transformers.",
        (),
    ),
    Step(
        "05_brecha_lexica_co_core_py",
        "notebook",
        "notebooks/analysis/05_brecha_lexica_co_core_py.ipynb",
        "Análisis de brecha léxica.",
        (),
    ),
    Step(
        "06_ingenieria_features_hibridas",
        "notebook",
        "notebooks/pipeline/06_ingenieria_features_hibridas.ipynb",
        "Generación de features híbridas.",
        ("data/processed/fe_*_core/features_core.parquet", "data/processed/fe_*_py/features_py.parquet"),
    ),
    Step(
        "07_entrenamiento_modelos_hibridos",
        "notebook",
        "notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb",
        "Entrenamiento y ablaciones híbridas en dev.",
        ("data/outputs/train_*/comparacion_modelos_dev.csv",),
    ),
    Step(
        "comparacion_backbones_hibrido",
        "script",
        "scripts/comparar_backbones_hibrido.py",
        "Comparación controlada de backbones contextuales en el híbrido (dev).",
        ("data/outputs/comparacion_backbones_hibrido_*/comparacion_backbones_hibrido.csv",),
    ),
    Step(
        "08_resultados_hibrido_vs_lineas_base",
        "notebook",
        "notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb",
        "Consolidación comparativa de resultados.",
        ("data/outputs/results_*/tabla_comparativa_modelos.csv",),
    ),
    Step(
        "barrido_hibrido_dev",
        "script",
        "scripts/ejecutar_barrido_hibrido.py",
        "Barrido y ablaciones híbridas en dev (fases A/B/C).",
        ("data/outputs/barridos_hibridos/*/tabla_maestra_comparativa.csv",),
    ),
    Step(
        "freeze_lexico_preliminar",
        "script",
        "scripts/audit/generar_freeze_lexico.py",
        "Freeze léxico preliminar (sin tocar test).",
        ("data/outputs/freeze_lexico_*/freeze_lexico_resumen.md",),
    ),
    Step(
        "manifiesto_artefactos_backbone",
        "script",
        "scripts/audit/registrar_artefactos_backbone.py",
        "Auditoría no destructiva y trazabilidad de artefactos de backbone.",
        ("data/outputs/backbone_artifacts_manifest_latest.json",),
    ),
    Step(
        "09b_cierre_modelos_dev",
        "notebook",
        "notebooks/pipeline/09b_cierre_modelos_dev.ipynb",
        "Cierre formal de comparación y selección en dev.",
        ("data/outputs/cierre_modelos_dev_*/decision_modelo_final.md",),
    ),
    Step(
        "09_analisis_errores_hibrido",
        "notebook",
        "notebooks/analysis/09_analisis_errores_hibrido.ipynb",
        "Análisis de errores en dev.",
        ("data/outputs/error_analysis_*/",),
    ),
)


def _git_info(repo: Path) -> dict:
    out = {
        "commit": "",
        "commit_short": "",
        "branch": "",
        "dirty": None,
    }
    try:
        out["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
        out["commit_short"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo, text=True
        ).strip()
        out["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo, text=True
        )
        out["dirty"] = bool(status.strip())
    except Exception:
        pass
    return out


def _relevant_env() -> dict:
    prefixes = ("FE_", "TRAIN_", "RESULTS_", "ERROR_", "TRF_", "GEMINI_")
    selected = {}
    for key, value in os.environ.items():
        if key.startswith(prefixes):
            selected[key] = value
    return dict(sorted(selected.items()))


def _build_command(step: Step, repo: Path) -> list[str]:
    if step.tipo == "notebook":
        return [
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            step.path,
            "--inplace",
            "--ExecutePreprocessor.timeout=-1",
        ]
    if step.tipo == "script":
        if step.step_id == "barrido_hibrido_dev":
            feature_base = _latest_feature_base(repo) or "fe_20260310_082139"
            train_ref = _latest_train_run(repo) or "train_20260310_093418"
            return [
                "python",
                step.path,
                "--eval-split",
                "dev",
                "--feature-run-base",
                feature_base,
                "--ref-train-run",
                train_ref,
                "--fases",
                "A,B,C",
                "--top-c",
                "3",
            ]
        if step.step_id == "comparacion_backbones_hibrido":
            return [
                "python",
                step.path,
                "--backbones",
                "beto,roberta_clinical",
                "--incluir-biomedical",
                "0",
            ]
        if step.step_id == "manifiesto_artefactos_backbone":
            return ["python", step.path]
        return ["python", step.path]
    raise ValueError(f"Tipo de paso no soportado: {step.tipo}")


def _latest_train_run(repo: Path) -> str | None:
    base = repo / "data" / "outputs"
    dirs = [p for p in base.glob("train_*") if p.is_dir()]
    if not dirs:
        return None
    canonical = [p for p in dirs if re.fullmatch(r"train_\d{8}_\d{6}", p.name)]
    if canonical:
        latest = max(canonical, key=lambda p: p.stat().st_mtime)
    else:
        latest = max(dirs, key=lambda p: p.stat().st_mtime)
    return latest.name


def _latest_feature_base(repo: Path) -> str | None:
    base = repo / "data" / "processed"
    dirs = [p for p in base.glob("fe_*_core") if p.is_dir()]
    if not dirs:
        return None
    latest = max(dirs, key=lambda p: p.stat().st_mtime)
    name = latest.name
    if name.endswith("_core"):
        return name[:-5]
    return name


def _slice_steps(desde: str | None, hasta: str | None, steps: Sequence[Step]) -> list[Step]:
    ids = [s.step_id for s in steps]
    i_start = 0
    i_end = len(steps) - 1
    if desde:
        if desde not in ids:
            raise ValueError(f"--desde inválido: {desde}")
        i_start = ids.index(desde)
    if hasta:
        if hasta not in ids:
            raise ValueError(f"--hasta inválido: {hasta}")
        i_end = ids.index(hasta)
    if i_start > i_end:
        raise ValueError("--desde está después de --hasta")
    return list(steps[i_start : i_end + 1])


def _cleanup_outputs(repo: Path, dry_run: bool) -> list[str]:
    targets = [
        "data/processed/fe_*",
        "data/outputs/train_*",
        "data/outputs/results_*",
        "data/outputs/error_analysis_*",
        "data/outputs/barridos_hibridos/20*",
        "data/outputs/freeze_lexico_*",
        "data/outputs/backbone_artifacts_manifest_*",
        "data/outputs/comparacion_backbones_hibrido_latest.json",
        "data/outputs/cierre_modelos_dev_*",
        "data/outputs/comparacion_backbones_hibrido_*",
        "data/outputs/regeneracion_desarrollo_*",
    ]
    removed: list[str] = []
    for pattern in targets:
        for path in sorted(repo.glob(pattern)):
            removed.append(str(path))
            if dry_run:
                continue
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
    return removed


def _find_matches(repo: Path, patterns: Sequence[str]) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        for path in sorted(repo.glob(pattern)):
            matches.append(str(path))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenera el pipeline de desarrollo hasta el cierre actual en dev."
    )
    parser.add_argument(
        "--desde",
        default="",
        help="Paso inicial (step_id). Ejemplo: 06_ingenieria_features_hibridas",
    )
    parser.add_argument(
        "--hasta",
        default="",
        help="Paso final (step_id). Ejemplo: 09b_cierre_modelos_dev",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra pasos/comandos sin ejecutarlos.",
    )
    parser.add_argument(
        "--limpiar-outputs",
        action="store_true",
        help="Limpia outputs de desarrollo antes de ejecutar.",
    )
    parser.add_argument(
        "--incluir-comparacion-backbones",
        action="store_true",
        help="Incluye la comparación controlada de backbones contextuales en el flujo.",
    )
    parser.add_argument(
        "--confirmar-limpieza",
        action="store_true",
        help="Confirmación explícita requerida para limpiar outputs.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    now = datetime.now()
    run_id = f"regeneracion_desarrollo_{now.strftime('%Y%m%d_%H%M%S')}"
    out_dir = repo / "data" / "outputs" / run_id
    logs_dir = out_dir / "logs"

    if args.limpiar_outputs and not args.confirmar_limpieza:
        raise SystemExit(
            "Para usar --limpiar-outputs debes agregar --confirmar-limpieza."
        )

    steps = list(STEPS)
    if not args.incluir_comparacion_backbones:
        steps = [s for s in steps if s.step_id != "comparacion_backbones_hibrido"]

    selected_steps = _slice_steps(args.desde or None, args.hasta or None, steps=steps)
    git_info = _git_info(repo)
    env_info = _relevant_env()

    cleaned = []
    if args.limpiar_outputs:
        cleaned = _cleanup_outputs(repo, dry_run=args.dry_run)

    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for idx, step in enumerate(selected_steps, start=1):
        cmd = _build_command(step, repo)
        log_path = logs_dir / f"{idx:02d}_{step.step_id}.log"
        started = time.time()

        if args.dry_run:
            status = "DRY_RUN"
            returncode = 0
            stdout = ""
            stderr = ""
            log_path.write_text(
                f"$ {' '.join(cmd)}\n\n[DRY_RUN]\nComando no ejecutado.\n",
                encoding="utf-8",
            )
        else:
            step_env = os.environ.copy()
            if step.step_id == "08_resultados_hibrido_vs_lineas_base":
                # Evita que 08 tome por accidente corridas `train_backbone_*` de comparación controlada.
                canonical_train = _latest_train_run(repo)
                if canonical_train:
                    step_env["RESULTS_TRAIN_RUN_ID"] = canonical_train
            proc = subprocess.run(
                cmd,
                cwd=repo,
                text=True,
                capture_output=True,
                env=step_env,
            )
            status = "OK" if proc.returncode == 0 else "ERROR"
            returncode = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            log_path.write_text(
                f"$ {' '.join(cmd)}\n\n[STDOUT]\n{stdout}\n\n[STDERR]\n{stderr}\n",
                encoding="utf-8",
            )

        duration = time.time() - started
        output_matches = _find_matches(repo, step.expected_outputs) if step.expected_outputs else []

        step_result = {
            "step_id": step.step_id,
            "descripcion": step.descripcion,
            "tipo": step.tipo,
            "path": step.path,
            "command": cmd,
            "status": status,
            "returncode": returncode,
            "duracion_segundos": round(duration, 3),
            "log_path": str(log_path),
            "expected_outputs_found": output_matches,
        }
        results.append(step_result)

        if status == "ERROR":
            break

    ok_count = sum(1 for r in results if r["status"] in ("OK", "DRY_RUN"))
    fail_count = sum(1 for r in results if r["status"] == "ERROR")
    estado = "OK" if fail_count == 0 else "ERROR"

    summary = {
        "run_id": run_id,
        "fecha": now.isoformat(timespec="seconds"),
        "repo": str(repo),
        "modo": "dry-run" if args.dry_run else "ejecucion",
        "estado_general": estado,
        "n_steps_planificados": len(selected_steps),
        "n_steps_ejecutados": len(results),
        "n_ok": ok_count,
        "n_error": fail_count,
        "desde": args.desde or selected_steps[0].step_id,
        "hasta": args.hasta or selected_steps[-1].step_id,
        "limpieza_solicitada": bool(args.limpiar_outputs),
        "limpieza_objetos": cleaned,
        "git": git_info,
        "env_relevante": env_info,
        "steps": results,
        "nota_alcance": {
            "incluye_test": False,
            "incluye_xai_final": False,
            "comentario": "La regeneración cubre solo la fase de desarrollo hasta cierre en dev.",
        },
        "documentacion_generada_por_pipeline": [
            "data/outputs/freeze_lexico_<timestamp>/freeze_lexico_resumen.md",
            "data/outputs/backbone_artifacts_manifest_latest.md",
            "data/outputs/cierre_modelos_dev_<timestamp>/decision_modelo_final.md",
            "data/outputs/comparacion_backbones_hibrido_<timestamp>/resumen_backbones_hibrido.md",
        ],
    }

    json_path = out_dir / "resumen_regeneracion.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = []
    md.append("# Resumen de regeneración de pipeline de desarrollo")
    md.append("")
    md.append(f"- Run ID: `{run_id}`")
    md.append(f"- Fecha: {summary['fecha']}")
    md.append(f"- Modo: `{summary['modo']}`")
    md.append(f"- Estado general: `{summary['estado_general']}`")
    md.append(f"- Rango ejecutado: `{summary['desde']}` -> `{summary['hasta']}`")
    md.append(f"- Pasos OK/DRY_RUN: {summary['n_ok']}")
    md.append(f"- Pasos con error: {summary['n_error']}")
    md.append(f"- Incluye fase test: `{summary['nota_alcance']['incluye_test']}`")
    md.append(f"- Incluye fase xAI final: `{summary['nota_alcance']['incluye_xai_final']}`")
    md.append("")
    md.append("## Pasos ejecutados")
    for r in results:
        md.append(
            f"- `{r['step_id']}` | estado=`{r['status']}` | duración={r['duracion_segundos']}s | log=`{r['log_path']}`"
        )
    md.append("")
    md.append("## Limpieza de outputs")
    if args.limpiar_outputs:
        md.append(f"- Limpieza solicitada: sí (`dry-run={args.dry_run}`)")
        md.append(f"- Objetos detectados para limpieza: {len(cleaned)}")
    else:
        md.append("- Limpieza solicitada: no")
    md.append("")
    md.append("## Nota metodológica")
    md.append(
        "- Esta regeneración cubre exclusivamente desarrollo y cierre en `dev`; la evaluación final en `test` y la fase final de xAI quedan pendientes."
    )
    md.append("")
    md.append("## Rutas clave")
    md.append(f"- Resumen JSON: `{json_path}`")
    md.append(f"- Directorio de logs: `{logs_dir}`")
    (out_dir / "resumen_regeneracion.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
