# Face Recognition Attendance System
# =====================================
# Screenshot போல் exact same design - OpenCV + Python + HTML

## STEP 1 - Install Requirements
pip install flask flask-cors face-recognition opencv-python numpy pillow

## Note: face-recognition install ஆக CMake தேவைப்படலாம்
## Windows-ல் problem வந்தால்:
##   pip install cmake
##   pip install dlib
##   pip install face-recognition

## STEP 2 - Run Backend (Terminal 1)
python app.py

## STEP 3 - Open Frontend (Browser)
## index.html ஐ browser-ல் open செய்யுங்கள்
## அல்லது Terminal 2-ல்:
##   python -m http.server 8080
## பிறகு: http://localhost:8080

## HOW IT WORKS:
## ─────────────
## முதல் முறை:  Face → Not recognized → Register பண்ணுங்கள் → Details save
## அடுத்த முறை: Face → Recognized → Employee details automatically காட்டும்
##               → Attendance mark ஆகும்

## FILES:
## ─────
## app.py        → Python backend (Flask + face-recognition)
## index.html    → Frontend UI
## employees.json → Auto-created (employee data)
## attendance.json → Auto-created (attendance records)
## face_data/    → Auto-created (face encodings stored here)
