import cv2
import numpy as np
from typing import Tuple, List, Optional, Union


class FaceAnalyzer:
    """
    Face detection using MediaPipe.
    Falls back to OpenCV Haar Cascade if MediaPipe is unavailable.
    """

    def __init__(
        self,
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.3,
        min_tracking_confidence=0.3,
    ):

        self.face_mesh = None
        self.face_cascade = None
        self.use_mediapipe = False
        self.previous_center = None

        self.FOREHEAD_INDEX = 10
        self.LEFT_CHEEK_INDEX = 234
        self.RIGHT_CHEEK_INDEX = 454

        # --------------------------
        # Try MediaPipe
        # --------------------------
        try:
            import mediapipe as mp

            print("========== MEDIAPIPE LOADED ==========")

            self.mp_face_mesh = mp.solutions.face_mesh

            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=static_image_mode,
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )

            self.use_mediapipe = True

        except Exception as e:

            print("========== MEDIAPIPE FAILED ==========")
            print(e)

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            print("Cascade Path:", cascade_path)

            self.face_cascade = cv2.CascadeClassifier(cascade_path)

            if self.face_cascade.empty():
                print("Haar Cascade could not be loaded.")
                self.face_cascade = None
            else:
                print("========== HAAR CASCADE LOADED ==========")

    # ----------------------------------------------------------

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[Optional[Union[List, dict]], np.ndarray]:

        if self.use_mediapipe and self.face_mesh is not None:

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                return results.multi_face_landmarks[0].landmark, frame

            return None, frame

        if self.face_cascade is None:
            return None, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )

        if len(faces) == 0:
            return None, frame

        x, y, w, h = faces[0]

        return {"bbox": (x, y, w, h)}, frame

    # ----------------------------------------------------------

    def get_roi_mask(self, frame, landmarks):

        h, w = frame.shape[:2]

        mask = np.zeros((h, w), dtype=np.uint8)

        if landmarks is None:
            return mask

        # Haar Cascade
        if isinstance(landmarks, dict):

            x, y, width, height = landmarks["bbox"]

            cv2.rectangle(
                mask,
                (x + width // 5, y + height // 10),
                (x + width * 4 // 5, y + height // 3),
                255,
                -1,
            )

            return mask

        # MediaPipe

        indices = [
            10,
            67,
            109,
            107,
            336,
            296,
            334,
            293,
            234,
            93,
            132,
            58,
            172,
            136,
            150,
            454,
            323,
            361,
            287,
            373,
            365,
            379,
        ]

        pts = []

        for idx in indices:

            p = landmarks[idx]

            pts.append([int(p.x * w), int(p.y * h)])

        hull = cv2.convexHull(np.array(pts))

        cv2.fillConvexPoly(mask, hull, 255)

        return mask

    # ----------------------------------------------------------

    def extract_green_mean(self, frame, landmarks):

        if landmarks is None:
            return 0.0

        mask = self.get_roi_mask(frame, landmarks)

        roi = mask > 0

        if np.count_nonzero(roi) == 0:
            return 0.0

        green = frame[:, :, 1].astype(np.float32)

        return float(np.mean(green[roi]))

    # ----------------------------------------------------------

    def extract_signal_sample(self, frame, landmarks):

        sample = self.extract_green_mean(frame, landmarks)

        if sample == 0:
            return sample, 0.0, {}

        return sample, 1.0, {}

    # ----------------------------------------------------------

    def close(self):

        if self.face_mesh is not None:
            self.face_mesh.close()