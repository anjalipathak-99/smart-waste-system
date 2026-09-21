import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from extensions import db
from models import CitizenReport, Alert
from routes.auth import role_required

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@reports_bp.route("", methods=["POST"])
@jwt_required()
def create_report():
    citizen_id = get_jwt_identity()
    report_type = request.form.get("report_type")
    description = request.form.get("description", "")
    bin_id = request.form.get("bin_id", type=int)
    latitude = request.form.get("latitude", type=float)
    longitude = request.form.get("longitude", type=float)

    if report_type not in {"overflow", "damaged", "missed_collection", "other"}:
        return jsonify({"error": "Invalid report_type"}), 400

    image_path = None
    if "image" in request.files and request.files["image"].filename:
        file = request.files["image"]
        if not _allowed(file.filename):
            return jsonify({"error": "Invalid image type"}), 400
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name))
        image_path = f"uploads/{unique_name}"

    report = CitizenReport(
        citizen_id=int(citizen_id), bin_id=bin_id, report_type=report_type,
        description=description, image_path=image_path,
        latitude=latitude, longitude=longitude,
    )
    db.session.add(report)

    if bin_id:
        alert = Alert(bin_id=bin_id, alert_type="damage" if report_type == "damaged" else "overflow",
                       severity="medium",
                       message=f"Citizen reported '{report_type}' for bin #{bin_id}.")
        db.session.add(alert)

    db.session.commit()
    return jsonify(report.to_dict()), 201


@reports_bp.route("", methods=["GET"])
@jwt_required()
def list_reports():
    claims = get_jwt()
    q = CitizenReport.query
    if claims.get("role") == "citizen":
        q = q.filter_by(citizen_id=int(get_jwt_identity()))
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    reports = q.order_by(CitizenReport.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports]), 200


@reports_bp.route("/<int:report_id>/status", methods=["PUT"])
@role_required("admin", "worker")
def update_report_status(report_id):
    report = CitizenReport.query.get_or_404(report_id)
    data = request.get_json(force=True) or {}
    new_status = data.get("status")
    if new_status not in {"pending", "in_progress", "resolved"}:
        return jsonify({"error": "Invalid status"}), 400
    report.status = new_status
    if new_status == "resolved":
        report.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify(report.to_dict()), 200
