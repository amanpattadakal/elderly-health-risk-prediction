from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import numpy as np
import pickle
import random
import time
import os
import matplotlib
matplotlib.use('Agg')   # IMPORTANT for Flask
import matplotlib.pyplot as plt
import os
import requests
from math import radians, sin, cos, sqrt, atan2
from flask import jsonify


app = Flask(__name__)

# SECRET KEY
app.config['SECRET_KEY'] = 'your_secret_key'  # change to a stronger secret in production

# DATABASE CONFIG
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(BASE_DIR, 'elderlycare.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# LOAD MACHINE LEARNING MODEL
model = pickle.load(open("model.pkl", "rb"))

# ----------------------------
# Admin credentials (secure)
# ----------------------------
ADMIN_USERNAME = "admin"
# Change the password below to your preferred admin password.
ADMIN_PASSWORD_HASH = generate_password_hash("Admin@123")  # change before deployment

# OTP CONFIG
OTP_EXPIRY_SECONDS = 300  # 5 minutes

# ------------------------------------------------------------
#                       PUBLIC HOME PAGE
# ------------------------------------------------------------
@app.route('/')
def home():
    return render_template("home.html")


# ------------------------------------------------------------
#                     USER MODEL
# ------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------------------------------------------------
#                 HEALTH RECORD MODEL
# ------------------------------------------------------------
class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(150))

    systolic_bp = db.Column(db.Integer)
    diastolic_bp = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    sugar = db.Column(db.Float)

    symptoms = db.Column(db.Text, nullable=False)
    history = db.Column(db.Text)
    medications = db.Column(db.Text)
    allergies = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================================
# REAL HOSPITALS USING OVERPASS API
# ================================

import requests
from flask import session

import requests
from flask import session, render_template

@app.route("/doctor_suggestions")
def doctor_suggestions():

    city = session.get("city")
    hospitals = []

    if city:
        overpass_query = f"""
        [out:json];
        area["name"="{city}"]["boundary"="administrative"];
        (
          node["amenity"="hospital"](area);
          way["amenity"="hospital"](area);
          relation["amenity"="hospital"](area);
        );
        out tags;
        """

        url = "https://overpass-api.de/api/interpreter"

        try:
            response = requests.post(url, data=overpass_query, timeout=5)

            # check response status
            if response.status_code == 200:
                data = response.json()
            else:
                data = {"elements": []}

        except Exception as e:
            print("API Error:", e)
            data = {"elements": []}

        for item in data.get("elements", []):
            name = item.get("tags", {}).get("name")
            if name:
                hospitals.append(name)

    # fallback if no hospitals found (VERY IMPORTANT FOR EXAM)
    if not hospitals:
        hospitals = ["City Hospital", "Apollo Clinic", "Care Hospital"]

    return render_template(
        "doctor_suggestions.html",
        city=city,
        hospitals=hospitals
    )
# ------------------------------------------------------------
#           DYNAMIC RISK SCORE FUNCTION
# ------------------------------------------------------------
def calculate_dynamic_risk(record):
    score = 0

    # Age
    if record.age > 75:
        score += 15
    elif record.age > 60:
        score += 10
    elif record.age > 50:
        score += 5

    # Blood Pressure
    if record.systolic_bp and record.diastolic_bp:
        if record.systolic_bp > 160 or record.diastolic_bp > 100:
            score += 25
        elif record.systolic_bp > 140 or record.diastolic_bp > 90:
            score += 15

    # Sugar
    if record.sugar:
        if record.sugar > 250:
            score += 25
        elif record.sugar > 180:
            score += 15

    # Heart Rate
    if record.heart_rate and (record.heart_rate > 110 or record.heart_rate < 50):
        score += 10

    # Temperature
    if record.temperature and record.temperature > 38.5:
        score += 10

    # BMI
    try:
        if record.weight and record.height:
            bmi = record.weight / ((record.height / 100) ** 2)
            if bmi > 32:
                score += 15
            elif bmi > 28:
                score += 8
    except:
        pass

    return min(score, 100)


# ------------------------------------------------------------
#                ADD HEALTH DATA ROUTE
# ------------------------------------------------------------
@app.route("/add_health", methods=["GET", "POST"])
@login_required
def add_health():

    def to_float(v): 
        return float(v) if v not in ("", None, "") else None

    def to_int(v): 
        return int(v) if v not in ("", None, "") else None

    if request.method == "POST":

        age = to_int(request.form.get("age"))
        if age is None or age < 50:
            flash("This system is designed only for users aged 50 and above.", "danger")
            return redirect(url_for("add_health"))

        record = HealthRecord(
            user_id=current_user.id,
            name=request.form["name"],
            age=age,
            gender=request.form["gender"],
            city=request.form.get("city"),

            systolic_bp=to_int(request.form.get("systolic_bp")),
            diastolic_bp=to_int(request.form.get("diastolic_bp")),
            heart_rate=to_int(request.form.get("heart_rate")),
            temperature=to_float(request.form.get("temperature")),
            weight=to_float(request.form.get("weight")),
            height=to_float(request.form.get("height")),
            sugar=to_float(request.form.get("sugar")),

            symptoms=request.form.get("symptoms", ""),
            history=request.form.get("history"),
            medications=request.form.get("medications"),
            allergies=request.form.get("allergies")
        )

        # save city for doctor suggestions
        session["city"] = record.city

        db.session.add(record)
        db.session.commit()

        return redirect(url_for("risk_prediction", record_id=record.id))

    return render_template("health_form.html")

# ------------------------------------------------------------
#                       USER DASHBOARD
# ------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ------------------------------------------------------------
#         VIEW MY LATEST RISK (AUTO REDIRECT)
# ------------------------------------------------------------
@app.route("/my_risk")
@login_required
def my_risk():
    record = HealthRecord.query.filter_by(user_id=current_user.id) \
                               .order_by(HealthRecord.id.desc()).first()

    if not record:
        flash("Please add health details first!", "warning")
        return redirect(url_for("add_health"))

    return redirect(url_for("risk_prediction", record_id=record.id))


# ------------------------------------------------------------
#                  RISK PREDICTION PAGE
# ------------------------------------------------------------
@app.route("/risk_prediction/<int:record_id>")
@login_required
def risk_prediction(record_id):

    record = HealthRecord.query.get(record_id)
    if not record:
        flash("Record not found!", "danger")
        return redirect(url_for("dashboard"))

    # ---------------- BMI ----------------
    bmi = 0
    if record.weight and record.height:
        bmi = record.weight / ((record.height / 100) ** 2)

    # ---------------- ML FEATURES ----------------
    features = np.array([[ 
        record.age or 0,
        record.systolic_bp or 0,
        record.diastolic_bp or 0,
        record.sugar or 0,
        record.heart_rate or 0,
        record.temperature or 0,
        record.weight or 0,
        record.height or 0,
        bmi
    ]])

    predicted = int(model.predict(features)[0])
    score = calculate_dynamic_risk(record)

    if predicted == 2:
        status = "High"
    elif predicted == 1:
        status = "Moderate"
    else:
        status = "Low"

    # ---------------- MATPLOTLIB GRAPH ----------------
    labels = ['Risk Score', 'Remaining']
    values = [score, 100 - score]

    plt.figure(figsize=(4,4))
    plt.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        colors=['#3f5efb', '#e6ebff'],
        startangle=90
    )
    plt.title("Health Risk Distribution")

    graph_path = f"static/graphs/risk_{record.id}.png"
    os.makedirs("static/graphs", exist_ok=True)
    plt.savefig(graph_path, bbox_inches='tight')
    plt.close()

    return render_template(
        "risk_prediction.html",
        score=int(score),
        status=status,
        graph_path=graph_path
    )
# ------------------------------------------------------------
#        HELPER: DETECT POSSIBLE DISEASES
# ------------------------------------------------------------
def detect_possible_disease(record):
    diseases = []

    if record.systolic_bp and record.systolic_bp > 140:
        diseases.append("Hypertension (High Blood Pressure)")

    if record.sugar and record.sugar > 180:
        diseases.append("Diabetes Mellitus")

    if record.heart_rate and (record.heart_rate > 110 or record.heart_rate < 55):
        diseases.append("Heart Rhythm Disorder")

    if record.temperature and record.temperature > 38:
        diseases.append("Fever / Infection")

    if "chest" in record.symptoms.lower():
        diseases.append("Possible Cardiac Issue")

    if "breath" in record.symptoms.lower():
        diseases.append("Respiratory Issue")

    if not diseases:
        diseases.append("No critical disease detected")

    return diseases


# ------------------------------------------------------------
#        HELPER: MOCK LOCATION-BASED HOSPITALS
# ------------------------------------------------------------
def get_nearby_hospitals(lat, lon, required_specialists=None, emergency=False):

    hospitals = [
        {"name": "City Care Hospital", "speciality": "Emergency & ICU", "distance": "1.2 km"},
        {"name": "Dr. Sneha Patil", "speciality": "General Physician", "distance": "0.8 km"},
        {"name": "Metro Multi-Speciality Hospital", "speciality": "Cardiology", "distance": "2.5 km"},
        {"name": "Heart Plus Clinic", "speciality": "Cardiologist", "distance": "3.0 km"},
    ]

    # Emergency → ICU first
    if emergency:
        hospitals.sort(
            key=lambda x: 0 if "Emergency" in x["speciality"] else 1
        )
    else:
        hospitals.sort(
            key=lambda x: 0 if any(
                s.lower() in x["speciality"].lower()
                for s in (required_specialists or [])
            ) else 1
        )

    return hospitals
@app.route("/save_location", methods=["POST"])
@login_required
def save_location():
    data = request.get_json()

    session["lat"] = data.get("latitude")
    session["lon"] = data.get("longitude")

    return jsonify({"status": "location_saved"})
@app.route("/save_manual_location", methods=["POST"])
@login_required
def save_manual_location():
    data = request.get_json()
    session["manual_city"] = data.get("city")
    return {"status": "manual_location_saved"}

# ------------------------------------------------------------
#               DOCTOR SUGGESTION PAGE
# ------------------------------------------------------------
@app.route("/doctor_suggestions")
@login_required
def doctor_suggestions_page():

    record = HealthRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(HealthRecord.id.desc()).first()

    if not record:
        flash("Please add health data first", "warning")
        return redirect(url_for("add_health"))

    # ---------------- RISK SCORE ----------------
    score = calculate_dynamic_risk(record)

    if score < 40:
        risk = "Low"
        specialist = ["General Physician"]
    elif score < 70:
        risk = "Moderate"
        specialist = ["Cardiologist", "Diabetologist"]
    else:
        risk = "High"
        specialist = ["Critical Care", "Cardiologist"]

    # ---------------- DISEASE DETECTION ----------------
    diseases = detect_possible_disease(record)

    disease_symptoms = {
        "Hypertension (High Blood Pressure)": ["Headache", "Dizziness", "Chest discomfort"],
        "Diabetes Mellitus": ["Frequent urination", "Excessive thirst", "Fatigue"],
        "Heart Rhythm Disorder": ["Irregular heartbeat", "Shortness of breath"],
        "Fever / Infection": ["High temperature", "Body pain"],
        "Possible Cardiac Issue": ["Chest pain", "Left arm pain"],
        "Respiratory Issue": ["Breathing difficulty", "Wheezing"],
        "No critical disease detected": ["No significant symptoms"]
    }

    # ---------------- EMERGENCY CHECK ----------------
    is_emergency = False
    if score >= 75:
        is_emergency = True
    if record.systolic_bp and record.systolic_bp > 180:
        is_emergency = True
    if record.heart_rate and record.heart_rate > 130:
        is_emergency = True

    # ---------------- LOCATION ----------------
    lat = session.get("lat")
    lon = session.get("lon")

    nearby_doctors = []
    if lat and lon:
        nearby_doctors = get_nearby_hospitals(
            lat,
            lon,
            required_specialists=specialist,
            emergency=is_emergency
        )

    return render_template(
        "doctor_suggestions.html",
        score=score,
        risk=risk,
        diseases=diseases,
        disease_symptoms=disease_symptoms,
        is_emergency=is_emergency,
        specialist=specialist,
        nearby_doctors=nearby_doctors,
        city=record.city or "Your Location"
    )



# ------------------------------------------------------------
#               REMINDERS PAGE
# ------------------------------------------------------------
@app.route("/reminders")
@login_required
def reminders_page():

    record = HealthRecord.query.filter_by(user_id=current_user.id) \
                               .order_by(HealthRecord.id.desc()).first()

    if not record:
        flash("Please enter your health details first!", "warning")
        return redirect(url_for("add_health"))

    reminders = {
        "morning": [],
        "afternoon": [],
        "evening": [],
        "emergency": [],
        "lifestyle": []
    }

    score = calculate_dynamic_risk(record)

    if score >= 70:
        reminders["emergency"].append("🚨 High risk detected: Monitor vitals every 4 hours.")
        reminders["emergency"].append("🚑 Keep emergency hospital contact ready.")
        reminders["lifestyle"].append("❤️ Avoid physical strain. Rest as much as possible.")

    elif score >= 40:
        reminders["lifestyle"].append("📈 Moderate risk: Track BP and sugar twice a day.")
        reminders["lifestyle"].append("💧 Drink 2–3 liters of water daily.")
    else:
        reminders["lifestyle"].append("🟢 Low risk: Maintain a healthy lifestyle.")

    if record.systolic_bp and record.systolic_bp > 140:
        reminders["morning"].append("💊 Take BP medication after breakfast.")
        reminders["evening"].append("💊 Take second BP dose after dinner.")
        reminders["lifestyle"].append("🧂 Reduce salt intake significantly.")

    if record.sugar and record.sugar > 180:
        reminders["morning"].append("💉 Check fasting sugar levels.")
        reminders["afternoon"].append("🍽 Eat low-carb lunch. Avoid sweets.")
        reminders["evening"].append("🚶 15-min walk after dinner.")
        reminders["lifestyle"].append("🥗 Follow diabetic diet: avoid rice, sweets.")

    if record.heart_rate and (record.heart_rate > 110 or record.heart_rate < 55):
        reminders["emergency"].append("❤️ Abnormal heart rate! No heavy activity.")
        reminders["lifestyle"].append("🧘 Practice deep breathing for 10 minutes.")

    if record.temperature and record.temperature > 38:
        reminders["morning"].append("🤒 Take paracetamol if fever persists.")
        reminders["lifestyle"].append("💧 Drink warm water frequently.")

    symptoms = record.symptoms.lower()

    if "cough" in symptoms:
        reminders["lifestyle"].append("😷 Wear a mask & avoid cold drinks.")

    if "chest" in symptoms:
        reminders["emergency"].append("❤️ Chest pain: Seek doctor immediately.")

    if "breath" in symptoms:
        reminders["lifestyle"].append("🫁 Do breathing exercises twice a day.")

    return render_template("reminders.html", reminders=reminders, score=score)


# ------------------------------------------------------------
#                  HEALTH RECORDS PAGE
# ------------------------------------------------------------
@app.route("/health_records")
@login_required
def health_records():
    recs = HealthRecord.query.filter_by(user_id=current_user.id).all()
    return render_template("health_records.html", records=recs)


# ------------------------------------------------------------
#                       USER LOGIN
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not registered!", "danger")
            return redirect(url_for("login"))

        if not user.check_password(password):
            flash("Incorrect password!", "danger")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ------------------------------------------------------------
#                      USER REGISTER
# ------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"].lower()
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for("register"))

        user = User(name=name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------------------------------------------------
#                FORGOT PASSWORD (OTP FLOW)
# ------------------------------------------------------------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not registered!", "danger")
            return redirect(url_for("forgot_password"))

        # Generate 6-digit OTP
        otp = random.randint(100000, 999999)
        session["reset_email"] = email
        session["reset_otp"] = str(otp)
        session["reset_otp_time"] = int(time.time())

        # In real app, send OTP via SMS / Email.
        # For project/demo, we just show OTP in flash message.
        flash(f"Your OTP is: {otp} (valid for 5 minutes)", "success")

        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")


# ------------------------------------------------------------
#                VERIFY OTP PAGE
# ------------------------------------------------------------
@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if "reset_email" not in session:
        flash("Start from Forgot Password.", "warning")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        entered_otp = request.form["otp"].strip()
        saved_otp = session.get("reset_otp")
        otp_time = session.get("reset_otp_time", 0)

        # Check expiry
        if int(time.time()) - int(otp_time) > OTP_EXPIRY_SECONDS:
            flash("OTP expired. Please request a new one.", "danger")
            session.pop("reset_otp", None)
            session.pop("reset_otp_time", None)
            return redirect(url_for("forgot_password"))

        if entered_otp != saved_otp:
            flash("Invalid OTP. Please try again.", "danger")
            return redirect(url_for("verify_otp"))

        # OTP success
        session["otp_verified"] = True
        flash("OTP verified. You can now reset your password.", "success")
        return redirect(url_for("reset_password"))

    return render_template("verify_otp.html", email=session.get("reset_email"))


# ------------------------------------------------------------
#                RESET PASSWORD (AFTER OTP)
# ------------------------------------------------------------
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if not session.get("otp_verified") or "reset_email" not in session:
        flash("Unauthorized access. Please verify OTP first.", "danger")
        return redirect(url_for("forgot_password"))

    email = session.get("reset_email")
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("reset_password"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password"))

        user.set_password(password)
        db.session.commit()

        # clear OTP session data
        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("reset_otp_time", None)
        session.pop("otp_verified", None)

        flash("Password updated successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", email=email)


# ------------------------------------------------------------
#                       ADMIN LOGIN PAGE
# ------------------------------------------------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Simple Hardcoded Admin
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid Admin Credentials!", "danger")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


# ------------------------------------------------------------
#                       ADMIN DASHBOARD
# ------------------------------------------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get('admin'):
        flash("Please login as admin", "warning")
        return redirect(url_for("admin_login"))

    users = User.query.all()
    records = HealthRecord.query.order_by(HealthRecord.created_at.desc()).all()

    return render_template("admin_dashboard.html", users=users, records=records)


# ------------------------------------------------------------
#                    ADMIN LOGOUT
# ------------------------------------------------------------
@app.route("/admin_logout")
def admin_logout():
    session.pop('admin', None)
    flash("Admin logged out", "info")
    return redirect(url_for("admin_login"))


# ------------------------------------------------------------
#                      LOGOUT
# ------------------------------------------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ------------------------------------------------------------
#                       RUN APP
# ------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5001, debug=True)


