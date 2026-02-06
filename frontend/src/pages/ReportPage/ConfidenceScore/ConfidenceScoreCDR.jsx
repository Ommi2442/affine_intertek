import React, { useEffect } from 'react';
import ConfidenceScoreCard from './ConfidenceScoreCard';
import { useDispatch, useSelector } from 'react-redux';
import { calculateConfidenceScoreCDR } from '../../../utils/calculateConfidenceScoreCDR';
import { setConfidenceScore } from '../../../redux/features/confidence/confidenceSlice';

export const ConfidenceScoreCDR = ({ data, confidenceTick }) => {
  const dispatch = useDispatch();
  const summary = useSelector((state) => state.confidence.summary);

  useEffect(() => {
    if (!data) return;

    const result = calculateConfidenceScoreCDR(data);

    if (result) {
      dispatch(setConfidenceScore(result));
    }
  }, [data, confidenceTick, dispatch]);

  return <ConfidenceScoreCard summary={summary} />;
};
