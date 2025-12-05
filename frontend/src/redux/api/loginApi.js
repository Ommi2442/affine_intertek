import api from '../../services/api';

export const ssouserdataApi = async (userInfo) => {
  try {
    const response = await api.post('/sso-login', userInfo);
    return response;
  } catch (error) {
    console.error('SSO Login Error:', error);
    throw error;
  }
};
