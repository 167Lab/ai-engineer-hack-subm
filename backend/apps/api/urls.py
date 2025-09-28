from django.urls import path
from .views import (
    AnalyzeDataSourceView, GenerateDAGView,
    GetRecommendationsView, DeployDAGView
)

urlpatterns = [
    path("analyze", AnalyzeDataSourceView.as_view(), name="analyze"),
    path("generate_dag", GenerateDAGView.as_view(), name="generate_dag"),
    path("recommendations", GetRecommendationsView.as_view(), name="recommendations"),
    path("deploy_dag", DeployDAGView.as_view(), name="deploy_dag"),
]
