NODE_TPL = {
    "Source.FileRead":      "airflow/nodes/source/file_read.j2",
    "Source.DBQuery":       "airflow/nodes/source/db_query.j2",
    "Source.CloudStorage":  "airflow/nodes/source/cloud_storage.j2",
    "Schema.Infer":         "airflow/nodes/schema/infer.j2",
    "Type.Cast":            "airflow/nodes/schema/type_cast.j2",
    "Time.Parse":           "airflow/nodes/schema/time_parse.j2",
    "Clean.Deduplicate":    "airflow/nodes/clean/deduplicate.j2",
    "Clean.Nulls":          "airflow/nodes/clean/nulls.j2",
    "Clean.Text":           "airflow/nodes/clean/text.j2",
    "Transform.Join":       "airflow/nodes/transform/join.j2",
    "Transform.Aggregate":  "airflow/nodes/transform/aggregate.j2",
    "Transform.SortRank":   "airflow/nodes/transform/sort_rank.j2",
    "Transform.Pivot":      "airflow/nodes/transform/pivot.j2",
    "DQ.Profile":           "airflow/nodes/dq/profile.j2",
    "Sink.DBWrite":         "airflow/nodes/sink/db_write.j2",
    "Sink.DataLake":        "airflow/nodes/sink/data_lake.j2",
    "Sink.Files":           "airflow/nodes/sink/files.j2",
    # Orchestration / Ops
    "Orch.Partitioning":    "airflow/nodes/orch/partitioning.j2",
    "Orch.Trigger":         "airflow/nodes/orch/trigger.j2",
    "Audit.Log":            "airflow/nodes/orch/audit_log.j2",
    # AI helpers
    "AI.StoreRecommend":    "airflow/nodes/ai/store_recommend.j2",
    "AI.DDLGenerate":       "airflow/nodes/ai/ddl_generate.j2",
    "AI.QueryAssist":       "airflow/nodes/ai/query_assist.j2",
    "AI.Report":            "airflow/nodes/ai/report.j2",
}


