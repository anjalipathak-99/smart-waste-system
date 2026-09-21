"""
Virtual IoT sensor simulator.

Because this is a software-only project (no ESP32 / physical ultrasonic,
load-cell or temperature sensors), this module generates realistic,
physically-plausible sensor readings so every downstream feature (alerts,
dashboards, ML prediction, route optimization) operates on real, evolving
data rather than static fixtures.

Model per bin:
- fill_level rises over time following the bin's assigned fill-rate
  (liters/kg accumulated per hour, itself a function of bin_type and a
  per-bin random "traffic" factor), with added Gaussian sensor noise.
- weight_kg rises roughly proportional to fill_level with type-dependent
  density (e.g. metal/glass denser than paper/plastic) + noise.
- temperature_c fluctuates around an ambient baseline with daily cycle
  (warmer in afternoon) + small random walk, and organic bins run a little
  warmer due to decomposition.
- When fill_level crosses 85% -> "critical" status + overflow Alert row.
  When it crosses 60% -> "warning".
  A small random chance per tick simulates a "damaged" sensor/bin needing
  a citizen-style alert.
- Collection resets fill_level/weight to ~0-5% and updates last_collected_at.

This runs as an APScheduler background job (see app.py) every
SIMULATION_INTERVAL_SECONDS, and also exposes a manual `tick()` you can
call from a REST endpoint for on-demand demo control.
"""
import random
import math
from datetime import datetime

FILL_RATE_BY_TYPE = {   # percent fill gained per hour, baseline
    "General": 1.8, "Plastic": 1.4, "Paper": 1.2, "Metal": 0.6,
    "Glass": 0.7, "Organic": 2.4, "E-waste": 0.3,
}
DENSITY_BY_TYPE = {      # kg per 1% fill at full capacity, rough proxy
    "General": 0.9, "Plastic": 0.5, "Paper": 0.6, "Metal": 1.6,
    "Glass": 1.8, "Organic": 1.0, "E-waste": 1.3,
}

WARNING_THRESHOLD = 60.0
CRITICAL_THRESHOLD = 85.0
DAMAGE_PROBABILITY_PER_TICK = 0.002  # small chance any tick "damages" a bin


def _ambient_temperature(now: datetime):
    # simple daily sinusoidal cycle, peak mid-afternoon, base 26C
    hour_frac = now.hour + now.minute / 60.0
    return 26.0 + 6.0 * math.sin((hour_frac - 8) / 24 * 2 * math.pi)


def tick_bin(bin_obj, minutes_elapsed=1.0):
    """Advances one bin's simulated sensors by `minutes_elapsed` minutes.
    Mutates and returns the bin_obj (SQLAlchemy model instance) fields;
    caller is responsible for committing and logging a SensorReading."""
    if bin_obj.status == "damaged":
        return bin_obj  # damaged bins stop reporting sane data until fixed

    hours = minutes_elapsed / 60.0
    base_rate = FILL_RATE_BY_TYPE.get(bin_obj.bin_type, 1.5)
    traffic_factor = random.uniform(0.6, 1.6)   # per-tick variability (foot traffic, events)
    noise = random.gauss(0, 0.4)

    delta_fill = max(base_rate * traffic_factor * hours + noise, 0)
    bin_obj.fill_level = min(bin_obj.fill_level + delta_fill, 100.0)

    density = DENSITY_BY_TYPE.get(bin_obj.bin_type, 1.0)
    target_weight = (bin_obj.fill_level / 100.0) * bin_obj.capacity_kg * (density / 1.0)
    bin_obj.weight_kg = max(target_weight + random.gauss(0, 0.5), 0)

    ambient = _ambient_temperature(datetime.utcnow())
    organic_bonus = 4.0 if bin_obj.bin_type == "Organic" else 0.0
    bin_obj.temperature_c = ambient + organic_bonus + random.gauss(0, 0.6)

    bin_obj.battery_percent = max(bin_obj.battery_percent - random.uniform(0, 0.05), 2.0)

    if random.random() < DAMAGE_PROBABILITY_PER_TICK:
        bin_obj.status = "damaged"
    elif bin_obj.fill_level >= CRITICAL_THRESHOLD:
        bin_obj.status = "critical"
    elif bin_obj.fill_level >= WARNING_THRESHOLD:
        bin_obj.status = "warning"
    else:
        bin_obj.status = "normal"

    return bin_obj


def collect_bin(bin_obj):
    """Simulates a worker emptying the bin."""
    bin_obj.fill_level = round(random.uniform(0, 5), 1)
    bin_obj.weight_kg = round(bin_obj.fill_level / 100.0 * bin_obj.capacity_kg, 1)
    bin_obj.status = "normal"
    bin_obj.last_collected_at = datetime.utcnow()
    return bin_obj
