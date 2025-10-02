from typing import Dict, Any, List

def deduplicate(data_ref: Dict[str, Any], keys: List[str], ts_col: str | None, keep: str) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", ""), "removed": 0}

def handle_nulls(data_ref: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}

def normalize_text(data_ref: Dict[str, Any], columns: List[str], ops: List[str]) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}


