from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from .serializers import (
    DataSourceAnalysisRequestSer, DAGGenerationRequestSer,
    DataSourceAnalysisResponseSer, DAGDeploymentRequestSer
)
from apps.agents.integration import MASIntegration
from services.airflow import render_dag_py, deploy_dag_to_airflow, get_recs_for_source

# Create your views here.

# /api/v1/analyze
class AnalyzeDataSourceView(APIView):
    def post(self, request):
        import asyncio
        
        ser = DataSourceAnalysisRequestSer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        try:
            mas = MASIntegration()
            # Запускаем async функцию в event loop
            result = asyncio.run(mas.analyze_data_source(ser.validated_data))
            return Response(result)
        except Exception as e:
            return Response({
                'error': str(e),
                'status': 'failed'
            }, status=400)

# /api/v1/generate_dag
class GenerateDAGView(APIView):
    def post(self, request):
        ser = DAGGenerationRequestSer(data=request.data)
        ser.is_valid(raise_exception=True)
        dag_py, dag_id = render_dag_py(ser.validated_data)
        return Response({"dag_id": dag_id, "dag_py": dag_py})

# /api/v1/recommendations?source_id=...
class GetRecommendationsView(APIView):
    def get(self, request):
        source_id = request.query_params.get("source_id")
        if not source_id:
            raise ValidationError({"source_id": "This query parameter is required"})
        recs = get_recs_for_source(source_id)
        return Response({"source_id": source_id, "recommendations": recs})

# /api/v1/deploy_dag
class DeployDAGView(APIView):
    def post(self, request):
        ser = DAGDeploymentRequestSer(data=request.data)
        ser.is_valid(raise_exception=True)
        deploy_info = deploy_dag_to_airflow(ser.validated_data)
        return Response(deploy_info)
