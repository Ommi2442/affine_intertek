import React from 'react';
import { getLetterItem } from '../../utils/letterResolver';
import LetterDataFrameTable from './LetterComponents/LetterDataFrameTable';
import LetterSmartField from './LetterComponents/LetterSmartField';
import { IconButton } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import LetterHeader from './LetterComponents/LetterHeader';
import LetterCriticalDataFrameTable from './LetterComponents/LetterCriticalDataFrameTable';

const LetterPage3 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
  onConfidenceChange,
  pdfLoaded,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  //  Hover actions for Letter tables (Approve / Comment / Bookmark)
  const renderHoverActions = (tIdx, iIdx, userEditable, directItem) => {
    const item =
      directItem ??
      (tIdx != null && iIdx != null
        ? json?.Tables?.[tIdx]?.Items?.[iIdx]
        : null);

    if (!item) return null;

    //  Allow dataframe rows unconditionally
    if (!directItem) {
      const isLetterTableItem = item.dataframe_table === true;
      if (!isLetterTableItem && userEditable !== true) return null;

      const hasValueField = Object.prototype.hasOwnProperty.call(item, 'value');
      if (!hasValueField) return null;
    }
    const isNonConformanceTable = item.key === 'Non-conformance Table';
    const isDataFrameRow = Boolean(directItem);
    const canApprove =
      isNonConformanceTable || isDataFrameRow || item.ai_fillable === true;

    return (
      <div className="dt-hover-actions">
        {canApprove && (
          <IconButton
            size="small"
            onClick={() => {
              if (directItem) {
                directItem.is_user_edited = true;
                onConfidenceChange?.();
                forceUpdate();
              }
            }}
          >
            <CheckCircleIcon className="dt-icon-approve" />
          </IconButton>
        )}

        <IconButton size="small" onClick={() => openComment?.(item)}>
          <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
        </IconButton>

        <IconButton size="small" onClick={() => onBookmarkClick?.(item)}>
          <MenuBookOutlinedIcon className="dt-icon-bookmark" />
        </IconButton>
      </div>
    );
  };

  return (
    <div className="letter-page">
      <LetterHeader
        json={json}
        editMode={editMode}
        onChange={forceUpdate}
        onApprove={handleApprove}
        onComment={openComment}
        onBookmark={onBookmarkClick}
      />

      <h3 style={{ marginBottom: '5%' }}>Letter Report</h3>
      <p>
        Please review the following identified sections of the above referenced
        standards for the complete details of the requirements in question.
      </p>

      <p>
        Furthermore if{' '}
        <LetterSmartField
          json={json}
          name="<additional/modified>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
          onConfidenceChange={onConfidenceChange}
          pdfLoaded={pdfLoaded}
        />
        samples or technical documentation are required to support the testing
        of your product, these will be detailed along with any non-conformity
        items in section 2.
      </p>

      <h3 className="section">SECTION 2</h3>
      <span>
        <b>NON-CONFORMANCES</b>
      </span>

      <p>
        The shared documents were evaluated during the intrinsic safety analysis
        and constructional evaluation and following non-conformances were
        observed:
      </p>

      {(() => {
        const item = getLetterItem(json, 'Non-conformance Table');

        if (item?.dataframe_table === true && Array.isArray(item.value)) {
          if (item.value.length === 0) {
            return (
              <p style={{ fontStyle: 'italic', color: '#666', marginTop: 8 }}>
                No Table Data
              </p>
            );
          }

          return (
            <LetterDataFrameTable
              item={item}
              editMode={editMode}
              onChange={(updatedRows) => {
                item.value = updatedRows;
                forceUpdate();
              }}
              renderHoverActions={renderHoverActions}
            />
          );
        }

        return null;
      })()}

      <p>
        Note: The above non-conformances were identified during the Initial
        Documentation Review phase of the project. Additional non-conformances
        may be identified during the continued construction evaluation of the
        equipment.{' '}
      </p>

      <h3 className="section">SECTION 3</h3>
      <span>
        <b>CRITICAL COMPONENTS & MATERIALS</b>
      </span>
      {(() => {
        const item = getLetterItem(json, 'Critical components table');

        if (item?.dataframe_table === true && Array.isArray(item.value)) {
          if (item.value.length === 0) {
            return (
              <p style={{ fontStyle: 'italic', color: '#666', marginTop: 8 }}>
                No Data Found
              </p>
            );
          }

          return (
            <LetterCriticalDataFrameTable
              item={item}
              editMode={editMode}
              onChange={forceUpdate}
              renderHoverActions={renderHoverActions}
            />
          );
        }

        return null;
      })()}
    </div>
  );
};

export default LetterPage3;
