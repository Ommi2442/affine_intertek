import api from '../../services/api';

export const reGenerateTrfClear = async (payload) => {
  const res = await api.post('/projects/trf-regenrate-reset', payload, {
    showLoader: true, 
  });

  return res.data;
};

export const reGenerateCdrClear = async (payload) => {
  const res = await api.post('/projects/cdr-regenrate-reset', payload, {
    showLoader: true, 
  });

  return res.data;
};

export const reGenerateLetterClear = async (payload) => {
  const res = await api.post('/projects/letter-regenrate-reset', payload, {
    showLoader: true, 
  });

  return res.data;
};