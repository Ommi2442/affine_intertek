import React, { useEffect } from 'react';
import { IntertekLogo } from './LetterComponents/IntertekLogo';
import { getLetterItem } from '../../utils/letterResolver';
import { formatIssueDate } from './LetterComponents/formatIssueDate';
import LetterSmartField from './LetterComponents/LetterSmartField';

const LetterPage1 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);

  useEffect(() => {
    const item = getLetterItem(json, 'KEY3'); // Issue Date key
    if (!item) return;

    // Only auto-fill once
    if (!item.value) {
      item.value = formatIssueDate();
      item.is_user_edited = false; // system-filled
      forceUpdate();
    }
  }, [json]);
  return (
    <div className="letter-page">
      <IntertekLogo />
      <h1 className="page1_cust_name">
        <LetterSmartField
          json={json}
          name="CUSTOMER NAME"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
      </h1>
      <h2 className="page1_letter_report">LETTER REPORT</h2>
      <h4>SCOPE OF WORK</h4>
      <LetterSmartField
        json={json}
        name="KEY1"
        editMode={editMode}
        onChange={forceUpdate}
        onApprove={handleApprove}
        onComment={openComment}
        onBookmark={onBookmarkClick}
        wide={true}
      />

      <h4>REPORT NUMBER</h4>
      <LetterSmartField
        json={json}
        name="XXXXXXXXXXXXXXXXXXXXXXXX"
        editMode={editMode}
        onChange={forceUpdate}
        onApprove={handleApprove}
        onComment={openComment}
        onBookmark={onBookmarkClick}
      />

      <div style={{ display: 'flex' }}>
        <div style={{ marginRight: '2%' }}>
          <h4>ISSUE DATE</h4>
          <LetterSmartField
            json={json}
            name="KEY3"
            editMode={editMode}
            onChange={forceUpdate}
            onApprove={handleApprove}
            onComment={openComment}
            onBookmark={onBookmarkClick}
          />
        </div>

        <div>
          <h4>[REVISED DATE]</h4>
          <LetterSmartField
            json={json}
            name="[DD-mmmm-yyyy]"
            editMode={editMode}
            onChange={forceUpdate}
            onApprove={handleApprove}
            onComment={openComment}
            onBookmark={onBookmarkClick}
          />
        </div>
      </div>
      <div className="letter-header-row">
        {/* LEFT TEXT BLOCK */}
        <div className="letter-header-text">
          <div>
            Pages{'  '}
            <LetterSmartField
              json={json}
              name="Pages"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
          <div style={{ fontWeight: 700, marginTop: '10%' }}>
            DOCUMENT CONTROL NUMBER
          </div>

          <span>GFT-OP-10a (21-June-2019)</span>
          <br />
          <span>© 2019 INTERTEK</span>
        </div>

        {/* RIGHT IMAGE */}
        <img
          src="/images/search_logo_letter.png"
          className="letter-header-image"
        />
      </div>
    </div>
  );
};

export default LetterPage1;
