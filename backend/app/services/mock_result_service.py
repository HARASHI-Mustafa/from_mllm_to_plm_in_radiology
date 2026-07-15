import json

from app.core.config import MOCK_OUTPUT_JSON


def load_mock_analysis_result() -> dict:
    with MOCK_OUTPUT_JSON.open("r", encoding="utf-8") as result_file:
        return json.load(result_file)
