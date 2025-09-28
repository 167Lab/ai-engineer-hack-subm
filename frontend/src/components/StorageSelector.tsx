import React from 'react';
import { Card, Radio, Typography, Tag, Space, Alert } from 'antd';
import { CheckCircleOutlined, DatabaseOutlined, CloudServerOutlined, HddOutlined } from '@ant-design/icons';
import { TargetType } from '../types';

const { Title, Text } = Typography;

interface StorageOption {
    type: TargetType;
    name: string;
    description: string;
    icon: React.ReactNode;
    pros: string[];
    cons: string[];
}

const storageOptions: StorageOption[] = [
    {
        type: TargetType.POSTGRES,
        name: 'PostgreSQL',
        description: 'Реляционная база данных для транзакционных данных',
        icon: <DatabaseOutlined />,
        pros: ['ACID транзакции', 'SQL запросы', 'Хорошая производительность для небольших данных'],
        cons: ['Не подходит для больших данных', 'Ограниченная масштабируемость']
    },
    {
        type: TargetType.CLICKHOUSE,
        name: 'ClickHouse',
        description: 'Колоночная база данных для аналитических запросов',
        icon: <CloudServerOutlined />,
        pros: ['Высокая скорость аналитических запросов', 'Сжатие данных', 'Масштабируемость'],
        cons: ['Не подходит для транзакций', 'Сложность настройки']
    },
    {
        type: TargetType.HDFS,
        name: 'HDFS',
        description: 'Распределенная файловая система для больших данных',
        icon: <HddOutlined />,
        pros: ['Масштабируемость', 'Отказоустойчивость', 'Подходит для любых данных'],
        cons: ['Сложность управления', 'Требует Hadoop экосистему']
    }
];

interface StorageSelectorProps {
    recommendations?: any[];
    selectedStorage?: TargetType;
    onStorageSelect: (storage: TargetType) => void;
}

const StorageSelector: React.FC<StorageSelectorProps> = ({ 
    recommendations, 
    selectedStorage, 
    onStorageSelect 
}) => {
    const getRecommendationForStorage = (storageType: TargetType) => {
        return recommendations?.find(rec => 
            (rec.storage_type?.toLowerCase() === storageType) || 
            (rec.primary_storage?.toLowerCase() === storageType)
        );
    };

    return (
        <div>
            <Title level={4}>Выберите хранилище для данных</Title>
            
            {recommendations && recommendations.length > 0 && (
                <Alert
                    message="Рекомендации ИИ"
                    description="На основе анализа ваших данных система рекомендует следующие варианты хранения"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                />
            )}

            <Radio.Group 
                value={selectedStorage} 
                onChange={(e) => onStorageSelect(e.target.value)}
                style={{ width: '100%' }}
            >
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {storageOptions.map((option) => {
                        const recommendation = getRecommendationForStorage(option.type);
                        const isRecommended = !!recommendation;
                        
                        return (
                            <Card 
                                key={option.type}
                                style={{ 
                                    width: '100%',
                                    border: isRecommended ? '2px solid #52c41a' : '1px solid #d9d9d9',
                                    backgroundColor: isRecommended ? '#f6ffed' : 'white'
                                }}
                                size="small"
                            >
                                <Radio value={option.type} style={{ width: '100%' }}>
                                    <div style={{ marginLeft: 8 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                                            {option.icon}
                                            <Title level={5} style={{ margin: '0 0 0 8px' }}>
                                                {option.name}
                                            </Title>
                                            {isRecommended && (
                                                <Tag 
                                                    icon={<CheckCircleOutlined />} 
                                                    color="success" 
                                                    style={{ marginLeft: 8 }}
                                                >
                                                    Рекомендовано ИИ
                                                </Tag>
                                            )}
                                        </div>
                                        
                                        <Text type="secondary">{option.description}</Text>
                                        
                                        {recommendation && (
                                            <div style={{ marginTop: 8, padding: '8px', background: '#e6f7ff', borderRadius: '6px' }}>
                                                <Text strong>Обоснование: </Text>
                                                <Text>{recommendation.reasoning}</Text>
                                                {recommendation.confidence && (
                                                    <div style={{ marginTop: 4 }}>
                                                        <Text type="secondary">
                                                            Уверенность: {Math.round(recommendation.confidence * 100)}%
                                                        </Text>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        
                                        <div style={{ marginTop: 12 }}>
                                            <div style={{ marginBottom: 4 }}>
                                                <Text strong style={{ color: '#52c41a' }}>Преимущества:</Text>
                                            </div>
                                            <div style={{ marginBottom: 8 }}>
                                                {option.pros.map((pro, idx) => (
                                                    <Tag key={idx} color="green">
                                                        {pro}
                                                    </Tag>
                                                ))}
                                            </div>
                                            
                                            <div style={{ marginBottom: 4 }}>
                                                <Text strong style={{ color: '#ff4d4f' }}>Ограничения:</Text>
                                            </div>
                                            <div>
                                                {option.cons.map((con, idx) => (
                                                    <Tag key={idx} color="volcano">
                                                        {con}
                                                    </Tag>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </Radio>
                            </Card>
                        );
                    })}
                </Space>
            </Radio.Group>
        </div>
    );
};

export default StorageSelector;
