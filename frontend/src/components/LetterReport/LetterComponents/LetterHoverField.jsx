// components/LetterReport/LetterHoverField.jsx
import React, { useState } from 'react';
import { Box } from '@mui/material';
import HoverActionWrapper from '../../Common/HoverActionsWrapper';
import LetterInlineInput from './LetterInlineInput';
import { renderConfidenceColor } from '../../../utils/renderConfidenceColor';

const LetterHoverField = ({
  item,
  editMode,
  onChange,
  onApprove,
  onComment,
  onBookmark,
  onConfidenceChange,
  wide = false,
  pdfLoaded,
}) => {
  const [hover, setHover] = useState(false);
  if (!item) return null;

  const hasValue =
    item.value !== null && String(item.value || '').trim() !== '';

  const canApprove =
    item.ai_fillable === true || item.confidence_overRide === true;

  return (
    <Box
      component={wide ? 'div' : 'span'}
      sx={{
        display: wide ? 'flex' : 'inline-flex',
        alignItems: 'center',
        position: 'relative',
        paddingRight: '1%',
        whiteSpace: wide ? 'normal' : 'nowrap',
        maxWidth: wide ? '100%' : 600,
        width: wide ? '100%' : 'auto',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* FIELD */}
      <LetterInlineInput
        item={item}
        editMode={editMode}
        onChange={onChange}
        onConfidenceChange={onConfidenceChange}
        wide={wide}
      />

      {/* CONFIDENCE DOT */}
      {(item.ai_fillable || item.confidence_overRide) &&
        renderConfidenceColor(
          item.confidence,
          item.is_user_edited,
          item.ai_fillable || item.confidence_overRide,
          true
        )}

      {/* HOVER BUTTONS — MUST be inside same hover box */}
      <Box
        sx={{
          position: 'absolute',
          right: 0,
          top: '-19px',
          zIndex: 5,
          pointerEvents: hover ? 'auto' : 'none',
        }}
      >
        <HoverActionWrapper
          show={hover}
          onApprove={canApprove ? onApprove : null}
          onComment={onComment}
          onBookmark={hasValue ? onBookmark : null}
          bookmarkDisabled={!pdfLoaded}
        />
      </Box>
    </Box>
  );
};

export default LetterHoverField;
