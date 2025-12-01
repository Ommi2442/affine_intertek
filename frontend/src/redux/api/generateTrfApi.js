import api from '../../services/api';

export const generateTrfApi = async ({ project_id, file }) => {
  const token = localStorage.getItem('token');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', project_id);

  const response = await api.post('/projects/Trf-reports', formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
