from typing import Dict, Any

def recommend_store(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {"engine": "clickhouse", "reason": "stub"}

def generate_ddl(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {"engine": "postgres", "ddl": ""}

def generate_query(prompt: str, dialect: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"sql": "SELECT 1"}

def build_report(artifacts: Dict[str, Any]) -> Dict[str, Any]:
    return {"report_path": ""}


