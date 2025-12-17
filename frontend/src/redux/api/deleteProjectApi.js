import api from '../../services/api';

export const deleteProjectApi = async (payload) => {
  const token = localStorage.getItem('token');

  const response = await api.delete(`/projects/${payload}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
