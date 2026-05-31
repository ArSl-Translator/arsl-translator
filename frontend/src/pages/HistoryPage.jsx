import React, { useCallback, useEffect, useState } from 'react';
import { Camera, ChevronLeft, ChevronRight, Clock, Search, Video } from 'lucide-react';
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
      setHistory(await getHistory(page, pageSize));
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
    <div className="mx-auto max-w-7xl">
      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="section-title">Audit trail</p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-950">Prediction history</h2>
                {history && <p className="mt-1 text-sm text-gray-500">{history.total} saved predictions</p>}
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-500">
              <Search className="h-4 w-4" />
              Stored locally through the API database
            </div>
          </div>
        </div>

        <div className="p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-gray-950"></div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && history?.items.length === 0 && (
            <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 py-14 text-center text-gray-500">
              <Clock className="mx-auto mb-3 h-12 w-12 opacity-30" />
              <p className="font-semibold text-gray-700">No predictions yet</p>
              <p className="mt-1 text-sm">Your prediction history will appear here.</p>
            </div>
          )}

          {!loading && !error && history?.items.length > 0 && (
            <>
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full min-w-[720px] text-sm">
                  <thead className="bg-gray-50">
                    <tr className="border-b border-gray-200">
                      <th className="px-4 py-3.5 text-left font-semibold text-gray-600">Date</th>
                      <th className="px-4 py-3.5 text-left font-semibold text-gray-600">Source</th>
                      <th className="px-4 py-3.5 text-left font-semibold text-gray-600">Top prediction</th>
                      <th className="px-4 py-3.5 text-right font-semibold text-gray-600">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {history.items.map((item) => {
                      const isVideo = item.prediction_type?.startsWith('video');
                      return (
                        <tr key={item.id} className="transition-colors hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-700">
                            {new Date(item.created_at).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center gap-1 rounded-lg bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
                              {isVideo ? <Video className="h-3 w-3" /> : <Camera className="h-3 w-3" />}
                              {item.prediction_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-gray-950">
                            {item.top_prediction_text || item.top_prediction_label || '-'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {item.top_prediction_confidence != null ? (
                              <span className="inline-flex rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
                                {(item.top_prediction_confidence * 100).toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {totalPages > 1 && (
                <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4">
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary">
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </button>
                  <span className="text-sm font-medium text-gray-500">
                    Page {page} of {totalPages}
                  </span>
                  <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="btn-secondary">
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
