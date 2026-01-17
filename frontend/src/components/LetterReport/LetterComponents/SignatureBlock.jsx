import React from 'react';

import './SignatureBlock.css';
import LetterSmartField from './LetterSmartField';

const SignatureBlock = ({
  json,
  editMode,
  forceUpdate,
  handleApprove,
  openComment,
  onBookmarkClick,
}) => {
  return (
    <div className="signature-grid">
      {/* LEFT SIDE */}
      <div className="sig-col">
        <div className="sig-row">
          <div className="sig-label">Completed by:</div>
          <div className="sig-value">
            <LetterSmartField
              json={json}
              name="Completed By"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Title:</div>
          <div className="sig-value">
            <LetterSmartField
              json={json}
              name="Compliance Investigator"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Signature:</div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Date</div>
        </div>
      </div>

      {/* RIGHT SIDE */}
      <div className="sig-col">
        <div className="sig-row">
          <div className="sig-label">Reviewed by:</div>
          <div className="sig-value">
            <LetterSmartField
              json={json}
              name="«Reviewer»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Title:</div>
          <div className="sig-value">
            <LetterSmartField
              json={json}
              name="«ReviewerTitle»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Signature</div>
        </div>

        <div className="sig-row">
          <div className="sig-label">Date:</div>
        </div>
      </div>
    </div>
  );
};

export default SignatureBlock;
