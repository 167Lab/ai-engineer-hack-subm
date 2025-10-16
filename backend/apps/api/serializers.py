from rest_framework import serializers
from .types import SourceType, TargetType

CHOICE_SOURCE = [e.value for e in SourceType]
CHOICE_TARGET = [e.value for e in TargetType]

class DataSourceAnalysisRequestSer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=CHOICE_SOURCE)
    connection_params = serializers.DictField()
    sample_size = serializers.IntegerField(required=False, default=1000, min_value=1)
    target_candidates = serializers.ListField(
        child=serializers.ChoiceField(choices=CHOICE_TARGET),
        required=False, allow_null=True
    )

class DataSourceAnalysisResponseSer(serializers.Serializer):
    metadata = serializers.DictField()
    recommendations = serializers.ListField(child=serializers.DictField())
    proposed_ddl = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    estimated_volume = serializers.IntegerField(required=False, allow_null=True)
    data_quality_issues = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )

class DAGGenerationRequestSer(serializers.Serializer):
    source_config = serializers.DictField()
    target_config = serializers.DictField()
    transformations = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    schedule = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dag_name = serializers.CharField()

class DAGDeploymentRequestSer(serializers.Serializer):
    dag_name = serializers.CharField()
    source_config = serializers.DictField()
    target_config = serializers.DictField(required=False, default=dict)
    schedule = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    owner = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    retries = serializers.IntegerField(required=False, default=1, min_value=0)
    retry_delay = serializers.IntegerField(required=False, default=5, min_value=0)
