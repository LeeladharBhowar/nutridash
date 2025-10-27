from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3, os
from datetime import datetime
import pytesseract
import cv2
import re
from PIL import Image
import json 
from google import genai 
from google.genai.errors import APIError 

# For demonstration, manually providing the API key from the .env file content
GEMINI_API_KEY = "AIzaSyDZI9rYRBAmqs9d-iIZ9FLZGF_RxbLfvnY"

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Tesseract/OCR Setup ---
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set tesseract path (update this if needed)
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception as e:
    print(f"Warning: Tesseract path might be incorrect or missing. OCR will fall back to RegEx or fail. Error: {e}")

# --- Gemini Client Setup ---
client = None
try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        print("GEMINI API KEY not set. AI analysis will fall back to Tesseract/RegEx.")
except Exception as e:
    client = None
    print(f"Error initializing Gemini client: {e}. AI analysis will fall back to Tesseract/RegEx.")


# ---------------- Database Setup ----------------
DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT theme, weight, health_goal FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS users")
        c.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                theme TEXT DEFAULT 'light',
                weight REAL DEFAULT 70.0,
                health_goal TEXT DEFAULT 'maintain'
            )
        """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logged_meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
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

init_db()

# ---------------- Flask-Login Setup ----------------
login_manager = LoginManager()
login_manager.login_view = "login_page"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, name, phone):
        self.id = id
        self.username = name
        self.phone = phone
        self.email = f"{phone}@example.com"

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

# ---------------- Food Data ----------------
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

staple_foods = [{"name":"Chapati (40g)", "calories":120, "protein":3, "carbs":25, "fat":0.4, "sugar":0.2, "fiber":3},] 
pulses_foods = [{"name":"Dal (1 cup)", "calories":180, "protein":12, "carbs":28, "fat":3, "sugar":1, "fiber":7},]
veg_foods = [{"name":"Spinach (100g)", "calories":40, "protein":5, "carbs":7, "fat":0.5, "sugar":1, "fiber":4},] 
fruits_foods = [{"name":"Banana (1 medium)", "calories":105, "protein":1.3, "carbs":27, "fat":0.3, "sugar":14, "fiber":3},]
dairy_foods = [{"name":"Milk (1 cup)", "calories":150, "protein":8, "carbs":12, "fat":8, "sugar":12, "fiber":0},]
snacks_foods = [{"name":"Burger (1 medium)", "calories":400, "protein":17.5, "carbs":45, "fat":20, "sugar":8.5, "fiber":3},]
drinks_foods = [{"name":"Tea (1 cup)", "calories":70, "protein":2, "carbs":10, "fat":2, "sugar":8, "fiber":0},]


# ---------------- OCR & ANALYSIS HELPER FUNCTIONS (ADVANCED) ----------------

def extract_text(image_path):
    """Extracts raw text from an image using Tesseract (used for fallback or raw display)."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return "OCR_ERROR_FILE_READ" 
        
        # Enhanced preprocessing for better Tesseract results
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5) # Larger blur for better text aggregation
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='eng')
        return text
    except Exception as e:
        print(f"OCR Error during extraction: {e}")
        return f"OCR_ERROR_EXTRACTION_FAILED: {e}"

def analyze_food_health(text):
    """Analyzes Tesseract-extracted text for key nutritional values and calculates a score (Fallback)."""
    
    if text.startswith("OCR_ERROR_"):
        return {
            "Energy": 0, "Protein": 0, "Total Carbohydrates": 0, "Dietary Fiber": 0, "Sugars": 0, 
            "Added Sugar": 0, "Total Fat": 0, "Saturated Fat": 0, "Trans Fat": 0, "Sodium": 0, "Cholesterol": 0,
            "score": 0.0, 
            "level": "Error ❌",
            "risk_score": "N/A", 
            "ingredients_risk": [] 
        }

    # Enhanced RegEx logic to find key metrics and default to 0
    def find_nutrient(pattern):
        # Look for the pattern, then search for the first number (int or float) after the match
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
             # Search for number (with optional decimal) following the match, up to 15 characters later
             num_match = re.search(r'(\d+\.?\d*)', text[match.end():match.end()+15], re.IGNORECASE)
             if num_match:
                 try:
                     return float(num_match.group(1))
                 except ValueError:
                     return 0
        return 0

    results = {
        "Energy": find_nutrient(r'calories|energy\s*(\d+)'), # kcal
        "Protein": find_nutrient(r'protein\s*(\d+)'), # g
        "Total Carbohydrates": find_nutrient(r'carbohydrate|carbs\s*(\d+)'), # g
        "Dietary Fiber": find_nutrient(r'fiber\s*(\d+)'), # g
        "Sugars": find_nutrient(r'sugars?\s*(\d+)'), # g
        "Added Sugar": find_nutrient(r'added\s*sugar\s*(\d+)'), # g
        "Total Fat": find_nutrient(r'total\s*fat\s*(\d+)'), # g
        "Saturated Fat": find_nutrient(r'saturated\s*fat\s*(\d+)'), # g
        "Trans Fat": find_nutrient(r'trans\s*fat\s*(\d+)'), # g
        "Cholesterol": find_nutrient(r'cholesterol\s*(\d+)'), # mg
        "Sodium": find_nutrient(r'sodium\s*(\d+)'), # mg
    }
    
    # Advanced Scoring Logic (Fallback)
    c = results.get("Energy", 0)
    p = results.get("Protein", 0)
    sf = results.get("Saturated Fat", 0)
    asg = results.get("Added Sugar", 0)
    df = results.get("Dietary Fiber", 0)
    sod = results.get("Sodium", 0) / 1000 # Convert mg to rough g for scoring

    score = 100.0
    score -= (c * 0.05)      # Energy penalty
    score -= (sf * 3.0)      # High Sat Fat penalty
    score -= (asg * 5.0)     # Very High Added Sugar penalty
    score -= (sod * 2.0)     # Sodium penalty
    score += (p * 2.5)       # High Protein reward
    score += (df * 1.5)      # Fiber reward

    score = max(0.0, min(100.0, score))

    level = "Healthy 🟢" if score >= 70 else ("Moderate 🟡" if score >= 40 else "Unhealthy 🔴")
    
    for k, v in results.items():
        results[k] = round(v, 2)
        
    return {
        **results,
        "score": round(score, 2), 
        "level": level,
        "risk_score": "Tesseract Fallback",
        "ingredients_risk": ["Tesseract was used for macro extraction (less reliable)."]
    }

def gemini_ingredient_risk_analysis(image_path):
    """
    Uses Gemini to analyze the ingredient list from the image for risks and benefits.
    """
    global client
    if not client:
        return {"risk_score": "N/A", "ingredients_risk": ["Gemini client not available."]}
    
    INGREDIENT_RISK_SCHEMA = {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "description": "Overall risk level: 'Low', 'Medium', or 'High'."},
            "ingredients_flagged": {
                "type": "array",
                "description": "List of 3-5 specific ingredients flagged as high risk (e.g., 'hydrogenated oils') or high benefit (e.g., 'whole grains').",
                "items": {"type": "string"}
            }
        },
        "required": ["risk_level", "ingredients_flagged"]
    }

    prompt = (
        "Analyze the ingredient list from the image. Identify the 3-5 most critical ingredients, "
        "labeling them as either (High Risk), (Medium Risk), or (High Benefit). "
        "Determine the overall Risk Level for the product based on these ingredients. "
        "Ignore common items like water, salt, and spices. Output must strictly follow the JSON schema."
    )

    try:
        img_part = Image.open(image_path)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img_part],
            config={
                'response_mime_type': 'application/json',
                'response_schema': INGREDIENT_RISK_SCHEMA
            }
        )
        
        data = json.loads(response.text)
        
        return {
            "risk_score": data.get('risk_level', 'N/A'),
            "ingredients_risk": data.get('ingredients_flagged', ['Failed to parse ingredients.'])
        }

    except APIError as e:
        print(f"Gemini Ingredient Risk API Error: {e}")
        return {"risk_score": "API Error", "ingredients_risk": [f"API Error: {str(e)}"]}
    except Exception as e:
        print(f"General Gemini Ingredient Error: {e}")
        return {"risk_score": "Error", "ingredients_risk": [f"General Error: {str(e)}"]}

def gemini_structured_analysis(image_path):
    """Uses the Gemini API in JSON mode with the image for structured, comprehensive data extraction."""
    global client
    if not client:
        return None, None 
    
    # --- CORRECT AND COMPREHENSIVE SCHEMA for all requested nutrients ---
    GEMINI_OUTPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "description": "A health verdict: 'Excellent', 'Good', 'Caution', or 'Poor'."},
            "Energy": {"type": "number", "description": "Energy/Calories (number only, in kcal)."},
            "Protein": {"type": "number", "description": "Protein in grams (number only)."},
            "Total Carbohydrates": {"type": "number", "description": "Total Carbohydrates in grams (number only)."},
            "Dietary Fiber": {"type": "number", "description": "Dietary Fiber in grams (number only)."},
            "Sugars": {"type": "number", "description": "Total Sugar in grams (number only)."},
            "Added Sugar": {"type": "number", "description": "Added Sugar in grams (number only, 0 if not listed)."},
            "Total Fat": {"type": "number", "description": "Total Fat in grams (number only)."},
            "Saturated Fat": {"type": "number", "description": "Saturated Fat in grams (number only)."},
            "Trans Fat": {"type": "number", "description": "Trans Fat in grams (number only, 0 if not listed)."},
            "Cholesterol": {"type": "number", "description": "Cholesterol in milligrams (number only, 0 if not listed)."},
            "Sodium": {"type": "number", "description": "Sodium in milligrams (number only)."},
            "suggestion": {"type": "string", "description": "A detailed, constructive suggestion (2-3 sentences) based on the label, offering alternatives or moderation advice."}
        },
        "required": ["verdict", "Energy", "Protein", "Total Carbohydrates", "Dietary Fiber", "Sugars", "Total Fat", "Saturated Fat", "Sodium", "suggestion"]
    }

    prompt = (
        "Analyze the uploaded nutrition facts label. Extract all key macronutrients, including 'Energy', 'Protein', 'Total Carbohydrates', 'Dietary Fiber', 'Sugars', 'Added Sugar', 'Total Fat', 'Saturated Fat', 'Trans Fat', 'Cholesterol', and 'Sodium'. "
        "If a specific nutrient is not explicitly listed, return 0 for its value. "
        "Provide a health verdict (Excellent, Good, Caution, or Poor) and a detailed, constructive suggestion (2-3 sentences) based on the values. "
        "The output must strictly follow the provided JSON schema."
    )

    try:
        img_part = Image.open(image_path)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img_part],
            config={
                'response_mime_type': 'application/json',
                'response_schema': GEMINI_OUTPUT_SCHEMA
            }
        )

        data = json.loads(response.text)
        
        # --- NEW SCORING LOGIC for enhanced accuracy ---
        c = data.get("Energy", 0)
        p = data.get("Protein", 0)
        sf = data.get("Saturated Fat", 0)
        asg = data.get("Added Sugar", 0)
        df = data.get("Dietary Fiber", 0)
        sod = data.get("Sodium", 0) / 1000 # Convert mg to rough g for scoring

        score = 100.0
        score -= (c * 0.05)      # Energy penalty
        score -= (sf * 3.0)      # High Sat Fat penalty
        score -= (asg * 5.0)     # Very High Added Sugar penalty
        score -= (sod * 2.0)     # Sodium penalty
        score += (p * 2.5)       # High Protein reward
        score += (df * 1.5)      # Fiber reward

        score = max(0.0, min(100.0, score))
        
        for k in data:
            if isinstance(data[k], (int, float)):
                data[k] = round(data[k], 2)
        
        structured_result = {
            "score": round(score, 2), 
            "level": f"{data['verdict']} ✨",
            "suggestion": data.pop('suggestion', 'No detailed suggestion provided.'),
            **data 
        }

        return structured_result.pop('suggestion'), structured_result 

    except APIError as e:
        return f"GEMINI_API_ERROR: {e}", None
    except Exception as e:
        return f"GEMINI_GENERAL_ERROR: {e}", None


def gemini_macro_suggestion(weight_kg, goal):
    """Uses the Gemini API to provide a personalized macro target and suggestion."""
    global client
    if not client:
        return json.dumps({"error": "Gemini client not available. Cannot generate advice."})

    if goal == 'maintain':
        goal_text = "maintaining their current weight."
        protein_g_per_kg = 1.2
    elif goal == 'lose':
        goal_text = "losing weight (in a calorie deficit)."
        protein_g_per_kg = 1.6
    elif goal == 'gain':
        goal_text = "gaining muscle mass (in a calorie surplus)."
        protein_g_per_kg = 2.0
    else:
        goal_text = "achieving a balanced diet."
        protein_g_per_kg = 1.2
        
    target_protein = round(weight_kg * protein_g_per_kg, 0)

    prompt = (
        f"The user weighs {weight_kg} kg and is aiming for {goal_text}. "
        f"Their target protein intake is {target_protein} grams per day. "
        "Provide a detailed, structured, daily nutrition intake goal (Calories, Protein, Carbs, Fat) "
        "and a brief, motivating tip (1-2 sentences). "
        "The output must strictly follow the provided JSON schema."
    )

    GEMINI_MACRO_SCHEMA = {
        "type": "object",
        "properties": {
            "daily_calories": {"type": "number"},
            "daily_protein_g": {"type": "number"},
            "daily_carbs_g": {"type": "number"},
            "daily_fat_g": {"type": "number"},
            "tip": {"type": "string"}
        },
        "required": ["daily_calories", "daily_protein_g", "daily_carbs_g", "daily_fat_g", "tip"]
    }

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config={
                'response_mime_type': 'application/json',
                'response_schema': GEMINI_MACRO_SCHEMA
            }
        )
        return response.text 
    
    except APIError as e:
        print(f"Gemini Suggestion API Error: {e}")
        return json.dumps({"error": "Failed to get AI advice due to API limits or error."})
    except Exception as e:
        print(f"General Gemini Suggestion Error: {e}")
        return json.dumps({"error": "Failed to generate structured advice."})


# ---------------- Helper Functions (Database/User) ----------------
def get_user_data(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT weight, health_goal FROM users WHERE name = ?", (username,))
    result = c.fetchone()
    conn.close()
    return {
        'weight': result[0] if result and result[0] is not None else 70.0,
        'goal': result[1] if result and result[1] else 'maintain'
    }

def get_all_foods():
    return staple_foods + pulses_foods + veg_foods + fruits_foods + dairy_foods + snacks_foods + drinks_foods

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


# ---------------- AUTH ROUTES ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
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
    
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth.html")

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


# ---------------- APPLICATION ROUTES (Organized Flow) ----------------

# 1. Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username, foods=foods)

# 2. Food Analysis (Input)
@app.route("/food-analysis")
@login_required
def food_analysis():
    # This route is now correct and separate from the result.html logic
    return render_template("food_analysis.html", username=current_user.username)

# 3. Analyze (Processing & Output)
@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    file = request.files.get("file")
    if not file or file.filename == '':
        return redirect(url_for("food_analysis"))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    result = None
    suggestion = None # Now holds the detailed suggestion from Gemini
    
    # 1. PRIMARY ANALYSIS (Macros + Suggestion)
    if client:
        suggestion, gemini_result = gemini_structured_analysis(filepath)
        if gemini_result:
            result = gemini_result
            print("Successfully analyzed macros using Gemini.")
            
    # 2. FALLBACK (If Gemini failed or was skipped)
    if not result:
        print("Falling back to Tesseract/RegEx analysis for macros.")
        raw_ocr_text = extract_text(filepath)
        result = analyze_food_health(raw_ocr_text)
        suggestion = "Tesseract/RegEx Fallback: Macro analysis succeeded, but detailed suggestion is limited. Aim for whole foods and moderation."
        if raw_ocr_text.startswith("OCR_ERROR_"):
             suggestion = "FATAL OCR ERROR: " + raw_ocr_text.replace("OCR_ERROR_", "")
    
    # 3. ADVANCED INGREDIENT RISK ANALYSIS
    risk_data = gemini_ingredient_risk_analysis(filepath)
    
    # 4. MERGE RESULTS
    if result and isinstance(result, dict):
        result.update(risk_data)
        
    if not result:
        result = {
            "Energy": 0, "Protein": 0, "Total Carbohydrates": 0, "Dietary Fiber": 0, "Sugars": 0, "Added Sugar": 0, 
            "Total Fat": 0, "Saturated Fat": 0, "Trans Fat": 0, "Cholesterol": 0, "Sodium": 0,
            "score": 0.0, "level": "Critical Error ❌", "risk_score": "N/A", "ingredients_risk": ["CRITICAL ERROR: Analysis failed to complete."]
        }
        suggestion = suggestion or "CRITICAL ERROR: Analysis could not complete."
        
    # IMPORTANT: The 'text' variable from the old structure is no longer used, only 'suggestion'
    return render_template(
        "result.html", 
        image=file.filename,
        result=result, 
        suggestion=suggestion
    )

# 4. Reports
@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html", username=current_user.username, foods=foods)

# 5. Settings
@app.route("/settings")
@login_required
def settings():
    user_data = get_user_data(current_user.username)
    return render_template("settings.html", 
                           username=current_user.username, 
                           current_weight=user_data['weight'],
                           current_goal=user_data['goal'])

@app.route("/api/suggest-macros", methods=["POST"])
@login_required
def suggest_macros():
    data = request.get_json()
    try:
        weight = float(data.get('weight'))
        goal = data.get('goal')
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input for weight or goal."}), 400

    if goal not in ['lose', 'maintain', 'gain']:
        return jsonify({"error": "Invalid goal selected."}), 400
        
    json_response = gemini_macro_suggestion(weight, goal)
    
    if isinstance(json_response, str) and "Gemini client not available" in json_response:
        return jsonify({"error": json_response}), 503
    
    return Response(json_response, mimetype='application/json')

@app.route("/update-theme", methods=["POST"])
@login_required
def update_theme():
    data = request.get_json()
    theme = data.get("theme")
    username = current_user.username

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET theme=? WHERE name=?", (theme, username))
    conn.commit()
    conn.close()

    # Crucial: Update the session variable so Flask templates (like the sidebar) update immediately
    session['theme'] = theme 
    
    return jsonify({"success": True, "message": f"Theme updated to {theme}"})

# 6. Tracker
@app.route("/tracker")
@login_required
def tracker():
    foods_by_category = {
        "Staple": staple_foods, "Pulses": pulses_foods, "Vegetables": veg_foods, "Fruits": fruits_foods, 
        "Dairy/Protein": dairy_foods, "Snacks": snacks_foods, "Drinks": drinks_foods
    }
    return render_template("tracker.html", foods_by_category=foods_by_category, username=current_user.username)

@app.route("/calculate_nutrition", methods=["POST"])
@login_required
def calculate_nutrition():
    data = request.get_json()
    selected_foods = data.get("foods", [])

    total_nutrition = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "sugar": 0.0, "fiber": 0.0,}
    food_lookup = {food["name"].lower(): food for food in get_all_foods()}
    user_data = get_user_data(current_user.username)

    for item in selected_foods:
        name = item.get("name", "").strip()
        try:
            quantity = float(item.get("quantity", 0))
        except ValueError:
            continue

        food_data = food_lookup.get(name.lower())

        if food_data and quantity > 0:
            for nutrient in total_nutrition.keys():
                try:
                    value = float(food_data.get(nutrient, 0))
                    total_nutrition[nutrient] += value * quantity
                except ValueError:
                    continue
    
    rounded_nutrition = {k: round(v, 2) for k, v in total_nutrition.items()}
    suggestion = f"Tracking successful! Total Calories: {rounded_nutrition['calories']}. Check your goal of '{user_data['goal']}'."

    response = {
        "total_nutrition": rounded_nutrition,
        "suggestion": suggestion,
    }

    return jsonify(response)


# 7. Logout
@app.route("/logout")
@login_required
def logout():
    session.pop("user", None)
    logout_user()
    return redirect(url_for("login_page"))


# ---------------- PROFILE & OTHER API ROUTES ----------------
@app.route("/update-password", methods=["POST"])
@login_required
def update_password():
    data = request.get_json()
    current = data.get("current")
    new_pass = data.get("new")
    username = current_user.username

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE name=?", (username,))
    db_pass = c.fetchone()
    
    if db_pass is None or db_pass[0] != current:
        conn.close()
        return jsonify({"success": False, "message": "Current password incorrect"})

    c.execute("UPDATE users SET password=? WHERE name=?", (new_pass, username))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Password updated successfully"})

@app.route("/get-theme", methods=["GET"])
@login_required
def get_theme():
    username = current_user.username
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT theme FROM users WHERE name=?", (username,))
    row = c.fetchone()
    conn.close()

    theme = row[0] if row and row[0] else "light"
    return jsonify({"theme": theme})

@app.route("/update-user-profile", methods=["POST"])
@login_required
def update_user_profile():
    data = request.get_json()
    weight = data.get("weight")
    goal = data.get("goal")

    username = current_user.username
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    update_fields = []
    update_values = []
    
    if weight:
        try:
            weight_float = float(weight)
            if weight_float > 0:
                update_fields.append("weight=?")
                update_values.append(weight_float)
        except ValueError:
            pass
            
    if goal in ['lose', 'gain', 'maintain']:
        update_fields.append("health_goal=?")
        update_values.append(goal)

    if not update_fields:
        conn.close()
        return jsonify({"success": False, "message": "No valid profile data provided"}), 400

    query = f"UPDATE users SET {', '.join(update_fields)} WHERE name=?"
    update_values.append(username)
    
    c.execute(query, tuple(update_values))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Profile (Weight & Goal) updated successfully. Suggestions will be updated."})


@app.route("/api/goals/<username>", methods=["GET"])
@login_required
def get_user_goals(username):
    if current_user.username != username:
        return jsonify({"error": "Unauthorized access (username mismatch)"}), 403
        
    user_data = get_user_data(username)
    weight_kg = user_data['weight']
    goal = user_data['goal']
    
    BMR = weight_kg * 24 
    TDEE = BMR * 1.55 
    
    calorie_adjustment = 0 
    if goal == 'lose':
        calorie_adjustment = -500 
    elif goal == 'gain':
        calorie_adjustment = 500   

    target_calories = TDEE + calorie_adjustment
    
    protein_multiplier = 1.8 if goal == 'gain' else 1.6
    target_protein = weight_kg * protein_multiplier
    
    target_fat_cals = target_calories * 0.25
    target_fat = target_fat_cals / 9
    
    protein_cals = target_protein * 4
    carb_cals = target_calories - protein_cals - target_fat_cals
    target_carbs = carb_cals / 4
    if target_carbs < 50: target_carbs = 50

    return jsonify({
        "goal": goal.upper(),
        "weight": round(weight_kg, 1),
        "target_calories": round(target_calories, 0),
        "target_protein": round(target_protein, 0),
        "target_fat": round(target_fat, 0),
        "target_carbs": round(target_carbs, 0)
    })

@app.route("/profile")
@login_required
def user_profile():
    return render_template("profile.html", username=current_user.username)

@app.route("/api/user-profile", methods=["POST"])
@login_required
def api_user_profile_post():
    try:
        data = request.get_json()
        username = data.get('username')
    except:
        return jsonify({"error": "Invalid JSON data."}), 400

    user_id = current_user.id 

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT phone, weight, health_goal, name FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        return jsonify({"error": "User data not found."}), 404

    phone, weight, health_goal, db_username = result
    
    if db_username != username:
        return jsonify({"error": "Unauthorized access attempt (username mismatch)."}), 403

    last_updated_time = datetime.now().strftime("%I:%M %p") 
    
    return jsonify({
        "name": db_username,
        "phone": phone,
        "weight": weight,
        "health_goal": health_goal,
        "last_updated": f"Today at {last_updated_time}"
    })


# ---------------- Run ----------------
if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)