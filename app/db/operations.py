# app/db/operations.py

from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any
from app.db.clients import get_async_redis_client, get_mongo_db
import logging

from pymongo import ReturnDocument

logger = logging.getLogger("mtca")


async def get_tenant_config(
    org_id: str,
    branch_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetches tenant rules. Checks Redis cache first, falls back to MongoDB.
    """
    redis = await get_async_redis_client()
    cache_key = f"tenant_config:{org_id}:{branch_id}"

    # 1. Try Redis Cache
    cached_config = await redis.get(cache_key)
    if cached_config:
        return json.loads(cached_config)

    # 2. Fallback to MongoDB
    mongo_db = get_mongo_db()

    config = await mongo_db["tenant_configurations"].find_one(
        {
            "orgId": org_id,
            "branchId": branch_id,
        }
    )

    if config:
        config.pop("_id", None)
        await redis.setex(cache_key, 86400, json.dumps(config))
        return config

    return None


async def insert_captured_lead(
    org_id: str,
    branch_id: str,
    lead_dict: dict,
    user_email: str,
    username: str,
) -> str:
    """
    Pure database CRUD utility executed against the 'captured_leads' collection.
    Builds the document payload with immutable audit relations.
    """
    db = get_mongo_db()
    collection = db["captured_leads"]

    document = {
        "orgId": org_id,
        "branchId": branch_id,
        "leadDetails": lead_dict,
        "status": "unassigned_new",
        "capturedAt": datetime.now(timezone.utc),
        "createdBy": {
            "email": user_email,
            "username": username,
        },
    }

    result = await collection.insert_one(document)
    return str(result.inserted_id)



def _now() -> datetime:
    return datetime.now(timezone.utc)


def _col(org_id: str):
    """One collection per org -- fast queries, physical tenant separation."""
    return get_mongo_db()[f"bookings_{org_id}"]


# ----------------------------------------------------------------------------
# WRITE
# ----------------------------------------------------------------------------

async def db_insert_booking(
    *,
    org_id: str,
    branch_id: str,
    user_id: str,
    user_email: str,
    event_id: str,
    service: str,
    start_iso: str,
    end_iso: str,
    tz: str,
) -> str:
    """
    Inserts a new booking record. Returns the inserted document's string _id.
    Caller is responsible for sequencing: Calendar write must succeed before
    this is called. If this insert fails the Calendar event still exists and
    can be reconciled manually -- never roll back a confirmed Calendar event
    because of a Mongo failure.
    """
    doc = {
        "event_id":   event_id,
        "org_id":     org_id,
        "branch_id":  branch_id,
        "user_id":    user_id,
        "user_email": user_email.strip().lower(),
        "service":    service,
        "start_iso":  start_iso,
        "end_iso":    end_iso,
        "timezone":   tz,
        "status":     "active",
        "created_at": _now(),
        "updated_at": _now(),
    }
    result = await _col(org_id).insert_one(doc)
    inserted_id = str(result.inserted_id)
    logger.info("db_insert_booking -- mongo_id=%s event_id=%s", inserted_id, event_id)
    return inserted_id


async def db_update_booking(
    *,
    org_id: str,
    event_id: str,
    new_start_iso: str,
    new_end_iso: str,
) -> Optional[dict]:
    """
    Updates start/end and flips status to 'rescheduled'.
    Returns the updated document or None if the event_id wasn't found.
    """
    doc = await _col(org_id).find_one_and_update(
        {"event_id": event_id, "org_id": org_id},
        {"$set": {
            "start_iso":  new_start_iso,
            "end_iso":    new_end_iso,
            "status":     "rescheduled",
            "updated_at": _now(),
        }},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        doc["_id"] = str(doc["_id"])
        logger.info("db_update_booking -- event_id=%s", event_id)
    else:
        logger.warning("db_update_booking: event_id not found -- %s", event_id)
    return doc


async def db_cancel_booking(
    *,
    org_id: str,
    event_id: str,
) -> Optional[dict]:
    """
    Soft-deletes by setting status to 'cancelled'. Preserves audit trail.
    Returns the updated document or None if not found.
    """
    doc = await _col(org_id).find_one_and_update(
        {"event_id": event_id, "org_id": org_id},
        {"$set": {
            "status":     "cancelled",
            "updated_at": _now(),
        }},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        doc["_id"] = str(doc["_id"])
        logger.info("db_cancel_booking -- event_id=%s", event_id)
    else:
        logger.warning("db_cancel_booking: event_id not found -- %s", event_id)
    return doc


# ----------------------------------------------------------------------------
# READ
# ----------------------------------------------------------------------------

async def db_get_user_bookings(
    *,
    org_id: str,
    branch_id: str,
    user_id: str,
    status: str = "active",
) -> list[dict]:
    """
    Returns all booking records matching org/branch/user/status,
    sorted ascending by start time.
    """
    cursor = _col(org_id).find(
        {"user_id": user_id, "branch_id": branch_id, "status": status},
        sort=[("start_iso", 1)],
    )
    bookings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        bookings.append(doc)

    logger.info(
        "db_get_user_bookings -- user_id=%s org=%s branch=%s status=%s count=%d",
        user_id, org_id, branch_id, status, len(bookings),
    )
    return bookings


async def db_get_booking_by_event_id(
    *,
    org_id: str,
    event_id: str,
) -> Optional[dict]:
    """Fetches a single booking by its Calendar event_id for ownership checks."""
    doc = await _col(org_id).find_one({"event_id": event_id, "org_id": org_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc