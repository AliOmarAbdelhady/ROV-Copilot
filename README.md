# Iceberg Threat Assessment

Small Flask app for the MATE ROV iceberg mission.

## Run

```bash
python3 -m flask --app app run --debug --port 5001
```

Open `http://127.0.0.1:5001`.

## What it does

- Accepts latitude, longitude, heading, and keel depth.
- Compares the iceberg track against Hibernia, Hebron, Sea Rose, and Terra Nova.
- Calculates platform and subsea threat levels using the rules from the provided PDFs.
- Draws a rendered matplotlib track plot with geographic grid labels.
- Exports the full result as a PDF report.
- Uses a two-step input flow so Enter moves from position input to track input.

## Validation

```bash
python3 -m unittest discover -s tests
```
