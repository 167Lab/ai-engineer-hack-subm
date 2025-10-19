import React, { useState } from 'react';
import { Card, Typography, Alert, Button, Space, Tabs, message, Spin, Progress, Collapse } from 'antd';
import { PlayCircleOutlined, CloudUploadOutlined, EyeOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { generateDag, deployDag } from '../services/api';
import { TargetType, DAGDeploymentResult } from '../types';
import { PipelineConfigData } from './PipelineConfig';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface DAGPreviewProps {
    sourceConfig: any;
    selectedStorage: TargetType;
    pipelineConfig: PipelineConfigData;
    analysisResult?: any;
}

interface DAGGenerationResult {
    dag_id: string;
    dag_py: string;
}

const DAGPreview: React.FC<DAGPreviewProps> = ({ 
    sourceConfig, 
    selectedStorage, 
    pipelineConfig,
    analysisResult 
}) => {
    const [generatedDAG, setGeneratedDAG] = useState<DAGGenerationResult | null>(null);
    const [deployResult, setDeployResult] = useState<DAGDeploymentResult | null>(null);
    const [graphNodes, setGraphNodes] = useState<string[]>([]);
    const [deployProgress, setDeployProgress] = useState<number>(0);

    // Мутация для генерации DAG
    const generateMutation = useMutation<DAGGenerationResult, Error, any>({
        mutationFn: generateDag,
        onSuccess: (data) => {
            message.success('DAG успешно сгенерирован!');
            setGeneratedDAG(data);
        },
        onError: (error: Error) => {
            message.error(`Ошибка генерации DAG: ${error.message}`);
        },
    });

    // Мутация для деплоя DAG
    const deployMutation = useMutation<DAGDeploymentResult, Error, any>({
        mutationFn: deployDag,
        onSuccess: (data) => {
            message.success('DAG успешно развернут в Airflow!');
            setDeployResult(data);
        },
        onError: (error: Error) => {
            message.error(`Ошибка деплоя DAG: ${error.message}`);
        },
    });

    const handleGenerateDAG = () => {
        const persistedPath = analysisResult?.raw_response?.file_info?.persisted_path || sourceConfig.connection_params.file_path;
        const dagConfig = {
            dag_name: pipelineConfig.pipeline_name,
            source_config: {
                type: sourceConfig.source_type,
                path: persistedPath || `/opt/airflow/data/${sourceConfig.source_type}_data.${sourceConfig.source_type}`
            },
            target_config: {
                type: selectedStorage,
                table: pipelineConfig.target_table
            },
            schedule: pipelineConfig.schedule,
            description: pipelineConfig.description,
            owner: 'etl-system'
        };

        generateMutation.mutate(dagConfig);
    };

    const handleDeployDAG = () => {
        if (!generatedDAG) {
            message.error('Сначала сгенерируйте DAG');
            return;
        }

        const persistedPath = analysisResult?.raw_response?.file_info?.persisted_path || sourceConfig.connection_params.file_path;
        const deployConfig = {
            dag_name: generatedDAG.dag_id,
            source_config: {
                type: sourceConfig.source_type,
                path: persistedPath || `/opt/airflow/data/${sourceConfig.source_type}_data.${sourceConfig.source_type}`
            },
            target_config: {
                type: selectedStorage,
                table: pipelineConfig.target_table
            },
            schedule: pipelineConfig.schedule,
            description: pipelineConfig.description,
            owner: 'etl-system'
        };

        setDeployProgress(5);
        const timer = setInterval(() => {
            setDeployProgress((p) => Math.min(p + 7, 90));
        }, 400);
        deployMutation.mutate(deployConfig, {
            onSettled: () => {
                clearInterval(timer);
                setDeployProgress(100);
                setTimeout(() => setDeployProgress(0), 1500);
            }
        });
    };

    const renderConfigurationSummary = () => (
        <Card size="small" title="Конфигурация пайплайна" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                    <Text strong>Источник данных:</Text> {sourceConfig.source_type.toUpperCase()}
                    <br />
                    <Text type="secondary">
                        {sourceConfig.connection_params.file_path || sourceConfig.connection_params.table || 'Не указан'}
                    </Text>
                </div>
                
                <div>
                    <Text strong>Хранилище:</Text> {selectedStorage.toUpperCase()}
                    <br />
                    <Text type="secondary">{pipelineConfig.target_table}</Text>
                </div>
                
                <div>
                    <Text strong>Расписание:</Text> {pipelineConfig.schedule}
                    <br />
                    <Text type="secondary">{pipelineConfig.description}</Text>
                </div>

                {generatedDAG && (
                    <div>
                        <Text strong>DAG ID:</Text> {generatedDAG.dag_id}
                        <br />
                        <Text strong>Файл:</Text> <Text type="secondary">{`/opt/airflow/dags/${generatedDAG.dag_id}.py`}</Text>
                    </div>
                )}

                {analysisResult?.raw_response?.analysis_result?.llm_recommendations && (
                    <div>
                        <Text strong>Рекомендации ИИ учтены:</Text>
                        <br />
                        <Text type="secondary">
                            Система использовала рекомендации для оптимизации пайплайна
                        </Text>
                    </div>
                )}
            </Space>
        </Card>
    );

    const renderDAGCode = () => {
        if (!generatedDAG) return null;

        return (
            <Card size="small" title="Сгенерированный DAG код">
                <pre style={{ 
                    background: '#f5f5f5', 
                    padding: '16px', 
                    borderRadius: '6px',
                    fontSize: '12px',
                    lineHeight: '1.4',
                    overflow: 'auto',
                    maxHeight: '400px'
                }}>
                    {generatedDAG.dag_py}
                </pre>
            </Card>
        );
    };

    const parseDagGraph = () => {
        if (!generatedDAG?.dag_py) {
            setGraphNodes([]);
            return;
        }
        const code = generatedDAG.dag_py;
        const taskIdRegex = /task_id\s*=\s*['"]([^'"]+)['"]/g;
        const ids = new Set<string>();
        let m;
        while ((m = taskIdRegex.exec(code))) {
            ids.add(m[1]);
        }
        let nodes = Array.from(ids);
        // Простая эвристика порядка
        const order = ['extract_data', 'transform_data', 'load_data'];
        nodes.sort((a,b) => order.indexOf(a) - order.indexOf(b));
        setGraphNodes(nodes);
    };


    return (
        <div>
            <Title level={4}>Предпросмотр и запуск пайплайна</Title>
            
            <Alert
                message="Финальный шаг"
                description="Проверьте конфигурацию, сгенерируйте DAG и разверните в Airflow"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
            />

            <Tabs defaultActiveKey="config">
                <TabPane tab={<><EyeOutlined />Конфигурация</>} key="config">
                    {renderConfigurationSummary()}
                    
                    <Space wrap>
                        <Button
                            type="primary"
                            icon={<PlayCircleOutlined />}
                            onClick={handleGenerateDAG}
                            loading={generateMutation.isPending}
                            size="large"
                            aria-label="Сгенерировать DAG"
                        >
                            Сгенерировать DAG
                        </Button>
                        
                        {generatedDAG && (
                            <Button
                                type="primary"
                                icon={<CloudUploadOutlined />}
                                onClick={handleDeployDAG}
                                loading={deployMutation.isPending}
                                style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                                size="large"
                                aria-label="Развернуть в Airflow"
                            >
                                Развернуть в Airflow
                            </Button>
                        )}

                        {generatedDAG && (
                            <Button onClick={() => window.open('http://localhost:8080', '_blank')}>
                                Открыть Airflow
                            </Button>
                        )}
                    </Space>

                    {deployMutation.isPending || deployProgress > 0 ? (
                        <Card style={{ marginTop: 16 }} size="small">
                            <Progress percent={deployProgress} status={deployProgress < 100 ? 'active' : 'success'} />
                        </Card>
                    ) : null}

                    {deployResult?.status === 'deployed' && (
                        <Collapse style={{ marginTop: 16 }}>
                            <Collapse.Panel header="Как использовать DAG" key="howto">
                                <Space direction="vertical" style={{ width: '100%' }}>
                                    <div>
                                        <Text>1. Откройте Airflow UI по кнопке «Открыть Airflow»</Text>
                                    </div>
                                    <div>
                                        <Text>2. Найдите ваш DAG: </Text>
                                        <Text code copyable>{deployResult.dag_id}</Text>
                                    </div>
                                    <div>
                                        <Text>3. Переключите тумблер рядом с именем DAG в положение "ON"</Text>
                                    </div>
                                    <div>
                                        <Text>4. При желании нажмите "Trigger DAG" для немедленного запуска</Text>
                                    </div>
                                    <div>
                                        <Text>5. Следите за выполнением в «Graph View» или «Tree View»</Text>
                                    </div>
                                </Space>
                            </Collapse.Panel>
                        </Collapse>
                    )}
                </TabPane>
                
                <TabPane tab="Python код" key="code" disabled={!generatedDAG}>
                    {renderDAGCode()}
                </TabPane>

                <TabPane tab="Схема DAG" key="graph" disabled={!generatedDAG}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Button onClick={parseDagGraph} disabled={!generatedDAG}>Обновить схему</Button>
                        {graphNodes.length > 0 ? (
                            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                                {graphNodes.map((n, idx) => (
                                    <div key={n} style={{
                                        padding: '8px 12px',
                                        border: '1px solid #d9d9d9',
                                        borderRadius: 6,
                                        background: idx === 0 ? '#e6f7ff' : (idx === graphNodes.length-1 ? '#f6ffed' : '#fff')
                                    }}>
                                        {n}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <Alert message="Схема будет доступна после генерации DAG" type="info" showIcon />
                        )}
                    </Space>
                </TabPane>
                
            </Tabs>

            {/* Индикаторы загрузки */}
            {generateMutation.isPending && (
                <Card style={{ marginTop: 16 }}>
                    <div style={{ textAlign: 'center' }}>
                        <Spin size="large" />
                        <Paragraph style={{ marginTop: 16 }}>
                            Генерация DAG файла...
                        </Paragraph>
                    </div>
                </Card>
            )}

            {deployMutation.isPending && (
                <Card style={{ marginTop: 16 }}>
                    <div style={{ textAlign: 'center' }}>
                        <Spin size="large" />
                        <Paragraph style={{ marginTop: 16 }}>
                            Развертывание в Airflow...
                        </Paragraph>
                    </div>
                </Card>
            )}
        </div>
    );
};

export default DAGPreview;
