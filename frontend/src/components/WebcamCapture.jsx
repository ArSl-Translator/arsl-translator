import React, { useState, useRef, useEffect } from 'react';
import { Camera, Circle, Square, Play } from 'lucide-react';
import { predictFrames } from '../services/api';
import PredictionResults from './PredictionResults';

const WebcamCapture = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [frameBuffer, setFrameBuffer] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [webcamError, setWebcamError] = useState(null);
  const [isVideoReady, setIsVideoReady] = useState(false);

  const [bufferSize, setBufferSize] = useState(60);
  const captureIntervalRef = useRef(null);

  const startWebcam = async () => {
    try {
      setWebcamError(null);
      setError(null);
      setIsVideoReady(false);

      // Stop previous stream if any (avoids “busy device” edge cases)
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });

      setStream(mediaStream);
    } catch (err) {
      setWebcamError(`Failed to access webcam: ${err.message}`);
      console.error('Webcam error:', err);
    }
  };

  const stopWebcam = () => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    setIsRecording(false);
    setFrameBuffer([]);
    setIsVideoReady(false);

    if (videoRef.current) {
      videoRef.current.pause?.();
      videoRef.current.srcObject = null;
    }

    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  };

  // ✅ Key fix: when stream changes AND video element exists, attach srcObject
  useEffect(() => {
    const videoEl = videoRef.current;
    if (!stream || !videoEl) return;

    setIsVideoReady(false);
    videoEl.srcObject = stream;

    const onReady = () => {
      // Sometimes loadedmetadata fires but videoWidth is still 0,
      // so we also rely on canplay/playing.
      setIsVideoReady(true);
    };

    const onLoadedMetadata = () => {
      videoEl.play().catch(() => {
        // If autoplay is blocked for some reason, user can click Start Recording later
      });
    };

    videoEl.addEventListener('loadedmetadata', onLoadedMetadata);
    videoEl.addEventListener('canplay', onReady);
    videoEl.addEventListener('playing', onReady);

    return () => {
      videoEl.removeEventListener('loadedmetadata', onLoadedMetadata);
      videoEl.removeEventListener('canplay', onReady);
      videoEl.removeEventListener('playing', onReady);
    };
  }, [stream]);

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return null;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (video.videoWidth === 0 || video.videoHeight === 0) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    return canvas.toDataURL('image/jpeg', 0.8);
  };

  const stopRecording = () => {
    setIsRecording(false);
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
  };

  const handlePredict = async (frames = frameBuffer) => {
    if (!frames.length) {
      setError('No frames captured');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const prediction = await predictFrames(frames, 5);
      setResult(prediction);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const startRecording = () => {
    if (!stream) {
      setError('Start the webcam first.');
      return;
    }
    if (!isVideoReady) {
      setError('Video is not ready yet. Please wait a second.');
      return;
    }

    setIsRecording(true);
    setFrameBuffer([]);
    setResult(null);
    setError(null);

    captureIntervalRef.current = setInterval(() => {
      const frame = captureFrame();
      if (!frame) return;

      setFrameBuffer((prev) => {
        const next = [...prev, frame];

        if (next.length >= bufferSize) {
          // stop and predict with the full buffer
          stopRecording();
          handlePredict(next);
        }

        return next;
      });
    }, 33);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => stopWebcam();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Webcam Capture</h2>
        <p className="text-gray-600 mb-6">
          Capture video from your webcam and get real-time sign language predictions.
        </p>

        <div className="relative bg-gray-900 rounded-lg overflow-hidden mb-4">
          {!stream ? (
            <div className="aspect-video flex items-center justify-center">
              <button onClick={startWebcam} className="btn-primary">
                <Camera className="w-5 h-5 inline mr-2" />
                Start Webcam
              </button>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full max-h-[500px] mx-auto"
                style={{ display: 'block' }}
              />

              {!isVideoReady && (
                <div className="absolute top-4 left-4 bg-yellow-500 text-white px-4 py-2 rounded-full font-semibold">
                  Loading video...
                </div>
              )}

              {isRecording && (
                <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500 text-white px-4 py-2 rounded-full font-semibold">
                  <Circle className="w-3 h-3 animate-pulse fill-current" />
                  Recording {frameBuffer.length}/{bufferSize}
                </div>
              )}

              <div className="absolute top-4 right-4 bg-black bg-opacity-70 text-white px-4 py-2 rounded-full font-semibold">
                {frameBuffer.length} frames
              </div>
            </>
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        {webcamError && (
          <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800 font-medium">{webcamError}</p>
          </div>
        )}

        {stream && (
          <div className="mb-4 p-4 bg-gray-50 rounded-lg">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Buffer Size: {bufferSize} frames (~{(bufferSize / 30).toFixed(1)}s)
            </label>
            <input
              type="range"
              min="30"
              max="120"
              step="10"
              value={bufferSize}
              onChange={(e) => setBufferSize(Number(e.target.value))}
              disabled={isRecording}
              className="w-full"
            />
          </div>
        )}

        {stream && (
          <div className="flex gap-3">
            {!isRecording ? (
              <>
                <button
                  onClick={startRecording}
                  disabled={!isVideoReady}
                  className="btn-primary flex-1"
                >
                  <Play className="w-5 h-5 inline mr-2" />
                  {isVideoReady ? 'Start Recording' : 'Loading...'}
                </button>
                <button onClick={stopWebcam} className="btn-secondary">
                  Stop Webcam
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => {
                    stopRecording();
                    handlePredict();
                  }}
                  className="btn-primary flex-1"
                >
                  <Square className="w-5 h-5 inline mr-2" />
                  Stop & Predict
                </button>
                <button onClick={stopRecording} className="btn-danger">
                  Cancel
                </button>
              </>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Error: {error}</p>
          </div>
        )}
      </div>

      <PredictionResults result={result} loading={loading} />
    </div>
  );
};

export default WebcamCapture;
