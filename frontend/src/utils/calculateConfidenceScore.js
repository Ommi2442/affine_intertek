export const calculateConfidenceScore = (data) => {
  console.log('data', data);
  if (!data?.Tables) return null;

  // flatten all items from all tables
  const allItems = data.Tables.flatMap((table) => table.Items || []);
  console.log('allItem', allItems);

  // AI fillable fields with confidence
  const aiFields = allItems.filter(
    (item) =>
      item.ai_fillable === true &&
      item.accuracy_level === true &&
      typeof item.confidence === 'number'
  );

  const totalAiFields = aiFields.length;

  let high = 0;
  let medium = 0;
  let low = 0;
  let userEditedCount = 0;
  let sumConfidence = 0;

  aiFields.forEach((field) => {
    // 👇 user approved overrides AI confidence
    if (field.is_user_approved === true) {
      userEditedCount++;
      return;
    }
    const c = field.confidence;
    sumConfidence += c;

    if (c >= 75) high++;
    else if (c >= 50) medium++;
    else low++;
  });

  const avgConfidence = totalAiFields
    ? Math.round(sumConfidence / totalAiFields)
    : 0;

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
