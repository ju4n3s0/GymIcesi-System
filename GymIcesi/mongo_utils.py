# mongo_utils.py
from django import db
from pymongo import MongoClient, ASCENDING
from django.conf import settings
import datetime as dt
from bson import ObjectId
from pymongo import MongoClient
from bson import ObjectId
import datetime





_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGO_URI,
            connect=False,
            serverSelectionTimeoutMS=settings.MONGO_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGO_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGO_TIMEOUT_MS,
        )
    return _client

def get_db():
    return get_client()[settings.MONGO_DBNAME]

def ensure_indexes():
    col = get_db()["trainer_assignments"]
    # → única “activa” por usuario usando índice parcial sobre status="active"
    col.create_index(
        [("userId", ASCENDING)],
        unique=True,
        name="uq_user_active",
        partialFilterExpression={"status": "active"},
    )
    col.create_index([("trainerId", ASCENDING)], name="ix_trainer")
    col.create_index([("status", ASCENDING)], name="ix_status")
    return col

def list_assignments(filter_:dict=None, limit:int=200):
    col = ensure_indexes()
    q = filter_ or {}
    return list(col.find(q).sort([("status", -1), ("since", -1)]).limit(limit))

def upsert_active_assignment(*, user_id:str, trainer_id:str, since=None, until=None):
    """
    Deja UNA activa por usuario:
      1) inactiva cualquier activa previa
      2) inserta nueva con status='active'
    """
    col = ensure_indexes()
    now = dt.datetime.utcnow()

    # 1) inactivar previas
    col.update_many(
        {"userId": user_id, "status": "active"},
        {"$set": {"status": "ended", "until": until or now, "updatedAt": now}}
    )

    # 2) insertar nueva activa
    doc = {
        "userId": user_id,
        "trainerId": trainer_id,
        "status": "active",
        "since": since or now,
        "until": until,            # normalmente None
        "createdAt": now,
        "updatedAt": now,
    }
    res = col.insert_one(doc)
    return str(res.inserted_id)

def inactivate_assignment_by_id(_id):
    from bson import ObjectId
    col = ensure_indexes()
    now = dt.datetime.utcnow()
    col.update_one({"_id": ObjectId(_id)}, {"$set": {"status": "inactive", "until": now, "updatedAt": now}})

# --- Progreso de usuario (nuevo) ---
def ensure_progress_indexes():
    col = get_db()["progress_logs"]
    col.create_index([("userId", ASCENDING)], name="ix_user")
    col.create_index([("date", ASCENDING)], name="ix_date")
    return col


def list_progress_logs(user_id: str, limit: int = 100):
    """
    Devuelve los registros de progreso de un usuario ordenados por fecha descendente.
    """
    col = ensure_progress_indexes()
    return list(col.find({"userId": user_id}).sort("date", -1).limit(limit))


def insert_progress_log(user_id, exercise_id, date, reps=None, weight=None):
    db = get_db()
    exercise_oid = ObjectId(exercise_id)

    # ✅ obtener nombre real del ejercicio
    exercise_name = db.exercises.find_one({"_id": exercise_oid}).get("name", "Desconocido")

    doc = {
        "userId": user_id,
        "date": date,
        "entries": [
            {
                "exerciseId": exercise_oid,  # ✅ guardamos como ObjectId real
                "exerciseName": exercise_name,  # ✅ requerido por el schema
                "sets": [
                    {
                        "reps": reps,
                        "weight": weight
                    }
                ]
            }
        ]
    }

    return db.progress_logs.insert_one(doc)


def get_exercise_name_by_id(exercise_id):
    db = get_db()
    exercise = db.exercises.find_one({"_id": ObjectId(exercise_id)})
    return exercise.get("name", "Desconocido") if exercise else "Desconocido"



def get_progress_logs_by_user(user_id):
    db = get_db()
    return list(
        db.progress_logs.find({"userId": user_id}).sort("date", -1)
    )



from typing import Iterable, Dict, Any

def ping() -> dict:
    """Prueba conexión/auth rápidamente (útil para debug)."""
    return get_client().admin.command("ping")

def get_collection():
    """Acceso directo a la colección de asignaciones con índices garantizados."""
    return ensure_indexes()

def get_active_assignment(user_id: str) -> dict | None:
    """Devuelve el documento ACTIVO de un usuario (o None)."""
    col = get_collection()
    return col.find_one(
        {"userId": user_id, "status": "active"},
        {"userId": 1, "trainerId": 1, "since": 1, "until": 1}  # proyección
    )

def get_active_map(user_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """
    Dado un iterable de usernames, retorna un dict:
      { "<username>": {doc activo}, ... }
    Solo devuelve entradas para los que tengan asignación activa.
    """
    ulist = list(user_ids)
    if not ulist:
        return {}

    col = get_collection()
    cur = col.find(
        {"userId": {"$in": ulist}, "status": "active"},
        {"userId": 1, "trainerId": 1, "since": 1, "until": 1}
    )
    return {doc["userId"]: doc for doc in cur}
