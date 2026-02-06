export const calculateConfidenceScoreCDR = (data) => {
  if (!data) return null;

  let blocks = [];

  if (Array.isArray(data)) {
    blocks = data;
  } else if (Array.isArray(data?.Sheets)) {
    blocks = data.Sheets;
  } else if (Array.isArray(data?.Tables)) {
    blocks = data.Tables;
  }

  if (!blocks.length) return null;

  const allEntries = blocks.flatMap((block) => [
    ...(block.Items || []),
    ...(block.Rows || []),
  ]);

  const normalizeConfidence = (value) => {
    const num = Number(value);
    if (Number.isNaN(num)) return null;
    return num <= 1 ? Math.round(num * 100) : Math.round(num);
  };

  const aiFields = allEntries.filter(
    (item) =>
      item?.ai_fillable === true &&
      (item.accuracy_level === undefined || item?.accuracy_level === true) &&
      normalizeConfidence(item.confidence) !== null
  );

  if (!aiFields.length) return null;

  const userEditedFields = aiFields.filter(
    (item) => item?.is_user_edited === true
  );

  let high = 0;
  let medium = 0;
  let low = 0;
  let sumConfidence = 0;
  let aiConfidenceCount = 0;

  aiFields.forEach((field) => {
    if (field?.is_user_edited === true) {
      sumConfidence += 100;
      aiConfidenceCount++;
      return;
    }

    const c = normalizeConfidence(field.confidence);
    if (c === null) return;

    sumConfidence += c;
    aiConfidenceCount++;

    if (c >= 75) high++;
    else if (c >= 50) medium++;
    else low++;
  });

  const avgConfidence =
    aiConfidenceCount > 0 ? Math.round(sumConfidence / aiConfidenceCount) : 0;

  const overallLabel =
    avgConfidence < 50 ? 'Low' : avgConfidence < 75 ? 'Medium' : 'High';

  return {
    totalAiFields: aiFields.length,
    high,
    medium,
    low,
    avgConfidence,
    overallLabel,
    userEditedCount: userEditedFields.length,
  };
};
