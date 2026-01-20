import React from 'react';

import { IntertekLogo } from './IntertekLogo';
import LetterSmartField from './LetterSmartField';

const LetterHeader = ({
  json,
  editMode,
  onChange,
  onApprove,
  onComment,
  onBookmark,
  minWidth = 260,
  companyFieldName = '«AppCOMPANYNAME»',
  reportNumberFieldName = '«ReportNumber»',
  reportLabel = 'Intertek Report: No:',
}) => {
  if (!json) return null; //  guard

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 12,
      }}
    >
      <IntertekLogo />

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: '6px',
          minWidth,
        }}
      >
        <LetterSmartField
          json={json}
          name={companyFieldName}
          editMode={editMode}
          onChange={onChange}
          onApprove={onApprove}
          onComment={onComment}
          onBookmark={onBookmark}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '6px',
            width: '100%',
          }}
        >
          <div style={{ whiteSpace: 'nowrap', fontWeight: 500 }}>
            {reportLabel}
          </div>

          <LetterSmartField
            json={json}
            name={reportNumberFieldName}
            editMode={editMode}
            onChange={onChange}
            onApprove={onApprove}
            onComment={onComment}
            onBookmark={onBookmark}
          />
        </div>
      </div>
    </div>
  );
};

export default LetterHeader;
