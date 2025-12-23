export const getLoggedInUser = () => {
  try {
    const user = localStorage.getItem('name');
    return user || 'User';
  } catch {
    return 'User';
  }
};
