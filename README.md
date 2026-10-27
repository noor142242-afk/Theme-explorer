# Theme-explorer

A Streamlit dashboard for exploring hospital and clinic website themes from ThemeForest.

## Features

- Search themes and filter by hospital or clinic.
- Browse a paginated table with theme, demo, and mobile links where available.
- Preview descriptions and download filtered results as JSON.
- Includes 94 unique themes across `hospital.json` and `clinic.json`; themes may belong to both categories.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, `./start-app.ps1` also starts the dashboard.

## Refresh the collection

```bash
python code.py
```

The scraper opens Chrome and searches ThemeForest for hospital, clinic, medical, and healthcare themes. Complete any verification in the browser. It saves results next to the script. Chrome major version 155 is currently configured in `code.py`; update `version_main` if your installed Chrome changes.

The dashboard reads saved JSON files; it does not run the scraper automatically. Missing mobile links are stored as `null`. Theme content and external demos belong to their respective owners.

## Streamlit deployment

Use `app.py` as the entry point, with both JSON files and `requirements.txt` included. The dashboard can run without Chrome; Chrome is needed only to run the scraper locally.
