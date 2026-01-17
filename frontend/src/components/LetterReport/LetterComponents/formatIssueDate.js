export const formatIssueDate = (date = new Date()) => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = date.toLocaleString('en-US', { month: 'long' });
  const year = String(date.getFullYear());
  return `${day}-${month}-${year}`;
};
