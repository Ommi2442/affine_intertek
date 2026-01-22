import React, { useEffect, useState } from 'react';

const LetterInlineInput = ({
  item,
  onChange,
  editMode,
  onConfidenceChange,
  wide,
}) => {
  if (!item) return null;

  const [localValue, setLocalValue] = useState(item.value ?? item.key ?? '');

  // Sync when item changes externally
  useEffect(() => {
    setLocalValue(item.value ?? '');
  }, [item.value]);

  return (
    <input
      type="text"
      value={localValue}
      disabled={!editMode}
      onChange={(e) => {
        if (!editMode) return;
        setLocalValue(e.target.value); // fast typing, no global re-render
      }}
      onBlur={() => {
        if (!editMode) return;
        item.value = localValue; // commit on blur
        item.is_user_edited = true;
        onChange?.(); // one re-render only
        onConfidenceChange?.();
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
