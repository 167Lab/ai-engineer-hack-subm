import React, { useState } from 'react';
import { Card, Steps, Button, message, Form, Select, Input, Upload, Radio, Space, Alert } from 'antd';
import { UploadOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { analyzeDataSource } from '../services/api';
import { SourceType, TargetType, AnalysisResult, MASAnalysisResult } from '../types';
import AnalysisDisplay from './AnalysisDisplay';
import StorageSelector from './StorageSelector';
import PipelineConfig, { PipelineConfigData } from './PipelineConfig';
import DAGPreview from './DAGPreview';

const { Step } = Steps;
const { Option } = Select;

const sourceTypes = Object.values(SourceType);

const Step1Form = () => {
    const form = Form.useFormInstance();
    const sourceType = Form.useWatch('source_type', form);
    const fileInputType = Form.useWatch('file_input_type', form) || 'path';
    const [uploadedFile, setUploadedFile] = useState<any>(null);

    const handleFileUpload = (file: any) => {
        // Проверяем размер файла (ограничение 500 МБ для браузера)
        const maxSize = 500 * 1024 * 1024; // 500 МБ
        if (file.size > maxSize) {
            message.error(`Файл слишком большой! Максимальный размер: 500 МБ. Размер вашего файла: ${(file.size / 1024 / 1024).toFixed(1)} МБ`);
            return false;
        }

        // Показываем индикатор загрузки для больших файлов
        if (file.size > 10 * 1024 * 1024) { // Если файл больше 10 МБ
            message.loading('Читаем файл, это может занять время...', 0);
        }

        // Создаем временный URL для файла
        const reader = new FileReader();
        reader.onload = (e) => {
            message.destroy(); // Убираем индикатор загрузки
            setUploadedFile({
                file: file,
                name: file.name,
                content: e.target?.result,
                size: file.size
            });
            // Устанавливаем имя файла как путь для анализа
            form.setFieldsValue({ 
                file_path: file.name,
                uploaded_file_content: e.target?.result
            });
        };
        reader.onerror = () => {
            message.destroy(); // Убираем индикатор загрузки
            message.error('Ошибка чтения файла');
        };
        reader.readAsText(file, 'UTF-8');
        return false; // Предотвращаем автоматическую загрузку
    };

    const renderConnectionParams = () => {
        switch (sourceType) {
            case SourceType.CSV:
            case SourceType.JSON:
            case SourceType.XML:
                return (
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item
                            name="file_input_type"
                            label="Способ указания файла"
                        >
                            <Radio.Group>
                                <Radio value="path">
                                    <FolderOpenOutlined /> Путь к файлу на сервере
                                </Radio>
                                <Radio value="upload">
                                    <UploadOutlined /> Загрузить локальный файл
                                </Radio>
                            </Radio.Group>
                        </Form.Item>

                        {fileInputType === 'path' ? (
                            <Form.Item
                                name="file_path"
                                label="Путь к файлу на сервере"
                                rules={[{ required: true, message: 'Введите путь к файлу!' }]}
                                help="Путь к файлу внутри Docker контейнера (например: /opt/airflow/data/test_frontend.csv)"
                            >
                                <Input placeholder="/opt/airflow/data/test_frontend.csv" />
                            </Form.Item>
                        ) : (
                            <Form.Item
                                name="uploaded_file"
                                label="Выберите файл"
                                rules={[{ 
                                    required: true, 
                                    validator: () => {
                                        if (!uploadedFile) {
                                            return Promise.reject(new Error('Выберите файл для загрузки!'));
                                        }
                                        return Promise.resolve();
                                    }
                                }]}
                            >
                                <Upload
                                    beforeUpload={handleFileUpload}
                                    maxCount={1}
                                    accept={sourceType === SourceType.CSV ? '.csv' : 
                                           sourceType === SourceType.JSON ? '.json' : 
                                           sourceType === SourceType.XML ? '.xml' : ''}
                                    showUploadList={{ 
                                        showRemoveIcon: true,
                                        showPreviewIcon: false 
                                    }}
                                    onRemove={() => {
                                        setUploadedFile(null);
                                        form.setFieldsValue({ file_path: '', uploaded_file_content: '' });
                                    }}
                                    className="upload-dragger"
                                    style={{ width: '100%' }}
                                >
                                    <Button icon={<UploadOutlined />}>
                                        Выбрать {sourceType === SourceType.CSV ? 'CSV' : 
                                                 sourceType === SourceType.JSON ? 'JSON' : 
                                                 sourceType === SourceType.XML ? 'XML' : sourceType.toUpperCase()} файл
                                    </Button>
                                </Upload>
                                {uploadedFile && (
                                    <div style={{ marginTop: 8 }}>
                                        <Alert
                                            message={`Файл загружен: ${uploadedFile.name}`}
                                            description={`Размер: ${uploadedFile.size > 1024 * 1024 ? 
                                                (uploadedFile.size / 1024 / 1024).toFixed(1) + ' МБ' : 
                                                (uploadedFile.size / 1024).toFixed(1) + ' КБ'} | Тип: ${sourceType.toUpperCase()}`}
                                            type="success"
                                            showIcon
                                            closable={false}
                                        />
                                    </div>
                                )}
                            </Form.Item>
                        )}
                        
                        {/* Скрытое поле для хранения содержимого файла */}
                        <Form.Item name="uploaded_file_content" hidden>
                            <Input type="hidden" />
                        </Form.Item>
                    </Space>
                );
            case SourceType.POSTGRES:
            case SourceType.CLICKHOUSE:
                return (
                    <Form.Item
                        name="table"
                        label="Имя таблицы"
                        rules={[{ required: true, message: 'Введите имя таблицы!' }]}
                    >
                        <Input placeholder="public.my_table" />
                    </Form.Item>
                );
            default:
                return (
                    <Form.Item label="Параметры подключения">
                        <Input.TextArea
                            rows={4}
                            placeholder="Выберите тип источника, чтобы увидеть нужные поля"
                            disabled
                        />
                    </Form.Item>
                );
        }
    };

    return (
        <>
            <Form.Item
                name="source_type"
                label="Тип источника"
                rules={[{ required: true, message: 'Пожалуйста, выберите тип источника!' }]}
            >
                <Select placeholder="Выберите тип источника">
                    {sourceTypes.map(type => (
                        <Option key={type} value={type}>{type.toUpperCase()}</Option>
                    ))}
                </Select>
            </Form.Item>
            {renderConnectionParams()}
        </>
    );
};

const DataSourceWizard: React.FC = () => {
    const [current, setCurrent] = useState(0);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [selectedStorage, setSelectedStorage] = useState<TargetType | undefined>(undefined);
    const [pipelineConfig, setPipelineConfig] = useState<PipelineConfigData | undefined>(undefined);
    const [sourceConfig, setSourceConfig] = useState<any>(null);
    const [form] = Form.useForm();

    const analysisMutation = useMutation<MASAnalysisResult, Error, any>({
        mutationFn: analyzeDataSource,
        onSuccess: (data) => {
            message.success('Анализ успешно завершен!');
            // Преобразуем MAS результат в удобный формат
            const processedResult: AnalysisResult = {
                row_count: data.analysis_result?.metadata?.row_count || 0,
                column_count: data.analysis_result?.metadata?.column_count || 0,
                columns: data.analysis_result?.metadata?.columns || {},
                data_quality: data.analysis_result?.data_quality,
                recommendations: data.analysis_result?.recommendations || [],
                llm_recommendations: data.analysis_result?.llm_recommendations,
                error: data.error,
                raw_response: data
            };
            setAnalysisResult(processedResult);
            setCurrent(current + 1);
        },
        onError: (error: Error) => {
            message.error(`Ошибка при анализе: ${error.message}`);
        },
    });

    const handleNext = () => {
        if (current === 0) {
            form.submit();
        } else if (canGoToNextStep()) {
            setCurrent(current + 1);
        } else {
            message.warning('Пожалуйста, завершите текущий шаг перед переходом к следующему');
        }
    };

    const handlePrev = () => {
        setCurrent(current - 1);
    };

    const onFormFinish = (values: any) => {
        const { source_type, file_path, table, file_input_type, uploaded_file_content } = values;
        let connection_params = {};

        switch (source_type) {
            case SourceType.CSV:
            case SourceType.JSON:
            case SourceType.XML:
                if (file_input_type === 'upload' && uploaded_file_content) {
                    // Для загруженного файла передаем содержимое
                    connection_params = { 
                        file_content: uploaded_file_content,
                        file_name: file_path,
                        is_uploaded: true
                    };
                } else {
                    // Для файла на сервере передаем путь
                    connection_params = { 
                        file_path,
                        is_uploaded: false 
                    };
                }
                break;
            case SourceType.POSTGRES:
            case SourceType.CLICKHOUSE:
                connection_params = { table };
                break;
        }

        const payload = {
            source_type,
            connection_params,
        };
        
        console.log('Отправляем на анализ:', payload);
        
        // Сохраняем конфигурацию источника для дальнейшего использования
        setSourceConfig(payload);
        analysisMutation.mutate(payload);
    };

    const handleStorageSelect = (storage: TargetType) => {
        setSelectedStorage(storage);
    };

    const handlePipelineConfigChange = (config: PipelineConfigData) => {
        setPipelineConfig(config);
    };

    const canGoToNextStep = () => {
        switch (current) {
            case 0: return true; // форма валидируется автоматически
            case 1: return !!analysisResult; // должны быть результаты анализа
            case 2: return !!selectedStorage; // должно быть выбрано хранилище
            case 3: return !!pipelineConfig; // должна быть конфигурация пайплайна
            case 4: return true; // финальный шаг
            default: return false;
        }
    };

    const steps = [
        {
            title: 'Источник данных',
            content: <Step1Form />,
        },
        {
            title: 'Анализ данных',
            content: (
                <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '16px' }}>
                    {analysisMutation.isPending ? <p>Идет анализ...</p> : <AnalysisDisplay analysisResult={analysisResult} />}
                </div>
            ),
        },
        {
            title: 'Выбор хранилища',
            content: analysisResult ? (
                <StorageSelector 
                    recommendations={analysisResult.recommendations}
                    selectedStorage={selectedStorage}
                    onStorageSelect={handleStorageSelect}
                />
            ) : (
                <p>Сначала завершите анализ данных</p>
            ),
        },
        {
            title: 'Настройка пайплайна',
            content: selectedStorage ? (
                <PipelineConfig 
                    selectedStorage={selectedStorage}
                    onConfigChange={handlePipelineConfigChange}
                />
            ) : (
                <p>Сначала выберите хранилище</p>
            ),
        },
        {
            title: 'Предпросмотр и запуск',
            content: (sourceConfig && selectedStorage && pipelineConfig) ? (
                <DAGPreview 
                    sourceConfig={sourceConfig}
                    selectedStorage={selectedStorage}
                    pipelineConfig={pipelineConfig}
                    analysisResult={analysisResult}
                />
            ) : (
                <p>Завершите все предыдущие шаги</p>
            ),
        },
    ];

    return (
        <Card title="Мастер создания пайплайна">
            <Steps current={current}>
                {steps.map(item => (
                    <Step key={item.title} title={item.title} />
                ))}
            </Steps>
            <div className="steps-content" style={{ marginTop: 24, minHeight: 200, padding: 24, background: '#fafafa' }}>
                <Form form={form} onFinish={onFormFinish} layout="vertical" style={{ display: current === 0 ? 'block' : 'none' }}>
                   {steps[0].content}
                </Form>
                {current !== 0 && steps[current].content}
            </div>
            <div className="steps-action" style={{ marginTop: 24 }}>
                {current > 0 && (
                    <Button style={{ margin: '0 8px' }} onClick={handlePrev}>
                        Назад
                    </Button>
                )}
                {current < steps.length - 1 && (
                    <Button 
                        type="primary" 
                        onClick={handleNext} 
                        loading={analysisMutation.isPending}
                        disabled={!canGoToNextStep()}
                    >
                        Далее
                    </Button>
                )}
            </div>
        </Card>
    );
};

export default DataSourceWizard;
