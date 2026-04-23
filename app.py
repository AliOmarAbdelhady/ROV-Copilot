from __future__ import annotations

from base64 import b64encode
from io import BytesIO
import os

from flask import Flask, render_template, request, send_file

from threat_logic import assess_mission, format_coordinate_label, parse_coordinate, parse_heading, parse_keel_depth, render_report_pdf, render_track_preview_png


app = Flask(__name__)

DEFAULT_FORM = {
    "latitude": "47.39.00",
    "longitude": "48.37.00",
    "heading": "158",
    "keel_depth": "99",
}


@app.route("/", methods=["GET", "POST"])
def index():
    form = DEFAULT_FORM.copy()
    result = None
    error = None

    if request.method == "POST":
        form = {
            "latitude": request.form.get("latitude", ""),
            "longitude": request.form.get("longitude", ""),
            "heading": request.form.get("heading", ""),
            "keel_depth": request.form.get("keel_depth", ""),
        }
        try:
            latitude = parse_coordinate(form["latitude"], "latitude")
            longitude = parse_coordinate(form["longitude"], "longitude")
            heading = parse_heading(form["heading"])
            keel_depth = parse_keel_depth(form["keel_depth"])
            assessments = assess_mission(latitude, longitude, heading, keel_depth)
            result = {
                "latitude": latitude,
                "longitude": longitude,
                "latitude_label": format_coordinate_label(latitude, "latitude"),
                "longitude_label": format_coordinate_label(longitude, "longitude"),
                "heading": heading,
                "keel_depth": keel_depth,
                "assessments": assessments,
                "graph_png": b64encode(render_track_preview_png(latitude, longitude, heading, assessments)).decode("ascii"),
            }
        except ValueError as exc:
            error = str(exc)

    return render_template("index.html", form=form, result=result, error=error)


@app.get("/export/pdf")
def export_pdf():
    try:
        latitude = parse_coordinate(request.args.get("latitude", ""), "latitude")
        longitude = parse_coordinate(request.args.get("longitude", ""), "longitude")
        heading = parse_heading(request.args.get("heading", ""))
        keel_depth = parse_keel_depth(request.args.get("keel_depth", ""))
        assessments = assess_mission(latitude, longitude, heading, keel_depth)
        pdf_bytes = render_report_pdf(latitude, longitude, heading, keel_depth, assessments)
    except ValueError as exc:
        return str(exc), 400

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="iceberg-threat-report.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
