import React from 'react';
import './SimpleSignatureBlock.css';

const SimpleSignatureBlock = () => {
  return (
    <div className="simple-signature">
      <div className="simple-row">
        <div className="simple-label">Completed by:</div>
      </div>

      <div className="simple-row">
        <div className="simple-label">Title:</div>
      </div>

      <div className="simple-row">
        <div className="simple-label">Signature:</div>
      </div>

      <div className="simple-row">
        <div className="simple-label">Date</div>
      </div>
    </div>
  );
};

export default SimpleSignatureBlock;
