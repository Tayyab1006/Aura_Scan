import React, { useEffect, useRef, useState } from 'react';

const CameraView = ({ onFrame, isActive }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isActive) return;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
         video: {
    width: { ideal: 320 },
    height: { ideal: 240 },
    facingMode: "user",
    frameRate: { ideal: 30, max: 30 }
}
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } catch (err) {
        setError("Camera access denied or not found");
      }
    }

    setupCamera();

    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      }
    };
  }, [isActive]);

  useEffect(() => {
    if (!isActive) return;

    let animationFrameId;
    const capture = async () => {
      if (videoRef.current && canvasRef.current) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');

        if (video.videoWidth === 0 || video.videoHeight === 0) {
          animationFrameId = requestAnimationFrame(capture);
          return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        onFrame(dataUrl);
      }
      animationFrameId = setTimeout(capture, 33);
    };

    capture();
    return () => clearTimeout(animationFrameId);
  }, [isActive, onFrame]);

  return (
    <div className="group relative h-full w-full overflow-hidden rounded-lg border border-white/10 bg-void-800">
      {error && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/80 text-aura-red p-4 text-center">
          {error}
        </div>
      )}

      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover transition-opacity duration-500 ${isActive ? 'opacity-100' : 'opacity-30'}`}
      />

      <canvas ref={canvasRef} className="hidden" />

      <div className="absolute top-4 left-4 flex gap-2 items-center">
        <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-red-500 animate-pulse' : 'bg-void-600'}`}></div>
        <span className="text-xs text-void-400 font-mono uppercase tracking-tighter">
          {isActive ? 'Global Scan Active' : 'Command Standby'}
        </span>
      </div>

      {!isActive && (
        <div className="absolute inset-0 flex items-center justify-center bg-void-900/40 backdrop-blur-sm">
          <p className="text-sm font-semibold uppercase tracking-widest text-void-400">Start enterprise scan</p>
        </div>
      )}
    </div>
  );
};

export default CameraView;
