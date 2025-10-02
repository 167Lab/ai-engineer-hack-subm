from django.urls import path
from .views import (
    AnalyzeDataSourceView, GenerateDAGView,
    GetRecommendationsView, DeployDAGView,
    DeleteDAGCompleteView, CleanupOrphanedDAGsView,
    DAGHealthReportView, AnalyzeFileStreamView,
    UploadChunkView, FinalizeChunkedUploadView, CleanupUploadView
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
]
