import React from 'react';
const normalizeConfidence = (value) => {
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return num <= 1 ? Math.round(num * 100) : Math.round(num);
};

const getConfidenceColor = (confidence, isUserEdited) => {
  if (isUserEdited) return 'grey';

  const c = normalizeConfidence(confidence);
  if (c === null) return null;

  if (c >= 75) return 'green';
  if (c >= 50) return 'orange';
  return 'red';
};

export const renderConfidenceColor = (confidenceScore, isUserEdited) => {
  if (confidenceScore === null || confidenceScore === undefined) return null;

  const color = getConfidenceColor(confidenceScore, isUserEdited);

  return (
    <div>
      <span className={`confidence-dot ${color}`} />
    </div>
  );
};
