import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime
from openai import OpenAI

# --- 🔑 Setup Keys ---
WEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip().replace('"', '')
EMAIL_USER = os.environ.get("EMAIL_USER", "").strip()
EMAIL_PASS = os.environ.get("EMAIL_PASS", "").strip()

# --- 👤 Sender Details ---
SENDER_NAME = "Suman Karan"

# --- 📧 রিসিভার লিস্ট ---
RECIPIENTS = [
    EMAIL_USER,                       
    "mangalmishra.contai@gmail.com",  
    "tazlaloki@gmail.com"             
]

CITY = "Contai"

# --- OpenAI Client (OpenRouter) ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

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
            1: {"label": "Good", "emoji": "🟢", "advice": "Great air quality!"},
            2: {"label": "Fair", "emoji": "🟡", "advice": "Acceptable air quality."},
            3: {"label": "Moderate", "emoji": "🟠", "advice": "Sensitive groups take care."},
            4: {"label": "Poor", "emoji": "🔴", "advice": "Unhealthy! Wear a mask."},
            5: {"label": "Hazardous", "emoji": "☠️", "advice": "Dangerous! Stay indoors."},
        }
        
        info = meta.get(aqi_index, {"label": "Unknown", "emoji": "❓", "advice": "No Data"})
        return {"index": aqi_index, "label": info["label"], "emoji": info["emoji"], "advice": info["advice"]}
    except:
        return {"index": "?", "label": "Unknown", "emoji": "❓", "advice": "No Data"}

# --- 3. Generate HTML Report (Creative Mode) ---
def generate_html_report(w, aqi):
    print("Asking DeepSeek to create a unique design...")
    
    # --- HERE IS THE MAGIC PROMPT ---
    # আমরা ডিজাইন বলে দিচ্ছি না, AI-কে স্বাধীনতা দিচ্ছি।
    prompt = f"""
    You are a World-Class UI/UX Designer.
    
    TASK: Create a stunning, modern HTML Email Template for today's weather.
    
    REAL-TIME DATA:
    - Location: {w['city']}
    - Weather: {w['temp']}°C, {w['condition']} ({w['description']})
    - Air Quality: AQI {aqi['index']} ({aqi['label']} {aqi['emoji']})
    - Advice: {aqi['advice']}
    
    CREATIVE INSTRUCTIONS:
    1. **Design Freedom:** I am NOT giving you color codes or layout rules. You decide the best design based on the weather condition.
       - Example: If it's sunny, maybe use warm, bright gradients. If it's rainy, use moody blues/grays. If AQI is bad, make it look urgent (Red/Dark).
    2. **Modern aesthetic:** Make it look like an Apple/Google Weather App widget.
    3. **Tech Stack:** Use only HTML and inline CSS. No JavaScript.
    4. **Responsiveness:** It must look perfect on Mobile screens (Gmail).
    
    OUTPUT: Provide ONLY the raw HTML code starting with <!DOCTYPE html>. Do not add any markdown blocks or explanations.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3.2", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            extra_body={"reasoning": {"enabled": True}}
        )
        
        content = response.choices[0].message.content
        # Cleaning Markdown
        return content.replace("```html", "").replace("```", "").strip()
        
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- 4. Send Individual Emails ---
def send_email(html_content, weather, aqi):
    print(f"Sending to {len(RECIPIENTS)} people...")

    emoji = "☀️" if "Clear" in weather["condition"] else "☁️"
    if "Rain" in weather["condition"]: emoji = "🌧️"
    
    subject = f"{emoji} {weather['city']} Weather: {weather['temp']}°C | AQI: {aqi['label']}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            
            for person in RECIPIENTS:
                msg = EmailMessage()
                msg["Subject"] = subject
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
