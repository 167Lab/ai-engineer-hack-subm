import csv
import json
from typing import Any, Dict


class HybridFileAnalyzer:
    """
    Minimal analyzer for uploaded files to support streaming UI flow.
    - CSV: reads a small sample, infers simple column stats
    - JSON: attempts to parse NDJSON or array and build basic schema
    - XML: returns stub metadata (can be extended later)
    """

    def analyze_uploaded_file(self, file_path: str, source_type: str, sample_size: int = 1000, original_filename: str = "") -> Dict[str, Any]:
        source_type = (source_type or "csv").lower()
        if source_type == "csv":
            return self._analyze_csv(file_path, sample_size, original_filename)
        if source_type == "json":
            return self._analyze_json(file_path, sample_size, original_filename)
        if source_type == "xml":
            return self._analyze_xml(file_path, sample_size, original_filename)
        # default fallback
        return {
            "original_filename": original_filename,
            "source_type": source_type,
            "total_rows": 0,
            "columns": [],
            "column_types": {},
            "null_counts": {},
            "data_quality_score": 100,
        }

    def _analyze_csv(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        rows = 0
        columns = []
        null_counts: Dict[str, int] = {}
        types: Dict[str, str] = {}
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []
                for col in columns:
                    null_counts[col] = 0
                for i, row in enumerate(reader):
                    if i >= sample_size:
                        break
                    rows += 1
                    for col in columns:
                        val = row.get(col)
                        if val in (None, ""):
                            null_counts[col] += 1
                        else:
                            # naive typing
                            if col not in types:
                                types[col] = self._guess_type(val)
        except Exception:
            pass
        return {
            "original_filename": original_filename,
            "source_type": "csv",
            "total_rows": rows,
            "columns": columns,
            "column_types": {c: types.get(c, "string") for c in columns},
            "null_counts": null_counts,
            "data_quality_score": 100,
        }

    def _analyze_json(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        rows = 0
        columns: Dict[str, str] = {}
        null_counts: Dict[str, int] = {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                first = f.read(1)
                f.seek(0)
                if first == "[":
                    data = json.load(f)
                    iterable = data if isinstance(data, list) else []
                else:
                    iterable = (json.loads(line) for line in f if line.strip())
                for i, obj in enumerate(iterable):
                    if i >= sample_size:
                        break
                    if isinstance(obj, dict):
                        rows += 1
                        for k, v in obj.items():
                            if k not in columns:
                                columns[k] = self._guess_type(v)
                            if v in (None, ""):
                                null_counts[k] = null_counts.get(k, 0) + 1
        except Exception:
            pass
        return {
            "original_filename": original_filename,
            "source_type": "json",
            "total_rows": rows,
            "columns": list(columns.keys()),
            "column_types": columns,
            "null_counts": null_counts,
            "data_quality_score": 100,
        }

    def _analyze_xml(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        # Stub: parsing XML robustly requires more logic; return minimal metadata
        return {
            "original_filename": original_filename,
            "source_type": "xml",
            "total_rows": 0,
            "columns": [],
            "column_types": {},
            "null_counts": {},
            "data_quality_score": 100,
        }

    def _guess_type(self, value: Any) -> str:
        if isinstance(value, (int, float)):
            return "number"
        s = str(value)
        try:
            int(s)
            return "integer"
        except Exception:
            pass
        try:
            float(s)
            return "number"
        except Exception:
            pass
        if s.lower() in ("true", "false"):
            return "boolean"
        return "string"


