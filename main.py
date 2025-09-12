from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- Food Class & Data ----------------
class Food:
    def __init__(self, name, type, calories, protein, fat, carbs, description):
        self.name = name
        self.type = type
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.description = description

foods = [
    # Junk Foods
    Food("Burger", "junk", 500, 25, 30, 40, "A classic fast-food item with a juicy patty, cheese, and sauces."),
    Food("Pizza", "junk", 600, 20, 35, 50, "Cheesy and savory with high calories, often topped with processed meat."),
    Food("French Fries", "junk", 400, 5, 20, 50, "Crispy potato fries deep-fried in oil, very high in fat."),
    Food("Fried Chicken", "junk", 700, 30, 40, 45, "Crispy fried chicken with crunchy coating and lots of calories."),
    Food("Soft Drink (Cola)", "junk", 150, 0, 0, 39, "Sugary carbonated drink, no nutrition, only empty calories."),
    Food("Ice Cream", "junk", 300, 5, 15, 35, "Cold dessert with sugar and fat, very tempting but unhealthy."),
    Food("Hot Dog", "junk", 450, 15, 25, 35, "Processed meat sausage in bread, rich in sodium and fats."),
    Food("Donut", "junk", 320, 4, 18, 37, "Deep-fried sweet snack loaded with sugar and refined carbs."),
    Food("Nachos", "junk", 350, 6, 20, 40, "Crispy chips with cheese and toppings, high in fats."),
    Food("Chocolate Bar", "junk", 250, 3, 12, 30, "Sweet treat with sugar and fat, offers quick energy."),
    Food("Chips", "junk", 200, 2, 15, 20, "Crispy packaged snack, high in salt and oil."),
    Food("Cake", "junk", 450, 6, 20, 55, "Sweet baked dessert, high in sugar and butter."),
    Food("Milkshake", "junk", 380, 10, 15, 50, "Sweet blended drink with ice cream, milk, and syrup."),
    Food("Popcorn (Butter)", "junk", 300, 5, 20, 35, "Movie snack with added butter and salt, not healthy."),
    
    # Healthy Foods
    Food("Salad", "healthy", 150, 5, 5, 20, "A mix of fresh vegetables, rich in vitamins and fiber."),
    Food("Grilled Chicken", "healthy", 250, 35, 5, 10, "Lean protein source, cooked without excess oil."),
    Food("Apple", "healthy", 95, 0.5, 0.3, 25, "A nutritious fruit rich in fiber and antioxidants."),
    Food("Banana", "healthy", 105, 1.3, 0.3, 27, "Good source of potassium and quick energy."),
    Food("Brown Rice", "healthy", 215, 5, 1.8, 45, "Whole grain rich in fiber and slow-digesting carbs."),
    Food("Oatmeal", "healthy", 150, 6, 3, 27, "Great breakfast option with fiber and protein."),
    Food("Greek Yogurt", "healthy", 120, 12, 4, 9, "High protein dairy product, good for gut health."),
    Food("Almonds (10 pcs)", "healthy", 70, 3, 6, 2, "Nuts rich in healthy fats and vitamin E."),
    Food("Carrots", "healthy", 50, 1, 0.2, 12, "Crunchy vegetable rich in Vitamin A for good vision."),
    Food("Spinach", "healthy", 25, 3, 0.5, 4, "Leafy green packed with iron and vitamins."),
    Food("Broccoli", "healthy", 55, 4, 0.5, 11, "Rich in antioxidants and fiber, great for immunity."),
    Food("Strawberries", "healthy", 60, 1, 0.5, 15, "Sweet fruit packed with vitamin C and antioxidants."),
    Food("Fish (Salmon)", "healthy", 220, 25, 13, 0, "High in protein and omega-3 fatty acids."),
    Food("Eggs (Boiled)", "healthy", 78, 6, 5, 1, "Excellent protein-rich food with healthy fats.")
]

users = {}

# ---------------- Routes ----------------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    phone = data.get("phone")
    password = data.get("password")

    # Accept any phone and password
    if phone and password:
        session["user"] = phone
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Please enter phone number and password"})

# Registration page
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    password = data.get("password")

    if not (name and phone and password):
        return jsonify({"success": False, "message": "All fields are required"})

    if phone in users:
        return jsonify({"success": False, "message": "Phone number already registered"})

    users[phone] = {"name": name, "password": password}
    session["user"] = phone
    return jsonify({"success": True})

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

@app.route("/api/nutrition")
def api_nutrition():
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    return jsonify({"success": True, "foods": [food.__dict__ for food in foods]})

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True)
