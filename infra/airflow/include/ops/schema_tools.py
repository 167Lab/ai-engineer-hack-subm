from typing import Dict, Any

def infer_schema(source_ref: Dict[str, Any], sample_rows: int) -> Dict[str, Any]:
    return {"schema": {}}

def cast_types(data_ref: Dict[str, Any], casts: Dict[str, str], locale: str) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}

def parse_time(data_ref: Dict[str, Any], col: str, tz: str, round_to: str | None, add_cohort: bool) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}


