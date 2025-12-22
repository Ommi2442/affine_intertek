export const normalizeNewLines = (text = '') => {
  return (
    text
      // collapse lines that contain only whitespace
      .replace(/\n\s*\n+/g, '\n')
      // normalize Windows line endings
      .replace(/\r\n/g, '\n')
      // trim start/end junk
      .trim()
  );
};
