import React, { useState, useRef } from 'react';
import { Upload, Video, X } from 'lucide-react';
import { predictVideo } from '../services/api';
import PredictionResults from './PredictionResults';

const VideoUpload = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [model, setModel] = useState(() => localStorage.getItem('arsl_selected_model') || 'karsl');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResult(null);
      setError(null);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePredict = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const prediction = await predictVideo(file, 5, model);
      setResult(prediction);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 tracking-tight mb-2">Upload Video</h2>
        <p className="text-gray-500 mb-6">
          Upload a video file of a sign language gesture to get predictions.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-2">
              Model
            </label>
            <select
              value={model}
              onChange={(e) => {
                setModel(e.target.value);
                localStorage.setItem('arsl_selected_model', e.target.value);
                setResult(null);
                setError(null);
              }}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            >
              <option value="karsl">KArSL baseline classifier</option>
              <option value="arabsign">ArabSign pose translator</option>
            </select>
          </div>

          <div
            className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 ${
              file
                ? 'border-primary-400 bg-primary-50/50'
                : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              className="hidden"
              id="video-upload"
            />
            <label
              htmlFor="video-upload"
              className="cursor-pointer flex flex-col items-center"
            >
              {file ? (
                <Video className="w-12 h-12 text-primary-500 mb-2" />
              ) : (
                <Upload className="w-12 h-12 text-gray-400 mb-2" />
              )}
              <span className="text-base font-medium text-gray-700">
                {file ? file.name : 'Click to upload video'}
              </span>
              <span className="text-sm text-gray-500 mt-1">
                MP4, AVI, MOV (max 100MB)
              </span>
            </label>
          </div>

          {preview && (
            <div className="relative rounded-2xl overflow-hidden bg-black/5">
              <video
                src={preview}
                controls
                className="w-full max-h-96 rounded-2xl"
              />
              <button
                onClick={handleClear}
                className="absolute top-2 right-2 p-2 bg-red-500/90 text-white rounded-xl hover:bg-red-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handlePredict}
              disabled={!file || loading}
              className="btn-primary flex-1 rounded-xl"
            >
              {loading ? 'Processing...' : 'Predict Sign'}
            </button>
            {file && !loading && (
              <button onClick={handleClear} className="btn-secondary rounded-xl">
                Clear
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 px-4 py-3 rounded-xl bg-red-50 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      <PredictionResults result={result} loading={loading} />
    </div>
  );
};

export default VideoUpload;
