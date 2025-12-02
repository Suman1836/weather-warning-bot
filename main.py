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

# --- 📧 রিসিভার লিস্ট (বন্ধুদের ইমেইল এখানে দাও) ---
RECIPIENTS = [
    EMAIL_USER,                       # তোমার নিজের ইমেইল
    "mangalmishra.contai@gmail.com",  # ১ নম্বর বন্ধু
    "tazlaloki@gmail.com"             # ২ নম্বর বন্ধু
]

CITY = "Contai" 

client = genai.Client(api_key=GEMINI_KEY)

# --- 1. Get Weather Data ---
def get_weather():
    # প্রথমে আবহাওয়া এবং লোকেশন (Lat/Lon) নেওয়া
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

# --- 2. Get Air Quality (New Feature) ---
def get_air_quality(lat, lon):
    # বাতাসের মান চেক করা (OpenWeatherMap AQI API)
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={WEATHER_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        
        # AQI Index: 1 (Good), 2 (Fair), 3 (Moderate), 4 (Poor), 5 (Very Poor)
        aqi_index = data["list"][0]["main"]["aqi"]
        
        aqi_labels = {1: "Good 🟢", 2: "Fair 🟡", 3: "Moderate 🟠", 4: "Poor 🔴", 5: "Hazardous ☠️"}
        return aqi_labels.get(aqi_index, "Unknown")
    except: return "Unknown"

# --- 3. Generate HTML Report with AI ---
def generate_html_report(w, aqi):
    print("Generating HTML Card with AQI...")
    
    prompt = f"""
    Act as a Weather Reporter. Create an HTML Email Template for:
    - City: {w['city']}
    - Temp: {w['temp']}°C (Feels {w['feels_like']}°C)
    - Condition: {w['condition']}
    - Humidity: {w['humidity']}% | Wind: {w['wind']} m/s
    - **Air Quality (AQI):** {aqi}
    
    INSTRUCTIONS:
    1. **Language:** ENGLISH.
    2. **Design:** Create a beautiful "Morning Weather Card" (Mobile friendly).
       - Use gradient colors suitable for the weather.
       - **AQI Section:** Highlight the Air Quality prominently. If AQI is Poor/Hazardous, use RED/Warning colors for that section.
    3. **Content:**
       - Big Temperature display.
       - Short, practical advice (e.g., "Air quality is bad, wear a mask" or "Perfect weather for a walk!").
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

# --- 4. Send Email ---
def send_email(html_content, weather, aqi):
    print(f"Sending Email to {len(RECIPIENTS)} people...")
    
    msg = EmailMessage()
    emoji = "☀️" if "Clear" in weather['condition'] else "☁️"
    if "Rain" in weather['condition']: emoji = "🌧️"
    
    # Subject Line with AQI Warning if needed
    subject = f"{emoji} Weather: {weather['temp']}°C | AQI: {aqi}"
    
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = ", ".join(RECIPIENTS)
    
    msg.set_content("Please enable HTML to view this email.", subtype='plain')
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("✅ Report Sent Successfully!")
    except Exception as e:
        print(f"❌ Email Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    weather = get_weather()
    if weather:
        # আবহাওয়া পাওয়ার পর AQI চেক করা হবে
        aqi = get_air_quality(weather['lat'], weather['lon'])
        
        html_report = generate_html_report(weather, aqi)
        if html_report:
            send_email(html_report, weather, aqi)
    else:
        print("Failed to fetch weather data.")
    
