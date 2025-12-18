import React from 'react';

const getConfidenceColor = (confidence) => {
  if (confidence >= 75) return 'green';
  if (confidence >= 50) return 'orange';
  if (confidence < 50) return 'red';
  return 'grey';
};

export const renderConfidenceColor = (confidenceScore) => {
  console.log('conf', typeof confidenceScore);
  if (typeof confidenceScore !== 'number') return null;
  const color = getConfidenceColor(confidenceScore);

  return (
    <div>
      <span className={`confidence-dot ${color}`} />
    </div>
  );
};
