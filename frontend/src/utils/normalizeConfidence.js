export const normalizeConfidence = (value) => {
  if (value === null || value === undefined) return null;

  const num = Number(value);
  if (Number.isNaN(num)) return null;

  // 🔥 CDR scale (0–1)
  if (num <= 1) {
    return Math.round(num * 100);
  }

  // 🔥 TRF scale (1–100)
  if (num > 1 && num <= 100) {
    return Math.round(num);
  }

  return null;
};
