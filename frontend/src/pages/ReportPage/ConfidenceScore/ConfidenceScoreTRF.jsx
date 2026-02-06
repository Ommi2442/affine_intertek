import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ConfidenceScoreCard from './ConfidenceScoreCard';
import { calculateConfidenceScoreTRF } from '../../../utils/calculateConfidenceScoreTRF';
import { setConfidenceScore } from '../../../redux/features/confidence/confidenceSlice';

const ConfidenceScoreTRF = ({ data, confidenceTick }) => {
  const dispatch = useDispatch();
  const summary = useSelector((state) => state.confidence.summary);

  useEffect(() => {
    if (!data) return;

    const result = calculateConfidenceScoreTRF(data, 'TRF');
    if (result) dispatch(setConfidenceScore(result));
  }, [data, confidenceTick, dispatch]);

  return <ConfidenceScoreCard summary={summary} />;
};

export default ConfidenceScoreTRF;
