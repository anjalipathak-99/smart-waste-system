from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from extensions import db
from models import Bin, Alert, CitizenReport, WasteClassification, CollectionRoute, User

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    total_bins = Bin.query.count()
    status_counts = dict(db.session.query(Bin.status, func.count(Bin.id)).group_by(Bin.status).all())
    type_counts = dict(db.session.query(Bin.bin_type, func.count(Bin.id)).group_by(Bin.bin_type).all())
    area_avg_fill = db.session.query(Bin.area, func.avg(Bin.fill_level)).group_by(Bin.area).all()

    unresolved_alerts = Alert.query.filter_by(is_resolved=False).count()
    pending_reports = CitizenReport.query.filter_by(status="pending").count()
    total_classifications = WasteClassification.query.count()
    active_routes = CollectionRoute.query.filter(CollectionRoute.status != "completed").count()
    total_workers = User.query.filter_by(role="worker").count()

    week_ago = datetime.utcnow() - timedelta(days=7)
    classification_breakdown = dict(
        db.session.query(WasteClassification.predicted_class, func.count(WasteClassification.id))
        .filter(WasteClassification.created_at >= week_ago)
        .group_by(WasteClassification.predicted_class).all()
    )

    return jsonify({
        "total_bins": total_bins,
        "status_counts": status_counts,
        "type_counts": type_counts,
        "area_avg_fill": {area: round(float(avg), 1) for area, avg in area_avg_fill},
        "unresolved_alerts": unresolved_alerts,
        "pending_reports": pending_reports,
        "total_classifications": total_classifications,
        "active_routes": active_routes,
        "total_workers": total_workers,
        "classification_breakdown_7d": classification_breakdown,
    }), 200


@dashboard_bp.route("/alerts", methods=["GET"])
@jwt_required()
def alerts():
    rows = Alert.query.order_by(Alert.created_at.desc()).limit(100).all()
    return jsonify([a.to_dict() for a in rows]), 200


@dashboard_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@jwt_required()
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_resolved = True
    db.session.commit()
    return jsonify(alert.to_dict()), 200
