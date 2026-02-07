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
      const prediction = await predictVideo(file, 5);
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
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Upload Video</h2>
        <p className="text-gray-600 mb-6">
          Upload a video file of a sign language gesture to get predictions.
        </p>

        {/* File Input */}
        <div className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              file
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-300 hover:border-primary-400'
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
              <span className="text-lg font-medium text-gray-700">
                {file ? file.name : 'Click to upload video'}
              </span>
              <span className="text-sm text-gray-500 mt-1">
                MP4, AVI, MOV (max 100MB)
              </span>
            </label>
          </div>

          {/* Video Preview */}
          {preview && (
            <div className="relative">
              <video
                src={preview}
                controls
                className="w-full max-h-96 rounded-lg bg-black"
              />
              <button
                onClick={handleClear}
                className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handlePredict}
              disabled={!file || loading}
              className="btn-primary flex-1"
            >
              {loading ? 'Processing...' : 'Predict Sign'}
            </button>
            {file && !loading && (
              <button onClick={handleClear} className="btn-secondary">
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Error: {error}</p>
          </div>
        )}
      </div>

      {/* Results */}
      <PredictionResults result={result} loading={loading} />
    </div>
  );
};

export default VideoUpload;
