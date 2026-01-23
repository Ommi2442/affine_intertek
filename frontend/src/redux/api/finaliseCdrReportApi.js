import api from '../../services/api';

export const finaliseCdrReportApi = async (payload) => {
  const res = await api.post('/projects/finalize_report/cdr', payload, {
    showLoader: true, // optional: match your UX pattern
  });

  return res.data;
};
