# Iceberg Threat Assessment

Small Flask app for the MATE ROV iceberg mission.

## Run

```bash
python3 -m flask --app app run --debug
```

Open `http://127.0.0.1:5000`.

## What it does

- Accepts latitude, longitude, heading, and keel depth.
- Compares the iceberg track against Hibernia, Hebron, Sea Rose, and Terra Nova.
- Calculates platform and subsea threat levels using the rules from the provided PDFs.
- Draws an inline SVG graph of the iceberg trajectory and platform positions.

## Validation

```bash
python3 -m unittest discover -s tests
```
