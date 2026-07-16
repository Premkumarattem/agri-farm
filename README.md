# 🌾 Agri Farm

A farmer-facing web app covering the full crop lifecycle, disease help, nearby
fertilizer shops, machinery rental, and current market prices — in English,
Telugu, and Hindi.

## What's inside

- **Crop Guide** — Rice, Cotton, Maize, Chilli, Tomato, Groundnut, Turmeric,
  Onion. Every stage from land preparation to post-harvest, with exact
  fertilizer/pesticide doses, machinery needed, manual labour needed, and
  things to watch out for.
- **Disease Checker** — upload a photo (from gallery **or straight from your
  camera**, right in the browser) for a quick colour-based visual scan, or
  answer a symptom checklist. Either path gives symptoms, cause, treatment
  (with dose), and prevention.
- **Nearby Shops** — fertilizer/pesticide shop directory with **comprehensive
  Telangana coverage**: DCMS (co-operative) depots and Mana Gromor dealers
  across all 33 districts, plus shops in Andhra Pradesh, Karnataka, Tamil
  Nadu, Maharashtra, Punjab, Haryana, UP, West Bengal, and MP. Filterable by
  state/district, with a "use my location" button that sorts by real GPS
  distance.
- **Machinery Rental** — what tractors, rotavators, transplanters, combine
  harvesters, drone sprayers etc. cost to buy or rent, plus a directory of
  nearby Custom Hiring Centres (CHC) you can filter and locate the same way
  as the fertilizer shops.
- **Market Prices** — today's government-fixed fertilizer MRPs (Urea, DAP,
  MOP, NPK complexes) and typical retail pesticide price ranges, with an
  approximate cost-per-acre-per-spray for each, so farmers know what a
  treatment will actually cost before buying.
- **Farmer Tools** — sowing/harvest calendar, an input-cost estimator per
  acre, season tips, and helpline/scheme numbers (Kisan Call Centre, PM-KISAN,
  PM Fasal Bima Yojana, Soil Health Card).

## ⚠️ Two honest notes before real-world use

1. **The photo disease checker** is a lightweight colour-heuristic prototype,
   not a trained AI/CNN model. It looks at the mix of colours in the uploaded
   photo to narrow down plausible diseases, then always asks the farmer to
   confirm with the symptom checklist. Swap in a model trained on a labelled
   leaf-disease dataset (e.g. PlantVillage) in `guess_diseases_from_image()`
   in `app.py` for production accuracy.
2. **The shop and machinery-rental directories are sample/demo data** —
   realistic in structure and coverage (all 33 Telangana districts, DCMS +
   Gromor branding, plausible addresses/coordinates) but not independently
   verified real businesses or phone numbers. Before going live, replace
   `data/fertilizer_shops.json` and `data/chc_centers.json` with a verified
   source — your state's dealer/CHC registry, a government open-data feed, or
   manually confirmed listings. The app is fully wired up to just drop in
   real data with the same JSON shape.

Fertilizer and pesticide prices in `data/market_prices.json` reflect
government-fixed MRPs and typical 2026 retail ranges at time of writing —
double check current rates periodically since subsidy policy changes.

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser. On mobile, the camera
button opens your device camera directly (needs HTTPS or localhost to work,
per browser security rules).

## Project structure

```
agri-farm/
├── app.py                  # Flask app: routes, language handling, image heuristic, distance calc
├── requirements.txt
├── data/
│   ├── crops.json          # Full stage-by-stage crop lifecycle data (8 crops)
│   ├── diseases.json       # Disease symptoms/cause/treatment/prevention per crop
│   ├── fertilizer_shops.json  # 81 shops incl. all-Telangana DCMS + Gromor coverage
│   ├── chc_centers.json    # Machinery rental centre directory
│   ├── machinery.json      # Machine purchase/rental cost reference
│   ├── market_prices.json  # Current fertilizer MRP + pesticide price ranges
│   ├── extra.json          # Calendar, cost rates, helplines, season tips
│   └── translations.json   # UI strings in en/te/hi
├── templates/               # Jinja2 HTML templates
└── static/
    ├── css/style.css        # All styling (single stylesheet, CSS variables)
    ├── js/main.js
    └── uploads/              # Uploaded disease-check photos land here
```

## Extending it

- **Add a crop**: add an entry to `data/crops.json` (stages array) and
  `data/diseases.json` (disease list), then add an icon case in
  `templates/partials/crop_icon.html`.
- **Add a language**: add a new top-level key to `data/translations.json`
  and add it to `VALID_LANGS` in `app.py`.
- **Real fertilizer/machinery directories**: replace `data/fertilizer_shops.json`
  and `data/chc_centers.json` with a live/verified source and update
  `/api/shops` and `/api/chc` in `app.py` if the schema changes.
- **Real disease detection**: replace `guess_diseases_from_image()` in
  `app.py` with a call to a trained image-classification model.
- **Live market prices**: point `data/market_prices.json` at a scheduled job
  that pulls from the Dept. of Fertilizers / agmarknet or a similar official
  feed instead of the static snapshot.

"# agri-farm" 
