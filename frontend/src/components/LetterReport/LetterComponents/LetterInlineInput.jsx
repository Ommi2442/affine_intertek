import React from 'react';

const LetterInlineInput = ({ item, onChange, editMode, wide }) => {
  if (!item) return null;

  const displayValue = item.value && item.value !== '' ? item.value : item.key;

  return (
    <input
      type="text"
      value={displayValue}
      disabled={!editMode} //  THIS is the key
      onChange={(e) => {
        if (!editMode) return; // safety
        item.value = e.target.value;
        onChange?.();
      }}
      style={{
        border: '1px solid #535353',
        outline: 'none',
        background: editMode ? 'transparent' : '#faf7f7',
        fontSize: 'inherit',
        fontFamily: 'inherit',
        padding: '0 6px',
        cursor: editMode ? 'text' : 'default',
        width: wide ? '50%' : 'auto',
        flex: wide ? 1 : 'unset',
        minWidth: wide ? 0 : '120px',
        boxSizing: 'border-box',
      }}
    />
  );
};

export default LetterInlineInput;
