"""
Section-aware PLM inference pipeline.

This module connects:
- text validation,
- optional raw report section parsing,
- section-specific PLM prediction,
- Findings/Impression fusion,
- case-level metadata creation.

Supported modes:

1. Dataset mode:
   Uses already separated columns:
   - section_findings
   - section_impression

2. Raw-report mode:
   Uses full raw report text:
   - report
   Then section_parser.py extracts Findings and Impression.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import torch

from plm_inference.fusion import (
    fuse_impression_and_findings,
    fused_output_to_rows,
    summarize_fused_output,
)
from plm_inference.model import (
    load_full_finetuned_model,
    predict_one_text,
    predict_texts_batch,
)
from plm_inference.section_parser import parse_report_sections
from plm_inference.text_utils import (
    clean_text_or_none,
    combine_report_sections,
    detect_timepoints,
    valid_text,
)


class SectionAwarePLMPipeline:
    """
    Reusable section-aware PLM inference pipeline.

    The pipeline loads two models:
    1. Impression extractor
    2. Findings extractor

    It can work in two modes:
    - separated-section mode
    - raw-report parser mode
    """

    def __init__(
        self,
        impression_model_dir: Union[str, Path],
        findings_model_dir: Union[str, Path],
        base_model_name: str = "StanfordAIMI/RadBERT",
        device: Optional[Union[str, torch.device]] = None,
        max_length: int = 256,
        batch_size: int = 16,
    ):
        self.impression_model_dir = Path(impression_model_dir)
        self.findings_model_dir = Path(findings_model_dir)
        self.base_model_name = base_model_name
        self.device = torch.device(
            device if device is not None else (
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        )
        self.max_length = max_length
        self.batch_size = batch_size

        self.impression_model = None
        self.impression_tokenizer = None
        self.findings_model = None
        self.findings_tokenizer = None

    def load_models(self) -> None:
        """
        Load Impression and Findings PLM extractors.
        """
        print("Loading Impression model from:", self.impression_model_dir)

        self.impression_model, self.impression_tokenizer = load_full_finetuned_model(
            model_dir=self.impression_model_dir,
            base_model_name=self.base_model_name,
            device=self.device,
        )

        print("Loading Findings model from:", self.findings_model_dir)

        self.findings_model, self.findings_tokenizer = load_full_finetuned_model(
            model_dir=self.findings_model_dir,
            base_model_name=self.base_model_name,
            device=self.device,
        )

    def _check_models_loaded(self) -> None:
        """
        Raise an error if models are not loaded.
        """
        if self.impression_model is None or self.impression_tokenizer is None:
            raise RuntimeError(
                "Impression model is not loaded. "
                "Call pipeline.load_models() first."
            )

        if self.findings_model is None or self.findings_tokenizer is None:
            raise RuntimeError(
                "Findings model is not loaded. "
                "Call pipeline.load_models() first."
            )

    def run_single_report_inference(
        self,
        findings_text: Optional[str] = None,
        impression_text: Optional[str] = None,
        raw_report_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_raw_report_parser: bool = False,
        parser_use_fallback: bool = False,
        fallback_to_report_if_no_impression: bool = False,
    ) -> Dict[str, Any]:
        """
        Run section-aware inference for one report.

        Parameters
        ----------
        findings_text:
            Optional Findings section text.

        impression_text:
            Optional Impression section text.

        raw_report_text:
            Optional full raw report text.

        metadata:
            Optional metadata dictionary.

        use_raw_report_parser:
            If True, parse raw_report_text to extract Findings and Impression.
            Parsed sections are used when provided sections are missing.

        parser_use_fallback:
            If True, allows the parser to use conservative fallback rules.

        fallback_to_report_if_no_impression:
            If True, use the full raw report as Impression input when
            Impression is still missing after parsing. Default is False.

        Returns
        -------
        Dictionary with:
        - metadata
        - section availability
        - parser information
        - section outputs
        - fused findings
        - summary
        - label rows
        """
        self._check_models_loaded()

        metadata = metadata or {}

        findings_clean = clean_text_or_none(findings_text)
        impression_clean = clean_text_or_none(impression_text)

        parser_status = "parser_not_used"
        parser_detected_sections: List[str] = []
        parser_n_detected_sections = 0

        findings_source = "provided_section" if findings_clean is not None else "none"
        impression_source = "provided_section" if impression_clean is not None else "none"

        if use_raw_report_parser:
            parsed = parse_report_sections(
                raw_report_text,
                use_fallback=parser_use_fallback,
            )

            parser_status = parsed["parser_status"]
            parser_detected_sections = parsed["detected_sections"]
            parser_n_detected_sections = parsed["n_detected_sections"]

            if findings_clean is None and clean_text_or_none(parsed["findings_text"]) is not None:
                findings_clean = clean_text_or_none(parsed["findings_text"])
                findings_source = "parsed_raw_report"

            if impression_clean is None and clean_text_or_none(parsed["impression_text"]) is not None:
                impression_clean = clean_text_or_none(parsed["impression_text"])
                impression_source = "parsed_raw_report"

        used_fallback_as_impression = False

        if (
            impression_clean is None
            and fallback_to_report_if_no_impression
            and valid_text(raw_report_text)
        ):
            impression_clean = clean_text_or_none(raw_report_text)
            impression_source = "raw_report_fallback"
            used_fallback_as_impression = True

        combined_text = combine_report_sections(
            findings_text=findings_clean,
            impression_text=impression_clean,
        )

        if not valid_text(combined_text) and valid_text(raw_report_text):
            combined_text = str(raw_report_text).strip()

        timepoints = detect_timepoints(combined_text)

        impression_output = predict_one_text(
            text=impression_clean,
            model=self.impression_model,
            tokenizer=self.impression_tokenizer,
            device=self.device,
            max_length=self.max_length,
        )

        findings_output = predict_one_text(
            text=findings_clean,
            model=self.findings_model,
            tokenizer=self.findings_tokenizer,
            device=self.device,
            max_length=self.max_length,
        )

        fused = fuse_impression_and_findings(
            impression_output=impression_output,
            findings_output=findings_output,
            apply_consistency_rules=True,
        )

        summary = summarize_fused_output(fused)

        case_id = metadata.get("case_id", 1)

        label_rows = fused_output_to_rows(
            case_id=case_id,
            fused=fused,
        )

        result = {
            "metadata": {
                **metadata,
                "findings_available": findings_clean is not None,
                "impression_available": impression_clean is not None,
                "findings_source": findings_source,
                "impression_source": impression_source,
                "use_raw_report_parser": use_raw_report_parser,
                "parser_status": parser_status,
                "parser_detected_sections": parser_detected_sections,
                "parser_n_detected_sections": parser_n_detected_sections,
                "used_fallback_as_impression": used_fallback_as_impression,
                "multi_timepoint_report": len(timepoints) > 1,
                "n_detected_timepoints": len(timepoints),
                "detected_timepoints": timepoints,
            },
            "findings_text": findings_clean,
            "impression_text": impression_clean,
            "impression_output": impression_output,
            "findings_output": findings_output,
            "fused_findings": fused,
            "summary": summary,
            "label_rows": label_rows,
        }

        return result

    def run_raw_report_inference(
        self,
        raw_report_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        parser_use_fallback: bool = False,
        fallback_to_report_if_no_impression: bool = False,
    ) -> Dict[str, Any]:
        """
        Convenience method for final raw-report use.

        Input:
        - raw full report text

        Output:
        - parsed sections
        - PLM outputs
        - fused structured findings
        """
        return self.run_single_report_inference(
            findings_text=None,
            impression_text=None,
            raw_report_text=raw_report_text,
            metadata=metadata,
            use_raw_report_parser=True,
            parser_use_fallback=parser_use_fallback,
            fallback_to_report_if_no_impression=fallback_to_report_if_no_impression,
        )

    def run_batch_inference(
        self,
        df: pd.DataFrame,
        findings_col: str = "section_findings",
        impression_col: str = "section_impression",
        raw_report_col: str = "report",
        n_reports: Optional[int] = None,
        require_findings: bool = True,
        require_impression: bool = True,
        fallback_to_report_if_no_impression: bool = False,
        metadata_cols: Optional[List[str]] = None,
        use_raw_report_parser: bool = False,
        parser_use_fallback: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run section-aware inference on a batch of reports.

        In dataset mode:
            Uses findings_col and impression_col.

        In raw-report parser mode:
            Uses raw_report_col and section_parser.py.
            If separated section columns exist, they are used first.
            Parsed sections are used when separated sections are missing.

        Returns
        -------
        batch_metadata_df:
            One row per report.

        batch_comparison_df:
            One row per report per finding.
        """
        self._check_models_loaded()

        working_df = df.copy()

        has_findings_col = findings_col in working_df.columns
        has_impression_col = impression_col in working_df.columns
        has_raw_report_col = raw_report_col is not None and raw_report_col in working_df.columns

        if not use_raw_report_parser:
            if not has_findings_col:
                raise ValueError(f"Missing findings column: {findings_col}")

            if not has_impression_col:
                raise ValueError(f"Missing impression column: {impression_col}")

        if use_raw_report_parser and not has_raw_report_col:
            raise ValueError(
                f"Raw-report parser mode requires raw report column: {raw_report_col}"
            )

        if metadata_cols is None:
            metadata_cols = [
                "path_to_image",
                "path_to_dcm",
                "deid_patient_id",
                "split",
            ]

        metadata_cols = [
            col for col in metadata_cols
            if col in working_df.columns
        ]

        # ------------------------------------------------------------
        # Prepare raw report texts
        # ------------------------------------------------------------
        if has_raw_report_col:
            raw_report_texts = working_df[raw_report_col].tolist()
        else:
            raw_report_texts = [None] * len(working_df)

        # ------------------------------------------------------------
        # Prepare provided section texts
        # ------------------------------------------------------------
        if has_findings_col:
            provided_findings_texts = [
                clean_text_or_none(value)
                for value in working_df[findings_col].tolist()
            ]
        else:
            provided_findings_texts = [None] * len(working_df)

        if has_impression_col:
            provided_impression_texts = [
                clean_text_or_none(value)
                for value in working_df[impression_col].tolist()
            ]
        else:
            provided_impression_texts = [None] * len(working_df)

        # These are the actual section texts that will be sent to models.
        pipeline_findings_texts = list(provided_findings_texts)
        pipeline_impression_texts = list(provided_impression_texts)

        findings_sources = [
            "provided_section" if text is not None else "none"
            for text in pipeline_findings_texts
        ]

        impression_sources = [
            "provided_section" if text is not None else "none"
            for text in pipeline_impression_texts
        ]

        parser_statuses = ["parser_not_used"] * len(working_df)
        parser_detected_sections = [[] for _ in range(len(working_df))]
        parser_n_detected_sections = [0] * len(working_df)

        # ------------------------------------------------------------
        # Optional raw report parsing
        # ------------------------------------------------------------
        if use_raw_report_parser:
            print("Parsing raw reports into Findings and Impression sections...")

            for idx, raw_report_text in enumerate(raw_report_texts):
                parsed = parse_report_sections(
                    raw_report_text,
                    use_fallback=parser_use_fallback,
                )

                parser_statuses[idx] = parsed["parser_status"]
                parser_detected_sections[idx] = parsed["detected_sections"]
                parser_n_detected_sections[idx] = parsed["n_detected_sections"]

                parsed_findings = clean_text_or_none(parsed["findings_text"])
                parsed_impression = clean_text_or_none(parsed["impression_text"])

                if pipeline_findings_texts[idx] is None and parsed_findings is not None:
                    pipeline_findings_texts[idx] = parsed_findings
                    findings_sources[idx] = "parsed_raw_report"

                if pipeline_impression_texts[idx] is None and parsed_impression is not None:
                    pipeline_impression_texts[idx] = parsed_impression
                    impression_sources[idx] = "parsed_raw_report"

        # ------------------------------------------------------------
        # Optional fallback: full report as Impression
        # ------------------------------------------------------------
        used_fallback_as_impression = [False] * len(working_df)

        if fallback_to_report_if_no_impression:
            for idx in range(len(pipeline_impression_texts)):
                if (
                    pipeline_impression_texts[idx] is None
                    and valid_text(raw_report_texts[idx])
                ):
                    pipeline_impression_texts[idx] = clean_text_or_none(raw_report_texts[idx])
                    impression_sources[idx] = "raw_report_fallback"
                    used_fallback_as_impression[idx] = True

        # ------------------------------------------------------------
        # Add temporary columns for filtering
        # ------------------------------------------------------------
        working_df["_pipeline_findings_text"] = pipeline_findings_texts
        working_df["_pipeline_impression_text"] = pipeline_impression_texts
        working_df["_findings_source"] = findings_sources
        working_df["_impression_source"] = impression_sources
        working_df["_parser_status"] = parser_statuses
        working_df["_parser_detected_sections"] = parser_detected_sections
        working_df["_parser_n_detected_sections"] = parser_n_detected_sections
        working_df["_used_fallback_as_impression"] = used_fallback_as_impression

        working_df["_findings_valid"] = working_df["_pipeline_findings_text"].apply(valid_text)
        working_df["_impression_valid"] = working_df["_pipeline_impression_text"].apply(valid_text)

        if require_findings:
            working_df = working_df[working_df["_findings_valid"]].copy()

        if require_impression:
            working_df = working_df[working_df["_impression_valid"]].copy()

        if n_reports is not None:
            working_df = working_df.head(n_reports).copy()

        working_df = working_df.reset_index(drop=True)

        print("Batch size:", len(working_df))
        print("require_findings:", require_findings)
        print("require_impression:", require_impression)
        print("use_raw_report_parser:", use_raw_report_parser)

        findings_texts = working_df["_pipeline_findings_text"].tolist()
        impression_texts = working_df["_pipeline_impression_text"].tolist()

        raw_report_texts = (
            working_df[raw_report_col].tolist()
            if has_raw_report_col
            else [None] * len(working_df)
        )

        # ------------------------------------------------------------
        # Model prediction
        # ------------------------------------------------------------
        print("Predicting Impression sections...")

        impression_outputs = predict_texts_batch(
            texts=impression_texts,
            model=self.impression_model,
            tokenizer=self.impression_tokenizer,
            device=self.device,
            batch_size=self.batch_size,
            max_length=self.max_length,
        )

        print("Predicting Findings sections...")

        findings_outputs = predict_texts_batch(
            texts=findings_texts,
            model=self.findings_model,
            tokenizer=self.findings_tokenizer,
            device=self.device,
            batch_size=self.batch_size,
            max_length=self.max_length,
        )

        # ------------------------------------------------------------
        # Fusion and metadata
        # ------------------------------------------------------------
        metadata_rows: List[Dict[str, Any]] = []
        comparison_rows: List[Dict[str, Any]] = []

        for idx, row in working_df.iterrows():
            case_id = idx + 1

            findings_clean = row["_pipeline_findings_text"]
            impression_clean = row["_pipeline_impression_text"]
            raw_report_text = raw_report_texts[idx]

            combined_text = combine_report_sections(
                findings_text=findings_clean,
                impression_text=impression_clean,
            )

            if not valid_text(combined_text) and valid_text(raw_report_text):
                combined_text = str(raw_report_text).strip()

            timepoints = detect_timepoints(combined_text)

            fused = fuse_impression_and_findings(
                impression_output=impression_outputs[idx],
                findings_output=findings_outputs[idx],
                apply_consistency_rules=True,
            )

            summary = summarize_fused_output(fused)

            metadata = {
                "case_id": case_id,
                "findings_available": findings_clean is not None,
                "impression_available": impression_clean is not None,
                "findings_source": row["_findings_source"],
                "impression_source": row["_impression_source"],
                "use_raw_report_parser": use_raw_report_parser,
                "parser_status": row["_parser_status"],
                "parser_detected_sections": row["_parser_detected_sections"],
                "parser_n_detected_sections": row["_parser_n_detected_sections"],
                "used_fallback_as_impression": row["_used_fallback_as_impression"],
                "multi_timepoint_report": len(timepoints) > 1,
                "n_detected_timepoints": len(timepoints),
                **summary,
            }

            for col in metadata_cols:
                metadata[col] = row[col]

            metadata_rows.append(metadata)

            comparison_rows.extend(
                fused_output_to_rows(
                    case_id=case_id,
                    fused=fused,
                )
            )

        batch_metadata_df = pd.DataFrame(metadata_rows)
        batch_comparison_df = pd.DataFrame(comparison_rows)

        return batch_metadata_df, batch_comparison_df