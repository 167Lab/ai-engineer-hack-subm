import React from 'react';
import { Descriptions, Tag, Progress, Card, Alert } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { AnalysisResult, ColumnDetails } from '../types';

interface AnalysisDisplayProps {
    analysisResult: AnalysisResult | null;
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ analysisResult }) => {
    if (!analysisResult) {
        return <Alert message="Нет данных для отображения." type="info" />;
    }

    const { row_count, column_count, columns, data_quality, recommendations, error, raw_response } = analysisResult;

    if (error) {
        return <Alert message={`Ошибка анализа: ${error}`} type="error" />;
    }
    
    // Показываем базовую информацию если есть сырой ответ МАС системы
    if (raw_response && !row_count && !column_count) {
        return (
            <Card title="Результаты анализа МАС системы">
                <Alert 
                    message="Анализ завершен успешно!" 
                    description={raw_response.final_result?.reviewed_report || "Данные обработаны мультиагентной системой"}
                    type="success" 
                    showIcon
                />
                {raw_response.analysis_result && (
                    <div style={{ marginTop: 16 }}>
                        <p><strong>Статус анализа:</strong> {raw_response.analysis_result.analysis_status}</p>
                        {raw_response.analysis_result.llm_recommendations && (
                            <div style={{ marginTop: 16 }}>
                                <h4>Рекомендации ИИ:</h4>
                                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '6px', whiteSpace: 'pre-wrap' }}>
                                    {JSON.stringify(raw_response.analysis_result.llm_recommendations, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </Card>
        );
    }
    
    // Fallback for empty results
    if (!row_count && !column_count) {
        return <Alert message="Анализ не вернул детальных результатов. Проверьте параметры источника." type="warning" />;
    }

    return (
        <Card title="Результаты анализа источника данных">
            <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Количество строк (в выборке)">{row_count}</Descriptions.Item>
                <Descriptions.Item label="Количество колонок">{column_count}</Descriptions.Item>

                {data_quality && (
                    <Descriptions.Item label="Качество данных" span={2}>
                        <Progress percent={Math.round(data_quality.completeness_score * 100)} status="active" />
                        <div style={{ marginTop: 8 }}>
                            <Tag color="volcano">Пропущено значений: {data_quality.total_nulls}</Tag>
                            <Tag color="red">Дубликатов строк: {data_quality.duplicate_rows}</Tag>
                        </div>
                    </Descriptions.Item>
                )}

                <Descriptions.Item label="Рекомендации по хранилищу" span={2}>
                    {recommendations && recommendations.length > 0 ? (
                        recommendations.map((rec: any, idx: number) => (
                            <div key={idx} style={{ marginBottom: 8 }}>
                                <Tag icon={<CheckCircleOutlined />} color="success">
                                    {rec.storage_type || rec.primary_storage}
                                </Tag>
                                <span>{rec.reasoning}</span>
                                {rec.confidence && (
                                    <span style={{ marginLeft: 8, color: '#666' }}>
                                        (Уверенность: {Math.round(rec.confidence * 100)}%)
                                    </span>
                                )}
                            </div>
                        ))
                    ) : (
                        <span style={{ color: '#999' }}>Рекомендации не сгенерированы</span>
                    )}
                </Descriptions.Item>
            </Descriptions>

            <h4 style={{ marginTop: 24 }}>Анализ колонок:</h4>
            {columns && Object.entries(columns).map(([colName, colDetails]: [string, ColumnDetails]) => (
                <Card key={colName} size="small" title={colName} style={{ marginBottom: 16 }}>
                    <Descriptions column={1} size="small">
                        <Descriptions.Item label="Тип данных"><Tag>{colDetails.dtype}</Tag></Descriptions.Item>
                        <Descriptions.Item label="Пропущено">{`${colDetails.null_count} (${colDetails.null_percentage.toFixed(2)}%)`}</Descriptions.Item>
                        <Descriptions.Item label="Уникальных значений">{colDetails.unique_count}</Descriptions.Item>
                        <Descriptions.Item label="Примеры значений">
                            {colDetails.sample_values.map((val: string, i: number) => <Tag key={i} color="blue">{val}</Tag>)}
                        </Descriptions.Item>
                    </Descriptions>
                </Card>
            ))}
        </Card>
    );
};

export default AnalysisDisplay;
