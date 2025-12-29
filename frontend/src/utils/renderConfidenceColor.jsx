import React from 'react';

const getConfidenceColor = (confidence) => {
  if (confidence >= 75 || confidence >= 0.75) return 'green';
  if (confidence >= 50 || confidence >= 0.5) return 'orange';
  if (confidence < 50 || confidence < 0.5) return 'red';
  return 'grey';
};

export const renderConfidenceColor = (confidenceScore) => {
  const upd_confidenceScore = Number(confidenceScore);
  if (confidenceScore === null || confidenceScore === undefined) return null;
  const color = getConfidenceColor(upd_confidenceScore);

  return (
    <div>
      <span className={`confidence-dot ${color}`} />
    </div>
  );
};
