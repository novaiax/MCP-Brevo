"""
MCP Server Brevo — Transactional email, contacts & stats via Brevo API.
Transport: SSE (Server-Sent Events) over FastAPI.
"""

import os
import logging
from datetime import datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-brevo")

# ── Config ───────────────────────────────────────────────────────────────────
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
DEFAULT_SENDER_EMAIL = os.environ.get("DEFAULT_SENDER_EMAIL", "contact@yannservice.com")
DEFAULT_SENDER_NAME = os.environ.get("DEFAULT_SENDER_NAME", "Yann Service")
BREVO_BASE = "https://api.brevo.com/v3"

# ── MCP Server ───────────────────────────────────────────────────────────────
mcp = FastMCP("Brevo")


def _headers() -> dict:
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY,
    }


# ── Tool: send_email ────────────────────────────────────────────────────────
@mcp.tool()
async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str = "",
    text_content: str = "",
    sender_email: str = "",
    sender_name: str = "",
    reply_to_email: str = "",
    cc: str = "",
    bcc: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Envoie un email transactionnel via Brevo.

    Args:
        to_email: Adresse email du destinataire.
        to_name: Nom du destinataire.
        subject: Objet de l'email.
        html_content: Corps HTML de l'email (prioritaire sur text_content).
        text_content: Corps texte brut (utilisé si html_content est vide).
        sender_email: Email de l'expéditeur (défaut: contact@yannservice.com).
        sender_name: Nom de l'expéditeur.
        reply_to_email: Adresse de réponse.
        cc: Adresses CC séparées par des virgules.
        bcc: Adresses BCC séparées par des virgules.
        tags: Tags pour le suivi.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    if not html_content and not text_content:
        return {"error": "html_content ou text_content requis."}

    payload: dict = {
        "sender": {
            "email": sender_email or DEFAULT_SENDER_EMAIL,
            "name": sender_name or DEFAULT_SENDER_NAME,
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
    }

    if html_content:
        payload["htmlContent"] = html_content
    else:
        payload["textContent"] = text_content

    if reply_to_email:
        payload["replyTo"] = {"email": reply_to_email}

    if cc:
        payload["cc"] = [{"email": e.strip()} for e in cc.split(",") if e.strip()]

    if bcc:
        payload["bcc"] = [{"email": e.strip()} for e in bcc.split(",") if e.strip()]

    if tags:
        payload["tags"] = tags

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BREVO_BASE}/smtp/email", headers=_headers(), json=payload)

    if resp.status_code == 201:
        data = resp.json()
        logger.info(f"Email envoyé à {to_email} — messageId: {data.get('messageId')}")
        return {"success": True, "messageId": data.get("messageId"), "to": to_email, "subject": subject}

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: send_batch_emails ─────────────────────────────────────────────────
@mcp.tool()
async def send_batch_emails(
    recipients: list[dict],
    subject: str,
    html_content: str = "",
    text_content: str = "",
    sender_email: str = "",
    sender_name: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Envoie un même email à plusieurs destinataires en un seul appel API.

    Args:
        recipients: Liste de dicts avec 'email' et optionnellement 'name'. Ex: [{"email":"a@b.com","name":"Alice"}]
        subject: Objet de l'email.
        html_content: Corps HTML.
        text_content: Corps texte brut.
        sender_email: Email expéditeur (défaut: contact@yannservice.com).
        sender_name: Nom expéditeur.
        tags: Tags pour le suivi.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    if not html_content and not text_content:
        return {"error": "html_content ou text_content requis."}

    to_list = [{"email": r["email"], "name": r.get("name", "")} for r in recipients]

    payload: dict = {
        "sender": {
            "email": sender_email or DEFAULT_SENDER_EMAIL,
            "name": sender_name or DEFAULT_SENDER_NAME,
        },
        "to": to_list,
        "subject": subject,
    }

    if html_content:
        payload["htmlContent"] = html_content
    else:
        payload["textContent"] = text_content

    if tags:
        payload["tags"] = tags

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BREVO_BASE}/smtp/email", headers=_headers(), json=payload)

    if resp.status_code == 201:
        data = resp.json()
        logger.info(f"Batch envoyé à {len(to_list)} destinataires")
        return {"success": True, "messageId": data.get("messageId"), "recipients_count": len(to_list)}

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: list_contacts ─────────────────────────────────────────────────────
@mcp.tool()
async def list_contacts(
    limit: int = 50,
    offset: int = 0,
    modified_since: str = "",
) -> dict:
    """Liste les contacts Brevo.

    Args:
        limit: Nombre de contacts à retourner (max 50).
        offset: Offset pour la pagination.
        modified_since: Filtre ISO date-time (YYYY-MM-DDTHH:mm:ss.SSSZ).
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    params: dict = {"limit": min(limit, 50), "offset": offset}
    if modified_since:
        params["modifiedSince"] = modified_since

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BREVO_BASE}/contacts", headers=_headers(), params=params)

    if resp.status_code == 200:
        data = resp.json()
        contacts = data.get("contacts", [])
        return {
            "count": data.get("count", len(contacts)),
            "contacts": [
                {
                    "email": c.get("email"),
                    "id": c.get("id"),
                    "attributes": c.get("attributes", {}),
                    "listIds": c.get("listIds", []),
                }
                for c in contacts
            ],
        }

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: get_contact ────────────────────────────────────────────────────────
@mcp.tool()
async def get_contact(identifier: str) -> dict:
    """Récupère les détails d'un contact Brevo par email ou ID.

    Args:
        identifier: Email ou ID numérique du contact.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BREVO_BASE}/contacts/{identifier}", headers=_headers())

    if resp.status_code == 200:
        c = resp.json()
        return {
            "email": c.get("email"),
            "id": c.get("id"),
            "attributes": c.get("attributes", {}),
            "listIds": c.get("listIds", []),
            "statistics": c.get("statistics", {}),
        }

    if resp.status_code == 404:
        return {"error": "Contact non trouvé."}

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: create_contact ────────────────────────────────────────────────────
@mcp.tool()
async def create_contact(
    email: str,
    first_name: str = "",
    last_name: str = "",
    company: str = "",
    phone: str = "",
    list_ids: list[int] | None = None,
    update_enabled: bool = True,
    attributes: dict | None = None,
) -> dict:
    """Crée (ou met à jour) un contact dans Brevo.

    Args:
        email: Adresse email du contact.
        first_name: Prénom.
        last_name: Nom.
        company: Entreprise.
        phone: Numéro de téléphone.
        list_ids: IDs des listes auxquelles ajouter le contact.
        update_enabled: Si True, met à jour le contact s'il existe déjà.
        attributes: Attributs supplémentaires (dict clé/valeur, clés en MAJUSCULES).
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    attrs = attributes or {}
    if first_name:
        attrs["FIRSTNAME"] = first_name
    if last_name:
        attrs["LASTNAME"] = last_name
    if company:
        attrs["COMPANY"] = company
    if phone:
        attrs["SMS"] = phone

    payload: dict = {
        "email": email,
        "updateEnabled": update_enabled,
    }
    if attrs:
        payload["attributes"] = attrs
    if list_ids:
        payload["listIds"] = list_ids

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BREVO_BASE}/contacts", headers=_headers(), json=payload)

    if resp.status_code in (201, 204):
        result: dict = {"success": True, "email": email}
        if resp.status_code == 201:
            result["id"] = resp.json().get("id")
        else:
            result["updated"] = True
        logger.info(f"Contact {'créé' if resp.status_code == 201 else 'mis à jour'}: {email}")
        return result

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: delete_contact ────────────────────────────────────────────────────
@mcp.tool()
async def delete_contact(identifier: str) -> dict:
    """Supprime un contact Brevo par email ou ID.

    Args:
        identifier: Email ou ID numérique du contact.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(f"{BREVO_BASE}/contacts/{identifier}", headers=_headers())

    if resp.status_code == 204:
        logger.info(f"Contact supprimé: {identifier}")
        return {"success": True, "deleted": identifier}

    if resp.status_code == 404:
        return {"error": "Contact non trouvé."}

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: list_contact_lists ────────────────────────────────────────────────
@mcp.tool()
async def list_contact_lists(limit: int = 50, offset: int = 0) -> dict:
    """Liste les listes de contacts Brevo.

    Args:
        limit: Nombre max de listes (max 50).
        offset: Offset pour la pagination.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    params = {"limit": min(limit, 50), "offset": offset}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BREVO_BASE}/contacts/lists", headers=_headers(), params=params)

    if resp.status_code == 200:
        data = resp.json()
        return {
            "count": data.get("count", 0),
            "lists": [
                {
                    "id": l.get("id"),
                    "name": l.get("name"),
                    "totalSubscribers": l.get("totalSubscribers", 0),
                    "totalBlacklisted": l.get("totalBlacklisted", 0),
                }
                for l in data.get("lists", [])
            ],
        }

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: get_email_stats ───────────────────────────────────────────────────
@mcp.tool()
async def get_email_stats(
    days: int = 30,
    start_date: str = "",
    end_date: str = "",
    tag: str = "",
) -> dict:
    """Récupère les statistiques agrégées des emails transactionnels.

    Args:
        days: Nombre de jours (inclut aujourd'hui). Ignoré si start_date/end_date fournis.
        start_date: Date de début (YYYY-MM-DD).
        end_date: Date de fin (YYYY-MM-DD).
        tag: Filtrer par tag.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    params: dict = {}
    if start_date and end_date:
        params["startDate"] = start_date
        params["endDate"] = end_date
    else:
        params["days"] = days

    if tag:
        params["tag"] = tag

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BREVO_BASE}/smtp/statistics/aggregatedReport",
            headers=_headers(),
            params=params,
        )

    if resp.status_code == 200:
        return resp.json()

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: get_email_events ──────────────────────────────────────────────────
@mcp.tool()
async def get_email_events(
    limit: int = 50,
    offset: int = 0,
    days: int = 30,
    email: str = "",
    event: str = "",
    tag: str = "",
) -> dict:
    """Récupère les événements détaillés des emails transactionnels (ouvertures, clics, bounces...).

    Args:
        limit: Nombre d'événements (max 100).
        offset: Offset pagination.
        days: Nombre de jours passés.
        email: Filtrer par email destinataire.
        event: Type d'événement: requests, delivered, opened, clicked, hardBounces, softBounces, blocked, spam, unsubscribed.
        tag: Filtrer par tag.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    params: dict = {"limit": min(limit, 100), "offset": offset, "days": days}
    if email:
        params["email"] = email
    if event:
        params["event"] = event
    if tag:
        params["tags"] = tag

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BREVO_BASE}/smtp/statistics/events",
            headers=_headers(),
            params=params,
        )

    if resp.status_code == 200:
        return resp.json()

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: get_transac_emails ────────────────────────────────────────────────
@mcp.tool()
async def get_transac_emails(
    email: str = "",
    limit: int = 50,
    offset: int = 0,
    sort: str = "desc",
) -> dict:
    """Liste les emails transactionnels envoyés (30 derniers jours par défaut).

    Args:
        email: Filtrer par email destinataire.
        limit: Nombre de résultats (max 100).
        offset: Offset pagination.
        sort: Tri: 'asc' ou 'desc'.
    """
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    params: dict = {"limit": min(limit, 100), "offset": offset, "sort": sort}
    if email:
        params["email"] = email

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BREVO_BASE}/smtp/emails", headers=_headers(), params=params)

    if resp.status_code == 200:
        data = resp.json()
        return {
            "count": data.get("count", 0),
            "emails": [
                {
                    "uuid": e.get("uuid"),
                    "messageId": e.get("messageId"),
                    "email": e.get("email"),
                    "subject": e.get("subject"),
                    "date": e.get("date"),
                    "from": e.get("from"),
                    "tags": e.get("tags", []),
                }
                for e in data.get("transactionalEmails", [])
            ],
        }

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Tool: get_account_info ──────────────────────────────────────────────────
@mcp.tool()
async def get_account_info() -> dict:
    """Récupère les informations du compte Brevo (plan, crédits restants, etc.)."""
    if not BREVO_API_KEY:
        return {"error": "BREVO_API_KEY non configurée."}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BREVO_BASE}/account", headers=_headers())

    if resp.status_code == 200:
        data = resp.json()
        return {
            "email": data.get("email"),
            "firstName": data.get("firstName"),
            "lastName": data.get("lastName"),
            "companyName": data.get("companyName"),
            "plan": data.get("plan", []),
            "credits": data.get("relay", {}).get("data", {}),
        }

    return {"error": f"Brevo API {resp.status_code}", "detail": resp.text}


# ── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting MCP Brevo server on port {port} (SSE transport)")
    mcp.run(transport="sse", host="0.0.0.0", port=port)
