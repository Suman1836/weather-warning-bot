import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime
from google import genai

# --- 🔑 Setup Keys ---
WEATHER_KEY = os.environ["OPENWEATHER_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"].strip().replace('"', '')
EMAIL_USER = os.environ["EMAIL_USER"].strip()
EMAIL_PASS = os.environ["EMAIL_PASS"].strip()

# --- 📧 রিসিভার লিস্ট ---
RECIPIENTS = [
    EMAIL_USER,                       # তোমার নিজের ইমেইল
    "mangalmishra.contai@gmail.com",  # ১ নম্বর বন্ধু
    "tazlaloki@gmail.com"             # ২ নম্বর বন্ধু
]

CITY = "Contai"

client = genai.Client(api_key=GEMINI_KEY)

# --- 1. Get Weather Data ---
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data["cod"] != 200: return None

        return {
            "temp": int(data["main"]["temp"]),
            "feels_like": int(data["main"]["feels_like"]),
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"].title(),
            "humidity": data["main"]["humidity"],
            "wind": data["wind"]["speed"],
            "city": data["name"],
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"]
        }
    except: return None

# --- 2. Get Air Quality ---
def get_air_quality(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={WEATHER_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        aqi_index = data["list"][0]["main"]["aqi"]

        meta = {
            1: {"label": "Good", "emoji": "🟢", "advice": "Enjoy outdoor activities."},
            2: {"label": "Fair", "emoji": "🟡", "advice": "Air quality is acceptable."},
            3: {"label": "Moderate", "emoji": "🟠", "advice": "Sensitive groups reduce exertion."},
            4: {"label": "Poor", "emoji": "🔴", "advice": "Limit time outside. Consider a mask."},
            5: {"label": "Hazardous", "emoji": "☠️", "advice": "Stay indoors! Wear a mask outside."},
        }
        info = meta.get(aqi_index, {"label": "Unknown", "emoji": "❓", "advice": "No Data"})
        return {"index": aqi_index, "label": info["label"], "emoji": info["emoji"], "advice": info["advice"]}
    except:
        return {"index": None, "label": "Unknown", "emoji": "❓", "advice": "No Data"}

# --- 3. Generate HTML Report ---
def generate_html_report(w, aqi):
    print("Generating HTML Card...")
    prompt = f"""
    Act as a UI Designer. Create a SINGLE HTML email template.
    DATA:
    - City: {w['city']}, Temp: {w['temp']}C, Cond: {w['condition']}
    - AQI: {aqi['index']} ({aqi['label']}) {aqi['emoji']} - {aqi['advice']}
    
    DESIGN:
    - Modern Weather Card style.
    - Beautiful Gradient Background.
    - Large Temp text.
    - Distinct section for AQI with color coding.
    - Footer: "Stay safe & productive!"
    OUTPUT: Only raw HTML code.
    """
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return res.text.replace("```html", "").replace("```", "")
    except: return None

# --- 4. Send Individual Emails (Loop) ---
def send_email(html_content, weather, aqi):
    print(f"Starting to send emails to {len(RECIPIENTS)} people...")

    emoji = "☀️" if "Clear" in weather["condition"] else "☁️"
    if "Rain" in weather["condition"]: emoji = "🌧️"
    
    subject = f"{emoji} {weather['city']} Weather: {weather['temp']}°C | AQI: {aqi['label']}"

    try:
        # সার্ভারের সাথে একবার কানেক্ট হয়ে লুপ চালানো হবে (দ্রুত হবে)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            
            # লুপ চালিয়ে প্রত্যেককে আলাদা আলাদা ইমেইল পাঠানো
            for person in RECIPIENTS:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = EMAIL_USER
                msg["To"] = person  # <--- এখানে যার ইমেইল, তার নামই বসবে
                
                msg.set_content("Please enable HTML to view this email.", subtype="plain")
                msg.add_alternative(html_content, subtype="html")
                
                smtp.send_message(msg)
                print(f"✅ Sent to: {person}")
                
    except Exception as e:
        print(f"❌ Email Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    weather = get_weather()
    if weather:
        aqi = get_air_quality(weather["lat"], weather["lon"])
        html = generate_html_report(weather, aqi)
        if html:
            send_email(html, weather, aqi)
    else:
        print("Failed to fetch data.")
