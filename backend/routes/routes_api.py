from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from extensions import db
from models import Bin, CollectionRoute, RouteStop, User
from routes.auth import role_required
from ml.route_optimizer import optimize_route

routes_api_bp = Blueprint("routes_api", __name__, url_prefix="/api/routes")

# Depot / collection-yard location used as the route start/end point.
# In a real deployment this would come from a "depots" table; kept as a
# simple config constant here since the project has exactly one yard.
DEPOT = {"id": "depot", "latitude": 28.6692, "longitude": 77.4538, "name": "Municipal Collection Yard"}


@routes_api_bp.route("/optimize", methods=["POST"])
@role_required("admin")
def generate_optimized_route():
    """
    Body: { "worker_id": int, "bin_ids": [int, ...] (optional -- defaults to
    all bins with status in [warning, critical]), "algorithm": "A*"|"Dijkstra" }
    """
    data = request.get_json(force=True) or {}
    worker_id = data.get("worker_id")
    algorithm = data.get("algorithm", "A*")

    if not worker_id or not User.query.get(worker_id):
        return jsonify({"error": "Valid worker_id is required"}), 400

    bin_ids = data.get("bin_ids")
    if bin_ids:
        bins = Bin.query.filter(Bin.id.in_(bin_ids)).all()
    else:
        bins = Bin.query.filter(Bin.status.in_(["warning", "critical"])).all()

    if not bins:
        return jsonify({"error": "No bins need collection right now"}), 400

    bin_payload = [{"id": b.id, "latitude": b.latitude, "longitude": b.longitude} for b in bins]
    result = optimize_route(DEPOT, bin_payload, algorithm=algorithm)

    route = CollectionRoute(
        worker_id=worker_id, route_date=date.today(), status="pending",
        total_distance_km=result["total_distance_km"],
        estimated_time_min=result["estimated_time_min"],
        algorithm_used=algorithm,
    )
    db.session.add(route)
    db.session.flush()  # get route.id before commit

    for seq, bin_id in enumerate(result["order"], start=1):
        stop = RouteStop(route_id=route.id, bin_id=bin_id, sequence_order=seq)
        db.session.add(stop)

    db.session.commit()

    response = route.to_dict()
    response["legs"] = result["legs"]
    response["depot"] = DEPOT
    return jsonify(response), 201


@routes_api_bp.route("", methods=["GET"])
@jwt_required()
def list_routes():
    claims = get_jwt()
    q = CollectionRoute.query
    if claims.get("role") == "worker":
        q = q.filter_by(worker_id=int(get_jwt_identity()))
    worker_id = request.args.get("worker_id", type=int)
    if worker_id:
        q = q.filter_by(worker_id=worker_id)
    routes = q.order_by(CollectionRoute.created_at.desc()).all()
    return jsonify([r.to_dict() for r in routes]), 200


@routes_api_bp.route("/<int:route_id>", methods=["GET"])
@jwt_required()
def get_route(route_id):
    route = CollectionRoute.query.get_or_404(route_id)
    data = route.to_dict()
    data["depot"] = DEPOT
    return jsonify(data), 200


@routes_api_bp.route("/stops/<int:stop_id>/complete", methods=["POST"])
@role_required("admin", "worker")
def complete_stop(stop_id):
    from datetime import datetime
    from simulation.sensor_simulator import collect_bin
    from models import SensorReading

    stop = RouteStop.query.get_or_404(stop_id)
    stop.status = "collected"
    stop.collected_at = datetime.utcnow()

    bin_obj = Bin.query.get(stop.bin_id)
    if bin_obj:
        collect_bin(bin_obj)
        db.session.add(SensorReading(bin_id=bin_obj.id, fill_level=bin_obj.fill_level,
                                      weight_kg=bin_obj.weight_kg, temperature_c=bin_obj.temperature_c,
                                      battery_percent=bin_obj.battery_percent))

    route = CollectionRoute.query.get(stop.route_id)
    all_done = all(s.status != "pending" for s in route.stops)
    if all_done:
        route.status = "completed"
    elif route.status == "pending":
        route.status = "in_progress"

    db.session.commit()
    return jsonify(stop.to_dict()), 200
