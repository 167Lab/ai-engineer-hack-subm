from typing import Dict, Any, List

def join_tables(left_ref: Dict[str, Any], right_ref: Dict[str, Any], on: List[str], how: str, suffixes: List[str]) -> Dict[str, Any]:
    return {"staging_path": left_ref.get("staging_path", "")}

def aggregate(data_ref: Dict[str, Any], group_by: List[str], metrics: Dict[str, Any], engine: str | None) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}

def sort_rank(data_ref: Dict[str, Any], order_by: List[Dict[str, Any]], partition_by: List[str], top_n: int | None) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}

def pivot(data_ref: Dict[str, Any], index: List[str], columns: List[str], values: List[str], aggfunc: str, fill_value: Any | None) -> Dict[str, Any]:
    return {"staging_path": data_ref.get("staging_path", "")}


