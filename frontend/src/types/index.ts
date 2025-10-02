export enum SourceType {
    CSV = "csv",
    JSON = "json",
    XML = "xml",
    POSTGRES = "postgres",
    CLICKHOUSE = "clickhouse",
    KAFKA = "kafka",
    HDFS = "hdfs",
}

export enum TargetType {
    POSTGRES = "postgres",
    CLICKHOUSE = "clickhouse",
    HDFS = "hdfs",
}

// Detailed types for the analysis result
export interface ColumnDetails {
    dtype: string;
    null_count: number;
    null_percentage: number;
    unique_count: number;
    sample_values: string[];
    max_length?: number;
    avg_length?: number;
}

export interface DataQuality {
    total_nulls: number;
    duplicate_rows: number;
    completeness_score: number;
    quality_score?: number;  // Для streaming анализа
    null_counts?: Record<string, number>; // Для streaming анализа
    issues?: string[];
}

export interface Recommendations {
    primary_storage: string;
    reasoning: string;
    ddl_suggestions: object;
    indexing_suggestions: any[];
}

// Интерфейс для реального ответа API (через МАС систему)
export interface MASAnalysisResult {
    final_result: {
        reviewed_report?: string;
    };
    analysis_result?: {
        analysis_status: string;
        metadata?: {
            row_count: number;
            column_count: number;
            columns: Record<string, ColumnDetails | string>;
        };
        data_quality?: DataQuality;
        recommendations?: any[];
        llm_recommendations?: any;
    };
    error?: string;
}

// Базовый интерфейс для анализа (если нужен отдельно)
export interface AnalysisResult {
    row_count?: number;
    column_count?: number;
    columns?: Record<string, ColumnDetails | string>;
    data_quality?: DataQuality;
    recommendations?: any[];
    llm_recommendations?: any;
    error?: string;
    raw_response?: MASAnalysisResult;
    streaming_info?: {
        file_size?: number;
        processed_size?: number;
        sample_size?: number;
        analysis_method?: string;
    };
}

// Интерфейс для результата развертывания DAG
export interface DAGDeploymentResult {
    dag_name?: string;
    dag_id?: string;
    status: 'deployed' | 'failed';
    file_path?: string;
    airflow_api_status?: string;
    airflow_dag_url?: string;
    airflow_ui_url?: string;
    message?: string;
    error?: string;
    instructions?: {
        step1?: string;
        step2?: string;
        step3?: string;
        step4?: string;
    };
}
