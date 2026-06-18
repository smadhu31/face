"""
Face Recognition Attendance System
Requirements: pip install flask flask-cors opencv-python face-recognition numpy pillow
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import face_recognition
import numpy as np
import base64
import json
import os
import datetime
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Storage files
EMPLOYEES_FILE = "employees.json"
ATTENDANCE_FILE = "attendance.json"
FACES_DIR = "face_data"

os.makedirs(FACES_DIR, exist_ok=True)

# ─── Load / Save Helpers ────────────────────────────────────────────────────

def load_employees():
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_employees(data):
    with open(EMPLOYEES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            return json.load(f)
    return []

def save_attendance(data):
    with open(ATTENDANCE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def decode_image(base64_str):
    """Convert base64 image to numpy array for face_recognition."""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_bytes = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)

def get_face_encoding(image_np):
    """Return face encoding or None if no face detected."""
    encodings = face_recognition.face_encodings(image_np)
    return encodings[0] if encodings else None

def load_all_encodings():
    """Load saved face encodings for all employees."""
    employees = load_employees()
    known_encodings = []
    known_ids = []
    for emp_id, emp_data in employees.items():
        enc_path = os.path.join(FACES_DIR, f"{emp_id}.npy")
        if os.path.exists(enc_path):
            enc = np.load(enc_path)
            known_encodings.append(enc)
            known_ids.append(emp_id)
    return known_encodings, known_ids

# ─── API Routes ─────────────────────────────────────────────────────────────

@app.route("/api/recognize", methods=["POST"])
def recognize():
    """
    Step 1: Recognize a face from captured image.
    Returns: { known: true, employee: {...} } or { known: false }
    """
    data = request.json
    image_b64 = data.get("image")
    if not image_b64:
        return jsonify({"error": "No image provided"}), 400

    img_np = decode_image(image_b64)
    encoding = get_face_encoding(img_np)

    if encoding is None:
        return jsonify({"error": "No face detected. Please look at the camera."}), 400

    known_encodings, known_ids = load_all_encodings()

    if not known_encodings:
        return jsonify({"known": False})

    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
    face_distances = face_recognition.face_distance(known_encodings, encoding)

    if True in matches:
        best_idx = int(np.argmin(face_distances))
        if matches[best_idx]:
            emp_id = known_ids[best_idx]
            employees = load_employees()
            emp = employees.get(emp_id)
            return jsonify({"known": True, "employee": emp})

    return jsonify({"known": False})


@app.route("/api/register", methods=["POST"])
def register():
    """
    Register a new employee with face capture.
    Body: { image, employee_id, name, department }
    """
    data = request.json
    image_b64 = data.get("image")
    emp_id    = data.get("employee_id", "").strip()
    name      = data.get("name", "").strip()
    department = data.get("department", "").strip()

    if not all([image_b64, emp_id, name, department]):
        return jsonify({"error": "All fields are required."}), 400

    img_np = decode_image(image_b64)
    encoding = get_face_encoding(img_np)

    if encoding is None:
        return jsonify({"error": "No face detected. Please position your face clearly."}), 400

    # Save encoding
    np.save(os.path.join(FACES_DIR, f"{emp_id}.npy"), encoding)

    # Save employee info
    employees = load_employees()
    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    employees[emp_id] = {
        "employee_id": emp_id,
        "name": name,
        "department": department,
        "registered_at": now
    }
    save_employees(employees)

    return jsonify({
        "success": True,
        "message": "Registration completed successfully!",
        "employee": employees[emp_id]
    })


@app.route("/api/attendance", methods=["POST"])
def mark_attendance():
    """Mark attendance for a recognized employee."""
    data = request.json
    emp_id = data.get("employee_id")
    if not emp_id:
        return jsonify({"error": "Employee ID required"}), 400

    employees = load_employees()
    emp = employees.get(emp_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404

    attendance = load_attendance()
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Check already marked today
    already = any(
        r["employee_id"] == emp_id and r["date"] == today
        for r in attendance
    )

    if already:
        return jsonify({"already_marked": True, "employee": emp})

    record = {
        "employee_id": emp_id,
        "name": emp["name"],
        "department": emp["department"],
        "date": today,
        "time": now.strftime("%I:%M %p"),
        "datetime_display": now.strftime("%d %b %Y, %I:%M %p")
    }
    attendance.append(record)
    save_attendance(attendance)

    return jsonify({"success": True, "record": record, "employee": emp})


@app.route("/api/attendance/list", methods=["GET"])
def get_attendance():
    """Get all attendance records."""
    attendance = load_attendance()
    return jsonify({"records": attendance})


@app.route("/api/employees", methods=["GET"])
def get_employees():
    """Get all registered employees."""
    employees = load_employees()
    return jsonify({"employees": list(employees.values())})


if __name__ == "__main__":
    print("=" * 50)
    print("  Face Recognition Attendance System")
    print("  Running at: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
