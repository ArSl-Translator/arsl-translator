import React from 'react';
import { Trophy, TrendingUp } from 'lucide-react';

const PredictionResults = ({ result, loading = false }) => {
  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-200 border-t-primary-500"></div>
          <span className="ml-4 text-gray-600">Processing...</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  const { top_prediction, top_k_predictions } = result;

  return (
    <div className="space-y-4">
      {top_prediction && (
        <div className="card bg-gradient-to-br from-primary-50/80 to-white">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
              <Trophy className="w-5 h-5 text-primary-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-gray-500 mb-1">Top Prediction</h3>
              <p className="text-2xl font-bold text-gray-900 mb-2">{top_prediction.text}</p>
              <div className="flex items-center gap-4 flex-wrap">
                <span className="text-base font-semibold text-primary-600">
                  {(top_prediction.confidence * 100).toFixed(1)}% confident
                </span>
                <span className="text-sm text-gray-500">Label ID: {top_prediction.label_id}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {top_k_predictions && top_k_predictions.length > 1 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-gray-500" />
            <h3 className="text-lg font-semibold text-gray-800">Other Predictions</h3>
          </div>
          <div className="space-y-2">
            {top_k_predictions.slice(1).map((pred, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-xl bg-gray-50/80 hover:bg-gray-100/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-200 text-gray-700 text-sm font-bold">
                    {idx + 2}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{pred.text}</p>
                    <p className="text-xs text-gray-500">Label ID: {pred.label_id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-primary-600">
                    {(pred.confidence * 100).toFixed(1)}%
                  </p>
                  <div className="w-20 bg-gray-200 rounded-full h-1.5 mt-1">
                    <div
                      className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${pred.confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PredictionResults;
