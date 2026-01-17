/* eslint-disable */

const normalize = (str = '') =>
  str
    .replace(/[«»<>]/g, '') // remove brackets
    .replace(/\s*\/\s*/g, '/') // normalize slash spacing
    .replace(/\u00A0/g, ' ') // remove NBSP
    .trim()
    .toLowerCase();

const getAllItems = (letterJson) => {
  if (!letterJson?.pages) return [];
  return letterJson.pages.flatMap((p) => p.items || []);
};

export const resolveLetterField = (letterJson, key) => {
  if (!letterJson || !key) return key;

  const items = getAllItems(letterJson);

  const found = items.find((i) => normalize(i.key) === normalize(key));

  if (found && found.value) return found.value;

  return key;
};

export const getLetterItem = (letterJson, key) => {
  if (!letterJson || !key) return null;

  const items = getAllItems(letterJson);

  return items.find((i) => normalize(i.key) === normalize(key));
};

export const getDropdownOptions = (key = '') => {
  if (!key) return [];

  // <CB Test Report/ETL CDR/Deliverable>
  if (key.includes('<') && key.includes('>')) {
    return key
      .replace(/[<>]/g, '')
      .split('/')
      .map((s) => s.trim());
  }

  // evaluation (Stage 1)/testing (Stage 2)
  return key.split('/').map((s) => s.trim());
};
