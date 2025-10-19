import React, { useState } from 'react';
import { Card, Steps, Button, message, Form, Select, Input, Upload, Radio, Space, Alert, Progress } from 'antd';
import { UploadOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { analyzeDataSource, generatePipeline, generateReport } from '../services/api';
import { SourceType, TargetType, AnalysisResult, MASAnalysisResult } from '../types';
import AnalysisDisplay from './AnalysisDisplay';
import { PipelineConfigData } from './PipelineConfig';
import StorageAndConfig from './StorageAndConfig';
import DAGPreview from './DAGPreview';
import { LargeFileUploader, MemorySafeFileReader } from '../utils/fileUploadUtils';
import ServerFileBrowser from './ServerFileBrowser';

const { Step } = Steps;
const { Option } = Select;

const sourceTypes = Object.values(SourceType);

const Step1Form = ({ 
    uploadProgress, 
    uploadedFile, 
    setUploadedFile, 
    setUploadProgress,
    setAnalysisResult,
    setSourceConfig
}: { 
    uploadProgress: any; 
    uploadedFile: any;
    setUploadedFile: any;
    setUploadProgress: any;
    setAnalysisResult: any;
    setSourceConfig: any;
}) => {
    const form = Form.useFormInstance();
    const sourceType = Form.useWatch('source_type', form);
    const fileInputType = Form.useWatch('file_input_type', form) || 'path';

    const handleFileUpload = async (file: File) => {
        // Проверяем размер файла (увеличен лимит до 1 ГБ)
        const maxSize = 1024 * 1024 * 1024; // 1 ГБ
        if (file.size > maxSize) {
            message.error(`Файл слишком большой для загрузки. Максимальный размер: 1 ГБ. Размер вашего файла: ${(file.size / 1024 / 1024 / 1024).toFixed(1)} ГБ`);
            return false;
        }

        // Определяем нужно ли использовать chunked upload
        const useChunkedUpload = LargeFileUploader.shouldUseChunkedUpload(file.size);
        
        // Автоматически определяем тип файла
        let detectedType = sourceType;
        try {
            const detection = await MemorySafeFileReader.detectFileType(file);
            if (detection.confidence > 0.7) {
                detectedType = detection.type as SourceType;
                console.log(`Автоматически определен тип файла: ${detectedType} (уверенность: ${detection.confidence})`);
            }
        } catch (error) {
            console.warn('Не удалось определить тип файла:', error);
        }
        
        // Устанавливаем информацию о выбранном файле
        setUploadedFile({
            file: file,
            name: file.name,
            size: file.size,
            useChunkedUpload: useChunkedUpload,
            detectedType: detectedType,
            isUploading: false,
            uploadCompleted: false,
            analysisResult: null
        });

        // *** НОВАЯ ЛОГИКА: СРАЗУ НАЧИНАЕМ ЗАГРУЗКУ НА СЕРВЕР ***
        if (useChunkedUpload) {
            // Для больших файлов сразу начинаем chunked upload
            message.info(`Начинается потоковая загрузка большого файла (${(file.size / 1024 / 1024).toFixed(1)} МБ) на сервер...`);
            await startImmediateUpload(file, detectedType);
        } else {
            // Для маленьких файлов сразу начинаем streaming upload  
            message.info(`Выполняется загрузка файла (${(file.size / 1024).toFixed(1)} КБ) на сервер...`);
            await startImmediateUpload(file, detectedType);
        }

        return false; // Предотвращаем автоматическую загрузку Antd
    };

    // Новая функция для немедленной загрузки файла на сервер
    const startImmediateUpload = async (file: File, detectedType: string) => {
        try {
            // Обновляем состояние - начинаем загрузку
            setUploadedFile((prev: any) => prev ? {...prev, isUploading: true} : null);
            
            // Показываем прогресс
            setUploadProgress({
                visible: true,
                percentage: 0,
                currentChunk: 0,
                totalChunks: 0,
                status: 'uploading',
                message: 'Подготовка к загрузке...'
            });

            let result;
            const useChunkedUpload = LargeFileUploader.shouldUseChunkedUpload(file.size);
            
            if (useChunkedUpload) {
                // Chunked upload для больших файлов
                result = await LargeFileUploader.uploadLargeFileForAnalysis(
                    file,
                    detectedType,
                    (progress) => {
                        setUploadProgress((prev: any) => ({
                            ...prev,
                            percentage: progress.percentage,
                            currentChunk: progress.currentChunk,
                            totalChunks: progress.totalChunks,
                            message: `Загружено ${(progress.loaded / 1024 / 1024).toFixed(1)} МБ из ${(progress.total / 1024 / 1024).toFixed(1)} МБ`
                        }));
                    }
                );
            } else {
                // Streaming upload для маленьких файлов
                const formData = new FormData();
                formData.append('file', file);
                formData.append('source_type', detectedType);
                formData.append('sample_size', '1000');
                
                const response = await fetch('/api/v1/analyze_file_stream', {
                    method: 'POST',
                    body: formData,
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(`Upload failed: ${errorData.error}`);
                }
                
                result = await response.json();
            }

            // Обрабатываем результат анализа
            const analysisResult = processAnalysisResult(result);
            
            // Обновляем состояние - загрузка завершена
            setUploadedFile((prev: any) => prev ? {
                ...prev, 
                isUploading: false,
                uploadCompleted: true,
                analysisResult: analysisResult
            } : null);
            
            // Устанавливаем результат анализа в основное состояние
            setAnalysisResult(analysisResult);
            const persistedPath = (result as any)?.file_info?.persisted_path as string | undefined;
            setSourceConfig({
                source_type: detectedType,
                connection_params: {
                    file_name: file.name,
                    is_uploaded: true,
                    server_processed: true,
                    file_path: persistedPath
                }
            });
            
            // Завершаем прогресс
            setUploadProgress((prev: any) => ({
                ...prev,
                status: 'complete',
                percentage: 100,
                message: 'Файл успешно загружен!'
            }));

            // Скрываем прогресс через 3 секунды
            setTimeout(() => {
                setUploadProgress((prev: any) => ({ ...prev, visible: false }));
            }, 3000);

            message.success(`Файл "${file.name}" успешно загружен!`);

        } catch (error: any) {
            console.error('Ошибка немедленной загрузки:', error);
            
            // Обновляем состояние - ошибка загрузки
            setUploadedFile((prev: any) => prev ? {
                ...prev, 
                isUploading: false,
                uploadCompleted: false,
                analysisResult: null
            } : null);
            
            setUploadProgress((prev: any) => ({
                ...prev,
                status: 'error',
                message: error.message || 'Ошибка загрузки файла'
            }));

            message.error(`Ошибка загрузки файла: ${error.message}`);
        }
    };

    // Функция для обработки результата анализа в единый формат
    const processAnalysisResult = (result: any): AnalysisResult => {
        const streamingResult = result.analysis_result || result;
        
        return {
            row_count: streamingResult?.total_rows || 0,
            column_count: streamingResult?.columns?.length || 0,
            columns: streamingResult?.column_types || {},
            data_quality: {
                total_nulls: streamingResult?.null_counts ? 
                    Object.values(streamingResult.null_counts as Record<string, number>)
                        .reduce((a: number, b: number) => a + b, 0) : 0,
                duplicate_rows: 0,
                completeness_score: streamingResult?.data_quality_score || 100,
                quality_score: streamingResult?.data_quality_score || 100,
                null_counts: streamingResult?.null_counts || {},
                issues: []
            },
            recommendations: [{
                type: 'server_processed',
                description: `Файл обработан на сервере. Размер: ${result.file_info?.size || 0} bytes`,
                confidence: 1.0
            }],
            llm_recommendations: [`Файл "${result.file_info?.name || 'unknown'}" успешно обработан на сервере.`],
            error: undefined,
            raw_response: result,
            streaming_info: {
                file_size: result.file_info?.size,
                processed_size: result.file_info?.processed_size,
                sample_size: result.file_info?.sample_size,
                analysis_method: result.file_info?.analysis_method || 'server_processed'
            }
        };
    };

    // Функция для отмены загрузки файла
    const cancelUpload = () => {
        setUploadedFile((prev: any) => prev ? {
            ...prev, 
            isUploading: false,
            uploadCompleted: false,
            analysisResult: null
        } : null);
        
        setUploadProgress((prev: any) => ({
            ...prev,
            visible: false,
            status: 'uploading',
            percentage: 0
        }));
        
        message.info('Загрузка файла отменена');
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
                            <Radio.Group aria-label="Способ указания файла">
                                <Radio value="path">
                                    <FolderOpenOutlined /> Путь к файлу на сервере
                                </Radio>
                                <Radio value="upload">
                                    <UploadOutlined /> Загрузить локальный файл
                                </Radio>
                            </Radio.Group>
                        </Form.Item>

                        {fileInputType === 'path' ? (
                            <>
                                <Form.Item
                                    name="file_path"
                                    label="Путь к файлу на сервере"
                                    rules={[{ required: true, message: 'Выберите файл на сервере!' }]}
                                    help="Выберите файл из каталога /opt/airflow/data/uploads"
                                >
                                    <Input placeholder="/opt/airflow/data/..." readOnly aria-label="Путь к файлу на сервере" />
                                </Form.Item>
                                <ServerFileBrowser
                                    rootPath="/opt/airflow/data/uploads"
                                    onSelectPath={(p: string) => form.setFieldsValue({ file_path: p })}
                                />
                            </>
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
                                    <Button icon={<UploadOutlined />} aria-label="Выбрать файл для загрузки">
                                        Выбрать {sourceType === SourceType.CSV ? 'CSV' : 
                                                 sourceType === SourceType.JSON ? 'JSON' : 
                                                 sourceType === SourceType.XML ? 'XML' : sourceType.toUpperCase()} файл
                                    </Button>
                                </Upload>
                                {uploadedFile && (
                                    <div style={{ marginTop: 8 }}>
                                        <Alert
                                            message={
                                                uploadedFile.isUploading ? 
                                                `Загружается: ${uploadedFile.name}` :
                                                uploadedFile.uploadCompleted ? 
                                                `Загружен: ${uploadedFile.name}` :
                                                `Выбран: ${uploadedFile.name}`
                                            }
                                            description={`Размер: ${uploadedFile.size > 1024 * 1024 ? 
                                                (uploadedFile.size / 1024 / 1024).toFixed(1) + ' МБ' : 
                                                (uploadedFile.size / 1024).toFixed(1) + ' КБ'} | Тип: ${sourceType.toUpperCase()}${uploadedFile.useChunkedUpload ? ' | Потоковая загрузка' : ''}${
                                                uploadedFile.uploadCompleted ? ' | Готов к анализу!' : 
                                                uploadedFile.isUploading ? ' | Идет загрузка...' : ' | Ожидает загрузки'
                                            }`}
                                            type={
                                                uploadedFile.uploadCompleted ? "success" :
                                                uploadedFile.isUploading ? "info" : "warning"
                                            }
                                            showIcon
                                            closable={false}
                                            action={
                                                uploadedFile.isUploading ? (
                                                    <Button 
                                                        size="small" 
                                                        danger 
                                                        onClick={() => cancelUpload()}
                                                        aria-label="Отменить загрузку"
                                                    >
                                                        Отменить
                                                    </Button>
                                                ) : undefined
                                            }
                                        />
                                    </div>
                                )}
                                
                                {/* Прогресс загрузки */}
                                {uploadProgress.visible && (
                                    <div style={{ marginTop: 12, padding: '12px', backgroundColor: '#f6ffed', borderRadius: '6px', border: '1px solid #b7eb8f' }}>
                                        <div style={{ marginBottom: '8px', fontWeight: 'bold', color: '#52c41a' }}>
                                            {uploadProgress.status === 'uploading' && 'Загружаем файл по частям...'}
                                            {uploadProgress.status === 'processing' && 'Анализируем данные...'}
                                            {uploadProgress.status === 'complete' && 'Загрузка завершена!'}
                                            {uploadProgress.status === 'error' && 'Ошибка загрузки'}
                                        </div>
                                        
                                        <Progress 
                                            percent={uploadProgress.percentage} 
                                            status={uploadProgress.status === 'error' ? 'exception' : 'active'}
                                            strokeColor={{
                                                '0%': '#87d068',
                                                '100%': '#52c41a',
                                            }}
                                            format={(percent?: number) => `${percent ?? 0}%`}
                                        />
                                        
                                        {uploadProgress.totalChunks > 1 && (
                                            <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                                Часть {uploadProgress.currentChunk} из {uploadProgress.totalChunks}
                                            </div>
                                        )}
                                        
                                        {uploadProgress.message && (
                                            <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                                {uploadProgress.message}
                                            </div>
                                        )}
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
            //case SourceType.POSTGRES:
            //case SourceType.CLICKHOUSE:
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
                <Select placeholder="Выберите тип источника" aria-label="Тип источника данных">
                    {sourceTypes.map(type => (
                        <Option key={type} value={type}>{type.toUpperCase()}</Option>
                    ))}
                </Select>
            </Form.Item>
            <Alert
                message="Подсказка"
                description="Выберите тип источника и способ указания файла: загрузка локально или выбор пути на сервере. Для крупных файлов используется потоковая загрузка."
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
            />
            {renderConnectionParams()}
        </>
    );
};

const DataSourceWizard: React.FC<{ resetSignal?: number }> = ({ resetSignal }: { resetSignal?: number }) => {
    const [current, setCurrent] = useState(0);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [selectedStorage, setSelectedStorage] = useState<TargetType | undefined>(undefined);
    const [pipelineConfig, setPipelineConfig] = useState<PipelineConfigData | undefined>(undefined);
    const [sourceConfig, setSourceConfig] = useState<any>(null);
    const [form] = Form.useForm();
    const [uploadProgress, setUploadProgress] = useState<{
        visible: boolean;
        percentage: number;
        currentChunk: number;
        totalChunks: number;
        status: 'uploading' | 'processing' | 'complete' | 'error';
        message: string;
    }>({
        visible: false,
        percentage: 0,
        currentChunk: 0,
        totalChunks: 0,
        status: 'uploading',
        message: ''
    });
    const [uploadedFile, setUploadedFile] = useState<any>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [pipelineResult, setPipelineResult] = useState<any>(null);
    const [reportResult, setReportResult] = useState<any>(null);

    // Reset to first step when resetSignal changes
    React.useEffect(() => {
        if (typeof resetSignal === 'number') {
            setCurrent(0);
            setSessionId(null);
            setPipelineResult(null);
            setReportResult(null);
        }
    }, [resetSignal]);

    const analysisMutation = useMutation<MASAnalysisResult, Error, any>({
        mutationFn: analyzeDataSource,
        onSuccess: (data: any) => {
            message.success('Анализ входных данных завершен!');
            
            // Сохраняем session_id для последующих вызовов
            if (data.session_id) {
                setSessionId(data.session_id);
                console.log('📌 Session ID saved:', data.session_id);
            }
            
            // Преобразуем результат в удобный формат
            const processedResult: AnalysisResult = {
                row_count: data.source_metadata?.total_rows || data.analysis_result?.metadata?.row_count || 0,
                column_count: data.source_metadata?.columns?.length || data.analysis_result?.metadata?.column_count || 0,
                columns: data.source_metadata?.column_types || data.analysis_result?.metadata?.columns || {},
                data_quality: data.data_quality_score || data.analysis_result?.data_quality,
                recommendations: [
                    ...(data.storage_recommendation ? [{
                        type: 'storage',
                        priority: 'high',
                        title: 'Рекомендованное хранилище',
                        description: data.storage_recommendation,
                        details: data.optimization_recommendations
                    }] : []),
                    ...(data.alternative_storages || []).map((alt: any) => ({
                        type: 'storage',
                        priority: alt.priority === 1 ? 'high' : alt.priority === 2 ? 'medium' : 'low',
                        title: `Альтернатива: ${alt.storage}`,
                        description: alt.reason
                    })),
                    ...(data.analysis_result?.recommendations || [])
                ],
                llm_recommendations: data.analysis_result?.llm_recommendations,
                error: data.error,
                raw_response: data
            };
            setAnalysisResult(processedResult);
            setCurrent((prev: number) => prev + 1);
        },
        onError: (error: Error) => {
            message.error(`Ошибка при анализе: ${error.message}`);
        },
    });

    // Старая streamingAnalysisMutation удалена - теперь используем немедленную загрузку при выборе файла

    const pipelineMutation = useMutation({
        mutationFn: generatePipeline,
        onSuccess: (data) => {
            message.success('DDL и пайплайн успешно сгенерированы!');
            setPipelineResult(data);
            
            // Store DDL and pipeline results for DAG generation
            if (data.ddl_result) {
                localStorage.setItem('ddl_result', JSON.stringify(data.ddl_result));
            }
            if (data.pipeline_result) {
                localStorage.setItem('pipeline_result', JSON.stringify(data.pipeline_result));
            }
            
            setCurrent((prev: number) => prev + 1);
        },
        onError: (error: Error) => {
            message.error(`Ошибка генерации пайплайна: ${error.message}`);
        }
    });

    const reportMutation = useMutation({
        mutationFn: generateReport,
        onSuccess: (data) => {
            message.success('Отчет успешно сгенерирован!');
            setReportResult(data);
        },
        onError: (error: Error) => {
            message.error(`Ошибка генерации отчета: ${error.message}`);
        }
    });

    const handleNext = () => {
        console.log('🔵 handleNext called, current step:', current);
        if (current === 0) {
            console.log('🔵 Submitting form...');
            form.submit();
        } else if (current === 2) {
            // Moving from storage selection to pipeline generation
            if (selectedStorage && pipelineConfig && sessionId) {
                console.log('🔵 Triggering pipeline generation with session:', sessionId);
                pipelineMutation.mutate({
                    session_id: sessionId,
                    user_choices: {
                        storage_type: selectedStorage,
                        pipeline_params: {
                            ...pipelineConfig,
                            schedule: pipelineConfig.schedule || '0 0 * * *',
                            retries: pipelineConfig.retries || 2,
                            email_on_failure: pipelineConfig.emailOnFailure || false
                        }
                    }
                });
            } else {
                message.warning('Выберите хранилище и настройте параметры пайплайна');
            }
        } else if (canGoToNextStep()) {
            console.log('🔵 Moving to next step');
            setCurrent((prev: number) => prev + 1);
        } else {
            console.log('🔵 Cannot proceed to next step');
            message.warning('Пожалуйста, завершите текущий шаг перед переходом к следующему');
        }
    };

    const handlePrev = () => {
        setCurrent((prev: number) => prev - 1);
    };

    const onFormFinish = async (values: any) => {
        console.log('🟢 onFormFinish called with values:', values);
        const { source_type, file_path, table, file_input_type } = values;

        // Если файл уже загружен и есть быстрый предпросмотр (streaming анализ),
        // используем его для UI, но всё равно запускаем LLM-анализ на бэкенде ниже.
        if (file_input_type === 'upload' && uploadedFile && uploadedFile.uploadCompleted && uploadedFile.analysisResult) {
            console.log('🟢 File already uploaded, using preview result for UI');
            setAnalysisResult(uploadedFile.analysisResult);
        }

        // Если загрузка еще не завершена, блокируем переход
        if (file_input_type === 'upload' && uploadedFile && uploadedFile.isUploading) {
            message.warning('Дождитесь завершения загрузки файла на сервер');
            return;
        }

        // Если выбран файл но он еще не загружен, запускаем загрузку
        if (file_input_type === 'upload' && uploadedFile && !uploadedFile.uploadCompleted) {
            message.warning('Файл выбран но еще не загружен. Попробуйте выбрать файл снова.');
            return;
        }

        let connection_params: any = {};

        switch (source_type) {
            case SourceType.CSV:
            case SourceType.JSON:
            case SourceType.XML:
                if (file_input_type === 'upload') {
                    // Для локальной загрузки полагаемся на состояние uploadedFile,
                    // файл уже загружен сервером в шаге немедленной загрузки
                    if (!uploadedFile || !uploadedFile.uploadCompleted) {
                        message.warning('Файл еще не загружен на сервер. Дождитесь завершения загрузки.');
                        return;
                    }
                    // Получаем путь к файлу из результата загрузки
                    const persistedPath = uploadedFile.analysisResult?.raw_response?.file_info?.persisted_path;
                    if (!persistedPath) {
                        message.error('Не найден путь к загруженному файлу на сервере');
                        return;
                    }
                    connection_params = {
                        file_path: persistedPath,
                        file_name: uploadedFile.name,
                        is_uploaded: true
                    };
                } else {
                    // Для файла, уже лежащего на сервере, передаем путь
                    connection_params = { 
                        file_path,
                        is_uploaded: false 
                    };
                }
                break;
            //case SourceType.POSTGRES:
            //case SourceType.CLICKHOUSE:
                connection_params = { table };
                break;
        }

        const payload = {
            source_type,
            connection_params,
        };
        
        console.log('🚀 [UI] POST /api/v1/analyze с payload:', payload);
        console.log('   file_path:', connection_params.file_path || 'NOT SET');
        
        // Сохраняем конфигурацию источника для дальнейшего использования
        setSourceConfig(payload);
        // Переходим сразу к шагу анализа и показываем индикатор, пока идет анализ
        setCurrent((prev: number) => prev + 1);
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
            case 0: {
                // Для шага выбора источника данных
                const formValues = form.getFieldsValue();
                const fileInputType = formValues.file_input_type || 'path';
                
                if (fileInputType === 'upload') {
                    // Если выбрана загрузка файла, проверяем состояние загрузки
                    if (!uploadedFile) return false;
                    if (uploadedFile.isUploading) return false; // Загрузка в процессе
                    if (!uploadedFile.uploadCompleted) return false; // Загрузка не завершена
                    return true; // Файл успешно загружен
                } else {
                    // Для файлов на сервере - форма валидируется автоматически
                    return true;
                }
            }
            case 1: return !!analysisResult; // должны быть результаты анализа
            case 2: return !!selectedStorage && !!pipelineConfig; // объединенный шаг
            case 3: return true; // финальный шаг
            default: return false;
        }
    };

    const steps = [
        {
            title: 'Источник данных',
            content: <Step1Form 
                uploadProgress={uploadProgress} 
                uploadedFile={uploadedFile}
                setUploadedFile={setUploadedFile}
                setUploadProgress={setUploadProgress}
                setAnalysisResult={setAnalysisResult}
                setSourceConfig={setSourceConfig}
            />,
        },
        {
            title: 'Анализ данных',
            content: (
                <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '16px' }}>
                    {analysisMutation.isPending ? (
                        <Card size="small">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <Progress percent={70} status="active" style={{ flex: 1 }} />
                                <span>Анализ данных...</span>
                            </div>
                        </Card>
                    ) : (
                        <AnalysisDisplay analysisResult={analysisResult} />
                    )}
                </div>
            ),
        },
        {
            title: 'Хранилище и конфигурация',
            content: analysisResult ? (
                <>
                    <StorageAndConfig 
                        recommendations={analysisResult.recommendations}
                        selectedStorage={selectedStorage}
                        onStorageSelect={handleStorageSelect}
                        onConfigChange={handlePipelineConfigChange}
                    />
                    {pipelineMutation.isPending && (
                        <Card size="small" style={{ marginTop: 16 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <Progress percent={50} status="active" style={{ flex: 1 }} />
                                <span>Генерация DDL и пайплайна...</span>
                            </div>
                        </Card>
                    )}
                </>
            ) : (
                <p>Сначала завершите анализ данных</p>
            ),
        },
        {
            title: 'Предпросмотр и запуск',
            content: (sourceConfig && selectedStorage && pipelineConfig) ? (
                <div>
                    <DAGPreview 
                        sourceConfig={sourceConfig}
                        selectedStorage={selectedStorage}
                        pipelineConfig={pipelineConfig}
                        analysisResult={analysisResult}
                    />
                    {sessionId && (
                        <div style={{ marginTop: 16 }}>
                            <Button 
                                type="default" 
                                onClick={() => reportMutation.mutate({ session_id: sessionId })}
                                loading={reportMutation.isPending}
                            >
                                Сгенерировать отчет
                            </Button>
                            {reportResult && (
                                <Card size="small" style={{ marginTop: 16 }}>
                                    <h4>Отчет</h4>
                                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                                        {reportResult.report || JSON.stringify(reportResult, null, 2)}
                                    </pre>
                                </Card>
                            )}
                        </div>
                    )}
                </div>
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
                    <Button style={{ margin: '0 8px' }} onClick={handlePrev} aria-label="Назад">
                        Назад
                    </Button>
                )}
                {current < steps.length - 1 && (
                    <Button 
                        type="primary" 
                        onClick={handleNext} 
                        loading={
                            analysisMutation.isPending || 
                            pipelineMutation.isPending ||
                            (current === 0 && uploadedFile && uploadedFile.isUploading)
                        }
                        disabled={!canGoToNextStep()}
                        aria-label="Далее"
                    >
                        {current === 0 && uploadedFile && uploadedFile.isUploading ? 'Загружается файл...' : 
                         current === 2 && pipelineMutation.isPending ? 'Генерация...' : 'Далее'}
                    </Button>
                )}
            </div>
        </Card>
    );
};

export default DataSourceWizard;
