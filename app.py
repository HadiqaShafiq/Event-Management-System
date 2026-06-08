from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename
from datetime import datetime

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "your_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_env_setting(name, default=""):
    value = os.environ.get(name)
    if value:
        return value

    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except OSError:
            pass

    return default


app.config['MAIL_SERVER'] = get_env_setting("MAIL_SERVER")
app.config['MAIL_PORT'] = int(get_env_setting("MAIL_PORT", "587"))
app.config['MAIL_USERNAME'] = get_env_setting("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = get_env_setting("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = get_env_setting("MAIL_USE_TLS", "true").lower() == "true"
app.config['MAIL_DEFAULT_SENDER'] = get_env_setting(
    "MAIL_DEFAULT_SENDER",
    app.config['MAIL_USERNAME']
)


# ---------------- DATABASE MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))

    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    phone = db.Column(db.String(20))
    reg_no = db.Column(db.String(50))
    campus = db.Column(db.String(100))
    department = db.Column(db.String(100))
    profile_image = db.Column(db.String(200))

    role = db.Column(db.String(10), nullable=False, default="user")
    status = db.Column(db.String(20), nullable=False, default="pending")

    created_at = db.Column(
        db.String(50),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    bookings = db.relationship('Booking', backref='user', lazy=True)
    issues = db.relationship('Issue', backref='user', lazy=True)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    venue = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    city = db.Column(db.String(50))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    image = db.Column(db.String(200))
    description = db.Column(db.String(300))
    price = db.Column(db.Float, nullable=False)

    bookings = db.relationship('Booking', backref='event', lazy=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    payment_status = db.Column(db.String(20), default="Paid")
    payment_receipt = db.Column(db.String(200))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event_name = db.Column(db.String(100))
    campus = db.Column(db.String(100))
    subject = db.Column(db.String(150))
    message = db.Column(db.String(500))

    created_at = db.Column(
        db.String(50),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event_name = db.Column(db.String(100))
    campus = db.Column(db.String(100))

    subject = db.Column(db.String(200))
    message = db.Column(db.String(500))

    created_at = db.Column(
        db.String(50),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


# -------- PASSWORD VALIDATION FUNCTION --------
def allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def is_strong_password(password):
    """Validate password strength: min 8 chars, mixed case, contains number or symbol"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower):
        return False, "Password must contain both uppercase and lowercase letters"
    
    if not (has_digit or has_special):
        return False, "Password must contain numbers or special characters"
    
    return True, "Strong password"


def send_email(to_email, subject, body):
    if not to_email:
        return False

    mail_server = app.config['MAIL_SERVER']
    mail_username = app.config['MAIL_USERNAME']
    mail_password = app.config['MAIL_PASSWORD']
    mail_sender = app.config['MAIL_DEFAULT_SENDER']

    if not all([mail_server, mail_username, mail_password, mail_sender]):
        print(f"Email not sent to {to_email}: mail settings are missing.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_sender
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(mail_server, app.config['MAIL_PORT']) as smtp:
            if app.config['MAIL_USE_TLS']:
                smtp.starttls()
            smtp.login(mail_username, mail_password)
            smtp.send_message(message)
        return True
    except Exception as error:
        print(f"Email not sent to {to_email}: {error}")
        return False


def send_bulk_email(users, subject, body):
    for user in users:
        send_email(user.email, subject, body)


def user_full_name(user):
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"


def ensure_user_profile_image_column():
    columns = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
    column_names = [column[1] for column in columns]

    if "profile_image" not in column_names:
        db.session.execute(text("ALTER TABLE user ADD COLUMN profile_image VARCHAR(200)"))
        db.session.commit()


def ensure_booking_payment_receipt_column():
    columns = db.session.execute(text("PRAGMA table_info(booking)")).fetchall()
    column_names = [column[1] for column in columns]

    if "payment_receipt" not in column_names:
        db.session.execute(text("ALTER TABLE booking ADD COLUMN payment_receipt VARCHAR(200)"))
        db.session.commit()


def parse_optional_price(price_value):
    price_value = (price_value or "").strip()
    return float(price_value) if price_value else 0.0


def event_requires_payment(event):
    return (event.price or 0) > 0


def today_string():
    return datetime.now().strftime("%Y-%m-%d")


def parse_event_date(date_value):
    if not date_value:
        return None

    try:
        return datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return None


def event_has_ended(event):
    event_end = parse_event_date(event.end_date) or parse_event_date(event.start_date)
    today = datetime.now().date()
    return bool(event_end and event_end < today)


def event_is_bookable(event):
    return not event_has_ended(event)


def event_status_label(event):
    event_start = parse_event_date(event.start_date)
    event_end = parse_event_date(event.end_date) or event_start
    today = datetime.now().date()

    if event_end and event_end < today:
        return "Ended"

    if event_start and event_start > today:
        return "Upcoming"

    return "Ongoing"


def chatbot_event_payload():
    events = Event.query.order_by(Event.start_date.asc()).all()

    return [
        {
            "title": event.title,
            "category": event.category or "",
            "venue": event.venue or "",
            "city": event.city or "",
            "start_date": event.start_date or "",
            "end_date": event.end_date or "",
            "description": event.description or "",
            "price": event.price or 0,
            "status": event_status_label(event),
            "bookable": event_is_bookable(event),
        }
        for event in events
    ]


def validate_event_dates(start_date, end_date):
    parsed_start = parse_event_date(start_date)
    parsed_end = parse_event_date(end_date)

    if not parsed_start or not parsed_end:
        return "Please select valid start and end dates."

    if parsed_end < parsed_start:
        return "End date cannot be before start date."

    return None


def update_password_from_form(user):
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    if not current_password and not new_password:
        return None

    if not current_password or not new_password:
        return "Enter both current password and new password to change your password."

    if current_password != user.password:
        return "Current password is incorrect."

    is_strong, message = is_strong_password(new_password)
    if not is_strong:
        return message

    user.password = new_password
    return None


def delete_uploaded_file(filename):
    if not filename:
        return

    upload_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
    file_path = os.path.abspath(os.path.join(upload_root, filename))

    if file_path.startswith(upload_root + os.sep) and os.path.isfile(file_path):
        os.remove(file_path)


def delete_booking_record(booking):
    delete_uploaded_file(booking.payment_receipt)
    db.session.delete(booking)


# ---------------- INIT DB ----------------
with app.app_context():
    db.create_all()
    ensure_user_profile_image_column()
    ensure_booking_payment_receipt_column()

    if not User.query.filter_by(email="admin@example.com").first():
        admin = User(
            email="admin@example.com",
            password="admin123",
            role="admin",
            status="approved",
            first_name="Admin",
            last_name="User"
        )
        db.session.add(admin)

    db.session.commit()


@app.context_processor
def inject_admin_profile():
    current_admin = None
    admin_logo_filename = "images/logo.png"
    current_user = None
    user_logo_filename = "images/logo.png"

    if session.get("role") == "admin" and session.get("user_id"):
        current_admin = User.query.get(session["user_id"])
        if current_admin and current_admin.profile_image:
            admin_logo_filename = f"uploads/{current_admin.profile_image}"

    if session.get("role") == "user" and session.get("user_id"):
        current_user = User.query.get(session["user_id"])
        if current_user and current_user.profile_image:
            user_logo_filename = f"uploads/{current_user.profile_image}"

    return dict(
        current_admin=current_admin,
        admin_logo_filename=admin_logo_filename,
        current_user=current_user,
        user_logo_filename=user_logo_filename,
        event_has_ended=event_has_ended,
        event_is_bookable=event_is_bookable,
        event_status_label=event_status_label,
        today_string=today_string,
        chatbot_events=chatbot_event_payload()
    )


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            email=request.form["email"],
            password=request.form["password"]
        ).first()

        if user:
            if user.status != "approved":
                return render_template("login.html", error="Your registration is pending admin approval")

            if user.role == "admin":
                session["user_id"] = user.id
                session["role"] = user.role
                session["user_name"] = f"{user.first_name} {user.last_name}"
                session["user_email"] = user.email
                return redirect("/admin")

            if user.role == "user":
                session["user_id"] = user.id
                session["role"] = user.role
                session["user_name"] = f"{user.first_name} {user.last_name}"
                session["user_email"] = user.email
                return redirect("/user")

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------- CHECK EMAIL --------
@app.route("/check-email", methods=["GET"])
def check_email():
    email = request.args.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"available": False, "message": "Email is required"})
    
    user = User.query.filter_by(email=email).first()
    
    if user:
        return jsonify({"available": False, "message": "Email already exists"})
    
    return jsonify({"available": True, "message": "Email is available"})


# -------- REGISTRATION --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        reg_no = request.form.get("reg_no", "").strip()
        phone = request.form.get("phone", "").strip()
        campus = request.form.get("campus", "").strip()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", "user").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        errors = []

        if not all([first_name, last_name, reg_no, phone, campus, department, role, email, password, confirm_password]):
            errors.append("All fields are required")

        if role not in ["user", "admin"]:
            errors.append("Please select a valid role")

        if email:
            if User.query.filter_by(email=email).first():
                errors.append("Email already exists")

        if password != confirm_password:
            errors.append("Passwords do not match")

        if password:
            is_strong, message = is_strong_password(password)
            if not is_strong:
                errors.append(message)

        if errors:
            return render_template("login.html", registration_errors=errors)

        # Create new user with "pending" status
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            reg_no=reg_no,
            phone=phone,
            campus=campus,
            department=department,
            email=email,
            password=password,
            role=role,
            status="pending"
        )

        db.session.add(new_user)
        db.session.commit()

        return render_template("login.html", success="Registration successful! Awaiting admin approval.")

    return render_template("login.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") == "admin":
        return render_template(
            "admin_dashboard.html",
            events=Event.query.all(),
            bookings=Booking.query.all(),
            users=User.query.all(),
            issues=Issue.query.all()
        )
    return redirect("/")


# ---------------- ADMIN PROFILE ----------------
@app.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():
    if session.get("role") == "admin":
        admin = User.query.get_or_404(session["user_id"])

        if request.method == "POST":
            admin.first_name = request.form.get("first_name", "").strip()
            admin.last_name = request.form.get("last_name", "").strip()
            admin.email = request.form.get("email", "").strip().lower()
            admin.phone = request.form.get("phone", "").strip()
            admin.campus = request.form.get("campus", "").strip()
            admin.department = request.form.get("department", "").strip()

            if not admin.email:
                return render_template(
                    "admin_profile.html",
                    admin=admin,
                    error="Email is required."
                )

            existing_admin = User.query.filter_by(email=admin.email).first()
            if existing_admin and existing_admin.id != admin.id:
                return render_template(
                    "admin_profile.html",
                    admin=admin,
                    error="Email already exists."
                )

            password_error = update_password_from_form(admin)
            if password_error:
                return render_template(
                    "admin_profile.html",
                    admin=admin,
                    error=password_error
                )

            file = request.files.get("profile_image")
            if file and file.filename:
                if not allowed_image_file(file.filename):
                    return render_template(
                        "admin_profile.html",
                        admin=admin,
                        error="Please upload a valid image file."
                    )

                original_filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"admin_{admin.id}_{timestamp}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                admin.profile_image = filename

            db.session.commit()
            session["user_name"] = f"{admin.first_name} {admin.last_name}"
            session["user_email"] = admin.email

            return render_template(
                "admin_profile.html",
                admin=admin,
                success="Profile updated successfully."
            )

        return render_template("admin_profile.html", admin=admin)

    return redirect("/")


# ---------------- ADD EVENT ----------------
@app.route("/admin/add_event", methods=["GET", "POST"])
def add_event():
    if session.get("role") == "admin":
        if request.method == "POST":
            date_error = validate_event_dates(
                request.form.get("start_date"),
                request.form.get("end_date")
            )

            if date_error:
                return render_template("add_event.html", error=date_error)

            file = request.files.get("image")
            filename = None

            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            event = Event(
                title=request.form["title"],
                category=request.form["category"],
                phone=request.form.get("phone"),
                venue=request.form["venue"],
                pincode=request.form.get("pincode"),
                city=request.form["city"],
                start_date=request.form["start_date"],
                end_date=request.form["end_date"],
                description=request.form["description"],
                price=parse_optional_price(request.form.get("price")),
                image=filename
            )

            db.session.add(event)
            db.session.commit()

            approved_users = User.query.filter_by(role="user", status="approved").all()
            send_bulk_email(
                approved_users,
                f"Event Management System: New event added",
                (
                    f"Hello,\n\n"
                    f"This message is from the Event Management System.\n\n"
                    f"A new event has been added.\n\n"
                    f"Event: {event.title}\n"
                    f"Venue: {event.venue}\n"
                    f"City: {event.city}\n"
                    f"Start Date: {event.start_date}\n"
                    f"End Date: {event.end_date}\n"
                    f"Price: Rs {event.price or 0}\n\n"
                    f"Please login to the Event Management System for more details."
                )
            )

            return redirect("/admin/manage_events")

        return render_template("add_event.html")

    return redirect("/")


# ---------------- MANAGE EVENTS ----------------
@app.route("/admin/manage_events")
def manage_events():
    if session.get("role") == "admin":

        search = request.args.get("search")

        if search:
            events = Event.query.filter(
                (Event.title.contains(search)) |
                (Event.category.contains(search))
            ).all()
        else:
            events = Event.query.all()

        return render_template(
            "manage_events.html",
            events=events,
            success=request.args.get("success")
        )

    return redirect("/")


# ---------------- EDIT EVENT ----------------
@app.route("/admin/edit_event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if session.get("role") == "admin":

        event = Event.query.get_or_404(event_id)

        if request.method == "POST":
            date_error = validate_event_dates(
                request.form.get("start_date"),
                request.form.get("end_date")
            )

            if date_error:
                return render_template("edit_event.html", event=event, error=date_error)

            file = request.files.get("image")

            event.title = request.form["title"]
            event.category = request.form["category"]
            event.venue = request.form["venue"]
            event.phone = request.form.get("phone")
            event.city = request.form["city"]
            event.start_date = request.form["start_date"]
            event.end_date = request.form["end_date"]
            event.description = request.form["description"]
            event.price = parse_optional_price(request.form.get("price"))

            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                event.image = filename

            db.session.commit()
            return redirect("/admin/manage_events")

        return render_template("edit_event.html", event=event)

    return redirect("/")

# ---------------- ADMIN DELETE EVENT ----------------
@app.route("/admin/delete_event/<int:event_id>")
def delete_event(event_id):
    if session.get("role") == "admin":

        event = Event.query.get(event_id)

        if event:
            for booking in Booking.query.filter_by(event_id=event.id).all():
                delete_booking_record(booking)

            delete_uploaded_file(event.image)
            db.session.delete(event)
            db.session.commit()

    return redirect(url_for("manage_events", success="Event deleted successfully."))

# ---------------- ADMIN BOOKINGS ----------------
@app.route("/admin/bookings")
def admin_bookings():
    if session.get("role") == "admin":
        
        search = request.args.get("search")
        
        query = Booking.query.join(User).join(Event)
        
        if search:
            query = query.filter(
                (User.email.contains(search)) |
                (Event.title.contains(search))
            )
        
        bookings = query.all()
        return render_template(
            "admin_bookings.html",
            bookings=bookings,
            success=request.args.get("success")
        )
    return redirect("/")


# ---------------- ADMIN BOOKING DETAILS ----------------
@app.route("/admin/booking/<int:booking_id>")
def admin_booking_details(booking_id):
    if session.get("role") == "admin":
        booking = Booking.query.get_or_404(booking_id)
        return render_template("admin_booking_details.html", booking=booking)

    return redirect("/")


# ---------------- ADMIN DELETE BOOKING ----------------
@app.route("/admin/delete_booking/<int:booking_id>")
def delete_booking(booking_id):
    if session.get("role") == "admin":
        booking = Booking.query.get(booking_id)

        if booking:
            user_email = booking.user.email if booking.user else None
            name = user_full_name(booking.user) if booking.user else "User"
            event_title = booking.event.title if booking.event else "your event"

            delete_booking_record(booking)
            db.session.commit()

            send_email(
                user_email,
                "Event Management System: Booking deleted",
                (
                    f"Hello {name},\n\n"
                    f"This message is from the Event Management System.\n\n"
                    f"Your booking for {event_title} has been deleted by the admin.\n\n"
                    f"If you have any questions, please contact the admin."
                )
            )

        return redirect(url_for("admin_bookings", success="Booking deleted successfully."))

    return redirect("/")


# ---------------- ADMIN USERS ----------------
@app.route("/admin/users")
def admin_users():
    if session.get("role") == "admin":

        search = request.args.get("search")

        if search:
            users = User.query.filter(
                (User.email.contains(search)) |
                (User.first_name.contains(search)) |
                (User.last_name.contains(search))
            ).all()
        else:
            users = User.query.all()

        return render_template(
            "admin_users.html",
            users=users,
            success=request.args.get("success")
        )

    return redirect("/")


# ---------------- DELETE USER ----------------
@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") == "admin":
        user = User.query.get(user_id)

        if user and user.id != session["user_id"]:
            user_email = user.email
            name = user_full_name(user)

            for booking in Booking.query.filter_by(user_id=user.id).all():
                delete_booking_record(booking)

            for issue in Issue.query.filter_by(user_id=user.id).all():
                db.session.delete(issue)

            delete_uploaded_file(user.profile_image)
            db.session.delete(user)
            db.session.commit()

            send_email(
                user_email,
                "Event Management System: Account deleted",
                (
                    f"Hello {name},\n\n"
                    f"This message is from the Event Management System.\n\n"
                    f"Your account has been deleted by the admin.\n\n"
                    f"If you think this was a mistake, please contact the admin."
                )
            )

    return redirect(url_for("admin_users", success="User deleted successfully."))


# -------- APPROVE USER --------
@app.route("/admin/approve_user/<int:user_id>")
def approve_user(user_id):
    if session.get("role") == "admin":
        user = User.query.get(user_id)
        
        if user and user.id != session["user_id"] and user.role in ["user", "admin"]:
            user.status = "approved"
            db.session.commit()

            send_email(
                user.email,
                "Event Management System: Registration approved",
                (
                    f"Hello {user_full_name(user)},\n\n"
                    f"This message is from the Event Management System.\n\n"
                    f"Your registration request has been approved by the admin.\n\n"
                    f"You can now login to the Event Management System."
                )
            )

    return redirect(url_for("admin_users", success="User accepted successfully."))


# -------- REJECT USER --------
@app.route("/admin/reject_user/<int:user_id>")
def reject_user(user_id):
    if session.get("role") == "admin":
        user = User.query.get(user_id)
        
        if user and user.id != session["user_id"] and user.role in ["user", "admin"]:
            user_email = user.email
            name = user_full_name(user)

            for booking in Booking.query.filter_by(user_id=user.id).all():
                delete_booking_record(booking)

            for issue in Issue.query.filter_by(user_id=user.id).all():
                db.session.delete(issue)

            delete_uploaded_file(user.profile_image)
            db.session.delete(user)
            db.session.commit()

            send_email(
                user_email,
                "Event Management System: Registration rejected",
                (
                    f"Hello {name},\n\n"
                    f"This message is from the Event Management System.\n\n"
                    f"Your registration request was rejected by the admin.\n\n"
                    f"If you have any questions, please contact the admin."
                )
            )

    return redirect(url_for("admin_users", success="User rejected successfully."))


# ---------------- ADMIN REPORTS ----------------
@app.route("/admin/reports")
def admin_reports():
    if session.get("role") == "admin":

        search = request.args.get("search")

        query = Issue.query.join(User)

        if search:
            query = query.filter(
                (User.email.contains(search)) |
                (User.first_name.contains(search)) |
                (User.last_name.contains(search)) |
                (Issue.subject.contains(search)) |
                (Issue.message.contains(search)) |
                (Issue.event_name.contains(search)) |
                (Issue.campus.contains(search))
            )

        reports = query.order_by(Issue.id.desc()).all()

        return render_template(
            "admin_reports.html",
            reports=reports,
            success=request.args.get("success")
        )

    return redirect("/")


# ---------------- DELETE REPORT ----------------
@app.route("/admin/delete_report/<int:report_id>")
def delete_report(report_id):
    if session.get("role") == "admin":
        report = Issue.query.get(report_id)
        if report:
            db.session.delete(report)
            db.session.commit()
    return redirect(url_for("admin_reports", success="Report deleted successfully."))


# ---------------- USER DASHBOARD ----------------
@app.route("/user")
def user_dashboard():
    if session.get("role") == "user":

        user_id = session["user_id"]
        user = User.query.get(user_id)

        today = today_string()

        upcoming_events = Event.query.filter(
            Event.end_date >= today
        ).all()

        bookings = Booking.query.filter_by(user_id=user_id).all()

        issues = Issue.query.filter_by(user_id=user_id)\
            .order_by(Issue.id.desc())\
            .all()

        return render_template(
            "user_dashboard.html",
            user=user,
            bookings=bookings,
            issues=issues,
            upcoming_events=upcoming_events
        )

    return redirect("/")


# ---------------- USER PROFILE ----------------
@app.route("/user/profile", methods=["GET", "POST"])
def user_profile():
    if session.get("role") == "user":
        user = User.query.get_or_404(session["user_id"])

        if request.method == "POST":
            user.first_name = request.form.get("first_name", "").strip()
            user.last_name = request.form.get("last_name", "").strip()
            user.email = request.form.get("email", "").strip().lower()
            user.phone = request.form.get("phone", "").strip()
            user.campus = request.form.get("campus", "").strip()
            user.department = request.form.get("department", "").strip()

            if not user.email:
                return render_template(
                    "user_profile.html",
                    user=user,
                    error="Email is required."
                )

            existing_user = User.query.filter_by(email=user.email).first()
            if existing_user and existing_user.id != user.id:
                return render_template(
                    "user_profile.html",
                    user=user,
                    error="Email already exists."
                )

            password_error = update_password_from_form(user)
            if password_error:
                return render_template(
                    "user_profile.html",
                    user=user,
                    error=password_error
                )

            file = request.files.get("profile_image")
            if file and file.filename:
                if not allowed_image_file(file.filename):
                    return render_template(
                        "user_profile.html",
                        user=user,
                        error="Please upload a valid image file."
                    )

                original_filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"user_{user.id}_{timestamp}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_image = filename

            db.session.commit()
            session["user_name"] = f"{user.first_name} {user.last_name}"
            session["user_email"] = user.email

            return render_template(
                "user_profile.html",
                user=user,
                success="Profile updated successfully."
            )

        return render_template("user_profile.html", user=user)

    return redirect("/")

# ---------------- USER EVENTS ----------------
@app.route("/user/events")
def user_events():
    if session.get("role") == "user":
        user_id = session["user_id"]

        bookings = Booking.query.filter_by(user_id=user_id).all()
        booked_event_ids = [b.event_id for b in bookings]

        search = request.args.get("search")

        if search:
            events = Event.query.filter(
                (Event.title.contains(search)) |
                (Event.city.contains(search))
            ).all()
        else:
            events = Event.query.all()

        return render_template(
            "user_events.html",
            events=events,
            booked_event_ids=booked_event_ids
        )

    return redirect("/")

# ---------------- USER EVENT DETAILS ----------------
@app.route("/user/event/<int:event_id>")
def user_event_details(event_id):
    if session.get("role") == "user":

        event = Event.query.get_or_404(event_id)

        return render_template("user_event_details.html", event=event)

    return redirect("/")

# ---------------- BOOK EVENT ----------------
@app.route("/user/book/<int:event_id>")
def book_event(event_id):
    if session.get("role") == "user":

        user_id = session["user_id"]
        event = Event.query.get_or_404(event_id)

        existing_booking = Booking.query.filter_by(
            user_id=user_id,
            event_id=event_id
        ).first()

        if existing_booking:
            return redirect("/user/bookings")

        if event_has_ended(event):
            return redirect("/user/events")

        if not event_requires_payment(event):
            booking = Booking(
                user_id=user_id,
                event_id=event_id,
                payment_status="Free"
            )

            db.session.add(booking)
            db.session.commit()
            return redirect("/user/bookings")

        return redirect(url_for("payment_page", event_id=event_id))

    return redirect("/")

    # ---------------- USER BOOKINGS ----------------
@app.route("/user/bookings")
def user_bookings():
    if session.get("role") == "user":
        user_id = session["user_id"]

        search = request.args.get("search")

        query = Booking.query.filter_by(user_id=user_id).join(Event)

        if search:
            query = query.filter(
                (Event.title.contains(search)) |
                (Event.venue.contains(search))
            )

        bookings = query.all()

        return render_template(
            "user_bookings.html",
            bookings=bookings
        )

    return redirect("/")

# ---------------- PAYMENT PAGE ----------------
@app.route("/user/payment/<int:event_id>", methods=["GET", "POST"])
def payment_page(event_id):
    if session.get("role") == "user":

        event = Event.query.get_or_404(event_id)
        user_id = session["user_id"]

        existing_booking = Booking.query.filter_by(
            user_id=user_id,
            event_id=event_id
        ).first()

        if existing_booking:
            return redirect("/user/bookings")

        if event_has_ended(event):
            return redirect("/user/events")

        if not event_requires_payment(event):
            return redirect(url_for("book_event", event_id=event_id))

        if request.method == "POST":

            # ---------------- REQUIRED FILE ----------------
            file = request.files.get("payment_slip")
            if not file or file.filename == "":
                return "Payment slip is required", 400

            if not allowed_image_file(file.filename):
                return "Please upload a valid receipt image", 400

            filename = secure_filename(f"receipt_{user_id}_{event_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # ---------------- CREATE BOOKING ----------------
            booking = Booking(
                user_id=user_id,
                event_id=event_id,
                payment_status="Paid",
                payment_receipt=filename
            )

            db.session.add(booking)
            db.session.commit()

            return redirect("/user/bookings")

        return render_template("user_payment.html", event=event)

    return redirect("/")

# ---------------- USER REPORTS ----------------
@app.route("/user/reports")
def user_reports():
    if session.get("role") == "user":

        user_id = session["user_id"]

        search = request.args.get("search")

        query = Issue.query.filter_by(user_id=user_id)

        if search:
            query = query.filter(
                (Issue.event_name.contains(search)) |
                (Issue.subject.contains(search)) |
                (Issue.campus.contains(search)) |
                (Issue.message.contains(search))
            )

        issues = query.order_by(Issue.id.desc()).all()

        return render_template("user_reports.html", issues=issues)

    return redirect("/")

# ---------------- USER CREATE REPORTS ----------------
@app.route("/user/reports/new", methods=["GET", "POST"])
def new_report():
    if session.get("role") == "user":

        if request.method == "POST":

            issue = Issue(
                user_id=session["user_id"],
                event_name=request.form["event_name"],
                campus=request.form["campus"],
                subject=request.form["subject"],
                message=request.form["message"]
            )

            db.session.add(issue)
            db.session.commit()

            return redirect("/user/reports")

        return render_template("new_report.html")

    return redirect("/")

 
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
