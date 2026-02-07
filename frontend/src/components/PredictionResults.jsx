import React from 'react';
import { Trophy, TrendingUp } from 'lucide-react';

const PredictionResults = ({ result, loading = false }) => {
  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          <span className="ml-4 text-lg text-gray-600">Processing...</span>
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
      {/* Top Prediction */}
      {top_prediction && (
        <div className="card bg-gradient-to-br from-primary-50 to-white border-2 border-primary-500">
          <div className="flex items-start gap-4">
            <Trophy className="w-8 h-8 text-primary-500 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-gray-500 mb-1">Top Prediction</h3>
              <p className="text-3xl font-bold text-gray-900 mb-2">{top_prediction.text}</p>
              <div className="flex items-center gap-4">
                <span className="text-lg font-semibold text-primary-600">
                  {(top_prediction.confidence * 100).toFixed(1)}% confident
                </span>
                <span className="text-sm text-gray-500">Label ID: {top_prediction.label_id}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top K Predictions */}
      {top_k_predictions && top_k_predictions.length > 1 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-gray-500" />
            <h3 className="text-lg font-semibold text-gray-800">Other Predictions</h3>
          </div>
          <div className="space-y-3">
            {top_k_predictions.slice(1).map((pred, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-6 h-6 bg-gray-200 text-gray-700 text-sm font-bold rounded">
                    {idx + 2}
                  </span>
                  <div>
                    <p className="font-semibold text-gray-900">{pred.text}</p>
                    <p className="text-xs text-gray-500">Label ID: {pred.label_id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-primary-600">
                    {(pred.confidence * 100).toFixed(1)}%
                  </p>
                  <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${pred.confidence * 100}%` }}
                    ></div>
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
