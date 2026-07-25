import asyncio
import threading
import cv2
import numpy as np
import base64
import time
import os
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.vision import FaceAnalyzer
    from backend.signal_processing import SignalProcessor
    from backend.websocket import manager
except ModuleNotFoundError:
    from vision import FaceAnalyzer
    from signal_processing import SignalProcessor
    from websocket import manager

from queue import Queue

CLINICAL_USE_ENABLED = os.getenv("CLINICAL_USE_ENABLED", "false").lower() == "true"
SAFETY_NOTICE = (
    "Prototype telemetry only. Not for emergency, life-support, diagnosis, "
    "triage, treatment, or patient monitoring unless cleared through the "
    "applicable clinical validation and regulatory pathway."
)

app = FastAPI(title="AURA Global API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://aura-scan-seven.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
state = {
    "streaming_active": False,
    "scan_active": False,
    "scan_duration": 60,
    "scan_progress": 0,
    "scan_end_time": None,
    "scan_time_left": 0,
    "current_bpm": 0.0,
    "current_rr": 0.0,
    "signal_quality": 0,
    "sample_reliability": 0,
    "samples_collected": 0,
    "scan_result": None,
    "clinical_use_enabled": CLINICAL_USE_ENABLED,
    "safety_notice": SAFETY_NOTICE,
}

@app.get("/vitals")
async def get_vitals():
    return state

# Frame queue for the processing thread
frame_queue = Queue(maxsize=30)
frame_timestamps = deque(maxlen=120)

# Initialize AI Core
analyzer = FaceAnalyzer()
processor = SignalProcessor(fps=120.0, buffer_size=7200)


def collected_duration_seconds() -> float:
    valid_times = [t for t in processor.sample_times if t is not None]
    if len(valid_times) >= 2:
        return max(0.0, valid_times[-1] - valid_times[0])
    return len(processor.signal_buffer) / max(processor.fps, 1.0)


def update_fps_from_timestamp(timestamp_ms: float):
    frame_timestamps.append(timestamp_ms / 1000.0)
    if len(frame_timestamps) < 5:
        return

    times = list(frame_timestamps)
    intervals = [t2 - t1 for t1, t2 in zip(times, times[1:]) if 0.005 < (t2 - t1) < 0.5]
    if not intervals:
        return

    avg_interval = sum(intervals) / len(intervals)
    estimated_fps = 1.0 / avg_interval
    processor.fps = min(120.0, max(15.0, estimated_fps))

scan_lock = threading.Lock()

def finalize_scan(main_loop, early=False):
    global processor

    if not state["scan_active"]:
        return

    state["scan_active"] = False
    state["streaming_active"] = False
    state["scan_end_time"] = None
    state["scan_time_left"] = 0
    state["scan_progress"] = 100
    frame_timestamps.clear()

    bpm, rr, filtered_sig, quality = processor.process()
    collected_seconds = collected_duration_seconds()
    average_reliability = (
        sum(processor.sample_reliability) / len(processor.sample_reliability)
        if processor.sample_reliability
        else 0.0
    )
    min_required_seconds = 45.0 if not early else 30.0
    production_quality_gate = 70
    production_reliability_gate = 0.55

    if (
        collected_seconds < min_required_seconds
        or bpm == 0.0
        or rr == 0.0
        or quality < production_quality_gate
        or average_reliability < production_reliability_gate
    ):
        message = "Measurement rejected by production quality gates."
        if collected_seconds < min_required_seconds:
            message = f"Only {int(collected_seconds)} seconds of usable signal collected. Run a full stable scan."
        elif average_reliability < production_reliability_gate:
            message = "Face, lighting, or motion stability was too low for real-world use."
        elif quality < production_quality_gate:
            message = "Signal quality did not meet the production readiness threshold. Improve lighting and keep still."
        state["scan_result"] = {
            "type": "scan_result",
            "success": False,
            "accepted": False,
            "clinical_use_enabled": CLINICAL_USE_ENABLED,
            "safety_notice": SAFETY_NOTICE,
            "message": message,
            "bpm": float(round(bpm, 2)) if bpm else 0.0,
            "rr": float(round(rr, 2)) if rr else 0.0,
            "quality": quality,
            "sample_reliability": int(round(average_reliability * 100)),
            "collected_seconds": int(round(collected_seconds)),
        }
    else:
        state["current_bpm"] = bpm
        state["current_rr"] = rr
        state["signal_quality"] = quality
        state["sample_reliability"] = int(round(average_reliability * 100))
        result_message = "Research-quality scan accepted. Do not use for clinical decisions."
        if CLINICAL_USE_ENABLED:
            result_message = "Scan accepted within the configured validated clinical-use mode."
        state["scan_result"] = {
            "type": "scan_result",
            "success": CLINICAL_USE_ENABLED,
            "accepted": True,
            "clinical_use_enabled": CLINICAL_USE_ENABLED,
            "safety_notice": SAFETY_NOTICE,
            "message": result_message,
            "bpm": float(round(bpm, 2)),
            "rr": float(round(rr, 2)),
            "quality": quality,
            "sample_reliability": int(round(average_reliability * 100)),
            "collected_seconds": int(round(collected_seconds)),
        }

    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(state["scan_result"]), main_loop)
    except Exception:
        pass

    processor = SignalProcessor(fps=120.0, buffer_size=7200)
    analyzer.previous_center = None


def processing_loop(main_loop):
    """
    The Eternal Loop: Consumes frames from the queue and processes them.
    Using the main event loop to broadcast results.
    """
    global state

    while True:
        if not state["streaming_active"]:
            while not frame_queue.empty():
                try: frame_queue.get_nowait()
                except: pass
            time.sleep(1)
            continue

        if state["scan_active"] and state["scan_end_time"]:
            state["scan_time_left"] = max(0, int(state["scan_end_time"] - time.time()))
            if state["scan_duration"] > 0:
                elapsed = state["scan_duration"] - state["scan_time_left"]
                state["scan_progress"] = min(100, max(0, int((elapsed / state["scan_duration"]) * 100)))
            if time.time() >= state["scan_end_time"]:
                finalize_scan(main_loop)
                continue

        try:
            frame = frame_queue.get(timeout=1.0)
        except:
            if state["scan_active"] and state["scan_end_time"] and time.time() >= state["scan_end_time"]:
                finalize_scan(main_loop)
            continue

        landmarks, _ = analyzer.process_frame(frame)

        if landmarks:
            green_mean, reliability, diagnostics = analyzer.extract_signal_sample(frame, landmarks)
            processor.add_sample(green_mean, timestamp=time.time(), reliability=reliability)
            bpm, rr, filtered_sig, quality = processor.process()
            state["current_bpm"] = bpm
            state["current_rr"] = rr
            state["signal_quality"] = quality
            state["sample_reliability"] = int(round(reliability * 100))
            state["samples_collected"] = len(processor.signal_buffer)

            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "vitals",
                    "bpm": bpm,
                    "rr": rr,
                    "signal": filtered_sig.tolist() if len(filtered_sig) > 0 else [],
                    "quality": quality,
                    "sample_reliability": state["sample_reliability"],
                    "samples_collected": state["samples_collected"],
                    "diagnostics": diagnostics,
                    "clinical_use_enabled": CLINICAL_USE_ENABLED,
                    "safety_notice": SAFETY_NOTICE,
                    "scan_active": state["scan_active"],
                    "scan_time_left": state["scan_time_left"],
                    "scan_progress": state["scan_progress"],
                }),
                main_loop
            )
        else:
            state["signal_quality"] = 0
            state["sample_reliability"] = 0
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "error",
                    "message": "No face detected",
                    "quality": 0,
                    "clinical_use_enabled": CLINICAL_USE_ENABLED,
                    "safety_notice": SAFETY_NOTICE,
                }),
                main_loop
            )

@app.on_event("startup")
async def startup_event():
    # Capture the event loop of the main thread
    main_loop = asyncio.get_running_loop()
    thread = threading.Thread(target=processing_loop, args=(main_loop,), daemon=True)
    thread.start()

@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "1.0.0",
        "clinical_use_enabled": CLINICAL_USE_ENABLED,
        "safety_notice": SAFETY_NOTICE,
    }

@app.post("/start-stream")
async def start_stream():
    now = time.time()
    state["streaming_active"] = True
    state["scan_active"] = True
    state["scan_progress"] = 0
    state["scan_end_time"] = now + state["scan_duration"]
    state["scan_time_left"] = state["scan_duration"]
    state["current_bpm"] = 0.0
    state["current_rr"] = 0.0
    state["signal_quality"] = 0
    state["sample_reliability"] = 0
    state["samples_collected"] = 0
    state["scan_result"] = None
    frame_timestamps.clear()
    global processor
    processor = SignalProcessor(fps=120.0, buffer_size=7200)
    analyzer.previous_center = None
    return {
        "message": "Scan initiated",
        "duration": state["scan_duration"],
        "clinical_use_enabled": CLINICAL_USE_ENABLED,
        "safety_notice": SAFETY_NOTICE,
    }

@app.post("/stop-stream")
async def stop_stream():
    if state["scan_active"]:
        finalize_scan(asyncio.get_running_loop(), early=True)
        return {"message": "Scan stopped and finalized early"}

    state["streaming_active"] = False
    return {"message": "Stream terminated"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "frame" and state["streaming_active"]:
                timestamp_ms = data.get("timestamp")
                if isinstance(timestamp_ms, (int, float)):
                    update_fps_from_timestamp(float(timestamp_ms))

                img_data = base64.b64decode(data["image"].split(',')[1])
                nparr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    if frame_queue.full():
                        try: frame_queue.get_nowait()
                        except: pass
                    frame_queue.put(frame)
                if state["scan_active"] and state["scan_end_time"] and time.time() >= state["scan_end_time"]:
                    finalize_scan(asyncio.get_running_loop(), early=False)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
