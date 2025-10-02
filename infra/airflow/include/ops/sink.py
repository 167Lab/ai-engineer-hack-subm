from typing import Dict, Any, List

def write_table(engine: str, data_ref: Dict[str, Any], table: str, mode: str, batch_size: int) -> Dict[str, Any]:
    return {"engine": engine, "table": table, "rows": 0}

def write_datalake(fmt: str, data_ref: Dict[str, Any], path: str, partition_by: List[str], storage: str, mode: str) -> Dict[str, Any]:
    return {"path": path, "format": fmt, "partitions": partition_by}

def export_files(data_ref: Dict[str, Any], fmt: str, path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    return {"path": path, "format": fmt}


