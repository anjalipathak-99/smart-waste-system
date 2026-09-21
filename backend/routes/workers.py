from flask import Blueprint, jsonify
from models import User
from routes.auth import role_required

workers_bp = Blueprint("workers", __name__, url_prefix="/api/workers")


@workers_bp.route("", methods=["GET"])
@role_required("admin")
def list_workers():
    workers = User.query.filter_by(role="worker").all()
    return jsonify([w.to_dict() for w in workers]), 200
