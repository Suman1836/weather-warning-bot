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

# --- 👤 Sender Name (তোমার নাম এখানে দাও) ---
SENDER_NAME = "Suman Karan" 

# --- 📧 রিসিভার লিস্ট ---
RECIPIENTS = [
    EMAIL_USER,                       # তোমার ইমেইল
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
        pm25 = data["list"][0]["components"]["pm2_5"]

        # Real AQI Calculation (Simplified)
        if pm25 <= 12.0: score = round((50/12)*pm25)
        elif pm25 <= 35.4: score = round(((49/23.3)*(pm25-12.1))+51)
        elif pm25 <= 55.4: score = round(((49/19.9)*(pm25-35.5))+101)
        else: score = round(((99/94.9)*(pm25-55.5))+151) # Rough high range

        if score <= 50: return {"score": score, "label": "Good", "emoji": "🟢", "color": "#00e400"}
        elif score <= 100: return {"score": score, "label": "Moderate", "emoji": "🟡", "color": "#ffff00"}
        elif score <= 150: return {"score": score, "label": "Sensitive", "emoji": "🟠", "color": "#ff7e00"}
        else: return {"score": score, "label": "Unhealthy", "emoji": "🔴", "color": "#ff0000"}
            
    except: return {"score": "N/A", "label": "Unknown", "emoji": "❓", "color": "#grey"}

# --- 3. Generate HTML Report ---
def generate_html_report(w, aqi):
    print("Generating HTML Card...")
    prompt = f"""
    Act as a UI Designer. Create a SINGLE HTML email template.
    DATA:
    - City: {w['city']}, Temp: {w['temp']}C, Cond: {w['condition']}
    - **Real AQI:** {aqi['score']} ({aqi['label']}) {aqi['emoji']}
    
    DESIGN:
    - Modern Weather Card style.
    - Large Temp text.
    - **AQI Section:** Circular badge with Score "{aqi['score']}". Color {aqi['color']}.
    - Footer: "Stay safe!"
    OUTPUT: Only raw HTML code.
    """
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return res.text.replace("```html", "").replace("```", "")
    except: return None

# --- 4. Send Personalized Emails ---
def send_email(html_content, weather, aqi):
    print(f"Sending to {len(RECIPIENTS)} people...")

    emoji = "☀️" if "Clear" in weather["condition"] else "☁️"
    if "Rain" in weather["condition"]: emoji = "🌧️"
    
    subject = f"{emoji} Weather: {weather['temp']}°C | AQI: {aqi['score']}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            
            for person in RECIPIENTS:
                msg = EmailMessage()
                msg["Subject"] = subject
                
                # --- এই লাইনটা পরিবর্তন করা হয়েছে ---
                # এখন দেখাবে: "Fuck <email@gmail.com>"
                msg["From"] = f"{SENDER_NAME} <{EMAIL_USER}>"
                
                msg["To"] = person
                
                msg.set_content("Enable HTML to view.", subtype="plain")
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
