import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import { calculateConfidenceScoreLetter } from '../../../utils/calculateConfidenceScoreLetter';
import { setConfidenceScore } from '../../../redux/features/confidence/confidenceSlice';
import ConfidenceScoreCard from './ConfidenceScoreCard';

const ConfidenceScoreLetter = ({ data, confidenceTick }) => {
  const dispatch = useDispatch();
  const summary = useSelector((state) => state.confidence.summary);

  useEffect(() => {
    if (!data?.pages) return;

    const normalizedData = {
      Tables: data.pages.map((p) => ({
        Items: p.items || [],
      })),
    };

    const result = calculateConfidenceScoreLetter(normalizedData, 'LETTER');
    if (result) dispatch(setConfidenceScore(result));
  }, [data, confidenceTick, dispatch]);

  return <ConfidenceScoreCard summary={summary} />;
};

export default ConfidenceScoreLetter;
