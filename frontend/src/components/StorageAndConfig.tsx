import React from 'react';
import { Card, Typography, Space, Divider } from 'antd';
import StorageSelector from './StorageSelector';
import PipelineConfig, { PipelineConfigData } from './PipelineConfig';
import { TargetType } from '../types';

const { Title, Paragraph } = Typography;

interface StorageAndConfigProps {
  recommendations?: any[];
  selectedStorage?: TargetType;
  onStorageSelect: (s: TargetType) => void;
  onConfigChange: (cfg: PipelineConfigData) => void;
}

const StorageAndConfig: React.FC<StorageAndConfigProps> = ({
  recommendations,
  selectedStorage,
  onStorageSelect,
  onConfigChange,
}) => {
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      {recommendations && recommendations.length > 0 && (
        <Card size="small" title="Рекомендация модели">
          <Paragraph style={{ margin: 0 }}>
            {recommendations[0]?.reasoning || 'Модель сформировала рекомендации по хранилищу и конфигурации пайплайна.'}
          </Paragraph>
        </Card>
      )}

      <Card size="small">
        <Title level={5} style={{ marginTop: 0 }}>Выбор хранилища</Title>
        <StorageSelector
          recommendations={recommendations}
          selectedStorage={selectedStorage}
          onStorageSelect={onStorageSelect}
        />
      </Card>

      <Divider style={{ margin: '8px 0' }} />

      <Card size="small">
        <Title level={5} style={{ marginTop: 0 }}>Параметры пайплайна</Title>
        {selectedStorage ? (
          <PipelineConfig onConfigChange={onConfigChange} selectedStorage={selectedStorage as TargetType} />
        ) : (
          <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
            Сначала выберите хранилище выше, затем настройте параметры пайплайна
          </Typography.Paragraph>
        )}
      </Card>
    </Space>
  );
};

export default StorageAndConfig;


