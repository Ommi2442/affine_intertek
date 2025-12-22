export const truncateWords = (text, wordLimit = 20) => {
  if (!text) return '';
  const words = text.split(/\s+/);
  return words.length > wordLimit ? words.slice(0, wordLimit).join(' ') : text;
};
