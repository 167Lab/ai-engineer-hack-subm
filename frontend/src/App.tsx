import React from 'react';
import DataSourceWizard from "./components/DataSourceWizard";
import { Layout, Button, Typography } from 'antd';
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import Login from './pages/Login.tsx';
import { logout } from './services/api';

const { Header, Content, Footer } = Layout;

function App() {
  const [resetSignal, setResetSignal] = React.useState(0);
  const navigate = useNavigate();
  const location = useLocation();

  const isAuthed = Boolean(typeof window !== 'undefined' && localStorage.getItem('auth_token'));

  React.useEffect(() => {
    if (!isAuthed && location.pathname !== '/login') {
      navigate('/login', { replace: true });
    }
    if (isAuthed && location.pathname === '/login') {
      navigate('/', { replace: true });
    }
  }, [isAuthed, location.pathname, navigate]);

  const handleGoHome = () => {
    navigate('/');
    setResetSignal((v) => v + 1);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (_) {}
    try {
      localStorage.removeItem('auth_token');
    } catch (_) {}
    navigate('/login', { replace: true });
  };

  return (
    <Layout className="layout">
      <Header>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '100%' }}>
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            Интеллектуальный цифровой инженер данных
          </Typography.Title>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button onClick={handleGoHome} aria-label="В начало" type="default">
              В начало
            </Button>
            <Button onClick={handleLogout} aria-label="Выход" danger>
              Выход
            </Button>
          </div>
        </div>
      </Header>
      <Content style={{ padding: '24px', marginTop: 64, display: 'flex', justifyContent: 'center' }}>
        <div
          className="site-layout-content"
          style={{
            background: '#fff',
            padding: 24,
            minHeight: 380,
            width: '100%',
            maxWidth: 1280,
          }}
        >
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={isAuthed ? <DataSourceWizard resetSignal={resetSignal} /> : <Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        Интеллектуальный цифровой инженер данных ©2025 Created by 167_lab
      </Footer>
    </Layout>
  )
}

export default App
