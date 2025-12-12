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
            "pressure": data["main"]["pressure"],
            "visibility": data.get("visibility", 0) / 1000, # Convert to km
            "wind": data["wind"]["speed"],
        }
    except Exception as e:
        print(f"Weather Fetch Error: {e}")
        return None

# --- 2. Generate HTML Report (Creative Mode) ---
def generate_html_report(w):
    print("Asking DeepSeek to create a unique design...")
    
    # --- HERE IS THE MAGIC PROMPT ---
    # আমরা ডিজাইন বলে দিচ্ছি না, AI-কে স্বাধীনতা দিচ্ছি।
    prompt = f"""
    You are a World-Class UI/UX Designer.
    
    TASK: Create a stunning, modern, and advanced HTML Email Template for today's weather.
    
    REAL-TIME DATA:
    - Location: {w['city']}, {w['country']}
    - Weather: {w['temp']}°C (Feels like {w['feels_like']}°C)
    - Condition: {w['condition']} ({w['description']})
    - Wind: {w['wind']} m/s
    - Humidity: {w['humidity']}%
    - Pressure: {w['pressure']} hPa
    - Visibility: {w['visibility']} km

    CREATIVE INSTRUCTIONS:
    1. **Design Philosophy:** Use "Glassmorphism" or "Neomorphism" style. Clean, minimalist, and high-end (Apple/iOS 17 style).
       - Use soft shadows, blur effects, and modern gradients matching the weather (e.g., Orange/Purple for Sunset, Blue/White for Clear Sky).
    2. **Content Strategy:**
       - **Greeting:** A warm, intelligent greeting based on the current weather.
       - **Outfit Advice:** Suggest what to wear (e.g., "Light jacket recommended", "Perfect for a t-shirt").
       - **Health/Activity Tip:** Suggest an activity or health tip (e.g., "Great for a run", "Stay hydrated").
       - **Quote:** A short, inspiring quote related to nature, weather, or success.
    3. **Tech Stack:** Use only HTML and inline CSS. No JavaScript.
    4. **Responsiveness:** It must look perfect on Mobile screens (Gmail, Apple Mail). Use a card-based layout centered on the screen.
    
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

# --- 3. Send Individual Emails ---
def send_email(html_content, weather):
    print(f"Sending to {len(RECIPIENTS)} people...")

    emoji = "☀️"
    if "Cloud" in weather["condition"]: emoji = "☁️"
    if "Rain" in weather["condition"]: emoji = "🌧️"
    if "Snow" in weather["condition"]: emoji = "❄️"
    if "Thunderstorm" in weather["condition"]: emoji = "⚡"
    if "Drizzle" in weather["condition"]: emoji = "🌦️"
    if "Mist" in weather["condition"] or "Fog" in weather["condition"]: emoji = "🌫️"
    
    subject = f"{emoji} {weather['city']} Weather Update: {weather['temp']}°C | {weather['condition']}"

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
        html = generate_html_report(weather)
        if html:
            send_email(html, weather)
    else:
        print("Failed to fetch data.")
