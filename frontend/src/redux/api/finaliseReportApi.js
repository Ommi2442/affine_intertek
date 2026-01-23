import api from '../../services/api';

export const finaliseReportApi = async (payload) => {
  const res = await api.post('/projects/finalize_report/trf', payload, {
    showLoader: true, // optional: match your UX pattern
  });

  return res.data;
};
