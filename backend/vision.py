import cv2
import numpy as np
from typing import Tuple, List, Optional, Union

class FaceAnalyzer:
    """
    The Eye of the Abyss: Handles facial detection and ROI extraction.
    Uses MediaPipe Face Mesh when available, otherwise falls back to OpenCV Haar cascades.
    """
    def __init__(self, static_image_mode=False, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.face_mesh = None
        self.face_cascade = None
        self.use_mediapipe = False

        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=static_image_mode,
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self.use_mediapipe = True
        except Exception:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                self.face_cascade = None

        self.FOREHEAD_INDEX = 10
        self.LEFT_CHEEK_INDEX = 234
        self.RIGHT_CHEEK_INDEX = 454
        self.previous_center = None

    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Union[List, dict]], np.ndarray]:
        """
        Detects the face and returns either landmarks or a bounding box.
        """
        if self.use_mediapipe and self.face_mesh is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            landmarks = None
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
            return landmarks, frame

        if self.face_cascade is None:
            return None, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None, frame

        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]
        return {"bbox": (x, y, w, h)}, frame

    def get_roi_mask(self, frame: np.ndarray, landmarks: Union[List, dict]) -> np.ndarray:
        """
        Creates a mask for the forehead and cheek ROI based on available detection data.
        """
        h, w, _ = frame.shape
        mask = np.zeros((h, w), dtype=np.uint8)

        if landmarks is None:
            return mask

        if isinstance(landmarks, dict) and "bbox" in landmarks:
            x, y, width, height = landmarks["bbox"]
            forehead_y = max(0, y + int(height * 0.05))
            forehead_h = max(1, int(height * 0.25))
            forehead_w = max(1, int(width * 0.7))
            forehead_x = max(0, x + int((width - forehead_w) / 2))
            cv2.rectangle(mask, (forehead_x, forehead_y), (forehead_x + forehead_w, forehead_y + forehead_h), 255, -1)
            cheeks_y = y + int(height * 0.25)
            cheeks_h = max(1, int(height * 0.25))
            cheek_w = max(1, int(width * 0.25))
            left_cheek_x = x + int(width * 0.1)
            right_cheek_x = x + width - cheek_w - int(width * 0.1)
            cv2.rectangle(mask, (left_cheek_x, cheeks_y), (left_cheek_x + cheek_w, cheeks_y + cheeks_h), 255, -1)
            cv2.rectangle(mask, (right_cheek_x, cheeks_y), (right_cheek_x + cheek_w, cheeks_y + cheeks_h), 255, -1)
            return mask

        forehead_indices = [10, 67, 109, 107, 336, 296, 334, 293]
        left_cheek_indices = [234, 93, 132, 58, 172, 136, 150]
        right_cheek_indices = [454, 323, 361, 287, 373, 365, 379]

        def get_hull_mask(indices):
            pts = []
            for idx in indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    pts.append([int(pt.x * w), int(pt.y * h)])
            if not pts:
                return None
            return cv2.convexHull(np.array(pts, dtype=np.int32))

        f_hull = get_hull_mask(forehead_indices)
        if f_hull is not None:
            cv2.fillConvexPoly(mask, f_hull, 255)

        lc_hull = get_hull_mask(left_cheek_indices)
        if lc_hull is not None:
            cv2.fillConvexPoly(mask, lc_hull, 255)

        rc_hull = get_hull_mask(right_cheek_indices)
        if rc_hull is not None:
            cv2.fillConvexPoly(mask, rc_hull, 255)

        return mask

    def extract_green_mean(self, frame: np.ndarray, landmarks: Union[List, dict]) -> float:
        """
        Extracts a normalized green-channel pulse signal from the detected ROI.
        Uses red/blue normalization to reduce lighting variation and improve accuracy.
        """
        if landmarks is None:
            return 0.0

        mask = self.get_roi_mask(frame, landmarks)
        if mask is None or mask.sum() == 0:
            return 0.0

        red = frame[:, :, 2].astype(np.float32)
        green = frame[:, :, 1].astype(np.float32)
        blue = frame[:, :, 0].astype(np.float32)

        roi = mask > 0
        red_mean = float(np.mean(red[roi]))
        green_mean = float(np.mean(green[roi]))
        blue_mean = float(np.mean(blue[roi]))

        intensity = red_mean + green_mean + blue_mean + 1e-8
        normalized = (2.0 * green_mean - red_mean - blue_mean) / intensity
        return float(normalized)

    def extract_signal_sample(self, frame: np.ndarray, landmarks: Union[List, dict]) -> Tuple[float, float, dict]:
        """
        Extracts an rPPG sample plus a reliability score used by the DSP layer.
        Reliability is intentionally conservative for real-world scans.
        """
        sample = self.extract_green_mean(frame, landmarks)
        mask = self.get_roi_mask(frame, landmarks)
        if mask is None or mask.sum() == 0:
            return sample, 0.0, {"reason": "empty_roi"}

        roi = mask > 0
        roi_area_ratio = float(np.count_nonzero(roi) / (frame.shape[0] * frame.shape[1]))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray[roi]))
        contrast = float(np.std(gray[roi]))
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        ys, xs = np.where(roi)
        center = np.array([float(np.mean(xs)), float(np.mean(ys))])
        motion_penalty = 0.0
        if self.previous_center is not None:
            frame_diag = float(np.hypot(frame.shape[0], frame.shape[1]))
            movement = float(np.linalg.norm(center - self.previous_center) / max(frame_diag, 1.0))
            motion_penalty = min(0.35, movement * 8.0)
        self.previous_center = center

        area_score = min(1.0, roi_area_ratio / 0.08)
        exposure_score = 1.0 - min(1.0, abs(brightness - 120.0) / 120.0)
        contrast_score = min(1.0, contrast / 35.0)
        blur_score_norm = min(1.0, blur_score / 80.0)

        reliability = (
            0.30 * area_score
            + 0.25 * exposure_score
            + 0.20 * contrast_score
            + 0.25 * blur_score_norm
            - motion_penalty
        )
        reliability = float(min(1.0, max(0.0, reliability)))

        diagnostics = {
            "roi_area_ratio": round(roi_area_ratio, 4),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "blur": round(blur_score, 2),
            "reliability": round(reliability, 3),
        }
        return sample, reliability, diagnostics

    def close(self):
        if self.face_mesh is not None:
            self.face_mesh.close()
