"""
face_recognition_service.py
Wraps the `face_recognition` / `dlib` library to provide:
  - encoding extraction from a base64 webcam frame
  - matching a live frame against all stored employee encodings
"""

import base64
import io
import os
import uuid

import numpy as np
import cv2
from PIL import Image

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except Exception:
    FACE_RECOGNITION_AVAILABLE = False

from config import Config
from models import EmployeeModel


class FaceRecognitionService:

    def __init__(self):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.KNOWN_FACES_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def decode_base64_image(data_url):
        """Convert a 'data:image/jpeg;base64,...' string into a numpy RGB array."""
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        img_bytes = base64.b64decode(data_url)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        return np.array(image)

    @staticmethod
    def save_snapshot(rgb_array, employee_id):
        """Persist a snapshot image to disk for record-keeping, return relative path."""
        filename = f"{employee_id}_{uuid.uuid4().hex[:8]}.jpg"
        path = os.path.join(Config.UPLOAD_FOLDER, filename)
        bgr = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        cv2.imwrite(path, bgr)
        return os.path.join("uploads", filename).replace("\\", "/")

    # ------------------------------------------------------------------
    # Encoding extraction (used at registration time)
    # ------------------------------------------------------------------

    def extract_encoding(self, rgb_array):
        """
        Detect exactly one face in the image and return its 128-d encoding.
        Returns (encoding, error_message). encoding is None if it failed.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return None, ("face_recognition library is not available on this server. "
                          "Please install dlib / face_recognition (see README).")

        face_locations = face_recognition.face_locations(rgb_array, model=Config.FACE_DETECTION_MODEL)

        if len(face_locations) == 0:
            return None, "No face detected. Please center your face in the frame and ensure good lighting."
        if len(face_locations) > 1:
            return None, "Multiple faces detected. Please make sure only one person is in frame."

        encodings = face_recognition.face_encodings(rgb_array, known_face_locations=face_locations)
        if not encodings:
            return None, "Could not compute face encoding. Please try again."

        return encodings[0], None

    # ------------------------------------------------------------------
    # Recognition (used at attendance time)
    # ------------------------------------------------------------------

    def recognize(self, rgb_array):
        """
        Compare the given frame against all known employee encodings.
        Returns a dict: {
            'matched': bool,
            'employee_id': str or None,
            'name': str or None,
            'distance': float or None,
            'face_location': tuple or None,
            'message': str
        }
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                "matched": False, "employee_id": None, "name": None,
                "distance": None, "face_location": None,
                "message": "face_recognition library not available on server."
            }

        face_locations = face_recognition.face_locations(rgb_array, model=Config.FACE_DETECTION_MODEL)
        if not face_locations:
            return {
                "matched": False, "employee_id": None, "name": None,
                "distance": None, "face_location": None,
                "message": "No face detected in frame."
            }

        face_encodings = face_recognition.face_encodings(rgb_array, known_face_locations=face_locations)
        if not face_encodings:
            return {
                "matched": False, "employee_id": None, "name": None,
                "distance": None, "face_location": None,
                "message": "Could not extract face encoding."
            }

        live_encoding = face_encodings[0]
        face_location = face_locations[0]

        known = EmployeeModel.get_all_with_encodings()
        if not known:
            return {
                "matched": False, "employee_id": None, "name": None,
                "distance": None, "face_location": face_location,
                "message": "No registered employees in the system yet."
            }

        known_encodings = [e[2] for e in known]
        distances = face_recognition.face_distance(known_encodings, live_encoding)
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])

        if best_distance <= Config.FACE_MATCH_TOLERANCE:
            employee_id, name, _ = known[best_idx]
            return {
                "matched": True,
                "employee_id": employee_id,
                "name": name,
                "distance": round(best_distance, 4),
                "face_location": face_location,
                "message": "Face recognized."
            }

        return {
            "matched": False, "employee_id": None, "name": None,
            "distance": round(best_distance, 4), "face_location": face_location,
            "message": "Face not recognized. Please register first or try again with better lighting."
        }


face_service = FaceRecognitionService()
