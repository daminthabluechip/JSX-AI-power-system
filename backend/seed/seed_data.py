import random
from datetime import date, time, timedelta

from app.extensions import db
from app.models import Depot, Event, Order, Plan, Position, Route, Stop, Vehicle

DEPOT = dict(name="Colombo Central Depot", latitude=6.9271, longitude=79.8612,
             opens_at=time(6, 0), closes_at=time(20, 0))

VEHICLES = [
    ("VH-2048", "Volvo FH16", "Nimal", 22000, 60, "on_route", "truck"),
    ("VH-1042", "Mercedes Actros", "Kamal", 18000, 50, "available", "refrigerated"),
    ("VH-3091", "DAF XF", "Sunil", 20000, 55, "on_route", "truck"),
    ("VH-2275", "Scania R500", "Ravi", 24000, 65, "maintenance", "truck"),
    ("VH-1189", "MAN TGX", "Chamara", 18000, 50, "available", "truck"),
    ("VH-4410", "Isuzu FVR", "Pradeep", 9000, 28, "available", "refrigerated"),
    ("VH-4411", "Isuzu FVR", "Lasantha", 9000, 28, "available", "van"),
    ("VH-5120", "Tata LPT", "Mahesh", 7000, 22, "available", "van"),
    ("VH-5121", "Tata LPT", "Ruwan", 7000, 22, "available", "van"),
    ("VH-6001", "Hino 500", "Dinesh", 12000, 36, "available", "flatbed"),
]

REQUIRED_TYPE = {"MEDICAL": "refrigerated", "City Pharma": "refrigerated", "BuildCo": "flatbed"}

TOWNS = [
    ("Colombo 10", 6.9300, 79.8660), ("Dehiwala", 6.8512, 79.8650), ("Negombo", 7.2008, 79.8737),
    ("Gampaha", 7.0873, 79.9925), ("Kurunegala", 7.4863, 80.3647), ("Kandy", 7.2906, 80.6337),
    ("Galle", 6.0535, 80.2210), ("Kalutara", 6.5854, 79.9607), ("Panadura", 6.7132, 79.9026),
    ("Avissawella", 6.9533, 80.2100), ("Ratnapura", 6.6828, 80.3992), ("Matara", 5.9549, 80.5550),
]

CUSTOMERS = ["DASUN", "FOOD", "MEDICAL", "Hardware", "DESHAN", "Fresh Mart", "City Pharma",
             "BuildCo", "AgroSupply", "Textile Hub"]
PRIORITIES = ["critical", "high", "medium", "medium", "low"]
WINDOWS = [(time(8, 0), time(12, 0)), (time(9, 0), time(15, 0)),
           (time(12, 0), time(17, 0)), (time(8, 0), time(17, 0))]


def reset():
    for model in (Stop, Route, Event, Position, Plan, Order, Vehicle, Depot):
        db.session.query(model).delete()
    db.session.commit()


def add_fleet():
    depot = Depot(**DEPOT)
    db.session.add(depot)
    db.session.flush()

    for reg, model, driver, kg, m3, status, kind in VEHICLES:
        db.session.add(Vehicle(
            registration=reg, model=model, driver=driver, vehicle_type=kind, weight_capacity_kg=kg,
            volume_capacity_m3=m3, shift_start=time(7, 0), shift_end=time(19, 0),
            status=status, depot_id=depot.id,
        ))


def add_orders(day):
    rng = random.Random(42)
    for i in range(50):
        town, lat, lon = rng.choice(TOWNS)
        start, end = rng.choice(WINDOWS)
        name = rng.choice(CUSTOMERS)
        db.session.add(Order(
            customer=f"{name} #{i + 1}",
            required_vehicle_type=REQUIRED_TYPE.get(name),
            address=f"{rng.randint(1, 250)} Main Street, {town}",
            latitude=lat + rng.uniform(-0.02, 0.02),
            longitude=lon + rng.uniform(-0.02, 0.02),
            weight_kg=round(rng.uniform(200, 2400), 1),
            volume_m3=round(rng.uniform(0.5, 7), 1),
            priority=rng.choice(PRIORITIES),
            target_date=day,
            earliest_arrival=start,
            latest_arrival=end,
            status="pending",
        ))


def seed(day=None):
    add_fleet()
    add_orders(day or date.today())
    db.session.commit()


def ensure_demo(days_around=1):
    if Depot.query.first() is None:
        add_fleet()
    filled = []
    for offset in range(-days_around, days_around + 1):
        day = date.today() + timedelta(days=offset)
        if Order.query.filter_by(target_date=day).count() == 0:
            add_orders(day)
            filled.append(day)
    db.session.commit()
    return filled
