import React from 'react';

const normalizeConfidence = (value) => {
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return num <= 1 ? Math.round(num * 100) : Math.round(num);
};

const getConfidenceColor = (
  confidence,
  isUserEdited,
  aiFillable,
  accuracyLevel
) => {
  if (accuracyLevel !== true) return null;
  if (isUserEdited === true) return 'grey';
  if (aiFillable !== true) return null;

  // Not an AI confidence field → no color
  if (aiFillable !== true || accuracyLevel !== true) return null;

  // User override → neutral
  if (isUserEdited === true && normalizeConfidence(confidence) < 75)
    return 'grey';

  const c = normalizeConfidence(confidence);
  if (c === null) return null;

  if (c >= 75) return 'green';
  if (c >= 50) return 'orange';
  return 'red';
};

export const renderConfidenceColor = (
  confidenceScore,
  isUserEdited,
  aiFillable,
  accuracyLevel
) => {
  const color = getConfidenceColor(
    confidenceScore,
    isUserEdited,
    aiFillable,
    accuracyLevel
  );

  if (!color) return null;

  return (
    <div>
      <span className={`confidence-dot ${color}`} />
    </div>
  );
};
