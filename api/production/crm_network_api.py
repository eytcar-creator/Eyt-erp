from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/v1/crm/network", tags=["CRM Network"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class EntityIn(BaseModel):
    entityType: str = Field(min_length=3, max_length=30)
    displayName: str = Field(min_length=1, max_length=250)
    customerId: Optional[UUID] = None
    mechanicId: Optional[UUID] = None
    storeId: Optional[UUID] = None
    representativeId: Optional[UUID] = None
    phone: Optional[str] = Field(default=None, max_length=80)
    email: Optional[str] = Field(default=None, max_length=250)
    city: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = None


class IdentityIn(BaseModel):
    channelCode: str = Field(min_length=2, max_length=50)
    externalId: Optional[str] = Field(default=None, max_length=250)
    handle: Optional[str] = Field(default=None, max_length=250)
    normalizedContact: Optional[str] = Field(default=None, max_length=250)


class ConsentIn(BaseModel):
    channelCode: str = Field(min_length=2, max_length=50)
    purpose: str = Field(default="MARKETING", max_length=40)
    granted: bool
    source: Optional[str] = Field(default=None, max_length=80)
    evidence: dict = Field(default_factory=dict)


class RelationshipIn(BaseModel):
    toEntityId: UUID
    relationshipType: str = Field(min_length=3, max_length=50)
    territory: Optional[str] = Field(default=None, max_length=120)


def _code(cur, entity_type: str) -> str:
    prefix = {
        "CONSUMER": "CUS", "MECHANIC": "MEC", "RETAILER": "RTL",
        "DISTRIBUTOR": "DST", "REPRESENTATIVE": "REP", "BRAND": "BRD",
        "SUPPLIER": "SUP", "FLEET": "FLT", "ORGANIZATION": "ORG"
    }.get(entity_type.upper(), "ENT")
    cur.execute(
        "SELECT COUNT(*) + 1 FROM eyt_network_entities WHERE entity_type=%s",
        (entity_type.upper(),),
    )
    return f"{prefix}-{int(cur.fetchone()[0]):06d}"


@router.get("/dashboard")
def dashboard(_=Depends(require_permission("crm.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT entity_type, COUNT(*)
            FROM eyt_network_entities
            WHERE status='ACTIVE'
            GROUP BY entity_type ORDER BY entity_type
        """)
        entities = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM eyt_channel_identities")
        identities = cur.fetchone()[0]
        cur.execute("""
            SELECT channel_code, COUNT(DISTINCT entity_id)
            FROM eyt_channel_attribution
            GROUP BY channel_code ORDER BY COUNT(DISTINCT entity_id) DESC
        """)
        channels = [{"channel": r[0], "entities": r[1]} for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM eyt_network_relationships")
        relationships = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM eyt_marketing_consents
            WHERE purpose='MARKETING' AND granted=TRUE
        """)
        marketingConsents = cur.fetchone()[0]
    return {
        "entities": entities,
        "identities": identities,
        "relationships": relationships,
        "marketingConsents": marketingConsents,
        "channels": channels,
    }


@router.get("/channels")
def channels(_=Depends(require_permission("crm.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT code, channel_type, name_fa, active
            FROM eyt_channel_definitions
            ORDER BY channel_type, name_fa
        """)
        rows = cur.fetchall()
    return [
        {"code": r[0], "type": r[1], "nameFa": r[2], "active": r[3]}
        for r in rows
    ]


@router.get("/entities")
def entities(
    entity_type: str = "",
    search: str = "",
    city: str = "",
    limit: int = Query(200, ge=1, le=1000),
    _=Depends(require_permission("crm.read")),
):
    with _connect() as conn, conn.cursor() as cur:
        like = f"%{search.strip()}%"
        cur.execute("""
            SELECT id, entity_code, entity_type, display_name, phone, email, city,
                   status, customer_id, mechanic_id, store_id, representative_id,
                   created_at, updated_at
            FROM eyt_network_entities
            WHERE (%s='' OR entity_type=%s)
              AND (%s='' OR display_name ILIKE %s OR COALESCE(phone,'') ILIKE %s
                   OR entity_code ILIKE %s)
              AND (%s='' OR COALESCE(city,'') ILIKE %s)
            ORDER BY created_at DESC
            LIMIT %s
        """, (entity_type.upper(), entity_type.upper(), search, like, like, like,
              city, f"%{city}%", limit))
        rows = cur.fetchall()
    return [
        {
            "id": str(r[0]), "code": r[1], "type": r[2], "displayName": r[3],
            "phone": r[4], "email": r[5], "city": r[6], "status": r[7],
            "customerId": str(r[8]) if r[8] else None,
            "mechanicId": str(r[9]) if r[9] else None,
            "storeId": str(r[10]) if r[10] else None,
            "representativeId": str(r[11]) if r[11] else None,
            "createdAt": r[12], "updatedAt": r[13],
        }
        for r in rows
    ]


@router.post("/entities")
def create_entity(payload: EntityIn, _=Depends(require_permission("crm.write"))):
    entity_type = payload.entityType.upper()
    allowed = {
        "CONSUMER", "MECHANIC", "RETAILER", "DISTRIBUTOR",
        "REPRESENTATIVE", "BRAND", "SUPPLIER", "FLEET", "ORGANIZATION"
    }
    if entity_type not in allowed:
        raise HTTPException(400, "Unsupported entity type")
    with _connect() as conn, conn.cursor() as cur:
        code = _code(cur, entity_type)
        cur.execute("""
            INSERT INTO eyt_network_entities(
                entity_code, entity_type, display_name, customer_id, mechanic_id,
                store_id, representative_id, phone, email, city, address
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, entity_code
        """, (
            code, entity_type, payload.displayName, payload.customerId,
            payload.mechanicId, payload.storeId, payload.representativeId,
            payload.phone, payload.email, payload.city, payload.address,
        ))
        row = cur.fetchone()
        conn.commit()
    return {"id": str(row[0]), "code": row[1], "status": "created"}


@router.get("/entities/{entity_id}")
def entity_detail(entity_id: UUID, _=Depends(require_permission("crm.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, entity_code, entity_type, display_name, phone, email, city,
                   address, status, customer_id, mechanic_id, store_id, representative_id
            FROM eyt_network_entities WHERE id=%s
        """, (entity_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Network entity not found")

        cur.execute("""
            SELECT id, channel_code, external_id, handle, normalized_contact,
                   first_seen_at, last_seen_at
            FROM eyt_channel_identities WHERE entity_id=%s
            ORDER BY last_seen_at DESC
        """, (entity_id,))
        ids = cur.fetchall()

        cur.execute("""
            SELECT channel_code, purpose, granted, source, granted_at, revoked_at
            FROM eyt_marketing_consents WHERE entity_id=%s
            ORDER BY channel_code, purpose
        """, (entity_id,))
        consents = cur.fetchall()

        cur.execute("""
            SELECT r.relationship_type, r.territory, r.valid_from, r.valid_to,
                   e.id, e.entity_code, e.entity_type, e.display_name
            FROM eyt_network_relationships r
            JOIN eyt_network_entities e ON e.id=r.to_entity_id
            WHERE r.from_entity_id=%s
            ORDER BY r.created_at DESC
        """, (entity_id,))
        relationships = cur.fetchall()

    return {
        "entity": {
            "id": str(row[0]), "code": row[1], "type": row[2], "displayName": row[3],
            "phone": row[4], "email": row[5], "city": row[6], "address": row[7],
            "status": row[8],
            "customerId": str(row[9]) if row[9] else None,
            "mechanicId": str(row[10]) if row[10] else None,
            "storeId": str(row[11]) if row[11] else None,
            "representativeId": str(row[12]) if row[12] else None,
        },
        "identities": [
            {"id": str(x[0]), "channel": x[1], "externalId": x[2], "handle": x[3],
             "normalizedContact": x[4], "firstSeenAt": x[5], "lastSeenAt": x[6]}
            for x in ids
        ],
        "consents": [
            {"channel": x[0], "purpose": x[1], "granted": x[2], "source": x[3],
             "grantedAt": x[4], "revokedAt": x[5]}
            for x in consents
        ],
        "relationships": [
            {"type": x[0], "territory": x[1], "validFrom": x[2], "validTo": x[3],
             "to": {"id": str(x[4]), "code": x[5], "type": x[6], "displayName": x[7]}}
            for x in relationships
        ],
    }


@router.post("/entities/{entity_id}/identities")
def add_identity(entity_id: UUID, payload: IdentityIn, _=Depends(require_permission("crm.write"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM eyt_network_entities WHERE id=%s", (entity_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Network entity not found")
        cur.execute("""
            INSERT INTO eyt_channel_identities(
                entity_id, channel_code, external_id, handle, normalized_contact
            ) VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(channel_code, external_id) DO UPDATE
            SET entity_id=EXCLUDED.entity_id, handle=EXCLUDED.handle,
                normalized_contact=EXCLUDED.normalized_contact,
                last_seen_at=CURRENT_TIMESTAMP
            RETURNING id
        """, (entity_id, payload.channelCode, payload.externalId,
              payload.handle, payload.normalizedContact))
        row = cur.fetchone()
        conn.commit()
    return {"id": str(row[0]), "status": "linked"}


@router.post("/entities/{entity_id}/consents")
def set_consent(entity_id: UUID, payload: ConsentIn, _=Depends(require_permission("crm.write"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM eyt_network_entities WHERE id=%s", (entity_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Network entity not found")
        cur.execute("""
            INSERT INTO eyt_marketing_consents(
                entity_id, channel_code, purpose, granted, source,
                granted_at, revoked_at, evidence
            ) VALUES(%s,%s,%s,%s,%s,
                     CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                     CASE WHEN %s THEN NULL ELSE CURRENT_TIMESTAMP END,
                     %s)
            ON CONFLICT(entity_id, channel_code, purpose) DO UPDATE
            SET granted=EXCLUDED.granted, source=EXCLUDED.source,
                granted_at=EXCLUDED.granted_at, revoked_at=EXCLUDED.revoked_at,
                evidence=EXCLUDED.evidence
            RETURNING id
        """, (
            entity_id, payload.channelCode, payload.purpose.upper(), payload.granted,
            payload.source, payload.granted, payload.granted, psycopg.types.json.Json(payload.evidence)
        ))
        row = cur.fetchone()
        conn.commit()
    return {"id": str(row[0]), "granted": payload.granted}


@router.post("/entities/{entity_id}/relationships")
def add_relationship(entity_id: UUID, payload: RelationshipIn, _=Depends(require_permission("crm.write"))):
    if entity_id == payload.toEntityId:
        raise HTTPException(400, "An entity cannot relate to itself")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM eyt_network_entities WHERE id=%s", (entity_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Source entity not found")
        cur.execute("SELECT 1 FROM eyt_network_entities WHERE id=%s", (payload.toEntityId,))
        if not cur.fetchone():
            raise HTTPException(404, "Target entity not found")
        cur.execute("""
            INSERT INTO eyt_network_relationships(
                from_entity_id,to_entity_id,relationship_type,territory
            ) VALUES(%s,%s,%s,%s)
            ON CONFLICT(from_entity_id,to_entity_id,relationship_type,valid_from)
            DO UPDATE SET territory=EXCLUDED.territory
            RETURNING id
        """, (entity_id, payload.toEntityId, payload.relationshipType.upper(), payload.territory))
        row = cur.fetchone()
        conn.commit()
    return {"id": str(row[0]), "status": "linked"}


@router.get("/graph/{entity_id}")
def graph(entity_id: UUID, depth: int = Query(1, ge=1, le=2), _=Depends(require_permission("crm.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            WITH RECURSIVE reachable(entity_id, depth) AS (
                SELECT %s::uuid, 0
                UNION
                SELECT r.to_entity_id, reachable.depth + 1
                FROM reachable
                JOIN eyt_network_relationships r
                  ON r.from_entity_id = reachable.entity_id
                WHERE reachable.depth < %s
            )
            SELECT e.entity_id, e.depth, n.entity_code, n.entity_type, n.display_name,
                   r.relationship_type, r.territory
            FROM reachable e
            JOIN eyt_network_entities n ON n.id=e.entity_id
            LEFT JOIN eyt_network_relationships r ON r.from_entity_id=e.entity_id
            ORDER BY e.depth, n.display_name
        """, (entity_id, depth))
        rows = cur.fetchall()
    return [
        {"id": str(r[0]), "depth": r[1], "code": r[2], "type": r[3],
         "displayName": r[4], "relationshipType": r[5], "territory": r[6]}
        for r in rows
    ]
