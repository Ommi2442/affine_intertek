import api from '../../services/api';

export const generateTrfApi = async (project_id) => {
  const token = localStorage.getItem('token');

  const response = await api.get('/projects/fetch-trf-reports', {
    params: { project_id },
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
