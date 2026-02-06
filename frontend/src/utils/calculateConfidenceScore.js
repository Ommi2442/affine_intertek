export const calculateConfidenceScore = (data, type) => {
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

  // AI fields only (pages 1–8)
  const aiFields = allEntries.filter(
    (item) =>
      item?.ai_fillable === true &&
      (item.accuracy_level === undefined || item.accuracy_level === true) &&
      normalizeConfidence(item.confidence) !== null
  );

  // Any user-edited field (all pages)
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

  if (type == 'TRF' || type == 'CDR') {
    //  AI scoring ONLY for non-edited AI fields
    aiFields.forEach((field) => {
      const isUserEdited =
        field?.ai_fillable === true &&
        field?.accuracy_level === true &&
        field.is_user_edited === true;

      if (isUserEdited) {
        //  remove from AI quality buckets
        sumConfidence += 100; // user override = trusted
        aiConfidenceCount++;
        return; // NO high/medium/low increment
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
      totalAiFields,
      high,
      medium,
      low,
      avgConfidence,
      overallLabel,
      userEditedCount: userEditedFields.length,
    };
  }

  /* ================================
      NEW: LETTER DATAFRAME TABLES
     ================================ */

  if (type === 'LETTER') {
    aiFields.forEach((field) => {
      const isUserEdited = field.is_user_edited === true;

      if (isUserEdited) {
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
  }

  // let dataframeHigh = 0;
  // let dataframeUserEdited = 0;

  // allEntries.forEach((item) => {
  //   if (item?.dataframe_table === true && Array.isArray(item.value)) {
  //     item.value.forEach((row) => {
  //       if (row?.is_user_edited === true) {
  //         dataframeUserEdited++;
  //       } else {
  //         dataframeHigh++;
  //       }
  //     });
  //   }
  // });
  // const dataframeHighCount = allEntries.reduce((count, item) => {
  //   if (
  //     item?.dataframe_table === true &&
  //     item?.confidence === 100 &&
  //     Array.isArray(item.value)
  //   ) {
  //     return count + item.value.length;
  //   }
  //   return count;
  // }, 0);

  // if (dataframeHigh > 0) {
  //   high += dataframeHigh;
  //   sumConfidence += dataframeHigh * 100;
  //   aiConfidenceCount += dataframeHigh;
  // }

  // const avgConfidence =
  //   aiConfidenceCount > 0 ? Math.round(sumConfidence / aiConfidenceCount) : 0;

  // const overallLabel =
  //   avgConfidence < 50 ? 'Low' : avgConfidence < 75 ? 'Medium' : 'High';

  // totalAiFields += dataframeHigh + dataframeUserEdited;

  // return {
  //   totalAiFields, // AI fields only
  //   high, // ONLY untouched AI fields
  //   medium,
  //   low,
  //   avgConfidence,
  //   overallLabel,
  //   userEditedCount: userEditedFields.length + dataframeUserEdited,
  //   // ALL edits
  // };
};
