import React from 'react';
import { getLetterItem } from '../../utils/letterResolver';
import { IntertekLogo } from './LetterComponents/IntertekLogo';
import LetterDataFrameTable from './LetterComponents/LetterDataFrameTable';
import LetterSmartField from './LetterComponents/LetterSmartField';

const LetterPage3 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  return (
    <div className="letter-page">
      <IntertekLogo />
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
              <LetterDataFrameTable
                item={item}
                editMode={editMode}
                onChange={forceUpdate}
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
