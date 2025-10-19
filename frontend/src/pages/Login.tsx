import React from 'react';
import { Card, Form, Input, Button, Typography, Alert, Space } from 'antd';
import { useNavigate } from 'react-router-dom';
import { login, bootstrapAirflowSession } from '../services/api';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onFinish = async (values: { username: string; password: string }) => {
    setError(null);
    setLoading(true);
    try {
      const data = await login(values);
      if (data?.token) {
        localStorage.setItem('auth_token', data.token);
      }
      // инициализируем сессию Airflow
      try {
        await bootstrapAirflowSession();
      } catch (_) {}
      navigate('/');
    } catch (e: any) {
      setError(e?.response?.data?.error || 'Ошибка авторизации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <Card style={{ width: 420 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Title level={4} style={{ marginBottom: 4 }}>Добро пожаловать</Title>
            <Text type="secondary">Войдите, чтобы продолжить работу с мастером пайплайна</Text>
          </div>

          {error && <Alert type="error" message={error} />}

          <Form form={form} layout="vertical" onFinish={onFinish}>
            <Form.Item label="Логин" name="username" rules={[{ required: true, message: 'Введите логин' }]}>
              <Input placeholder="admin" autoComplete="username" aria-label="Логин" size="large" />
            </Form.Item>
            <Form.Item label="Пароль" name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
              <Input.Password placeholder="******" autoComplete="current-password" aria-label="Пароль" size="large" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={loading} aria-label="Войти">
                Войти
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  );
};

export default Login;


