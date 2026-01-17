// LetterField.jsx
import React from 'react';
import { getLetterItem } from '../../../utils/letterResolver';
import LetterInlineInput from './LetterInlineInput';
import { renderConfidenceColor } from '../../../utils/renderConfidenceColor';

const LetterField = ({ json, name, editMode, onChange }) => {
  const item = getLetterItem(json, name);
  if (!item) return <span>{name}</span>;

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <LetterInlineInput item={item} editMode={editMode} onChange={onChange} />

      {item.ai_fillable &&
        renderConfidenceColor(
          item.confidence,
          item.is_user_edited,
          item.ai_fillable,
          true
        )}
    </span>
  );
};

export default LetterField;
