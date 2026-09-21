import os
from flask import Flask, jsonify, send_from_directory
from config import Config
from extensions import db, jwt, cors, scheduler


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    from routes.auth import auth_bp
    from routes.bins import bins_bp
    from routes.classify import classify_bp
    from routes.reports import reports_bp
    from routes.routes_api import routes_api_bp
    from routes.predictions import predictions_bp
    from routes.dashboard import dashboard_bp
    from routes.workers import workers_bp

    for bp in [auth_bp, bins_bp, classify_bp, reports_bp, routes_api_bp,
               predictions_bp, dashboard_bp, workers_bp]:
        app.register_blueprint(bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "simulation_mode": app.config["SIMULATION_MODE"]}), 200

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large"}), 413

    # ---------------- Background simulation scheduler ----------------
    if app.config["SIMULATION_MODE"] and not scheduler.running:
        scheduler.init_app(app)

        @scheduler.task("interval", id="sensor_simulation_tick",
                         seconds=app.config["SIMULATION_INTERVAL_SECONDS"])
        def scheduled_tick():
            with app.app_context():
                from models import Bin, SensorReading, Alert
                from simulation.sensor_simulator import tick_bin
                minutes = app.config["SIMULATION_INTERVAL_SECONDS"] / 60.0 * 20  # accelerate demo time
                bins = Bin.query.all()
                for b in bins:
                    prev_status = b.status
                    tick_bin(b, minutes_elapsed=minutes)
                    db.session.add(SensorReading(
                        bin_id=b.id, fill_level=b.fill_level, weight_kg=b.weight_kg,
                        temperature_c=b.temperature_c, battery_percent=b.battery_percent))
                    if b.status == "critical" and prev_status != "critical":
                        db.session.add(Alert(bin_id=b.id, alert_type="overflow", severity="high",
                                              message=f"Bin {b.code} reached {b.fill_level:.0f}% - needs collection."))
                    elif b.status == "damaged" and prev_status != "damaged":
                        db.session.add(Alert(bin_id=b.id, alert_type="sensor_fault", severity="medium",
                                              message=f"Bin {b.code} sensor fault detected."))
                db.session.commit()

        scheduler.start()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
