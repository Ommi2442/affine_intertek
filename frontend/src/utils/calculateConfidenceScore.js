export const calculateConfidenceScore = (data) => {
  if (!data) return null;

  // 🔹 support TRF (Tables) and CDR (Sheets)
  const blocks = data.Tables || data.Sheets;
  if (!Array.isArray(blocks)) return null;

  // 🔹 collect all possible entries
  const allEntries = blocks.flatMap((block) => [
    ...(block.Items || []),
    ...(block.Rows || []), // CDR support
  ]);

  // 🔹 normalize confidence (TRF: 1–100, CDR: 0–1)
  const normalizeConfidence = (value) => {
    const num = Number(value);
    if (Number.isNaN(num)) return null;
    return num <= 1 ? Math.round(num * 100) : Math.round(num);
  };

  // 🔹 filter valid AI confidence fields
  const aiFields = allEntries.filter(
    (item) =>
      item?.ai_fillable === true &&
      item?.accuracy_level === true &&
      item?.confidence !== undefined &&
      normalizeConfidence(item.confidence) !== null
  );

  const totalAiFields = aiFields.length;
  if (totalAiFields === 0) return null;

  let high = 0;
  let medium = 0;
  let low = 0;
  let userEditedCount = 0;
  let sumConfidence = 0;

  aiFields.forEach((field) => {
    // 👇 user-approved fields override AI
    if (field.is_user_approved === true) {
      userEditedCount++;
      return;
    }

    const c = normalizeConfidence(field.confidence);
    if (c === null) return;

    sumConfidence += c;

    if (c >= 75) high++;
    else if (c >= 50) medium++;
    else low++;
  });

  const avgConfidence = Math.round(sumConfidence / totalAiFields);

  const overallLabel =
    avgConfidence < 50 ? 'Low' : avgConfidence < 75 ? 'Medium' : 'High';

  return {
    totalAiFields,
    high,
    medium,
    low,
    avgConfidence,
    overallLabel,
    userEditedCount,
  };
};
