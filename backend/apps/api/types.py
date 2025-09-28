from enum import Enum

class SourceType(str, Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"
    KAFKA = "kafka"
    HDFS = "hdfs"

class TargetType(str, Enum):
    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"
    HDFS = "hdfs"
