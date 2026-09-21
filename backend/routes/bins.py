from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models import Bin, SensorReading, Alert
from routes.auth import role_required
from simulation.sensor_simulator import tick_bin, collect_bin, WARNING_THRESHOLD, CRITICAL_THRESHOLD

bins_bp = Blueprint("bins", __name__, url_prefix="/api/bins")


@bins_bp.route("", methods=["GET"])
@jwt_required()
def list_bins():
    area = request.args.get("area")
    status = request.args.get("status")
    q = Bin.query
    if area:
        q = q.filter(Bin.area == area)
    if status:
        q = q.filter(Bin.status == status)
    bins = q.order_by(Bin.id.asc()).all()
    return jsonify([b.to_dict() for b in bins]), 200


@bins_bp.route("/<int:bin_id>", methods=["GET"])
@jwt_required()
def get_bin(bin_id):
    b = Bin.query.get_or_404(bin_id)
    return jsonify(b.to_dict()), 200


@bins_bp.route("/<int:bin_id>/history", methods=["GET"])
@jwt_required()
def bin_history(bin_id):
    limit = int(request.args.get("limit", 100))
    readings = (SensorReading.query.filter_by(bin_id=bin_id)
                .order_by(SensorReading.recorded_at.desc()).limit(limit).all())
    return jsonify([r.to_dict() for r in reversed(readings)]), 200


@bins_bp.route("", methods=["POST"])
@role_required("admin")
def create_bin():
    data = request.get_json(force=True) or {}
    required = ["code", "area", "latitude", "longitude"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    if Bin.query.filter_by(code=data["code"]).first():
        return jsonify({"error": "Bin code already exists"}), 409

    b = Bin(
        code=data["code"], area=data["area"], address=data.get("address", ""),
        latitude=data["latitude"], longitude=data["longitude"],
        bin_type=data.get("bin_type", "General"),
        capacity_kg=data.get("capacity_kg", 100.0),
        fill_level=data.get("fill_level", 0.0),
        weight_kg=data.get("weight_kg", 0.0),
        temperature_c=data.get("temperature_c", 28.0),
        battery_percent=data.get("battery_percent", 100.0),
        last_collected_at=datetime.utcnow(),
    )
    db.session.add(b)
    db.session.commit()
    return jsonify(b.to_dict()), 201


@bins_bp.route("/<int:bin_id>", methods=["PUT"])
@role_required("admin")
def update_bin(bin_id):
    b = Bin.query.get_or_404(bin_id)
    data = request.get_json(force=True) or {}
    for field in ["area", "address", "latitude", "longitude", "bin_type", "capacity_kg"]:
        if field in data:
            setattr(b, field, data[field])
    db.session.commit()
    return jsonify(b.to_dict()), 200


@bins_bp.route("/<int:bin_id>", methods=["DELETE"])
@role_required("admin")
def delete_bin(bin_id):
    b = Bin.query.get_or_404(bin_id)
    db.session.delete(b)
    db.session.commit()
    return jsonify({"message": "Bin deleted"}), 200


@bins_bp.route("/<int:bin_id>/collect", methods=["POST"])
@role_required("admin", "worker")
def mark_collected(bin_id):
    """Simulates a worker emptying a bin -- resets fill level/weight."""
    b = Bin.query.get_or_404(bin_id)
    collect_bin(b)
    reading = SensorReading(bin_id=b.id, fill_level=b.fill_level, weight_kg=b.weight_kg,
                             temperature_c=b.temperature_c, battery_percent=b.battery_percent)
    db.session.add(reading)
    db.session.commit()
    return jsonify(b.to_dict()), 200


@bins_bp.route("/<int:bin_id>/repair", methods=["POST"])
@role_required("admin")
def repair_bin(bin_id):
    b = Bin.query.get_or_404(bin_id)
    b.status = "normal"
    b.fill_level = min(b.fill_level, 10.0)
    db.session.commit()
    return jsonify(b.to_dict()), 200


@bins_bp.route("/simulate/tick", methods=["POST"])
@role_required("admin")
def manual_simulate_tick():
    """Manually advances the virtual sensor simulation by N minutes for all
    bins -- lets a judge/demo trigger fill-level changes on demand instead
    of waiting for the background scheduler."""
    minutes = float(request.get_json(silent=True, force=True).get("minutes", 30)) \
        if request.get_json(silent=True) else 30.0

    bins = Bin.query.all()
    new_alerts = []
    for b in bins:
        prev_status = b.status
        tick_bin(b, minutes_elapsed=minutes)
        reading = SensorReading(bin_id=b.id, fill_level=b.fill_level, weight_kg=b.weight_kg,
                                 temperature_c=b.temperature_c, battery_percent=b.battery_percent)
        db.session.add(reading)

        if b.status == "critical" and prev_status != "critical":
            alert = Alert(bin_id=b.id, alert_type="overflow", severity="high",
                           message=f"Bin {b.code} is at {b.fill_level:.0f}% capacity and needs urgent collection.")
            db.session.add(alert)
            new_alerts.append(alert)
        elif b.status == "damaged" and prev_status != "damaged":
            alert = Alert(bin_id=b.id, alert_type="sensor_fault", severity="medium",
                           message=f"Bin {b.code} sensor reported a fault / possible physical damage.")
            db.session.add(alert)
            new_alerts.append(alert)
        elif b.temperature_c > 45 and prev_status != "warning":
            alert = Alert(bin_id=b.id, alert_type="high_temperature", severity="medium",
                           message=f"Bin {b.code} temperature is unusually high ({b.temperature_c:.1f}\u00b0C).")
            db.session.add(alert)
            new_alerts.append(alert)

    db.session.commit()
    return jsonify({
        "message": f"Simulation advanced by {minutes} minutes for {len(bins)} bins.",
        "new_alerts": [a.to_dict() for a in new_alerts],
        "bins": [b.to_dict() for b in bins],
    }), 200
