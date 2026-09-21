"""
Creates all tables and populates the database with:
  - Demo user accounts (admin / worker / citizen)
  - ~20 virtual smart bins spread across city areas with real-ish coordinates
  - 14 days of simulated historical sensor readings per bin (hourly), so the
    scikit-learn prediction models have real data to train on immediately
  - A handful of sample citizen reports and alerts

Run with:  python seed_data.py
Re-running wipes and recreates all tables (confirmation prompt shown).
"""
import random
from datetime import datetime, timedelta

from app import create_app
from extensions import db
from models import User, Bin, SensorReading, Alert, CitizenReport, WasteClassification
from simulation.sensor_simulator import tick_bin, collect_bin

random.seed(42)

# Ghaziabad / NCR-area coordinates used as a realistic demo city layout
AREAS = {
    "Vaishali":       (28.6469, 77.3389),
    "Indirapuram":    (28.6461, 77.3720),
    "Raj Nagar":      (28.6809, 77.4360),
    "Kaushambi":      (28.6461, 77.3169),
    "Vasundhara":     (28.6631, 77.3868),
    "Sahibabad":      (28.6890, 77.3540),
}
BIN_TYPES = ["General", "Plastic", "Paper", "Metal", "Glass", "Organic", "E-waste"]


def jitter(base, spread=0.01):
    return base + random.uniform(-spread, spread)


def seed():
    app = create_app()
    with app.app_context():
        print("Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()

        # ---------------- Users ----------------
        admin = User(name="Admin User", email="admin@smartwaste.gov.in", role="admin", phone="9990000001")
        admin.set_password("admin123")

        workers = []
        for i, wname in enumerate(["Ramesh Kumar", "Suresh Yadav", "Anil Sharma"], start=1):
            w = User(name=wname, email=f"worker{i}@smartwaste.gov.in", role="worker",
                     phone=f"999000001{i}")
            w.set_password("worker123")
            workers.append(w)

        citizens = []
        for i, cname in enumerate(["Priya Singh", "Amit Verma", "Neha Gupta"], start=1):
            c = User(name=cname, email=f"citizen{i}@example.com", role="citizen",
                     phone=f"999000002{i}")
            c.set_password("citizen123")
            citizens.append(c)

        db.session.add_all([admin, *workers, *citizens])
        db.session.commit()
        print(f"Created {1 + len(workers) + len(citizens)} users.")

        # ---------------- Bins ----------------
        bins = []
        bin_counter = 1
        for area, (lat, lon) in AREAS.items():
            for _ in range(random.randint(3, 4)):
                bin_type = random.choice(BIN_TYPES)
                b = Bin(
                    code=f"BIN-{bin_counter:03d}",
                    area=area,
                    address=f"{area} Sector {random.randint(1, 20)}, Ghaziabad",
                    latitude=round(jitter(lat), 6),
                    longitude=round(jitter(lon), 6),
                    bin_type=bin_type,
                    capacity_kg=random.choice([80, 100, 120, 150]),
                    fill_level=round(random.uniform(5, 30), 1),
                    weight_kg=0,
                    temperature_c=round(random.uniform(25, 32), 1),
                    battery_percent=round(random.uniform(70, 100), 1),
                    status="normal",
                    last_collected_at=datetime.utcnow() - timedelta(hours=random.randint(1, 10)),
                )
                b.weight_kg = round((b.fill_level / 100.0) * b.capacity_kg, 1)
                bins.append(b)
                bin_counter += 1

        db.session.add_all(bins)
        db.session.commit()
        print(f"Created {len(bins)} bins across {len(AREAS)} areas.")

        # ---------------- 14 days of hourly historical sensor readings ----------------
        print("Simulating 14 days of hourly sensor history (this trains the ML models)...")
        start_time = datetime.utcnow() - timedelta(days=14)

        # reset bins to a low starting fill for a clean simulation run
        for b in bins:
            b.fill_level = round(random.uniform(0, 10), 1)
            b.weight_kg = round((b.fill_level / 100.0) * b.capacity_kg, 1)
            b.last_collected_at = start_time

        readings_batch = []
        current_time = start_time
        hours_total = 14 * 24
        for h in range(hours_total):
            current_time = start_time + timedelta(hours=h + 1)
            for b in bins:
                tick_bin(b, minutes_elapsed=60)
                # simulate a collection truck emptying bins that get too full,
                # roughly matching a realistic collection schedule
                if b.fill_level >= 80 or (b.status == "damaged" and random.random() < 0.3):
                    collect_bin(b)
                readings_batch.append(SensorReading(
                    bin_id=b.id, fill_level=b.fill_level, weight_kg=b.weight_kg,
                    temperature_c=b.temperature_c, battery_percent=b.battery_percent,
                    recorded_at=current_time,
                ))
            if len(readings_batch) >= 2000:
                db.session.bulk_save_objects(readings_batch)
                readings_batch = []

        if readings_batch:
            db.session.bulk_save_objects(readings_batch)
        db.session.commit()
        print(f"Inserted {hours_total * len(bins)} historical sensor readings.")

        # bring a few bins into interesting current-day states for the demo
        for b in random.sample(bins, k=min(4, len(bins))):
            b.fill_level = round(random.uniform(80, 96), 1)
            b.weight_kg = round((b.fill_level / 100.0) * b.capacity_kg, 1)
            b.status = "critical"
        for b in random.sample([bx for bx in bins if bx.status != "critical"], k=min(3, len(bins))):
            b.fill_level = round(random.uniform(60, 79), 1)
            b.status = "warning"
        damaged_bin = random.choice(bins)
        damaged_bin.status = "damaged"
        db.session.commit()

        # ---------------- Sample alerts ----------------
        for b in bins:
            if b.status == "critical":
                db.session.add(Alert(bin_id=b.id, alert_type="overflow", severity="high",
                                      message=f"Bin {b.code} is at {b.fill_level:.0f}% capacity and needs urgent collection."))
            elif b.status == "damaged":
                db.session.add(Alert(bin_id=b.id, alert_type="sensor_fault", severity="medium",
                                      message=f"Bin {b.code} sensor reported a fault / possible physical damage."))
        db.session.commit()

        # ---------------- Sample citizen reports ----------------
        sample_reports = [
            (citizens[0], bins[0], "overflow", "Bin near the market is overflowing since yesterday."),
            (citizens[1], bins[3], "damaged", "The bin lid is broken and waste is scattered around."),
            (citizens[2], bins[6], "missed_collection", "Truck did not come to collect this week."),
        ]
        for citizen, b, rtype, desc in sample_reports:
            db.session.add(CitizenReport(
                citizen_id=citizen.id, bin_id=b.id, report_type=rtype, description=desc,
                latitude=jitter(b.latitude, 0.002), longitude=jitter(b.longitude, 0.002),
                status=random.choice(["pending", "in_progress"]),
            ))
        db.session.commit()

        print("\nSeed complete! Demo credentials:")
        print("  Admin   -> admin@smartwaste.gov.in   / admin123")
        print("  Worker  -> worker1@smartwaste.gov.in / worker123")
        print("  Citizen -> citizen1@example.com      / citizen123")


if __name__ == "__main__":
    seed()
