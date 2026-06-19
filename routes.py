"""
routes.py
All application routes: auth, registration, face capture/recognition,
employee dashboard and admin dashboard.
"""

import csv
import io
from datetime import datetime, date
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, jsonify, Response
)
from werkzeug.security import generate_password_hash

from models import UserModel, EmployeeModel, AttendanceModel
from face_recognition_service import face_service

bp = Blueprint("main", __name__)


# ============================================================
# Decorators
# ============================================================

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("main.login"))
            if role and session.get("role") != role:
                flash("You are not authorized to view this page.", "danger")
                return redirect(url_for("main.dashboard_redirect"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ============================================================
# Public / Auth routes
# ============================================================

@bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("main.dashboard_redirect"))
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = UserModel.get_by_username(username)
        if user and user["is_active"] and UserModel.verify_password(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["employee_id"] = user["employee_id"]
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("main.dashboard_redirect"))

        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/dashboard-redirect")
def dashboard_redirect():
    if session.get("role") == "admin":
        return redirect(url_for("main.admin_dashboard"))
    elif session.get("role") == "employee":
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


# ============================================================
# Employee Registration (Admin only)
# ============================================================

@bp.route("/register", methods=["GET", "POST"])
@login_required(role="admin")
def register():
    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        designation = request.form.get("designation", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip() or employee_id
        password = request.form.get("password", "").strip() or "Employee@123"
        face_image_data = request.form.get("face_image_data", "")

        if not employee_id or not name or not email:
            flash("Employee ID, Name and Email are required.", "danger")
            return render_template("register.html")

        if EmployeeModel.get_by_employee_id(employee_id):
            flash("Employee ID already exists.", "danger")
            return render_template("register.html")

        if EmployeeModel.get_by_email(email):
            flash("Email already registered.", "danger")
            return render_template("register.html")

        if not face_image_data:
            flash("Please capture a face photo before submitting.", "danger")
            return render_template("register.html")

        try:
            rgb = face_service.decode_base64_image(face_image_data)
        except Exception:
            flash("Could not process the captured image. Please try again.", "danger")
            return render_template("register.html")

        encoding, err = face_service.extract_encoding(rgb)
        if err:
            flash(err, "danger")
            return render_template("register.html")

        photo_path = face_service.save_snapshot(rgb, employee_id)

        ok, msg = EmployeeModel.create(
            employee_id, name, department, designation, phone, email, photo_path, encoding
        )
        if not ok:
            flash(f"Failed to create employee: {msg}", "danger")
            return render_template("register.html")

        ok_user, msg_user = UserModel.create_employee_user(username, password, employee_id, email)
        if not ok_user:
            flash(f"Employee created but user account failed: {msg_user}", "warning")
        else:
            flash(
                f"Employee '{name}' registered successfully! "
                f"Login username: {username} / password: {password}",
                "success",
            )

        return redirect(url_for("main.admin_dashboard"))

    return render_template("register.html")


@bp.route("/api/check-employee-id")
@login_required(role="admin")
def check_employee_id():
    employee_id = request.args.get("employee_id", "").strip()
    exists = EmployeeModel.get_by_employee_id(employee_id) is not None
    return jsonify({"exists": exists})


# ============================================================
# Face Capture / Recognition pages (live attendance)
# ============================================================

@bp.route("/face-capture")
@login_required()
def face_capture():
    """Generic page that opens webcam and recognizes the face for attendance."""
    return render_template("face_capture.html")


@bp.route("/api/recognize-face", methods=["POST"])
@login_required()
def api_recognize_face():
    data = request.get_json(silent=True) or {}
    image_data = data.get("image")
    if not image_data:
        return jsonify({"success": False, "message": "No image supplied."}), 400

    try:
        rgb = face_service.decode_base64_image(image_data)
    except Exception:
        return jsonify({"success": False, "message": "Invalid image data."}), 400

    result = face_service.recognize(rgb)

    if not result["matched"]:
        return jsonify({"success": False, "message": result["message"], "distance": result["distance"]})

    employee = EmployeeModel.get_by_employee_id(result["employee_id"])
    if not employee:
        return jsonify({"success": False, "message": "Employee record not found."})

    # If logged in as employee, restrict recognition to themselves for security
    if session.get("role") == "employee" and session.get("employee_id") != result["employee_id"]:
        return jsonify({
            "success": False,
            "message": "Face does not match your employee account."
        })

    today_record = AttendanceModel.get_today_record(employee["employee_id"])
    can_check_in = today_record is None
    can_check_out = today_record is not None and today_record["check_out_time"] is None

    return jsonify({
        "success": True,
        "employee": {
            "employee_id": employee["employee_id"],
            "name": employee["name"],
            "department": employee["department"],
            "designation": employee["designation"],
            "photo_path": employee["photo_path"],
        },
        "distance": result["distance"],
        "can_check_in": can_check_in,
        "can_check_out": can_check_out,
        "today_record": {
            "check_in_time": today_record["check_in_time"] if today_record else None,
            "check_out_time": today_record["check_out_time"] if today_record else None,
        } if today_record else None,
    })


@bp.route("/api/mark-attendance", methods=["POST"])
@login_required()
def api_mark_attendance():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    action = data.get("action")  # 'check_in' or 'check_out'

    if session.get("role") == "employee" and session.get("employee_id") != employee_id:
        return jsonify({"success": False, "message": "Not authorized for this employee."}), 403

    if not employee_id or action not in ("check_in", "check_out"):
        return jsonify({"success": False, "message": "Invalid request."}), 400

    employee = EmployeeModel.get_by_employee_id(employee_id)
    if not employee:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    if action == "check_in":
        ok, msg, row = AttendanceModel.check_in(employee_id)
    else:
        ok, msg, row = AttendanceModel.check_out(employee_id)

    response = {"success": ok, "message": msg}
    if row:
        response["record"] = {
            "date": row["date"],
            "check_in_time": row["check_in_time"],
            "check_out_time": row["check_out_time"],
            "working_hours": row["working_hours"],
            "status": row["status"],
        }
    return jsonify(response)


# ============================================================
# Employee Dashboard
# ============================================================

@bp.route("/dashboard")
@login_required(role="employee")
def dashboard():
    employee = EmployeeModel.get_by_employee_id(session["employee_id"])
    if not employee:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("main.logout"))

    today_record = AttendanceModel.get_today_record(employee["employee_id"])
    history = AttendanceModel.get_history(employee["employee_id"], limit=10)

    today = date.today()
    summary = AttendanceModel.get_monthly_summary(employee["employee_id"], today.year, today.month)

    return render_template(
        "dashboard.html",
        employee=employee,
        today_record=today_record,
        history=history,
        summary=summary,
        today_str=today.isoformat(),
    )


@bp.route("/attendance-history")
@login_required(role="employee")
def attendance_history():
    employee = EmployeeModel.get_by_employee_id(session["employee_id"])
    history = AttendanceModel.get_history(employee["employee_id"], limit=365)

    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month
    summary = AttendanceModel.get_monthly_summary(employee["employee_id"], year, month)

    return render_template(
        "attendance.html",
        employee=employee,
        history=history,
        summary=summary,
        selected_year=year,
        selected_month=month,
    )


@bp.route("/profile/update", methods=["POST"])
@login_required(role="employee")
def update_profile():
    employee_id = session["employee_id"]
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    designation = request.form.get("designation", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    EmployeeModel.update_profile(employee_id, name, department, designation, phone, email)
    flash("Profile updated successfully.", "success")
    return redirect(url_for("main.dashboard"))


# ============================================================
# Admin Dashboard
# ============================================================

@bp.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():
    total_employees = EmployeeModel.count_active()
    today_records = AttendanceModel.get_all_for_date()
    present_ids = AttendanceModel.get_present_employee_ids_for_date()
    present_count = len(present_ids)
    absent_count = max(total_employees - present_count, 0)

    employees = EmployeeModel.get_all(active_only=True)

    return render_template(
        "admin_dashboard.html",
        total_employees=total_employees,
        present_count=present_count,
        absent_count=absent_count,
        today_records=today_records,
        employees=employees,
        today_str=date.today().isoformat(),
    )


@bp.route("/admin/employees")
@login_required(role="admin")
def admin_employees():
    query = request.args.get("q", "").strip()
    if query:
        employees = EmployeeModel.search(query)
    else:
        employees = EmployeeModel.get_all(active_only=False)
    return render_template("admin_dashboard.html", employees=employees, search_query=query,
                            total_employees=EmployeeModel.count_active(),
                            present_count=len(AttendanceModel.get_present_employee_ids_for_date()),
                            absent_count=max(EmployeeModel.count_active() - len(AttendanceModel.get_present_employee_ids_for_date()), 0),
                            today_records=AttendanceModel.get_all_for_date(),
                            today_str=date.today().isoformat(),
                            employees_only_view=True)


@bp.route("/admin/employee/<employee_id>/toggle", methods=["POST"])
@login_required(role="admin")
def toggle_employee(employee_id):
    employee = EmployeeModel.get_by_employee_id(employee_id)
    if not employee:
        flash("Employee not found.", "danger")
    else:
        EmployeeModel.set_active(employee_id, not employee["is_active"])
        flash(f"Employee {employee['name']} status updated.", "success")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/employee/<employee_id>/delete", methods=["POST"])
@login_required(role="admin")
def delete_employee(employee_id):
    EmployeeModel.delete(employee_id)
    flash("Employee deleted permanently.", "info")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/reports")
@login_required(role="admin")
def admin_reports():
    start_date = request.args.get("start_date") or date.today().replace(day=1).isoformat()
    end_date = request.args.get("end_date") or date.today().isoformat()
    employee_id = request.args.get("employee_id") or None

    records = AttendanceModel.get_report(start_date, end_date, employee_id)
    employees = EmployeeModel.get_all(active_only=False)

    return render_template(
        "admin_dashboard.html",
        report_view=True,
        records=records,
        employees=employees,
        start_date=start_date,
        end_date=end_date,
        selected_employee_id=employee_id,
        total_employees=EmployeeModel.count_active(),
        present_count=len(AttendanceModel.get_present_employee_ids_for_date()),
        absent_count=max(EmployeeModel.count_active() - len(AttendanceModel.get_present_employee_ids_for_date()), 0),
        today_records=AttendanceModel.get_all_for_date(),
        today_str=date.today().isoformat(),
    )


@bp.route("/admin/reports/export")
@login_required(role="admin")
def export_csv():
    start_date = request.args.get("start_date") or date.today().replace(day=1).isoformat()
    end_date = request.args.get("end_date") or date.today().isoformat()
    employee_id = request.args.get("employee_id") or None

    records = AttendanceModel.get_report(start_date, end_date, employee_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Name", "Department", "Designation", "Date",
                      "Check In", "Check Out", "Working Hours", "Status"])
    for r in records:
        writer.writerow([
            r["employee_id"], r["name"], r["department"], r["designation"], r["date"],
            r["check_in_time"] or "-", r["check_out_time"] or "-", r["working_hours"], r["status"]
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"attendance_report_{start_date}_to_{end_date}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/admin/employee/<employee_id>/recapture", methods=["GET", "POST"])
@login_required(role="admin")
def recapture_face(employee_id):
    employee = EmployeeModel.get_by_employee_id(employee_id)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for("main.admin_dashboard"))

    if request.method == "POST":
        face_image_data = request.form.get("face_image_data", "")
        if not face_image_data:
            flash("Please capture a photo.", "danger")
            return render_template("face_capture.html", recapture_employee=employee)

        rgb = face_service.decode_base64_image(face_image_data)
        encoding, err = face_service.extract_encoding(rgb)
        if err:
            flash(err, "danger")
            return render_template("face_capture.html", recapture_employee=employee)

        photo_path = face_service.save_snapshot(rgb, employee_id)
        EmployeeModel.update_face_encoding(employee_id, encoding, photo_path)
        flash(f"Face data updated for {employee['name']}.", "success")
        return redirect(url_for("main.admin_dashboard"))

    return render_template("face_capture.html", recapture_employee=employee)
