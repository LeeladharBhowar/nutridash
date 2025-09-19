from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3, os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- Database Setup ----------------
DB_NAME = "users.db"

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

init_db()

# ---------------- Notifications DB ----------------
def init_notifications_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            user_id INTEGER PRIMARY KEY,
            email_notif INTEGER DEFAULT 1,
            push_notif INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_notifications_db()

# ---------------- Flask-Login Setup ----------------
login_manager = LoginManager()
login_manager.login_view = "login_page"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, name, phone):
        self.id = id
        self.username = name
        self.phone = phone
        self.email = f"{phone}@example.com"  # Dummy email

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, phone FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

# ---------------- Food Class ----------------
class Food:
    def __init__(self, name, type, calories, protein, fat, carbs, description):
        self.name = name
        self.type = type
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.description = description

# ---------------- Food Data ----------------
foods = [
    Food("Burger", "junk", 500, 25, 30, 40, "A classic fast-food item with a juicy patty, cheese, and sauces."),
    Food("Pizza", "junk", 600, 20, 35, 50, "Cheesy and savory with high calories, often topped with processed meat."),
    Food("French Fries", "junk", 400, 5, 20, 50, "Crispy potato fries deep-fried in oil, very high in fat."),
    Food("Fried Chicken", "junk", 700, 30, 40, 45, "Crispy fried chicken with crunchy coating and lots of calories."),
    Food("Hot Dog", "junk", 450, 15, 25, 35, "Processed meat sausage in bread, rich in sodium and fats."),
    Food("Donut", "junk", 320, 4, 18, 37, "Deep-fried sweet snack loaded with sugar and refined carbs."),
    Food("Salad", "healthy", 150, 5, 5, 20, "A mix of fresh vegetables, rich in vitamins and fiber."),
    Food("Grilled Chicken", "healthy", 250, 35, 5, 10, "Lean protein source, cooked without excess oil."),
    Food("Apple", "healthy", 95, 0.5, 0.3, 25, "A nutritious fruit rich in fiber and antioxidants."),
    Food("Banana", "healthy", 105, 1.3, 0.3, 27, "Good source of potassium and quick energy."),
    Food("Brown Rice", "healthy", 215, 5, 1.8, 45, "Whole grain rich in fiber and slow-digesting carbs."),
    Food("Oatmeal", "healthy", 150, 6, 3, 27, "Great breakfast option with fiber and protein."),
    Food("Greek Yogurt", "dairy", 120, 12, 4, 9, "High protein dairy product, good for gut health."),
    Food("Milk", "dairy", 150, 8, 5, 12, "Rich source of calcium and protein for strong bones."),
    Food("Cheese", "dairy", 110, 7, 9, 1, "Dairy product rich in calcium and protein."),
    Food("Paneer", "dairy", 265, 18, 20, 1, "Fresh Indian cottage cheese, high in protein and fats."),
    Food("Butter", "dairy", 72, 0, 8, 0, "Rich in fat, commonly used for cooking."),
    Food("Curd", "dairy", 61, 3, 3, 4, "Fermented dairy product good for digestion."),
    Food("Ice Cream", "frozen", 300, 5, 15, 35, "Cold dessert with sugar and fat, very tempting but unhealthy."),
    Food("Milkshake", "frozen", 380, 10, 15, 50, "Sweet blended drink with ice cream, milk, and syrup."),
    Food("Soft Drink", "frozen", 150, 0, 0, 39, "Sugary carbonated drink, no nutrition, only empty calories."),
    Food("Popcorn", "frozen", 300, 5, 20, 35, "Movie snack with added butter and salt, not healthy."),
    Food("Frozen Pizza", "frozen", 550, 22, 28, 50, "Pre-made frozen pizza, high in calories and fats."),
    Food("Frozen French Fries", "frozen", 400, 5, 22, 48, "Packaged frozen fries, quick to cook but unhealthy.")
]


# ---------------- Helper Functions ----------------
def get_user(phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, phone, password FROM users WHERE phone = ?", (phone,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(name, phone, password):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (name, phone, password) VALUES (?, ?, ?)", (name, phone, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# ---------------- Routes ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET"])
def login_page():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    phone = data.get("phone")
    password = data.get("password")
    user = get_user(phone)
    if user and user[3] == password:
        session["user"] = user[1].strip()
        user_obj = User(user[0], user[1], user[2])
        login_user(user_obj)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid phone or password"})

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    password = data.get("password")
    if get_user(phone):
        return jsonify({"success": False, "message": "Phone already registered"})
    if add_user(name, phone, password):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Registration failed"})

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", username=session["user"], foods=foods)

@app.route("/food-analysis")
def food_analysis():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("food_analysis.html", username=session["user"], foods=foods)

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    filepath = os.path.join("static", "uploads", file.filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    result = {
        "verdict": "Good",
        "ingredients": ["Oats", "Almonds", "Honey"],
        "nutrition": {"Calories": "200 kcal", "Protein": "5g", "Fat": "2g"}
    }
    return jsonify(result)

@app.route("/reports")
def reports():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("reports.html", username=session["user"], foods=foods)



# ================= Food Data for Tracker =================

staple_foods = [
    {"name":"Chapati (40g)", "calories":120, "protein":3, "carbs":25, "fat":0.4, "sugar":0.2, "fiber":3},
    {"name":"Rice (1 cup)", "calories":200, "protein":4, "carbs":45, "fat":0.4, "sugar":0.1, "fiber":0.6},
    {"name":"Brown Rice (1 cup)", "calories":215, "protein":5, "carbs":45, "fat":1.8, "sugar":0.7, "fiber":3.5},
    {"name":"Paratha (1, with oil)", "calories":220, "protein":4, "carbs":36, "fat":8, "sugar":1.5, "fiber":3},
    {"name":"Poha (1 cup cooked)", "calories":180, "protein":4, "carbs":30, "fat":5, "sugar":2, "fiber":2},
    {"name":"Upma (1 cup)", "calories":200, "protein":6, "carbs":32, "fat":6, "sugar":2, "fiber":3},
    {"name":"Idli (2 pcs)", "calories":150, "protein":4, "carbs":30, "fat":1, "sugar":0.5, "fiber":2},
    {"name":"Dosa (1 medium)", "calories":170, "protein":3.5, "carbs":35, "fat":2, "sugar":0.5, "fiber":2},
]

pulses_foods = [
    {"name":"Dal (1 cup)", "calories":180, "protein":12, "carbs":28, "fat":3, "sugar":1, "fiber":7},
    {"name":"Chana (100g)", "calories":160, "protein":9, "carbs":27, "fat":3, "sugar":4, "fiber":8},
    {"name":"Rajma (100g)", "calories":140, "protein":9, "carbs":23, "fat":0.5, "sugar":1, "fiber":6},
    {"name":"Soybean (100g)", "calories":170, "protein":16, "carbs":15, "fat":9, "sugar":3, "fiber":6},
    {"name":"Green Moong (100g)", "calories":105, "protein":7, "carbs":19, "fat":0.4, "sugar":2, "fiber":7},
]

veg_foods = [
    {"name":"Spinach (100g)", "calories":40, "protein":5, "carbs":7, "fat":0.5, "sugar":1, "fiber":4},
    {"name":"Ladyfinger (100g)", "calories":33, "protein":2, "carbs":7, "fat":0.2, "sugar":1.5, "fiber":3},
    {"name":"Brinjal (100g)", "calories":35, "protein":1, "carbs":8, "fat":0.2, "sugar":3, "fiber":2.5},
    {"name":"Carrot (100g)", "calories":25, "protein":0.5, "carbs":6, "fat":0.1, "sugar":3, "fiber":2},
    {"name":"Tomato (100g)", "calories":22, "protein":1, "carbs":5, "fat":0.2, "sugar":3, "fiber":1.5},
    {"name":"Potato (boiled, medium)", "calories":130, "protein":3, "carbs":30, "fat":0.2, "sugar":1.5, "fiber":3},
    {"name":"Onion (100g)", "calories":40, "protein":1.1, "carbs":9, "fat":0.1, "sugar":4.7, "fiber":1.5},
]

fruits_foods = [
    {"name":"Banana (1 medium)", "calories":105, "protein":1.3, "carbs":27, "fat":0.3, "sugar":14, "fiber":3},
    {"name":"Apple (1 medium)", "calories":95, "protein":0.5, "carbs":25, "fat":0.3, "sugar":19, "fiber":4},
    {"name":"Orange (1 medium)", "calories":62, "protein":1.2, "carbs":15, "fat":0.2, "sugar":12, "fiber":3},
    {"name":"Mango (1 medium)", "calories":150, "protein":1, "carbs":38, "fat":0.5, "sugar":32, "fiber":3},
    {"name":"Grapes (1 cup)", "calories":100, "protein":1, "carbs":27, "fat":0.3, "sugar":23, "fiber":1},
    {"name":"Watermelon (1 cup)", "calories":46, "protein":1, "carbs":12, "fat":0.2, "sugar":9, "fiber":0.5},
    {"name":"Papaya (1 cup)", "calories":60, "protein":1, "carbs":16, "fat":0.3, "sugar":9, "fiber":3},
]

dairy_foods = [
    {"name":"Milk (1 cup)", "calories":150, "protein":8, "carbs":12, "fat":8, "sugar":12, "fiber":0},
    {"name":"Curd (100g)", "calories":98, "protein":11, "carbs":4, "fat":4, "sugar":3, "fiber":0},
    {"name":"Paneer (100g)", "calories":265, "protein":18, "carbs":6, "fat":20, "sugar":3, "fiber":0},
    {"name":"Egg (1 large)", "calories":70, "protein":6, "carbs":0.6, "fat":5, "sugar":0.2, "fiber":0},
    {"name":"Chicken (100g)", "calories":165, "protein":31, "carbs":0, "fat":3.6, "sugar":0, "fiber":0},
    {"name":"Fish (100g)", "calories":200, "protein":22, "carbs":0, "fat":12, "sugar":0, "fiber":0},
    {"name":"Almonds (10 pcs)", "calories":70, "protein":2.5, "carbs":2.5, "fat":6, "sugar":0.5, "fiber":2},
    {"name":"Peanuts (30g)", "calories":160, "protein":7, "carbs":6, "fat":14, "sugar":1.5, "fiber":2},
]

snacks_foods = [
    {"name":"Burger (1 medium)", "calories":400, "protein":17.5, "carbs":45, "fat":20, "sugar":8.5, "fiber":3},
    {"name":"Pizza (1 slice)", "calories":315, "protein":12, "carbs":34, "fat":11, "sugar":5, "fiber":2},
    {"name":"Samosa (1 medium)", "calories":250, "protein":4, "carbs":30, "fat":15, "sugar":2, "fiber":2},
    {"name":"Pakora (100g)", "calories":300, "protein":8, "carbs":28, "fat":18, "sugar":3, "fiber":3},
    {"name":"Chips (30g)", "calories":160, "protein":2, "carbs":15, "fat":10, "sugar":0.5, "fiber":1},
    {"name":"Chocolate (40g)", "calories":210, "protein":2, "carbs":24, "fat":12, "sugar":20, "fiber":2},
    {"name":"Ice Cream (100g)", "calories":200, "protein":4, "carbs":25, "fat":10, "sugar":20, "fiber":0},
]

drinks_foods = [
    {"name":"Tea (1 cup)", "calories":70, "protein":2, "carbs":10, "fat":2, "sugar":8, "fiber":0},
    {"name":"Coffee (1 cup)", "calories":80, "protein":2, "carbs":12, "fat":2, "sugar":9, "fiber":0},
    {"name":"Cold Drink (330ml)", "calories":140, "protein":0, "carbs":35, "fat":0, "sugar":35, "fiber":0},
    {"name":"Soft Drink (500ml)", "calories":210, "protein":0, "carbs":52, "fat":0, "sugar":52, "fiber":0},
    {"name":"Energy Drink (250ml)", "calories":110, "protein":1, "carbs":28, "fat":0, "sugar":27, "fiber":0},
    {"name":"Fresh Lemon Water (200ml)", "calories":40, "protein":0, "carbs":10, "fat":0, "sugar":9, "fiber":0},
    {"name":"Coconut Water (200ml)", "calories":45, "protein":0.5, "carbs":11, "fat":0.5, "sugar":9, "fiber":1},
]

@app.route("/tracker")
def tracker():
    if "user" not in session:
        return redirect(url_for("login_page"))

    # Load foods from database (replace this with your actual DB query if you have a foods table)
    # For now, using the static lists
    foods_by_category = {
        "Staple": staple_foods,
        "Pulses": pulses_foods,
        "Vegetables": veg_foods,
        "Fruits": fruits_foods,
        "Dairy": dairy_foods,
        "Snacks": snacks_foods,
        "Drinks": drinks_foods
    }

    return render_template("tracker.html", foods_by_category=foods_by_category, username=session["user"])

# ---------------- SETTINGS PAGE ----------------
@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("settings.html", username=session["user"])


# ✅ Update Password
@app.route("/update-password", methods=["POST"])
def update_password():
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    current = data.get("current")
    new_pass = data.get("new")
    username = session["user"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE name=?", (username,))
    db_pass = c.fetchone()[0]

    if db_pass != current:
        conn.close()
        return jsonify({"success": False, "message": "Current password incorrect"})

    c.execute("UPDATE users SET password=? WHERE name=?", (new_pass, username))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Password updated successfully"})


# ✅ Update Theme Preference
@app.route("/update-theme", methods=["POST"])
def update_theme():
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    theme = data.get("theme")  # "light" or "dark"
    username = session["user"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET theme=? WHERE name=?", (theme, username))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Theme updated to {theme}"})


# ✅ Get Theme Preference
@app.route("/get-theme", methods=["GET"])
def get_theme():
    if "user" not in session:
        return jsonify({"theme": "light"})  # default light

    username = session["user"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT theme FROM users WHERE name=?", (username,))
    row = c.fetchone()
    conn.close()

    theme = row[0] if row and row[0] else "light"
    return jsonify({"theme": theme})


@app.route("/logout")
def logout():
    session.pop("user", None)
    logout_user()
    return redirect(url_for("login_page"))


# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True)



