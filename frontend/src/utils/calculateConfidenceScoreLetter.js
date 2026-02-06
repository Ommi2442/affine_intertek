export const calculateConfidenceScoreLetter = (data) => {
  if (!data) return null;

  const blocks = data.Tables || data.Sheets;
  if (!Array.isArray(blocks)) return null;

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
      (item.accuracy_level === undefined || item.accuracy_level === true) &&
      normalizeConfidence(item.confidence) !== null
  );

  const userEditedFields = allEntries.filter(
    (item) => item?.is_user_edited === true
  );

  let totalAiFields = aiFields.length;
  if (totalAiFields === 0) return null;

  let high = 0;
  let medium = 0;
  let low = 0;
  let sumConfidence = 0;
  let aiConfidenceCount = 0;

  aiFields.forEach((field) => {
    if (field.is_user_edited === true) {
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

  let dataframeHigh = 0;
  let dataframeUserEdited = 0;

  allEntries.forEach((item) => {
    if (item?.dataframe_table === true && Array.isArray(item.value)) {
      item.value.forEach((row) => {
        if (row?.is_user_edited === true) {
          dataframeUserEdited++;
        } else {
          dataframeHigh++;
        }
      });
    }
  });

  if (dataframeHigh > 0) {
    high += dataframeHigh;
    sumConfidence += dataframeHigh * 100;
    aiConfidenceCount += dataframeHigh;
    totalAiFields += dataframeHigh;
  } else {
    totalAiFields = high + userEditedFields.length + dataframeUserEdited;
  }

  const avgConfidence =
    aiConfidenceCount > 0 ? Math.round(sumConfidence / aiConfidenceCount) : 0;

  const overallLabel =
    avgConfidence < 50 ? 'Low' : avgConfidence < 75 ? 'Medium' : 'High';

  return {
    totalAiFields,
    high,
    medium,
    low,
    avgConfidence,
    overallLabel,
    userEditedCount: userEditedFields.length + dataframeUserEdited,
  };
};
