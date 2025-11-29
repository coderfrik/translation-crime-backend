from flask import Flask, request, jsonify
from flask_cors import CORS
import os, re, requests

app = Flask(__name__)

# ================================
# 1) REAL TRANSLATION CONFIG
# ================================
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")


# ================================
# 2) REAL TRANSLATION FUNCTIONS
# ================================

def real_translate(text):
    """
    Auto-detects input language and translates to English.
    Priority:
        1. DeepL
        2. Fallback
    """
    if DEEPL_API_KEY:
        return translate_deepl(text)

    return "[NO REAL TRANSLATION CONFIGURED]\n" + text


# ---------- DeepL Translation ----------
def translate_deepl(text):
    url = "https://api-free.deepl.com/v2/translate"

    data = {
        "auth_key": DEEPL_API_KEY,
        "text": text,
        "target_lang": "EN",
        "preserve_formatting": "1"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        return result["translations"][0]["text"]
    except Exception as e:
        return f"[DeepL Error: {e}]\n{text}"


# ======================================
# 3) ENTITY EXTRACTION (simple version)
# ======================================

def extract_entities(text):
    entities = []

    # PERSON (capitalized names)
    for m in re.finditer(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b", text):
        name = m.group(1)
        if len(name.split()) <= 4:
            entities.append({
                "start": m.start(),
                "end": m.end(),
                "label": "PERSON",
                "text": name
            })

    # LOCATIONS (simple keyword list)
    locations = [
        "Madrid", "Barcelona", "Spain", "Mexico", "Colombia", "Argentina",
        "Lima", "USA", "Peru", "Bogota", "Ecuador", "Chile", "Brazil"
    ]
    for loc in locations:
        for m in re.finditer(loc, text, flags=re.IGNORECASE):
            entities.append({
                "start": m.start(),
                "end": m.end(),
                "label": "LOCATION",
                "text": m.group()
            })

    # LAW TERMS
    laws = [
        "murder", "trafficking", "possession", "kidnapping", "arrested",
        "sentenced", "convicted", "assault", "robbery", "fraud", "charged",
        "indicted", "prosecutor"
    ]
    for term in laws:
        for m in re.finditer(term, text, flags=re.IGNORECASE):
            entities.append({
                "start": m.start(),
                "end": m.end(),
                "label": "LAW",
                "text": m.group()
            })

    return entities


# ======================================
# 4) SUMMARY BUILDER
# ======================================

def build_summary(text, entities):
    persons = [e for e in entities if e['label'] == "PERSON"]
    laws = [e for e in entities if e['label'] == "LAW"]
    locations = [e for e in entities if e['label'] == "LOCATION"]

    summary = []

    for p in persons:
        name = p['text']
        pos = p['start']

        related_crimes = []
        related_locations = []

        for l in laws:
            if abs(l["start"] - pos) < 200:
                related_crimes.append(l["text"])

        for loc in locations:
            if abs(loc["start"] - pos) < 300:
                related_locations.append(loc["text"])

        summary.append({
            "name": name,
            "crimes": list(dict.fromkeys(related_crimes)),
            "status": "",
            "locations": list(dict.fromkeys(related_locations))
        })

    return summary


# ======================================
# 5) MAIN API ENDPOINT
# ======================================

@app.route("/api/process", methods=["POST"])
def process():
    data = request.get_json()
    text = data.get("text", "")

    if not text.strip():
        return "No text provided", 400

    translated = real_translate(text)
    entities = extract_entities(translated)
    criminals = build_summary(translated, entities)

    return jsonify({
        "translated_text": translated,
        "entities": entities,
        "criminals": criminals
    })


# ======================================
# 6) RUN SERVER
# ======================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
