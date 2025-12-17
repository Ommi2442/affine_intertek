import api from '../../services/api';

export const archieveProjectApi = async (payload) => {
  const token = localStorage.getItem('token');

  const response = await api.put(
    `/projects/${payload.param}`,
    payload.bodyObj,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
};
