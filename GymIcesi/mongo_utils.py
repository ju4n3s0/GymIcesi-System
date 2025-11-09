# mongo_utils.py
from pymongo import MongoClient, ASCENDING
from django.conf import settings
import datetime as dt

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
    col.update_many({"userId": user_id, "status": "active"},
                    {"$set": {"status": "inactive", "until": until or now, "updatedAt": now}})

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