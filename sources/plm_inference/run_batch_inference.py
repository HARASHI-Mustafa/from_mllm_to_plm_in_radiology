"""
Command-line runner for section-aware PLM batch inference.

Example usage from the project root:

python src/plm_inference/run_batch_inference.py ^
  --input data/processed/chexpert_plus/master/chexpert_plus_master_plm.parquet ^
  --impression_model outputs/plm_results/track_a_full_finetuning/radbert_impression_track_a_full/best_model ^
  --findings_model outputs/plm_results/track_e_findings_only/radbert_findings_only_full/best_model ^
  --output_dir outputs/plm_inference_script_test ^
  --n_reports 200 ^
  --batch_size 8 ^
  --require_findings

For PowerShell, use backtick ` instead of ^ for multi-line commands.
"""

import argparse
import json
import time
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import torch

# Make src/ importable when this script is executed directly.
# File location:
# project_root/src/plm_inference/run_batch_inference.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from plm_inference.pipeline import SectionAwarePLMPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run section-aware PLM inference on CheXpert Plus reports."
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input parquet/csv file containing report sections.",
    )

    parser.add_argument(
        "--impression_model",
        type=str,
        required=True,
        help="Path to Impression PLM best_model directory.",
    )

    parser.add_argument(
        "--findings_model",
        type=str,
        required=True,
        help="Path to Findings PLM best_model directory.",
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory where output files will be saved.",
    )

    parser.add_argument(
        "--findings_col",
        type=str,
        default="section_findings",
        help="Name of Findings section column.",
    )

    parser.add_argument(
        "--impression_col",
        type=str,
        default="section_impression",
        help="Name of Impression section column.",
    )

    parser.add_argument(
        "--raw_report_col",
        type=str,
        default="report",
        help="Name of raw full report column.",
    )

    parser.add_argument(
        "--n_reports",
        type=int,
        default=None,
        help="Optional number of reports to process. If omitted, process all selected reports.",
    )

    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Inference batch size.",
    )

    parser.add_argument(
        "--max_length",
        type=int,
        default=256,
        help="Maximum tokenizer sequence length.",
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device: cuda, cpu, or omitted for auto-detection.",
    )

    parser.add_argument(
        "--base_model_name",
        type=str,
        default="StanfordAIMI/RadBERT",
        help="Base Hugging Face model name used to recreate architecture.",
    )

    parser.add_argument(
        "--require_findings",
        action="store_true",
        help="Keep only reports with valid Findings section.",
    )

    parser.add_argument(
        "--require_impression",
        action="store_true",
        help="Keep only reports with valid Impression section.",
    )

    parser.add_argument(
        "--fallback_to_report_if_no_impression",
        action="store_true",
        help="Use raw report as Impression input if Impression section is missing.",
    )

    return parser.parse_args()


def read_input_file(input_path: Path) -> pd.DataFrame:
    """
    Read parquet or csv input file.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(input_path)

    if suffix == ".csv":
        return pd.read_csv(input_path)

    raise ValueError(
        f"Unsupported input file format: {suffix}. "
        "Use .parquet or .csv."
    )


def save_json(data: Dict[str, Any], path: Path) -> None:
    """
    Save dictionary as readable JSON.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    impression_model_dir = Path(args.impression_model)
    findings_model_dir = Path(args.findings_model)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    device = args.device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 100)
    print("SECTION-AWARE PLM BATCH INFERENCE")
    print("=" * 100)

    print("Input:", input_path)
    print("Impression model:", impression_model_dir)
    print("Findings model:", findings_model_dir)
    print("Output dir:", output_dir)
    print("Device:", device)
    print("n_reports:", args.n_reports)
    print("batch_size:", args.batch_size)
    print("max_length:", args.max_length)
    print("require_findings:", args.require_findings)
    print("require_impression:", args.require_impression)

    print("\nReading input file...")
    df = read_input_file(input_path)

    print("Input shape:", df.shape)

    start_time = time.time()

    pipeline = SectionAwarePLMPipeline(
        impression_model_dir=impression_model_dir,
        findings_model_dir=findings_model_dir,
        base_model_name=args.base_model_name,
        device=device,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )

    pipeline.load_models()

    batch_metadata_df, batch_comparison_df = pipeline.run_batch_inference(
        df=df,
        findings_col=args.findings_col,
        impression_col=args.impression_col,
        raw_report_col=args.raw_report_col,
        n_reports=args.n_reports,
        require_findings=args.require_findings,
        require_impression=args.require_impression,
        fallback_to_report_if_no_impression=args.fallback_to_report_if_no_impression,
    )

    runtime_seconds = time.time() - start_time

    metadata_path = output_dir / "section_aware_batch_metadata.parquet"
    comparison_path = output_dir / "section_aware_label_comparison.parquet"
    metadata_csv_path = output_dir / "section_aware_batch_metadata.csv"
    comparison_csv_path = output_dir / "section_aware_label_comparison.csv"
    config_path = output_dir / "section_aware_inference_config.json"
    summary_path = output_dir / "section_aware_inference_summary.json"

    print("\nSaving outputs...")

    batch_metadata_df.to_parquet(metadata_path, index=False)
    batch_comparison_df.to_parquet(comparison_path, index=False)

    batch_metadata_df.to_csv(metadata_csv_path, index=False)
    batch_comparison_df.to_csv(comparison_csv_path, index=False)

    config = {
        "input": str(input_path),
        "impression_model": str(impression_model_dir),
        "findings_model": str(findings_model_dir),
        "output_dir": str(output_dir),
        "findings_col": args.findings_col,
        "impression_col": args.impression_col,
        "raw_report_col": args.raw_report_col,
        "n_reports": args.n_reports,
        "batch_size": args.batch_size,
        "max_length": args.max_length,
        "device": device,
        "base_model_name": args.base_model_name,
        "require_findings": args.require_findings,
        "require_impression": args.require_impression,
        "fallback_to_report_if_no_impression": args.fallback_to_report_if_no_impression,
    }

    summary = {
        "input_shape": list(df.shape),
        "batch_metadata_shape": list(batch_metadata_df.shape),
        "batch_comparison_shape": list(batch_comparison_df.shape),
        "runtime_seconds": runtime_seconds,
        "runtime_minutes": runtime_seconds / 60,
        "n_cases": int(len(batch_metadata_df)),
        "n_label_rows": int(len(batch_comparison_df)),
    }

    if "global_status" in batch_metadata_df.columns:
        summary["global_status_counts"] = (
            batch_metadata_df["global_status"]
            .value_counts(dropna=False)
            .to_dict()
        )

    if "review_recommended" in batch_comparison_df.columns:
        summary["n_label_review_recommended"] = int(
            batch_comparison_df["review_recommended"].sum()
        )

    save_json(config, config_path)
    save_json(summary, summary_path)

    print("\n" + "=" * 100)
    print("DONE")
    print("=" * 100)

    print("Runtime minutes:", round(runtime_seconds / 60, 3))
    print("batch_metadata_df shape:", batch_metadata_df.shape)
    print("batch_comparison_df shape:", batch_comparison_df.shape)

    print("\nSaved files:")
    print("-", metadata_path)
    print("-", comparison_path)
    print("-", metadata_csv_path)
    print("-", comparison_csv_path)
    print("-", config_path)
    print("-", summary_path)


if __name__ == "__main__":
    main()