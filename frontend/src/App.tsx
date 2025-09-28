import DataSourceWizard from "./components/DataSourceWizard";
import { Layout } from 'antd';

const { Header, Content, Footer } = Layout;

function App() {
  return (
    <Layout className="layout">
      <Header>
        <div className="logo" />
        {/* Can add Menu here later */}
      </Header>
      <Content style={{ padding: '0 50px', marginTop: 64 }}>
        <div className="site-layout-content" style={{ background: '#fff', padding: 24, minHeight: 380 }}>
          <DataSourceWizard />
        </div>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        ETL AI Assistant ©2025 Created by AI
      </Footer>
    </Layout>
  )
}

export default App
