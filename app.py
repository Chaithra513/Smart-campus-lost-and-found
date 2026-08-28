"""
app.py
------
Main Flask application file. Controls every route in the site.

Stage 3 changes from Stage 2:
  - Browse Items now supports searching by keyword and filtering by
    location and Lost/Found status (via ?keyword=&location=&status=).
  - New route /edit/<id>: lets you change a report's details, and
    optionally replace its image.
  - New route /delete/<id>: permanently removes a report.
  - New route /resolve/<id>: toggles a report between Resolved/Claimed
    and Active.

Note: there is still no login system, so (as in Stage 2) anyone can
submit, edit, delete, or resolve any report. Adding real user accounts
is left for a future stage.
"""

import os
from datetime import datetime

from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename

import database

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-later"

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
database.init_db()


def allowed_file(filename):
    """Return True if the uploaded file has an extension we accept as an image."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(image_file):
    """
    Save an uploaded image (if there is a valid one) and return its stored
    filename, or None if no image was uploaded. Shared by the Report and
    Edit forms so the saving logic only lives in one place.
    """
    if image_file and image_file.filename and allowed_file(image_file.filename):
        safe_name = secure_filename(image_file.filename)
        # Timestamp prefix keeps filenames unique.
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + safe_name
        image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None


@app.route("/")
def home():
    """Home page: title, description, and the two main buttons."""
    return render_template("index.html")


@app.route("/report", methods=["GET", "POST"])
def report():
    """
    Report page.

    GET  -> show the empty form.
    POST -> save the new report (and its image, if any) to the database,
            then send the user to Browse Items.
    """
    if request.method == "POST":
        item_name = request.form.get("item_name")
        description = request.form.get("description")
        location = request.form.get("location")
        date = request.form.get("date")
        status = request.form.get("report_type")
        contact = request.form.get("contact")
        image_filename = save_uploaded_image(request.files.get("image"))

        database.insert_item(
            item_name, description, location, date, status, contact, image_filename
        )

        flash("Thanks! Your report was submitted successfully.")
        return redirect(url_for("browse"))

    # ?type=lost or ?type=found (from the home page buttons) pre-selects
    # the dropdown.
    report_type = request.args.get("type", "")
    return render_template("report.html", report_type=report_type)


@app.route("/browse")
def browse():
    """
    Browse Items page. Reads optional search/filter values from the URL
    (?keyword=...&location=...&status=...) and shows matching reports.
    Visiting /browse with no query params shows everything.
    """
    keyword = request.args.get("keyword", "").strip()
    location = request.args.get("location", "").strip()
    status_filter = request.args.get("status", "").strip()

    items = database.get_filtered_items(keyword, location, status_filter)

    return render_template(
        "browse.html",
        items=items,
        keyword=keyword,
        location=location,
        status_filter=status_filter,
    )


@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    """
    Edit an existing report.

    GET  -> show the form pre-filled with the item's current details.
    POST -> save the changes. Uploading a new image replaces the old one;
            leaving the image field empty keeps the existing image.
    """
    item = database.get_item_by_id(item_id)
    if item is None:
        flash("That report no longer exists.")
        return redirect(url_for("browse"))

    if request.method == "POST":
        item_name = request.form.get("item_name")
        description = request.form.get("description")
        location = request.form.get("location")
        date = request.form.get("date")
        status = request.form.get("report_type")
        contact = request.form.get("contact")
        image_filename = save_uploaded_image(request.files.get("image"))

        database.update_item(
            item_id, item_name, description, location, date, status, contact, image_filename
        )

        flash("Report updated successfully.")
        return redirect(url_for("browse"))

    return render_template("edit.html", item=item)


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    """Permanently delete a report."""
    database.delete_item(item_id)
    flash("Report deleted.")
    return redirect(url_for("browse"))


@app.route("/resolve/<int:item_id>", methods=["POST"])
def resolve(item_id):
    """Toggle a report between Resolved/Claimed and Active."""
    item = database.get_item_by_id(item_id)
    if item is not None:
        database.set_resolved(item_id, not item["is_resolved"])
        flash("Report marked as unresolved." if item["is_resolved"] else "Report marked as resolved!")
    return redirect(url_for("browse"))


if __name__ == "__main__":
    app.run(debug=True)
