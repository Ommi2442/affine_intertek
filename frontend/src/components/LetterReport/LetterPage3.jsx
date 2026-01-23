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
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  //  Hover actions for Letter tables (Approve / Comment / Bookmark)
  const renderHoverActions = (tIdx, iIdx, userEditable, directItem) => {
    //  Allow direct item mode (Letter tables)
    const item =
      directItem ??
      (tIdx != null && iIdx != null
        ? json?.Tables?.[tIdx]?.Items?.[iIdx]
        : null);

    if (!item) return null;

    // For Letter dataframe tables → ignore user_editable gate
    const isLetterTableItem = item.dataframe_table === true;

    if (!isLetterTableItem && userEditable !== true) return null;

    const hasValueField = Object.prototype.hasOwnProperty.call(item, 'value');
    if (!hasValueField) return null;

    // const isTbdNotAvailable =
    //   typeof item.value === 'string' &&
    //   item.value.trim().toLowerCase() === 'tbd-info not available';

    const canApprove = item.ai_fillable === true;

    return (
      <div className="dt-hover-actions">
        {/* APPROVE */}
        {canApprove && (
          <IconButton
            size="small"
            onClick={() => {
              if (tIdx != null && iIdx != null) {
                handleApprove?.(tIdx, iIdx);
              }
            }}
          >
            <CheckCircleIcon className="dt-icon-approve" />
          </IconButton>
        )}

        {/* COMMENT */}
        <IconButton
          size="small"
          onClick={() => {
            //  Letter table → open comment using direct item
            if (directItem) {
              openComment?.(directItem);
              return;
            }

            // Normal DataTable path
            if (tIdx != null && iIdx != null) {
              openComment?.(tIdx, iIdx);
            }
          }}
        >
          <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
        </IconButton>

        {/* BOOKMARK */}
        {
          <IconButton
            size="small"
            onClick={() => {
              const row =
                item ??
                (tIdx != null && iIdx != null
                  ? { __t: tIdx, __i: iIdx }
                  : null);

              if (row) onBookmarkClick?.(row);
            }}
          >
            <MenuBookOutlinedIcon className="dt-icon-bookmark" />
          </IconButton>
        }
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

        if (
          item?.dataframe_table === true &&
          Array.isArray(item.value) &&
          item.value.length > 0
        ) {
          return (
            <LetterDataFrameTable
              item={item}
              editMode={editMode}
              onChange={forceUpdate}
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

        if (
          item?.dataframe_table === true &&
          Array.isArray(item.value) &&
          item.value.length > 0
        ) {
          return (
            item?.value && (
              <LetterCriticalDataFrameTable
                item={item}
                editMode={editMode}
                onChange={forceUpdate}
                renderHoverActions={renderHoverActions}
              />
            )
          );
        }

        return null;
      })()}
    </div>
  );
};

export default LetterPage3;
