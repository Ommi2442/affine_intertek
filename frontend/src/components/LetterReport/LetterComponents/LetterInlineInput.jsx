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

  const canCountAsUserEdit =
    item.ai_fillable === true || item.dataframe_table === true;

  return (
    <input
      type="text"
      value={localValue}
      disabled={!editMode}
      onChange={(e) => {
        if (!editMode) return;

        const val = e.target.value;
        setLocalValue(val);

        // Always update value
        item.value = val;

        // ONLY these fields affect user-edited count
        if (canCountAsUserEdit) {
          if (!item.is_user_edited) {
            item.is_user_edited = true;
          }
          onConfidenceChange?.();
        }

        // Persist + rerender
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
