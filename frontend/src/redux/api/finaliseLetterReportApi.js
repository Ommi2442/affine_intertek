import api from '../../services/api';

export const finaliseLetterReportApi = async (payload) => {
  const res = await api.post('/projects/finalize_report/letter', payload, {
    showLoader: true, // optional: match your UX pattern
  });

  return res.data;
};
