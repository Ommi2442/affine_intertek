import React from 'react';
import { IntertekLogo } from './LetterComponents/IntertekLogo';
import SignatureBlock from './LetterComponents/SignatureBlock';
import LetterSmartField from './LetterComponents/LetterSmartField';
import { getLetterItem } from '../../utils/letterResolver';
import LetterPhotoSection from './LetterComponents/LetterPhotoSection';

const LetterPage5 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  const item = getLetterItem(json, 'photograph');
  return (
    <div className="letter-page">
      <IntertekLogo />
      <h3 style={{ marginBottom: '5%' }}>Letter Report</h3>
      <h3 className="section">SECTION 5</h3>
      <span>
        <b>PHOTOGRAPHS</b>
      </span>

      <p>
        The following product photographs are provided to assist you in
        identifying the non-conformities identified above.
      </p>

      {item?.is_photo === true && (
        <LetterPhotoSection
          item={item}
          editMode={editMode}
          onChange={forceUpdate}
        />
      )}

      <h3 className="section">SECTION 6</h3>
      <span>
        <b>PROJECT STATUS & ACTION</b>
      </span>

      <p>
        Issuance of this letter report completes the evaluation (Stage 1) or/and
        testing (Stage 2) portion covered by Intertek Project No.
        <LetterSmartField
          json={json}
          name="«ProjectNumber»"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        .
      </p>

      <p>
        In responding, please provide a written record of your proposed
        resolutions numbered in accordance with the items outlined in this
        letter report. Responding in this way assures that all responses are
        properly identified.{' '}
      </p>

      <p>
        Once Intertek has received your response to all items outlined in this
        letter report, a Project Change Order (PCOR) may be issued to cover the
        scope of work necessary to review these responses
        <LetterSmartField
          json={json}
          name="<and conduct repeat testing, if required>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        (follow-up evaluation).
      </p>

      <p>
        Please note, to facilitate the follow-up project for your product(s), a
        modified sample{' '}
        <LetterSmartField
          json={json}
          name="<will/will not>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        be required to be submitted to Intertek.
      </p>

      <h3>IMPORTANT – CLIENT DECISION:</h3>
      <p>
        When you are ready to do so, please confirm your decision by completing
        the option table on{' '}
        <LetterSmartField
          json={json}
          name="<page no.>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        with your preferred option and returning it to{' '}
        <LetterSmartField
          json={json}
          name="Theresa Reinhardt via theresa.reinhardt@intertek.com"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        , along with your proposed resolutions and ready date for re-submission.
      </p>

      <p>
        If there are any questions regarding the results contained in this
        report, or any of the other services offered by Intertek, please do not
        hesitate to contact your dedicated Intertek Project Manager.
      </p>

      <SignatureBlock
        json={json}
        editMode={editMode}
        forceUpdate={forceUpdate}
        handleApprove
        openComment
        onBookmarkClick
      />
    </div>
  );
};

export default LetterPage5;
