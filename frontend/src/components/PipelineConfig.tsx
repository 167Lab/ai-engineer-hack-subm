import React from 'react';
import { Form, Input, Select, Card, Typography, Alert, InputNumber, Switch } from 'antd';
import { ClockCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { TargetType } from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

interface PipelineConfigProps {
    selectedStorage: TargetType;
    onConfigChange: (config: PipelineConfigData) => void;
}

export interface PipelineConfigData {
    pipeline_name: string;
    target_table: string;
    schedule: string;
    description: string;
    retries: number;
    emailOnFailure: boolean;
}

const scheduleOptions = [
    { value: '@once', label: 'Разовый запуск', description: 'Запуск только один раз' },
    { value: '@hourly', label: 'Каждый час', description: 'Запуск каждый час' },
    { value: '@daily', label: 'Ежедневно', description: 'Запуск каждый день в полночь' },
    { value: '@weekly', label: 'Еженедельно', description: 'Запуск каждую неделю' },
    { value: '@monthly', label: 'Ежемесячно', description: 'Запуск каждый месяц' },
];

const getStorageHelp = (storage: TargetType) => {
    switch (storage) {
        case TargetType.POSTGRES:
            return {
                tableLabel: 'Имя таблицы PostgreSQL',
                tablePlaceholder: 'public.my_table',
                tableHelp: 'Формат: схема.таблица (например: public.users)'
            };
        case TargetType.CLICKHOUSE:
            return {
                tableLabel: 'Имя таблицы ClickHouse',
                tablePlaceholder: 'default.my_table',
                tableHelp: 'Формат: база.таблица (например: default.events)'
            };
        case TargetType.HDFS:
            return {
                tableLabel: 'Путь в HDFS',
                tablePlaceholder: '/data/processed/my_data',
                tableHelp: 'Путь к директории или файлу в HDFS'
            };
        default:
            return {
                tableLabel: 'Имя целевой таблицы',
                tablePlaceholder: 'my_table',
                tableHelp: 'Введите имя таблицы или файла'
            };
    }
};

const PipelineConfig: React.FC<PipelineConfigProps> = ({ selectedStorage, onConfigChange }) => {
    const [form] = Form.useForm();
    const storageHelp = getStorageHelp(selectedStorage);

    const handleValuesChange = (_: any, allValues: PipelineConfigData) => {
        onConfigChange(allValues);
    };

    return (
        <div>
            <Title level={4}>Настройка пайплайна</Title>
            <Alert
                message="Настройка ETL пайплайна"
                description={`Настройте параметры пайплайна для загрузки данных в ${selectedStorage.toUpperCase()}`}
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
            />

            <Form
                form={form}
                layout="vertical"
                onValuesChange={handleValuesChange}
                initialValues={{
                    pipeline_name: 'etl_pipeline_' + Date.now().toString().slice(-6),
                    target_table: selectedStorage === TargetType.HDFS ? '/data/processed/my_data' : 'my_table',
                    schedule: '@daily',
                    description: 'Автоматически созданный ETL пайплайн',
                    retries: 2,
                    emailOnFailure: false,
                }}
            >
                <Card size="small" title={<><SettingOutlined /> Основные параметры</>} style={{ marginBottom: 16 }}>
                    <Form.Item
                        name="pipeline_name"
                        label="Имя пайплайна"
                        rules={[
                            { required: true, message: 'Введите имя пайплайна!' },
                            { pattern: /^[a-zA-Z0-9_]+$/, message: 'Только латинские буквы, цифры и подчеркивания!' }
                        ]}
                    >
                        <Input placeholder="my_etl_pipeline" />
                    </Form.Item>

                    <Form.Item
                        name="target_table"
                        label={storageHelp.tableLabel}
                        help={storageHelp.tableHelp}
                        rules={[{ required: true, message: 'Введите имя таблицы!' }]}
                    >
                        <Input placeholder={storageHelp.tablePlaceholder} />
                    </Form.Item>

                    <Form.Item
                        name="description"
                        label="Описание"
                        rules={[{ required: true, message: 'Введите описание пайплайна!' }]}
                    >
                        <Input.TextArea 
                            rows={3} 
                            placeholder="Краткое описание назначения пайплайна"
                        />
                    </Form.Item>
                </Card>

                <Card size="small" title={<><ClockCircleOutlined /> Расписание запуска</>} style={{ marginBottom: 16 }}>
                    <Form.Item
                        name="schedule"
                        label="Частота запуска"
                        rules={[{ required: true, message: 'Выберите расписание!' }]}
                    >
                        <Select placeholder="Выберите расписание" dropdownMatchSelectWidth={480}>
                            {scheduleOptions.map(option => (
                                <Option key={option.value} value={option.value}>
                                    <span style={{ display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
                                        <Text strong>{option.label}</Text>
                                        <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                            {option.description}
                                        </Text>
                                    </span>
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Alert
                        message="Информация о расписании"
                        description="После создания пайплайна вы сможете изменить расписание в интерфейсе Airflow"
                        type="info"
                        showIcon
                        style={{ marginTop: 16 }}
                    />
                </Card>

                <Card size="small" title={<><SettingOutlined /> Отказоустойчивость</>}>
                    <Form.Item
                        name="retries"
                        label="Количество повторных попыток"
                        help="Сколько раз задача будет перезапущена в случае сбоя."
                    >
                        <InputNumber min={0} max={10} style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item
                        name="emailOnFailure"
                        valuePropName="checked"
                        label="Отправлять email при сбое"
                        help="Уведомить по электронной почте, если задача не будет выполнена."
                    >
                        <Switch />
                    </Form.Item>
                </Card>
            </Form>
        </div>
    );
};

export default PipelineConfig;
