export const toArray = (v) => {
  if (Array.isArray(v)) return v;
  if (v == null || v === '') return [''];
  return [v];
};
