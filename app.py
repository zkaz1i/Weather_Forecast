import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

# force rebuild

import traceback
print("🔥 App is importing...")

try:
    print("🔧 Starting Flask setup...")
except Exception as e:
    print("❌ Import error:")
    traceback.print_exc()

print("App starts")



app = Flask(__name__, static_folder="static", static_url_path="/static")

from flask import send_file
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/static/<path:filename>")
def serve_videos(filename):
    path = os.path.join(BASE_DIR, "static", "videos", filename)
    return send_file(path, conditional=True)
    
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///weather.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to use that feature."

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    default_city = db.Column(db.String(120), nullable=True)
    use_celsius = db.Column(db.Boolean, default=True, nullable=False)
    use_24h_clock = db.Column(db.Boolean, default=False, nullable=False)
    favorites = db.relationship(
        "Favorite",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "city", name="uq_user_favorite_city"),)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def _temp_unit_label(use_celsius: bool) -> str:
    return "metric" if use_celsius else "imperial"


def _deg_suffix(use_celsius: bool) -> str:
    return "°C" if use_celsius else "°F"


def _wind_label(speed: float, use_celsius: bool) -> str:
    if use_celsius:
        return f"{round(speed * 3.6)} km/h"
    return f"{round(speed)} mph"


def _format_hour(dt: datetime, use_24h: bool) -> str:
    if use_24h:
        return dt.strftime("%H:%M")
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{dt.strftime('%M %p')}"


def _format_hour_from_api(
    hour_string: str,
    timezone_offset: int,
    use_24h: bool
) -> str:
    dt = datetime.strptime(
        hour_string,
        "%Y-%m-%d %H:%M:%S"
    ).replace(tzinfo=timezone.utc)

    local_dt = dt + timedelta(seconds=timezone_offset)

    return _format_hour(local_dt, use_24h)

def build_hourly(forecast_items: list, timezone_offset: int, use_24h: bool) -> list:
    hourly = []
    for item in forecast_items[:8]:
        hourly.append(
            {
                "time": _format_hour_from_api(item["dt_txt"], timezone_offset, use_24h),
                "temp": round(item["main"]["temp"]),
                "condition": item["weather"][0]["main"],
                "icon": item["weather"][0]["icon"],
            }
        )
    return hourly


def build_weekly(forecast_items: list) -> list:
    grouped = {}
    for item in forecast_items:
        day_key = item["dt_txt"].split(" ")[0]
        grouped.setdefault(day_key, []).append(item)

    weekly = []
    for day_key, items in list(grouped.items())[:7]:
        highs = [x["main"]["temp_max"] for x in items]
        lows = [x["main"]["temp_min"] for x in items]
        representative = min(
            items,
            key=lambda x: abs(
                datetime.strptime(x["dt_txt"], "%Y-%m-%d %H:%M:%S").hour - 12
            ),
        )
        weekly.append(
            {
                "day": datetime.strptime(day_key, "%Y-%m-%d").strftime("%a"),
                "high": round(max(highs)),
                "low": round(min(lows)),
                "condition": representative["weather"][0]["main"],
                "icon": representative["weather"][0]["icon"],
            }
        )
    return weekly


def fallback_weather(city: str, use_celsius: bool, use_24h: bool) -> dict:
    now = datetime.now()
    unit = _deg_suffix(use_celsius)
    hourly = []
    for i in range(8):
        hourly.append(
            {
                "time": _format_hour(now + timedelta(hours=i * 3), use_24h),
                "temp": 26 + (i % 3) if use_celsius else round((26 + (i % 3)) * 9 / 5 + 32),
                "condition": "Sunny",
                "icon": "01d",
            }
        )

    weekly = []
    for i in range(7):
        date = now + timedelta(days=i)
        hi = 30 + (i % 2) if use_celsius else round((30 + (i % 2)) * 9 / 5 + 32)
        lo = 22 + (i % 3) if use_celsius else round((22 + (i % 3)) * 9 / 5 + 32)
        weekly.append(
            {
                "day": date.strftime("%a"),
                "high": hi,
                "low": lo,
                "condition": "Clear",
                "icon": "01d",
            }
        )

    t, tmax, tmin = 27, 30, 23
    if not use_celsius:
        t = round(t * 9 / 5 + 32)
        tmax = round(tmax * 9 / 5 + 32)
        tmin = round(tmin * 9 / 5 + 32)

    return {
        "city": city.title(),
        "local_time": now.strftime("%H:%M") if use_24h else now.strftime("%I:%M %p"),
        "local_date": now.strftime("%d/%m/%Y"),
        "local_hour": now.hour,
        "temp": t,
        "temp_max": tmax,
        "temp_min": tmin,
        "temp_unit": unit,
        "condition": "Clear Sky",
        "icon": "01d",
        "hourly": hourly,
        "weekly": weekly,
        "info": {
            "uv": "5.2",
            "humidity": "62%",
            "wind": "11 km/h" if use_celsius else "7 mph",
            "feels_like": f"28 {unit}" if use_celsius else f"82 {unit}",
            "pressure": "1014 hPa",
            "visibility": "10 km",
        },
    }


def _weather_from_api(current: dict, forecast: dict, use_celsius: bool, use_24h: bool) -> dict:
    wind_speed = current["wind"]["speed"]
    unit = _deg_suffix(use_celsius)
    timezone_offset = current.get("timezone", 0)
    local_time = datetime.now(timezone.utc) + timedelta(seconds=timezone_offset)
    return {
        "city": current.get("name", "Unknown"),
        "local_time": local_time.strftime("%H:%M") if use_24h else local_time.strftime("%I:%M %p"),
        "local_date": local_time.strftime("%d/%m/%Y"),
        "local_hour": local_time.hour,
        "temp": round(current["main"]["temp"]),
        "temp_max": round(current["main"]["temp_max"]),
        "temp_min": round(current["main"]["temp_min"]),
        "temp_unit": unit,
        "condition": current["weather"][0]["description"].title(),
        "icon": current["weather"][0]["icon"],
        "hourly": build_hourly(forecast.get("list", []), timezone_offset, use_24h),
        "weekly": build_weekly(forecast.get("list", [])),
        "info": {
            "uv": "--",
            "humidity": f"{current['main']['humidity']}%",
            "wind": _wind_label(wind_speed, use_celsius),
            "feels_like": f"{round(current['main']['feels_like'])} {unit}",
            "pressure": f"{current['main']['pressure']} hPa",
            "visibility": f"{round(current.get('visibility', 10000) / 1000)} km",
        },
    }


def fetch_weather(city: str, use_celsius: bool, use_24h: bool) -> tuple[dict, str | None]:
    if not OPENWEATHER_API_KEY:
        return (
            fallback_weather(city, use_celsius, use_24h),
            "Missing API key. Showing placeholder weather.",
        )

    units = _temp_unit_label(use_celsius)
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": units}
    try:
        current_res = requests.get(CURRENT_WEATHER_URL, params=params, timeout=10)
        current_res.raise_for_status()
        current = current_res.json()

        forecast_res = requests.get(FORECAST_URL, params=params, timeout=10)
        forecast_res.raise_for_status()
        forecast = forecast_res.json()
    except requests.RequestException:
        return (
            fallback_weather(city, use_celsius, use_24h),
            "Weather service unavailable. Showing placeholder data.",
        )

    return _weather_from_api(current, forecast, use_celsius, use_24h), None


def fetch_weather_coords(
    lat: float, lon: float, use_celsius: bool, use_24h: bool
) -> tuple[dict, str | None]:
    if not OPENWEATHER_API_KEY:
        return (
            fallback_weather("Your location", use_celsius, use_24h),
            "Missing API key. Showing placeholder weather.",
        )

    units = _temp_unit_label(use_celsius)
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
    }
    try:
        current_res = requests.get(CURRENT_WEATHER_URL, params=params, timeout=10)
        current_res.raise_for_status()
        current = current_res.json()

        forecast_res = requests.get(FORECAST_URL, params=params, timeout=10)
        forecast_res.raise_for_status()
        forecast = forecast_res.json()
    except requests.RequestException:
        return (
            fallback_weather("Your location", use_celsius, use_24h),
            "Weather service unavailable. Showing placeholder data.",
        )

    return _weather_from_api(current, forecast, use_celsius, use_24h), None


def _user_prefs():
    if current_user.is_authenticated:
        return current_user.use_celsius, current_user.use_24h_clock
    return True, False


def _favorite_city_names() -> list[str]:
    if not current_user.is_authenticated:
        return []
    return [
        f.city
        for f in current_user.favorites.order_by(Favorite.city.asc()).all()
    ]


def _is_favorite(city_name: str) -> bool:
    if not current_user.is_authenticated or not city_name:
        return False
    return (
        current_user.favorites.filter(
            db.func.lower(Favorite.city) == city_name.strip().lower()
        ).first()
        is not None
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not email or "@" not in email:
            flash("Enter a valid email address.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != password2:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome!", "success")
            return redirect(url_for("index"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/api/favorites", methods=["POST"])
@login_required
def api_add_favorite():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    if not city:
        return jsonify({"ok": False, "error": "City is required."}), 400
    normalized = city.title()
    exists = (
        current_user.favorites.filter(
            db.func.lower(Favorite.city) == city.lower()
        ).first()
    )
    if exists:
        return jsonify({"ok": True, "favorites": _favorite_city_names()})
    db.session.add(Favorite(user_id=current_user.id, city=normalized))
    db.session.commit()
    return jsonify({"ok": True, "favorites": _favorite_city_names()})


@app.route("/api/favorites/<path:city_name>", methods=["DELETE"])
@login_required
def api_remove_favorite(city_name: str):
    fav = (
        current_user.favorites.filter(
            db.func.lower(Favorite.city) == city_name.strip().lower()
        ).first()
    )
    if fav:
        db.session.delete(fav)
        db.session.commit()
    return jsonify({"ok": True, "favorites": _favorite_city_names()})


@app.route("/api/preferences", methods=["POST"])
@login_required
def api_preferences():
    data = request.get_json(silent=True) or {}
    if "use_celsius" in data:
        current_user.use_celsius = bool(data["use_celsius"])
    if "use_24h_clock" in data:
        current_user.use_24h_clock = bool(data["use_24h_clock"])
    if "default_city" in data:
        dc = (data.get("default_city") or "").strip()
        current_user.default_city = dc if dc else None
    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "use_celsius": current_user.use_celsius,
            "use_24h_clock": current_user.use_24h_clock,
            "default_city": current_user.default_city or "",
        }
    )


@app.route("/", methods=["GET"])
def index():
    use_celsius, use_24h = _user_prefs()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")
    city_param = (request.args.get("city") or "").strip()

    weather = None
    alert = None
    active_city = ""

    if lat_raw and lon_raw:
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
            weather, alert = fetch_weather_coords(lat_f, lon_f, use_celsius, use_24h)
            active_city = weather["city"]
        except (TypeError, ValueError):
            active_city = (
                current_user.default_city.strip()
                if current_user.is_authenticated and current_user.default_city
                else "Bangalore"
            )
            weather, alert = fetch_weather(active_city, use_celsius, use_24h)
    elif city_param:
        active_city = city_param
        weather, alert = fetch_weather(city_param, use_celsius, use_24h)
    else:
        if current_user.is_authenticated and (current_user.default_city or "").strip():
            active_city = current_user.default_city.strip()
        else:
            active_city = "Bangalore"
        weather, alert = fetch_weather(active_city, use_celsius, use_24h)

    favorites = _favorite_city_names()
    is_fav = _is_favorite(weather["city"]) if weather else False

    default_city_val = (
        (current_user.default_city or "").strip()
        if current_user.is_authenticated
        else ""
    )

    return render_template(
        "index.html",
        weather=weather,
        city=active_city,
        alert=alert,
        favorites=favorites,
        is_favorite_city=is_fav,
        use_celsius=use_celsius,
        use_24h_clock=use_24h,
        default_city=default_city_val,
        favorites_json=json.dumps(favorites),
    )

@app.route("/debug-files")
def debug_files():
    import os
    return "<br>".join(os.listdir("static/videos"))

@app.route("/debug-file-size")
def debug_file_size():
    import os 
    path = os.path.join("static/videos", "clouds_day.mp4")
    return str(os.path.getsize(path))

@app.route("/debug-real-file")
def debug_real_file():
    import os
    path = os.path.join(os.getcwd(), "static/videos/clouds_day.mp4")
    return str(os.path.exists(path)) + " | " + str(os.path.getsize(path))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=port)