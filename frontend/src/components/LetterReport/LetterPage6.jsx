import React from 'react';
import OptionTable from './LetterComponents/OptionTable';
import SimpleSignatureBlock from './LetterComponents/SimpleSignatureBlock';
import LetterHeader from './LetterComponents/LetterHeader';
import LetterSmartField from './LetterComponents/LetterSmartField';

const LetterPage6 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
  onConfidenceChange,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
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
      <h3>PLEASE RETURN THIS PAGE TO THE INTERTEK PROJECT MANAGER</h3>
      <p>
        <b>Project Manager Name:</b>{' '}
        <LetterSmartField
          json={json}
          name="Project Manager Name"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
          onConfidenceChange={onConfidenceChange}
        />
      </p>
      <p>
        Please advise which of the following options <b>you</b> wish us to
        pursue
      </p>
      <OptionTable json={json} />
      <br />
      <br />
      <br />
      <br />
      <SimpleSignatureBlock json={json} />
    </div>
  );
};

export default LetterPage6;
