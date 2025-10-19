import type { ThemeConfig } from 'antd';

const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontSize: 14,
    wireframe: false,
  },
  components: {
    Button: {
      controlHeightLG: 44,
    },
    Input: {
      controlHeightLG: 44,
    },
    Select: {
      controlHeightLG: 44,
    },
  },
};

export default appTheme;


