# Face Recognition Employee Attendance System

A complete, production-ready employee attendance system built with **Flask**, **SQLite**,
**OpenCV**, and the **face_recognition** library. Employees check in/out by simply
looking into the webcam — no cards, no PINs.

---

## ✨ Features

- **Authentication**: Separate Admin and Employee logins with secure session management
  (Flask-Session, hashed passwords via Werkzeug).
- **Employee Registration** (Admin only): Capture employee details + face photo via webcam,
  automatically extracts and stores a 128-d face encoding.
- **Real-Time Face Recognition**: Opens the webcam, detects faces, matches against all
  registered employees, and shows a welcome message with employee details.
- **Attendance Engine**: Automatic check-in / check-out, working-hours calculation,
  daily/monthly history, Present/Half-Day/Absent status.
- **Employee Dashboard**: Profile, today's status, check-in/out shortcut, attendance history,
  monthly summary cards.
- **Admin Dashboard**: Live counts (Total / Present / Absent), employee management
  (search, activate/deactivate, delete, recapture face), attendance reports with date-range
  filters and **CSV export**.

---

## 🗂 Project Structure

```
face_attendance/
├── app.py                       # App entry point
├── config.py                    # Configuration
├── database.py                  # SQLite schema + connection
├── models.py                    # Data access layer (Users / Employees / Attendance)
├── routes.py                    # All Flask routes
├── face_recognition_service.py  # Face encoding / recognition logic
├── requirements.txt
├── README.md
├── instance/
│   └── attendance.db            # SQLite DB (auto-created on first run)
├── known_faces/                 # (reserved for future use)
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/                 # captured employee photos (auto-created)
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── face_capture.html
    ├── dashboard.html
    ├── attendance.html
    └── admin_dashboard.html
```

---

## 🚀 Getting Started

### 1. System dependencies (required for `dlib` / `face_recognition`)

**Ubuntu / Debian**
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake libopenblas-dev liblapack-dev libx11-dev
```

**macOS**
```bash
brew install cmake
```

**Windows**
Install [CMake](https://cmake.org/download/) and Visual Studio Build Tools (C++ workload)
before installing `dlib`.

### 2. Install Python dependencies

```bash
cd face_attendance
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> If `dlib` fails to build, install a prebuilt wheel matching your Python version, e.g.
> `pip install dlib-binary` or use `conda install -c conda-forge dlib`.

### 3. Run the application

```bash
python app.py
```

The app starts at **http://127.0.0.1:5000** and automatically:
- Creates `instance/attendance.db`
- Creates all required tables
- Seeds a default admin account

**Default Admin Login**
```
Username: admin
Password: Admin@123
```
⚠️ Change this password immediately in production.

### 4. Register your first employee

1. Log in as admin.
2. Go to **Add Employee**.
3. Fill in details, click **Start Camera**, then **Capture Photo**.
4. Click **Register Employee**. A login username/password is generated for the employee
   (or set your own in the form).

### 5. Mark attendance

- Employees log in and click **Check In/Out** → **Start Camera & Recognize**.
- The system scans every 2 seconds, recognizes the face, and shows Check-In / Check-Out
  buttons with a welcome message.

---

## 🛠 Database Tables

| Table        | Purpose                                                            |
|--------------|---------------------------------------------------------------------|
| `users`      | Login credentials for admins and employees (hashed passwords)       |
| `employees`  | Employee master data + serialized face encoding (128-d vector)      |
| `attendance` | Daily check-in/out records, working hours, status                  |

---

## 🔒 Security Notes

- Passwords are hashed with `werkzeug.security` (PBKDF2).
- Sessions are server-side (Flask-Session, filesystem backend) and signed.
- Face matching uses Euclidean distance with a configurable tolerance
  (`Config.FACE_MATCH_TOLERANCE`, default `0.5` — lower is stricter).
- Employees can only mark attendance for their own recognized face / account.

---

## ⚙️ Configuration

Edit `config.py` to change:
- `FACE_MATCH_TOLERANCE` — recognition strictness
- `FACE_DETECTION_MODEL` — `hog` (fast, CPU) or `cnn` (accurate, needs GPU)
- `SECRET_KEY` — set a strong random value in production
- Default admin credentials

---

## 📋 Requirements

See `requirements.txt`. Key packages: `Flask`, `Flask-Session`, `opencv-python`,
`face_recognition`, `dlib`, `numpy`, `Pillow`, `pandas`.

---

## 📈 Possible Enhancements

- Liveness detection (anti-spoofing) before marking attendance.
- Email/SMS notifications on check-in/out.
- Role-based admin permissions (HR vs Super Admin).
- Multi-camera / kiosk mode for entrance terminals.
- REST API + mobile app integration.

---

## 📝 License

This project is provided as-is for educational and internal business use.
