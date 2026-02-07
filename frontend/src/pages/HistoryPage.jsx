import React, { useState, useEffect, useCallback } from 'react';
import { Clock, Video, Camera, ChevronLeft, ChevronRight } from 'lucide-react';
import { getHistory } from '../services/api';

export default function HistoryPage() {
  const [history, setHistory] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const pageSize = 15;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHistory(page, pageSize);
      setHistory(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const totalPages = history ? Math.ceil(history.total / pageSize) : 0;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="card">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-primary-500 text-white p-2 rounded-lg">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Prediction History</h2>
            {history && (
              <p className="text-sm text-gray-500">{history.total} total predictions</p>
            )}
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && history?.items.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No predictions yet</p>
            <p className="text-sm mt-1">Your prediction history will appear here</p>
          </div>
        )}

        {!loading && !error && history?.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Date</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Top Prediction</th>
                    <th className="text-right py-3 px-2 font-medium text-gray-600">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {history.items.map((item) => (
                    <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-2 text-gray-700">
                        {new Date(item.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-2">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                          {item.prediction_type === 'video' ? (
                            <Video className="w-3 h-3" />
                          ) : (
                            <Camera className="w-3 h-3" />
                          )}
                          {item.prediction_type}
                        </span>
                      </td>
                      <td className="py-3 px-2 font-medium text-gray-900">
                        {item.top_prediction_text || item.top_prediction_label || '-'}
                      </td>
                      <td className="py-3 px-2 text-right">
                        {item.top_prediction_confidence != null ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700">
                            {(item.top_prediction_confidence * 100).toFixed(1)}%
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="btn-secondary flex items-center gap-1 !px-3 !py-2 text-sm"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="btn-secondary flex items-center gap-1 !px-3 !py-2 text-sm"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
