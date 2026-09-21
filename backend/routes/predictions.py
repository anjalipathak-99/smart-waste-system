from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from extensions import db
from models import Bin, SensorReading
from routes.auth import role_required
from ml.fill_predictor import (
    train_overflow_model, predict_bin_overflow,
    train_waste_forecast_model, forecast_waste_generation,
)

predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")


def _fetch_reading_rows():
    rows = (db.session.query(
        SensorReading.bin_id, SensorReading.fill_level, SensorReading.weight_kg,
        SensorReading.temperature_c, SensorReading.recorded_at,
        Bin.bin_type, Bin.capacity_kg, Bin.last_collected_at,
    ).join(Bin, Bin.id == SensorReading.bin_id).all())
    return [dict(zip(["bin_id", "fill_level", "weight_kg", "temperature_c",
                       "recorded_at", "bin_type", "capacity_kg", "last_collected_at"], r))
            for r in rows]


@predictions_bp.route("/train", methods=["POST"])
@role_required("admin")
def train_models():
    rows = _fetch_reading_rows()
    overflow_metrics = train_overflow_model(rows)

    daily_rows = _daily_collection_totals()
    forecast_metrics = train_waste_forecast_model(daily_rows)

    return jsonify({"overflow_model": overflow_metrics, "forecast_model": forecast_metrics}), 200


@predictions_bp.route("/overflow", methods=["GET"])
@jwt_required()
def overflow_predictions():
    bins = Bin.query.all()
    results = []
    for b in bins:
        recent = (SensorReading.query.filter_by(bin_id=b.id)
                  .order_by(SensorReading.recorded_at.desc()).limit(12).all())
        recent_dicts = [{"fill_level": r.fill_level, "recorded_at": r.recorded_at.isoformat()}
                         for r in reversed(recent)]
        pred = predict_bin_overflow(b.to_dict() | {
            "last_collected_at": b.last_collected_at.isoformat() if b.last_collected_at else None
        }, recent_dicts)
        pred["bin_code"] = b.code
        pred["area"] = b.area
        results.append(pred)

    results.sort(key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}[r["risk_level"]])
    return jsonify(results), 200


def _daily_collection_totals():
    """Aggregates simulated sensor_readings into per-area/day totals to
    stand in for historical 'kg collected per day' records."""
    rows = (db.session.query(
        Bin.area, func.date(SensorReading.recorded_at).label("date"),
        func.sum(SensorReading.weight_kg).label("total_kg"),
    ).join(Bin, Bin.id == SensorReading.bin_id)
        .group_by(Bin.area, func.date(SensorReading.recorded_at)).all())
    return [{"area": r[0], "date": str(r[1]), "total_kg": float(r[2] or 0)} for r in rows]


@predictions_bp.route("/waste-generation", methods=["GET"])
@jwt_required()
def waste_generation_forecast():
    days_ahead = int(request.args.get("days", 7))
    daily_rows = _daily_collection_totals()
    forecast = forecast_waste_generation(daily_rows, days_ahead=days_ahead)
    return jsonify(forecast), 200
