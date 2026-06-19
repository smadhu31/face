"""
models.py
Data-access layer (DAL). All raw SQL lives here so routes.py stays clean.
"""

import pickle
import calendar
from datetime import datetime, date

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection


# ============================================================
# USERS
# ============================================================

class UserModel:

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return row

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return row

    @staticmethod
    def create_employee_user(username, password, employee_id, email):
        conn = get_db_connection()
        try:
            conn.execute(
                """INSERT INTO users (username, password_hash, role, employee_id, email, is_active)
                   VALUES (?, ?, 'employee', ?, ?, 1)""",
                (username, generate_password_hash(password), employee_id, email),
            )
            conn.commit()
            return True, "User created"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    @staticmethod
    def verify_password(stored_hash, password):
        return check_password_hash(stored_hash, password)

    @staticmethod
    def create_admin(username, password, email):
        conn = get_db_connection()
        try:
            conn.execute(
                """INSERT INTO users (username, password_hash, role, email, is_active)
                   VALUES (?, ?, 'admin', ?, 1)""",
                (username, generate_password_hash(password), email),
            )
            conn.commit()
            return True, "Admin created"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


# ============================================================
# EMPLOYEES
# ============================================================

class EmployeeModel:

    @staticmethod
    def create(employee_id, name, department, designation, phone, email, photo_path, face_encoding):
        conn = get_db_connection()
        try:
            encoded_blob = pickle.dumps(face_encoding) if face_encoding is not None else None
            conn.execute(
                """INSERT INTO employees
                   (employee_id, name, department, designation, phone, email, photo_path, face_encoding, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (employee_id, name, department, designation, phone, email, photo_path, encoded_blob),
            )
            conn.commit()
            return True, "Employee created"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    @staticmethod
    def update_face_encoding(employee_id, face_encoding, photo_path=None):
        conn = get_db_connection()
        try:
            encoded_blob = pickle.dumps(face_encoding)
            if photo_path:
                conn.execute(
                    "UPDATE employees SET face_encoding = ?, photo_path = ? WHERE employee_id = ?",
                    (encoded_blob, photo_path, employee_id),
                )
            else:
                conn.execute(
                    "UPDATE employees SET face_encoding = ? WHERE employee_id = ?",
                    (encoded_blob, employee_id),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_by_employee_id(employee_id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
        conn.close()
        return row

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM employees WHERE email = ?", (email,)).fetchone()
        conn.close()
        return row

    @staticmethod
    def get_all(active_only=True):
        conn = get_db_connection()
        if active_only:
            rows = conn.execute(
                "SELECT * FROM employees WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_all_with_encodings():
        """Returns list of (employee_id, name, encoding_ndarray) for active employees."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT employee_id, name, face_encoding FROM employees WHERE is_active = 1 AND face_encoding IS NOT NULL"
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            try:
                enc = pickle.loads(r["face_encoding"])
                results.append((r["employee_id"], r["name"], enc))
            except Exception:
                continue
        return results

    @staticmethod
    def search(query):
        conn = get_db_connection()
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM employees
               WHERE (employee_id LIKE ? OR name LIKE ? OR department LIKE ? OR designation LIKE ? OR email LIKE ?)
               ORDER BY name""",
            (like, like, like, like, like),
        ).fetchall()
        conn.close()
        return rows

    @staticmethod
    def update_profile(employee_id, name, department, designation, phone, email):
        conn = get_db_connection()
        try:
            conn.execute(
                """UPDATE employees SET name = ?, department = ?, designation = ?, phone = ?, email = ?
                   WHERE employee_id = ?""",
                (name, department, designation, phone, email, employee_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def set_active(employee_id, is_active):
        conn = get_db_connection()
        try:
            conn.execute(
                "UPDATE employees SET is_active = ? WHERE employee_id = ?",
                (1 if is_active else 0, employee_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete(employee_id):
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def count_active():
        conn = get_db_connection()
        cnt = conn.execute("SELECT COUNT(*) AS c FROM employees WHERE is_active = 1").fetchone()["c"]
        conn.close()
        return cnt


# ============================================================
# ATTENDANCE
# ============================================================

class AttendanceModel:

    @staticmethod
    def get_today_record(employee_id, on_date=None):
        on_date = on_date or date.today().isoformat()
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
            (employee_id, on_date),
        ).fetchone()
        conn.close()
        return row

    @staticmethod
    def check_in(employee_id, on_date=None, check_time=None):
        on_date = on_date or date.today().isoformat()
        check_time = check_time or datetime.now().strftime("%H:%M:%S")
        conn = get_db_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
                (employee_id, on_date),
            ).fetchone()
            if existing:
                return False, "Already checked in today", existing
            conn.execute(
                """INSERT INTO attendance (employee_id, date, check_in_time, status)
                   VALUES (?, ?, ?, 'Present')""",
                (employee_id, on_date, check_time),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
                (employee_id, on_date),
            ).fetchone()
            return True, "Checked in successfully", row
        finally:
            conn.close()

    @staticmethod
    def check_out(employee_id, on_date=None, check_time=None):
        on_date = on_date or date.today().isoformat()
        check_time = check_time or datetime.now().strftime("%H:%M:%S")
        conn = get_db_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
                (employee_id, on_date),
            ).fetchone()
            if not existing:
                return False, "You have not checked in today", None
            if existing["check_out_time"]:
                return False, "Already checked out today", existing

            working_hours = AttendanceModel._calc_hours(existing["check_in_time"], check_time)
            status = "Present" if working_hours >= 4 else "Half Day"

            conn.execute(
                """UPDATE attendance SET check_out_time = ?, working_hours = ?, status = ?
                   WHERE employee_id = ? AND date = ?""",
                (check_time, working_hours, status, employee_id, on_date),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
                (employee_id, on_date),
            ).fetchone()
            return True, "Checked out successfully", row
        finally:
            conn.close()

    @staticmethod
    def _calc_hours(check_in_time, check_out_time):
        fmt = "%H:%M:%S"
        t_in = datetime.strptime(check_in_time, fmt)
        t_out = datetime.strptime(check_out_time, fmt)
        delta = (t_out - t_in).total_seconds() / 3600.0
        return round(max(delta, 0), 2)

    @staticmethod
    def get_history(employee_id, limit=30):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM attendance WHERE employee_id = ? ORDER BY date DESC LIMIT ?",
            (employee_id, limit),
        ).fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_monthly_summary(employee_id, year, month):
        conn = get_db_connection()
        month_str = f"{year:04d}-{month:02d}"
        rows = conn.execute(
            "SELECT * FROM attendance WHERE employee_id = ? AND date LIKE ? ORDER BY date",
            (employee_id, f"{month_str}%"),
        ).fetchall()
        conn.close()

        days_in_month = calendar.monthrange(year, month)[1]
        present_days = sum(1 for r in rows if r["status"] == "Present")
        half_days = sum(1 for r in rows if r["status"] == "Half Day")
        total_hours = sum(r["working_hours"] or 0 for r in rows)
        absent_days = days_in_month - len(rows) if year == date.today().year and month <= date.today().month else max(days_in_month - len(rows), 0)

        return {
            "records": rows,
            "days_in_month": days_in_month,
            "present_days": present_days,
            "half_days": half_days,
            "absent_days": absent_days,
            "total_hours": round(total_hours, 2),
            "avg_hours": round(total_hours / len(rows), 2) if rows else 0,
        }

    @staticmethod
    def get_all_for_date(on_date=None):
        on_date = on_date or date.today().isoformat()
        conn = get_db_connection()
        rows = conn.execute(
            """SELECT a.*, e.name, e.department, e.designation
               FROM attendance a
               JOIN employees e ON a.employee_id = e.employee_id
               WHERE a.date = ?
               ORDER BY a.check_in_time""",
            (on_date,),
        ).fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_present_employee_ids_for_date(on_date=None):
        on_date = on_date or date.today().isoformat()
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT employee_id FROM attendance WHERE date = ?", (on_date,)
        ).fetchall()
        conn.close()
        return {r["employee_id"] for r in rows}

    @staticmethod
    def get_report(start_date, end_date, employee_id=None):
        conn = get_db_connection()
        if employee_id:
            rows = conn.execute(
                """SELECT a.*, e.name, e.department, e.designation
                   FROM attendance a JOIN employees e ON a.employee_id = e.employee_id
                   WHERE a.date BETWEEN ? AND ? AND a.employee_id = ?
                   ORDER BY a.date DESC""",
                (start_date, end_date, employee_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT a.*, e.name, e.department, e.designation
                   FROM attendance a JOIN employees e ON a.employee_id = e.employee_id
                   WHERE a.date BETWEEN ? AND ?
                   ORDER BY a.date DESC, e.name""",
                (start_date, end_date),
            ).fetchall()
        conn.close()
        return rows
