import React from 'react';
import { Tree, Input, Button, Space, Typography } from 'antd';
import type { DataNode } from 'antd/es/tree';
import { listFiles, FileNode } from '../services/api';

const { Title } = Typography;

interface ServerFileBrowserProps {
  rootPath: string;
  onSelectPath: (path: string) => void;
}

const toTreeData = (node: FileNode): DataNode => ({
  title: node.title,
  key: node.key,
  isLeaf: node.isLeaf,
  children: node.children?.map(toTreeData),
});

const ServerFileBrowser: React.FC<ServerFileBrowserProps> = ({ rootPath, onSelectPath }) => {
  const [treeData, setTreeData] = React.useState<DataNode[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [filter, setFilter] = React.useState('');

  const loadRoot = async () => {
    setLoading(true);
    try {
      const data = await listFiles({ path: rootPath, depth: 3 });
      setTreeData([toTreeData(data.tree)]);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    loadRoot();
  }, [rootPath]);

  const onSelect = (keys: React.Key[]) => {
    const key = keys?.[0];
    if (typeof key === 'string') {
      onSelectPath(key);
    }
  };

  const filteredData = React.useMemo(() => {
    if (!filter.trim()) return treeData;
    const match = (node: DataNode): DataNode | null => {
      const title = String(node.title || '').toLowerCase();
      const ok = title.includes(filter.toLowerCase());
      const children = (node.children || [])
        .map(match)
        .filter(Boolean) as DataNode[];
      if (ok || children.length) return { ...node, children };
      return null;
    };
    return treeData.map(match).filter(Boolean) as DataNode[];
  }, [treeData, filter]);

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Title level={5} style={{ margin: 0 }}>Файлы на сервере</Title>
        <Space.Compact style={{ width: '100%' }}>
          <Input placeholder="Фильтр по имени" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Фильтр по имени файла" />
          <Button onClick={loadRoot} loading={loading} aria-label="Обновить список файлов">Обновить</Button>
        </Space.Compact>
        <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 8 }}>
          <Tree
            treeData={filteredData}
            onSelect={onSelect}
            selectable
            defaultExpandAll
            aria-label="Дерево файлов на сервере"
          />
        </div>
      </Space>
    </div>
  );
};

export default ServerFileBrowser;


