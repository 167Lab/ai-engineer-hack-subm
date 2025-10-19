from django.urls import path
from .views import (
    AnalyzeDataSourceView, GenerateDAGView,
    GetRecommendationsView, DeployDAGView,
    DeleteDAGCompleteView, CleanupOrphanedDAGsView,
    DAGHealthReportView, AnalyzeFileStreamView,
    UploadChunkView, FinalizeChunkedUploadView, CleanupUploadView,
    ListFilesView, PreviewFileView, LoginView, AirflowBootstrapSessionView, AirflowProxyView, LogoutView,
    LLMHealthView, GeneratePipelineView, GenerateReportView
)

urlpatterns = [
    path("analyze", AnalyzeDataSourceView.as_view(), name="analyze"),
    path("analyze_file_stream", AnalyzeFileStreamView.as_view(), name="analyze_file_stream"),
    path("generate_dag", GenerateDAGView.as_view(), name="generate_dag"),
    path("recommendations", GetRecommendationsView.as_view(), name="recommendations"),
    path("deploy_dag", DeployDAGView.as_view(), name="deploy_dag"),
    
    # Production DAG Management API
    path("delete_dag_complete/<str:dag_id>", DeleteDAGCompleteView.as_view(), name="delete_dag_complete"),
    path("dags/cleanup_orphaned", CleanupOrphanedDAGsView.as_view(), name="cleanup_orphaned_dags"),
    path("dags/health_report", DAGHealthReportView.as_view(), name="dag_health_report"),
    
    # Chunked File Upload API (для больших файлов)
    path("upload_chunk", UploadChunkView.as_view(), name="upload_chunk"),
    path("finalize_chunked_upload", FinalizeChunkedUploadView.as_view(), name="finalize_chunked_upload"), 
    path("cleanup_upload", CleanupUploadView.as_view(), name="cleanup_upload"),
    # File browsing and preview
    path("list_files", ListFilesView.as_view(), name="list_files"),
    path("preview", PreviewFileView.as_view(), name="preview"),
    # Auth and Airflow SSO bootstrap
    path("auth/login", LoginView.as_view(), name="auth_login"),
    path("auth/logout", LogoutView.as_view(), name="auth_logout"),
    path("airflow/bootstrap-session", AirflowBootstrapSessionView.as_view(), name="airflow_bootstrap_session"),
    path("airflow/proxy/<path:subpath>", AirflowProxyView.as_view(), name="airflow_proxy"),
    # LLM health
    path("llm/health", LLMHealthView.as_view(), name="llm_health"),
    
    # Staged pipeline generation
    path("generate_pipeline", GeneratePipelineView.as_view(), name="generate_pipeline"),
    path("generate_report", GenerateReportView.as_view(), name="generate_report"),
]
