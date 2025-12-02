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
        if data["cod"] != 200:
            return None

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
    except:
        return None

# --- 2. Get Air Quality (numeric AQI + label + advice) ---
def get_air_quality(lat, lon):
    # বাতাসের মান চেক করা (OpenWeatherMap AQI API)
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={WEATHER_KEY}"
    try:
        response = requests.get(url)
        data = response.json()

        # AQI Index: 1 (Good), 2 (Fair), 3 (Moderate), 4 (Poor), 5 (Very Poor/Hazardous)
        aqi_index = data["list"][0]["main"]["aqi"]

        meta = {
            1: {
                "label": "Good",
                "emoji": "🟢",
                "advice": "Air quality is good. Enjoy outdoor activities."
            },
            2: {
                "label": "Fair",
                "emoji": "🟡",
                "advice": "Air quality is acceptable for most people."
            },
            3: {
                "label": "Moderate",
                "emoji": "🟠",
                "advice": "Sensitive groups should reduce prolonged outdoor exertion."
            },
            4: {
                "label": "Poor",
                "emoji": "🔴",
                "advice": "Everyone should limit time outside. Consider a mask."
            },
            5: {
                "label": "Hazardous",
                "emoji": "☠️",
                "advice": "Very unhealthy air. Stay indoors and wear a mask if you go out."
            },
        }

        info = meta.get(aqi_index, {
            "label": "Unknown",
            "emoji": "❓",
            "advice": "Air quality data is not available."
        })

        return {
            "index": aqi_index,        # 1–5 number
            "label": info["label"],    # Good / Fair / ...
            "emoji": info["emoji"],
            "advice": info["advice"]
        }
    except:
        return {
            "index": None,
            "label": "Unknown",
            "emoji": "❓",
            "advice": "Air quality data is not available."
        }

# --- 3. Generate HTML Report with AI (modern + AQI section) ---
def generate_html_report(w, aqi):
    print("Generating HTML Card with AQI...")

    aqi_index = aqi["index"]
    aqi_label = aqi["label"]
    aqi_emoji = aqi["emoji"]
    aqi_advice = aqi["advice"]

    prompt = f"""
    You are a front-end email designer and a weather reporter.

    Create a SINGLE, COMPLETE HTML email (no markdown, no comments).
    It will be opened mostly on mobile, inside Gmail.

    DATA:
    - City: {w['city']}
    - Temperature: {w['temp']}°C (Feels like {w['feels_like']}°C)
    - Condition: {w['condition']} ({w['description']})
    - Humidity: {w['humidity']}%
    - Wind: {w['wind']} m/s
    - Air Quality Index (AQI): {aqi_index} ({aqi_label}) {aqi_emoji}
    - AQI advice: {aqi_advice}

    DESIGN REQUIREMENTS:
    1. Use a full-page background with a subtle vertical gradient.
    2. In the center, place a rounded card with soft shadow (max-width: 420px).
    3. Inside the card, show:
       - City name at the top.
       - Very large temperature (e.g. 48–60px).
       - Condition text under the temperature.
       - A small row for "Humidity" and "Wind".
    4. Below that, create a SEPARATE AQI section:
       - Use a bold title: "Air Quality (AQI)".
       - A pill/badge like "AQI {aqi_index} · {aqi_label}".
       - Background color based on AQI severity:
         - Good/Fair: greenish
         - Moderate: yellow/orange
         - Poor/Hazardous: red.
       - Show the AQI advice text in 1–2 short sentences.
    5. At the bottom add a small "Today’s Tip" line with practical advice
       combining weather + AQI.
    6. Use modern, clean fonts (system fonts like -apple-system, Roboto, etc).
    7. Use inline CSS inside a <style> tag in the <head>. No external CSS, no JS.
    8. Output ONLY raw HTML, no code fences, no extra text.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html = response.text.replace("```html", "").replace("```", "")
        return html
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- 4. Send Email ---
def send_email(html_content, weather, aqi):
    print(f"Sending Email to {len(RECIPIENTS)} people...")

    msg = EmailMessage()
    emoji = "☀️" if "Clear" in weather["condition"] else "☁️"
    if "Rain" in weather["condition"]:
        emoji = "🌧️"

    # Subject Line with AQI value + label
    aqi_part = f"AQI {aqi['index']} ({aqi['label']})"
    subject = f"{emoji} {weather['city']} Weather: {weather['temp']}°C | {aqi_part}"

    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(RECIPIENTS)

    msg.set_content("Please enable HTML to view this email.", subtype="plain")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
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
        aqi = get_air_quality(weather["lat"], weather["lon"])
        html_report = generate_html_report(weather, aqi)
        if html_report:
            send_email(html_report, weather, aqi)
    else:
        print("Failed to fetch weather data.")
