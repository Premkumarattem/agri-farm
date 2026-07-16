import json
import math
import os
import uuid

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "agri-farm-dev-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


TRANSLATIONS = load_json("translations.json")
CROPS = load_json("crops.json")
DISEASES = load_json("diseases.json")
SHOPS = load_json("fertilizer_shops.json")
EXTRA = load_json("extra.json")
MACHINERY = load_json("machinery.json")
CHC_CENTERS = load_json("chc_centers.json")
MARKET_PRICES = load_json("market_prices.json")

VALID_LANGS = ["en", "te", "hi"]

# Maps each disease's visual cue keyword to a broad colour bucket that we can
# actually estimate from a photo using simple pixel-colour analysis.
SPOT_COLOR_TO_BUCKET = {
    "grey_brown": "brown",
    "yellow_white": "yellow",
    "white_dry": "white_grey",
    "uniform_yellow": "yellow",
    "brown_hole": "brown",
    "dark_green_thick_vein": "green_curl",
    "dark_brown_black": "brown",
    "grey_green": "white_grey",
    "dark_sunken": "brown",
    "silver_streak": "white_grey",
    "dark_brown": "brown",
    "black_bottom": "brown",
}


# --------------------------------------------------------------------------
# Language helpers
# --------------------------------------------------------------------------
def get_lang():
    lang = session.get("lang", "en")
    return lang if lang in VALID_LANGS else "en"


def tr(dct, lang=None):
    """Pull the right language string out of a {'en':..,'te':..,'hi':..} dict."""
    if not isinstance(dct, dict):
        return dct
    lang = lang or get_lang()
    return dct.get(lang, dct.get("en", ""))


@app.context_processor
def inject_globals():
    lang = get_lang()
    ui = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return dict(ui=ui, lang=lang, tr=tr, crops=CROPS)


@app.route("/setlang/<code>")
def setlang(code):
    if code in VALID_LANGS:
        session["lang"] = code
    nxt = request.referrer or url_for("home")
    return redirect(nxt)


# --------------------------------------------------------------------------
# Core pages
# --------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/crop/<crop_id>")
def crop_detail(crop_id):
    crop = CROPS.get(crop_id)
    if not crop:
        return redirect(url_for("home"))
    return render_template("crop_detail.html", crop=crop, crop_id=crop_id)


@app.route("/disease", methods=["GET"])
def disease_home():
    crop_id = request.args.get("crop", "rice")
    if crop_id not in CROPS:
        crop_id = "rice"
    return render_template(
        "disease.html",
        selected_crop=crop_id,
        result=None,
        show_checklist=True,
        diseases_for_crop=DISEASES.get(crop_id, []),
    )


def classify_pixels(img: Image.Image):
    """Very lightweight colour-bucket analysis of a leaf/fruit photo.

    This is NOT a trained disease-detection model. It's a practical heuristic:
    it looks at the mix of colours in the photo (green / yellow / brown-black /
    white-grey) and uses that to narrow down which of the crop's known
    diseases are plausible, then asks the farmer to confirm with symptoms.
    """
    img = img.convert("RGB").resize((120, 120))
    pixels = list(img.getdata())
    total = len(pixels)
    counts = {"green_healthy": 0, "yellow": 0, "brown": 0, "white_grey": 0, "other": 0}

    for r, g, b in pixels:
        brightness = (r + g + b) / 3
        if g > r + 15 and g > b + 15 and g > 60:
            counts["green_healthy"] += 1
        elif r > 140 and g > 120 and b < 110 and abs(r - g) < 60:
            counts["yellow"] += 1
        elif brightness < 110 and max(r, g, b) - min(r, g, b) <= 45:
            counts["brown"] += 1
        elif r > g + 10 and r > 90 and b < 120:
            counts["brown"] += 1
        elif abs(r - g) < 20 and abs(g - b) < 20 and brightness > 100:
            counts["white_grey"] += 1
        else:
            counts["other"] += 1

    return {k: round(v * 100 / total, 1) for k, v in counts.items()}


def guess_diseases_from_image(crop_id, img: Image.Image):
    pct = classify_pixels(img)
    diseases = DISEASES.get(crop_id, [])

    if pct["green_healthy"] >= 78:
        return pct, "healthy", []

    # pick the strongest non-green signal
    signal_order = sorted(
        [("yellow", pct["yellow"]), ("brown", pct["brown"]), ("white_grey", pct["white_grey"])],
        key=lambda x: x[1], reverse=True
    )
    top_bucket, top_pct = signal_order[0]

    if top_pct < 8:
        # No strong colour signal either way - don't guess, let the farmer
        # use the symptom checklist instead.
        return pct, "inconclusive", []

    matches = []
    for d in diseases:
        bucket = SPOT_COLOR_TO_BUCKET.get(d["image_cues"]["spot_color"], "other")
        if bucket == top_bucket:
            matches.append(d)

    # green_curl diseases (leaf curl viruses) don't show strong colour spots,
    # so surface them too if the plant isn't clearly healthy and no strong
    # colour signal was found.
    if not matches and top_pct < 20:
        matches = [d for d in diseases if SPOT_COLOR_TO_BUCKET.get(d["image_cues"]["spot_color"]) == "green_curl"]

    confidence = min(92, max(35, round(top_pct * 1.6)))
    return pct, top_bucket, [(d, confidence) for d in matches[:2]]


@app.route("/disease/analyze", methods=["POST"])
def disease_analyze():
    crop_id = request.form.get("crop", "rice")
    if crop_id not in CROPS:
        crop_id = "rice"

    file = request.files.get("photo")
    image_url = None
    matches = []
    healthy = False
    error = None

    if file and file.filename:
        try:
            img = Image.open(file.stream)
            fname = f"{uuid.uuid4().hex}.jpg"
            save_path = os.path.join(UPLOAD_DIR, fname)
            img.convert("RGB").save(save_path, "JPEG", quality=85)
            image_url = url_for("static", filename=f"uploads/{fname}")

            pct, bucket, ranked = guess_diseases_from_image(crop_id, img)
            if bucket == "healthy":
                healthy = True
            else:
                matches = ranked
        except Exception:
            error = "image_error"
    else:
        error = "no_image"

    return render_template(
        "disease.html",
        selected_crop=crop_id,
        image_url=image_url,
        matches=matches,
        healthy=healthy,
        error=error,
        show_checklist=True,
        diseases_for_crop=DISEASES.get(crop_id, []),
    )


@app.route("/disease/diagnose", methods=["POST"])
def disease_diagnose():
    crop_id = request.form.get("crop", "rice")
    if crop_id not in CROPS:
        crop_id = "rice"
    selected = request.form.getlist("symptom")  # values like "diseaseid|index"

    diseases = DISEASES.get(crop_id, [])
    scores = {d["id"]: {"disease": d, "hit": 0, "total": len(d["symptoms"]["en"])} for d in diseases}

    for val in selected:
        try:
            did, _idx = val.split("|", 1)
        except ValueError:
            continue
        if did in scores:
            scores[did]["hit"] += 1

    ranked = []
    for did, s in scores.items():
        if s["hit"] > 0:
            confidence = round(min(96, (s["hit"] / max(1, s["total"])) * 100))
            ranked.append((s["disease"], confidence))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return render_template(
        "disease.html",
        selected_crop=crop_id,
        matches=ranked[:2],
        healthy=(len(ranked) == 0),
        show_checklist=True,
        diseases_for_crop=diseases,
        diagnosed=True,
    )


# --------------------------------------------------------------------------
# Fertilizer shops
# --------------------------------------------------------------------------
def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@app.route("/fertilizers")
def fertilizers():
    states = sorted({s["state"] for s in SHOPS})
    return render_template("fertilizers.html", shops=SHOPS, states=states)


@app.route("/api/shops")
def api_shops():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    state = request.args.get("state")
    district = request.args.get("district")

    results = SHOPS
    if state and state != "all":
        results = [s for s in results if s["state"] == state]
    if district and district != "all":
        results = [s for s in results if s["district"] == district]

    if lat is not None and lng is not None:
        results = sorted(results, key=lambda s: haversine(lat, lng, s["lat"], s["lng"]))
        results = [dict(s, distance_km=round(haversine(lat, lng, s["lat"], s["lng"]), 1)) for s in results]

    return jsonify(results)


@app.route("/api/chc")
def api_chc():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    state = request.args.get("state")
    district = request.args.get("district")

    results = CHC_CENTERS
    if state and state != "all":
        results = [s for s in results if s["state"] == state]
    if district and district != "all":
        results = [s for s in results if s["district"] == district]

    if lat is not None and lng is not None:
        results = sorted(results, key=lambda s: haversine(lat, lng, s["lat"], s["lng"]))
        results = [dict(s, distance_km=round(haversine(lat, lng, s["lat"], s["lng"]), 1)) for s in results]

    return jsonify(results)


@app.route("/machinery")
def machinery():
    states = sorted({c["state"] for c in CHC_CENTERS})
    return render_template("machinery.html", centers=CHC_CENTERS, states=states, reference=MACHINERY["reference"])


# --------------------------------------------------------------------------
# Market prices
# --------------------------------------------------------------------------
@app.route("/prices")
def prices():
    return render_template("prices.html", prices=MARKET_PRICES)


# --------------------------------------------------------------------------
# Extra tools
# --------------------------------------------------------------------------
@app.route("/extra")
def extra():
    return render_template("extra.html", extra=EXTRA)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
