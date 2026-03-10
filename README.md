# MCP-Brevo

Serveur MCP pour interagir avec l'API Brevo (ex-Sendinblue) : envoi d'emails transactionnels, gestion des contacts, statistiques.

## Outils exposés

| Outil | Description |
|-------|-------------|
| `send_email` | Envoi d'un email transactionnel (HTML ou texte) |
| `send_batch_emails` | Envoi groupé a plusieurs destinataires |
| `list_contacts` | Liste les contacts avec pagination |
| `get_contact` | Details d'un contact par email/ID |
| `create_contact` | Cree ou met a jour un contact |
| `delete_contact` | Supprime un contact |
| `list_contact_lists` | Liste les listes de contacts |
| `get_email_stats` | Stats agregees (ouvertures, clics, bounces) |
| `get_email_events` | Evenements detailles par email |
| `get_transac_emails` | Historique des emails envoyes |
| `get_account_info` | Info compte Brevo (plan, credits) |

## Stack

- Python + FastMCP
- Transport SSE
- API Brevo v3 via httpx

## Deploiement Railway

1. Connecter le repo a Railway
2. Ajouter la variable `BREVO_API_KEY`
3. Endpoint SSE : `https://<app>.up.railway.app/sse`

## Variables d'environnement

```
BREVO_API_KEY=xkeysib-...
DEFAULT_SENDER_EMAIL=contact@yannservice.com
DEFAULT_SENDER_NAME=Yann Service
PORT=8000
```
