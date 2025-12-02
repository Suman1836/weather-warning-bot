import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime
from google import genai

# --- Setup Keys ---
WEATHER_KEY = os.environ["OPENWEATHER_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"].strip().replace('"', '')
EMAIL_USER = os.environ["EMAIL_USER"].strip()
EMAIL_PASS = os.environ["EMAIL_PASS"].strip()

# --- 📧 Multiple Recipients ---
RECIPIENTS = [
    EMAIL_USER,              # তোমার নিজের ইমেইল
    # "mangalmishra.contai@gmail.com", "tazlaloki@gmail.com"   # চাইলে এখানে কমা দিয়ে আরও ইমেইল লিখতে পারো
]

CITY = "Contai" 

client = genai.Client(api_key=GEMINI_KEY)

# --- 1. Get Real-time Weather ---
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
            "city": data["name"]
        }
    except: return None

# --- 2. Generate English HTML Report ---
def generate_html_report(w):
    print("Generating English Weather Card...")
    
    # AI Prompt (Changed back to English)
    prompt = f"""
    Act as a Weather Reporter. Create an HTML Email Template for:
    - City: {w['city']}
    - Temp: {w['temp']}°C (Feels {w['feels_like']}°C)
    - Condition: {w['condition']}
    - Humidity: {w['humidity']}% | Wind: {w['wind']} m/s
    
    INSTRUCTIONS:
    1. **Language:** The content MUST be in **ENGLISH**.
    2. **Design:** Create a beautiful "Weather Card" (Mobile friendly).
       - Use colors based on weather (Orange/Yellow for Sun, Grey/Blue for Rain).
    3. **Content:**
       - Show Temperature boldly.
       - **Advice:** Give a short, caring advice (e.g., "Stay hydrated!" or "Don't forget your umbrella!").
    4. **Output:** Provide ONLY raw HTML code.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text.replace("```html", "").replace("```", "")
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- 3. Send Email ---
def send_email(html_content, weather):
    print(f"Sending Email to {len(RECIPIENTS)} people...")
    
    msg = EmailMessage()
    emoji = "☀️" if "Clear" in weather['condition'] else "☁️"
    if "Rain" in weather['condition']: emoji = "🌧️"
    
    # Subject Line in English
    msg['Subject'] = f"{emoji} Weather Update: {weather['temp']}°C in {weather['city']}"
    msg['From'] = EMAIL_USER
    msg['To'] = ", ".join(RECIPIENTS)
    
    msg.set_content("Please enable HTML to view this email.", subtype='plain')
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("✅ Weather Report Sent!")
    except Exception as e:
        print(f"❌ Email Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    weather_data = get_weather()
    if weather_data:
        html_report = generate_html_report(weather_data)
        if html_report:
            send_email(html_report, weather_data)
    else:
        print("Failed to fetch weather.")
  
