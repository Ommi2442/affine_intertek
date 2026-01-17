import React from 'react';
import { getDropdownOptions } from '../../../utils/letterResolver';

const LetterDropdown = ({ item, onChange }) => {
  const options = getDropdownOptions(item.key);

  return (
    <select
      value={item.value || ''}
      onChange={(e) => {
        item.value = e.target.value; // writes back to JSON
        onChange?.();
      }}
      style={{
        padding: '4px 6px',
        margin: '0 6px',
        border: '1px solid #888',
        borderRadius: '4px',
        fontSize: '14px',
      }}
    >
      <option value="">Select…</option>
      {options.map((opt, i) => (
        <option key={i} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
};

export default LetterDropdown;
