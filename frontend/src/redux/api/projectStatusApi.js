import api from "../../services/api"; 
// ← this should be your axios instance with baseURL configured

export const getProjectReportStatusApi = async (projectId) => {
  const response = await api.get(
    `/projects/report/status`,
    { params: { id: projectId } }
  );

  return response.data;
};

