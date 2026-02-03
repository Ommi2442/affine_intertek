import React from 'react';

import LetterHoverField from './LetterHoverField';
import {
  getLetterItem,
  resolveLetterField,
} from '../../../utils/letterResolver';

const LetterSmartField = ({
  json,
  name,
  editMode,
  onChange,
  onApprove,
  onComment,
  onBookmark,
  onConfidenceChange,
  wide = false,
  pdfLoaded,
}) => {
  const item = getLetterItem(json, name);

  if (!item) {
    return <>{resolveLetterField(json, name)}</>;
  }

  return (
    <LetterHoverField
      item={item}
      editMode={editMode}
      onChange={onChange}
      onApprove={() => onApprove?.(item)}
      onComment={() => onComment?.(item)}
      onBookmark={() => onBookmark?.(item)}
      onConfidenceChange={onConfidenceChange}
      wide={wide}
      pdfLoaded={pdfLoaded}
    />
  );
};

export default LetterSmartField;
