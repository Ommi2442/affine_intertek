import api from '../../services/api';

export const uploadReportImage = async (projectId, reportType, files) => {
  const token = localStorage.getItem('token');

  const formData = new FormData();
  formData.append('projectId', projectId);
  formData.append('report_type', reportType);

  // Only include real File objects
  const realFiles = files.filter((f) => f instanceof File);

  if (realFiles.length === 0) {
    console.warn(
      `Skipping upload for '${reportType}' because no real image found`
    );
    return { status: 'skipped', uploaded: [] };
  }

  realFiles.forEach((file) => {
    formData.append('files', file, file.name);
  });

  const response = await api.post('/projects/upload_images', formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
