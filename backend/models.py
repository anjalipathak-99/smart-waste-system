from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "worker", "citizen", name="user_role"),
                      nullable=False, default="citizen")
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship("CitizenReport", backref="citizen", lazy=True,
                               foreign_keys="CitizenReport.citizen_id")
    routes = db.relationship("CollectionRoute", backref="worker", lazy=True,
                              foreign_keys="CollectionRoute.worker_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "role": self.role, "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Bin(db.Model):
    __tablename__ = "bins"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    area = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    bin_type = db.Column(db.Enum("General", "Plastic", "Paper", "Metal", "Glass",
                                  "Organic", "E-waste", name="bin_type"),
                          default="General")
    capacity_kg = db.Column(db.Float, default=100.0)

    # Simulated live sensor state (mirrors latest SensorReading for fast dashboard reads)
    fill_level = db.Column(db.Float, default=0.0)       # percent 0-100
    weight_kg = db.Column(db.Float, default=0.0)
    temperature_c = db.Column(db.Float, default=28.0)
    battery_percent = db.Column(db.Float, default=100.0)

    status = db.Column(db.Enum("normal", "warning", "critical", "damaged",
                                name="bin_status"), default="normal")
    last_collected_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    readings = db.relationship("SensorReading", backref="bin", lazy=True,
                                cascade="all, delete-orphan")
    alerts = db.relationship("Alert", backref="bin", lazy=True,
                              cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "code": self.code, "area": self.area,
            "address": self.address, "latitude": self.latitude,
            "longitude": self.longitude, "bin_type": self.bin_type,
            "capacity_kg": self.capacity_kg, "fill_level": round(self.fill_level, 1),
            "weight_kg": round(self.weight_kg, 1),
            "temperature_c": round(self.temperature_c, 1),
            "battery_percent": round(self.battery_percent, 1),
            "status": self.status,
            "last_collected_at": self.last_collected_at.isoformat() if self.last_collected_at else None,
        }


class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False, index=True)
    fill_level = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    temperature_c = db.Column(db.Float, nullable=False)
    battery_percent = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id, "bin_id": self.bin_id,
            "fill_level": round(self.fill_level, 1),
            "weight_kg": round(self.weight_kg, 1),
            "temperature_c": round(self.temperature_c, 1),
            "battery_percent": round(self.battery_percent, 1),
            "recorded_at": self.recorded_at.isoformat(),
        }


class WasteClassification(db.Model):
    __tablename__ = "waste_classifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    predicted_class = db.Column(db.String(30), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    all_probabilities = db.Column(db.JSON, nullable=True)
    model_used = db.Column(db.String(60), default="MobileNetV2-TransferLearning")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "bin_id": self.bin_id,
            "image_path": self.image_path, "predicted_class": self.predicted_class,
            "confidence": round(self.confidence, 4),
            "all_probabilities": self.all_probabilities,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat(),
        }


class CitizenReport(db.Model):
    __tablename__ = "citizen_reports"

    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=True)
    report_type = db.Column(db.Enum("overflow", "damaged", "missed_collection", "other",
                                     name="report_type"), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.Enum("pending", "in_progress", "resolved",
                                name="report_status"), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id, "citizen_id": self.citizen_id,
            "citizen_name": self.citizen.name if self.citizen else None,
            "bin_id": self.bin_id, "report_type": self.report_type,
            "description": self.description, "image_path": self.image_path,
            "latitude": self.latitude, "longitude": self.longitude,
            "status": self.status, "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False)
    alert_type = db.Column(db.Enum("overflow", "damage", "sensor_fault", "high_temperature",
                                    name="alert_type"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.Enum("low", "medium", "high", name="alert_severity"),
                          default="medium")
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "bin_id": self.bin_id,
            "bin_code": self.bin.code if self.bin else None,
            "alert_type": self.alert_type, "message": self.message,
            "severity": self.severity, "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
        }


class CollectionRoute(db.Model):
    __tablename__ = "collection_routes"

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    route_date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.Enum("pending", "in_progress", "completed",
                                name="route_status"), default="pending")
    total_distance_km = db.Column(db.Float, default=0.0)
    estimated_time_min = db.Column(db.Float, default=0.0)
    algorithm_used = db.Column(db.String(30), default="A*")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stops = db.relationship("RouteStop", backref="route", lazy=True,
                             cascade="all, delete-orphan",
                             order_by="RouteStop.sequence_order")

    def to_dict(self, include_stops=True):
        data = {
            "id": self.id, "worker_id": self.worker_id,
            "worker_name": self.worker.name if self.worker else None,
            "route_date": self.route_date.isoformat() if self.route_date else None,
            "status": self.status, "total_distance_km": round(self.total_distance_km, 2),
            "estimated_time_min": round(self.estimated_time_min, 1),
            "algorithm_used": self.algorithm_used,
            "created_at": self.created_at.isoformat(),
        }
        if include_stops:
            data["stops"] = [s.to_dict() for s in self.stops]
        return data


class RouteStop(db.Model):
    __tablename__ = "route_stops"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("collection_routes.id"), nullable=False)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False)
    sequence_order = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum("pending", "collected", "skipped",
                                name="stop_status"), default="pending")
    collected_at = db.Column(db.DateTime, nullable=True)

    bin = db.relationship("Bin")

    def to_dict(self):
        return {
            "id": self.id, "route_id": self.route_id, "bin_id": self.bin_id,
            "bin": self.bin.to_dict() if self.bin else None,
            "sequence_order": self.sequence_order, "status": self.status,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
        }
