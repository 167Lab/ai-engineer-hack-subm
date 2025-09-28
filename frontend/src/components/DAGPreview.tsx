import React, { useState } from 'react';
import { Card, Typography, Alert, Button, Space, Tabs, message, Spin } from 'antd';
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
        const dagConfig = {
            dag_name: pipelineConfig.pipeline_name,
            source_config: {
                type: sourceConfig.source_type,
                path: sourceConfig.connection_params.file_path || `/opt/airflow/data/${sourceConfig.source_type}_data.${sourceConfig.source_type}`
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

        deployMutation.mutate({
            dag_name: generatedDAG.dag_id
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

    const renderDeploymentStatus = () => {
        if (!deployResult) return null;

        return (
            <Card 
                size="small" 
                title="Статус развертывания"
                style={{ marginTop: 16 }}
            >
                <Alert
                    message={deployResult.status === 'deployed' ? 'Успешно развернуто!' : 'Ошибка развертывания'}
                    description={deployResult.message}
                    type={deployResult.status === 'deployed' ? 'success' : 'error'}
                    showIcon
                    style={{ marginBottom: 16 }}
                />
                
                <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                        <Text strong>DAG ID:</Text> {deployResult.dag_id}
                    </div>
                    <div>
                        <Text strong>Файл:</Text> {deployResult.file_path}
                    </div>
                    {deployResult.airflow_dag_url && (
                        <div>
                            <Text strong>Ссылка на схему DAG:</Text>{' '}
                            <Button 
                                type="link" 
                                size="small" 
                                onClick={() => window.open(deployResult.airflow_dag_url, '_blank')}
                            >
                                Открыть Graph View
                            </Button>
                        </div>
                    )}
                <div>
                    <Text strong>Статус Airflow API:</Text> 
                    <br />
                    <Text type={deployResult.airflow_api_status?.includes('✅') ? 'success' : 'warning'}>
                        {deployResult.airflow_api_status || '❌ Статус неизвестен'}
                    </Text>
                </div>
                </Space>

                {deployResult.status === 'deployed' && (
                    <div>
                        <Alert
                            message="Пайплайн готов к запуску!"
                            description="DAG успешно развернут в Airflow."
                            type="success"
                            showIcon
                            style={{ marginTop: 16 }}
                            action={
                                <Space>
                                    <Button 
                                        size="small" 
                                        type="primary"
                                        onClick={() => window.open('http://localhost:8080', '_blank')}
                                    >
                                        Открыть Airflow
                                    </Button>
                                    <Button 
                                        size="small" 
                                        onClick={() => window.open(`http://localhost:8080/dags/${deployResult.dag_id}/graph`, '_blank')}
                                    >
                                        Схема DAG
                                    </Button>
                                </Space>
                            }
                        />
                        
                        <Card size="small" title="Как использовать DAG" style={{ marginTop: 16 }}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <div>
                                    <Text strong>1. Откройте Airflow UI:</Text>
                                    <br />
                                    <Text>Перейдите по ссылке </Text>
                                    <Text code copyable>http://localhost:8080</Text>
                                </div>
                                
                                <div>
                                    <Text strong>2. Найдите ваш DAG:</Text>
                                    <br />
                                    <Text>Ищите DAG с ID: </Text>
                                    <Text code copyable>{deployResult.dag_id}</Text>
                                </div>
                                
                                <div>
                                    <Text strong>3. Включите DAG:</Text>
                                    <br />
                                    <Text>Переключите тумблер рядом с именем DAG в положение "ON"</Text>
                                </div>
                                
                                <div>
                                    <Text strong>4. Запустите вручную (опционально):</Text>
                                    <br />
                                    <Text>Нажмите кнопку "Trigger DAG" для немедленного запуска</Text>
                                </div>
                                
                                <div>
                                    <Text strong>5. Мониторинг:</Text>
                                    <br />
                                    <Text>Следите за выполнением в разделе "Graph View" или "Tree View"</Text>
                                </div>
                            </Space>
                        </Card>
                        
                        {deployResult.airflow_api_status?.includes('❌') && (
                            <Alert
                                message="Обратите внимание"
                                description="API Airflow недоступно, но DAG файл создан. Убедитесь, что Airflow запущен и обновите список DAG в интерфейсе."
                                type="warning"
                                showIcon
                                style={{ marginTop: 16 }}
                            />
                        )}
                    </div>
                )}
            </Card>
        );
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
                    
                    <Space>
                        <Button
                            type="primary"
                            icon={<PlayCircleOutlined />}
                            onClick={handleGenerateDAG}
                            loading={generateMutation.isPending}
                            size="large"
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
                            >
                                Развернуть в Airflow
                            </Button>
                        )}
                    </Space>
                </TabPane>
                
                <TabPane tab="Python код" key="code" disabled={!generatedDAG}>
                    {renderDAGCode()}
                </TabPane>
                
                <TabPane tab="Статус" key="status" disabled={!deployResult}>
                    {renderDeploymentStatus()}
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
