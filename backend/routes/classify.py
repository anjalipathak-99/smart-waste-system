import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from extensions import db
from models import WasteClassification
from ml.waste_classifier import classify_image

classify_bp = Blueprint("classify", __name__, url_prefix="/api/classify")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@classify_bp.route("", methods=["POST"])
@jwt_required()
def classify():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided (field name must be 'image')"}), 400

    file = request.files["image"]
    if file.filename == "" or not _allowed(file.filename):
        return jsonify({"error": "Invalid or missing image file. Allowed: png, jpg, jpeg, webp, bmp"}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(save_path)

    try:
        result = classify_image(save_path)
    except Exception as e:
        return jsonify({"error": f"Classification failed: {e}"}), 500

    user_id = get_jwt_identity()
    bin_id = request.form.get("bin_id", type=int)

    record = WasteClassification(
        user_id=int(user_id) if user_id else None,
        bin_id=bin_id,
        image_path=f"uploads/{unique_name}",
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        all_probabilities=result["all_probabilities"],
        model_used=result["model_used"],
    )
    db.session.add(record)
    db.session.commit()

    return jsonify(record.to_dict()), 201


@classify_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    user_id = get_jwt_identity()
    limit = int(request.args.get("limit", 50))
    records = (WasteClassification.query.filter_by(user_id=int(user_id))
               .order_by(WasteClassification.created_at.desc()).limit(limit).all())
    return jsonify([r.to_dict() for r in records]), 200


@classify_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    from sqlalchemy import func
    rows = (db.session.query(WasteClassification.predicted_class, func.count(WasteClassification.id))
            .group_by(WasteClassification.predicted_class).all())
    return jsonify({cls: count for cls, count in rows}), 200
