import React from 'react';
import { Descriptions, Tag, Progress, Card, Alert, Table, Typography } from 'antd';
import { AnalysisResult } from '../types';
import { previewFile } from '../services/api';

const { Text } = Typography;

interface AnalysisDisplayProps {
    analysisResult: AnalysisResult | null;
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ analysisResult }) => {
    if (!analysisResult) {
        return <Alert message="Нет данных для отображения." type="info" />;
    }

    const { row_count, column_count, columns, data_quality, error, raw_response } = analysisResult;

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

    const [preview, setPreview] = React.useState<{ columns: string[]; rows: any[] } | null>(null);
    const [loadingPreview, setLoadingPreview] = React.useState(false);

    React.useEffect(() => {
        // авто-предпросмотр, если есть путь к файлу и тип
        const filePath = analysisResult?.raw_response?.file_info?.persisted_path;
        const sourceType = analysisResult?.raw_response?.file_info?.source_type;
        if (filePath && sourceType) {
            setLoadingPreview(true);
            previewFile({ path: filePath, type: sourceType as any, rows: 50 })
                .then(setPreview)
                .finally(() => setLoadingPreview(false));
        } else {
            setPreview(null);
        }
    }, [analysisResult?.raw_response?.file_info?.persisted_path, analysisResult?.raw_response?.file_info?.source_type]);

    return (
        <Card title="Результаты анализа источника данных">
            <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Количество строк (в выборке)">{row_count}</Descriptions.Item>
                <Descriptions.Item label="Количество колонок">{column_count}</Descriptions.Item>

                {data_quality && (
                <Descriptions.Item label="Качество данных" span={2}>
                    {(() => {
                        const score = data_quality.completeness_score ?? 100;
                        const percent = score > 1 ? Math.round(score) : Math.round(score * 100);
                        return <Progress percent={percent} status="active" />;
                    })()}
                        <div style={{ marginTop: 8 }}>
                            <Tag color="volcano">Пропущено значений: {data_quality.total_nulls}</Tag>
                            <Tag color="red">Дубликатов строк: {data_quality.duplicate_rows}</Tag>
                        </div>
                    </Descriptions.Item>
                )}
            </Descriptions>

            <h4 style={{ marginTop: 24 }}>Анализ колонок</h4>
            <Table
                size="small"
                pagination={false}
                dataSource={Object.entries(columns || {}).map(([colName, cd]: [string, any]) => {
                    const isSimple = typeof cd === 'string';
                    const dtype = isSimple ? cd : cd.dtype;
                    const nullCount = isSimple ? (data_quality?.null_counts?.[colName] ?? 0) : (cd.null_count ?? 0);
                    const perc = row_count ? (nullCount / row_count * 100) : 0;
                    const uniqueCount = isSimple ? '-' : (cd.unique_count ?? '-');
                    return { key: colName, dtype, nulls: `${nullCount} (${perc.toFixed(2)}%)`, unique: uniqueCount };
                })}
                columns={[
                    { title: 'Тип данных', dataIndex: 'dtype', key: 'dtype', render: (v) => <Tag>{v}</Tag> },
                    { title: 'Пропущено', dataIndex: 'nulls', key: 'nulls' },
                    { title: 'Уникальных значений', dataIndex: 'unique', key: 'unique' },
                ]}
            />

            <h4 style={{ marginTop: 24 }}>Предпросмотр данных (первые 50 строк):</h4>
            {!preview && (
                <Text type="secondary">Предпросмотр появится после загрузки/анализа файла на сервере</Text>
            )}
            {preview && (
                <div style={{ border: '1px solid #f0f0f0', borderRadius: 6, overflow: 'hidden' }}>
                    <Table
                        size="small"
                        pagination={{ pageSize: 50, hideOnSinglePage: true }}
                        loading={loadingPreview}
                        scroll={{ y: 300, x: true }}
                        columns={(preview.columns.length ? preview.columns : Object.keys(preview.rows[0] || {})).map((c) => ({
                            title: c,
                            dataIndex: c,
                            key: c,
                            render: (val: any) => <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{String(val ?? '')}</span>
                        }))}
                        dataSource={preview.rows.map((r, i) => ({ key: String(i), ...r }))}
                    />
                </div>
            )}
        </Card>
    );
};

export default AnalysisDisplay;
