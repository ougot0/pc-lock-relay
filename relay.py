"""
PC Lock - Serveur relais (cloud)
--------------------------------
Simple tuyau chiffre entre l'agent PC et le(s) telephone(s).
Ne voit jamais le PIN ni l'ecran en clair cote logique : il se contente de
transmettre les messages d'un cote a l'autre, par device_id.

- L'agent PC se connecte :   wss://<relais>/ws/agent/{device_id}?secret=XXXX
- Le telephone se connecte : wss://<relais>/ws/phone/{device_id}
- Tout ce que l'agent envoie est transmis a tous les telephones de ce device,
  et inversement. L'authentification (PIN) se fait de bout en bout dans l'agent.

Lancer en local :  uvicorn relay:app --host 0.0.0.0 --port 8080
"""

import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI(title="PC Lock Relay")
HERE = os.path.dirname(os.path.abspath(__file__))


@app.get("/app")
async def app_page():
    return FileResponse(os.path.join(HERE, "app.html"), media_type="text/html")

# Etat en memoire (un seul process). Pour de l'echelle -> Redis, mais inutile en v1.
agents = {}          # device_id -> WebSocket de l'agent connecte
agent_secrets = {}   # device_id -> secret lie a la 1re connexion (TOFU)
phones = {}          # device_id -> set() de WebSockets telephone


@app.get("/")
async def health():
    return {"ok": True, "service": "pc-lock-relay",
            "agents_online": len(agents)}


async def _send(ws, msg):
    """Transmet un message recu (texte OU binaire) tel quel."""
    try:
        if msg.get("text") is not None:
            await ws.send_text(msg["text"])
        elif msg.get("bytes") is not None:
            await ws.send_bytes(msg["bytes"])
    except Exception:
        pass


@app.websocket("/ws/agent/{device_id}")
async def ws_agent(ws: WebSocket, device_id: str, secret: str = ""):
    # TOFU : le 1er secret vu pour ce device fait foi ; ensuite il doit coller.
    known = agent_secrets.get(device_id)
    if known is None:
        agent_secrets[device_id] = secret
    elif known != secret:
        await ws.close(code=4403)   # secret invalide -> pas de vol d'ID
        return

    await ws.accept()
    agents[device_id] = ws
    await _broadcast_presence(device_id, True)
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            for p in list(phones.get(device_id, set())):
                await _send(p, msg)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if agents.get(device_id) is ws:
            del agents[device_id]
        await _broadcast_presence(device_id, False)


async def _broadcast_presence(device_id, online):
    data = json.dumps({"type": "presence", "online": online})
    for p in list(phones.get(device_id, set())):
        try:
            await p.send_text(data)
        except Exception:
            pass


@app.websocket("/ws/phone/{device_id}")
async def ws_phone(ws: WebSocket, device_id: str):
    await ws.accept()
    phones.setdefault(device_id, set()).add(ws)
    # Etat de presence du PC au moment de la connexion
    try:
        await ws.send_text(json.dumps({"type": "presence",
                                       "online": device_id in agents}))
    except Exception:
        pass
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            agent = agents.get(device_id)
            if agent is not None:
                await _send(agent, msg)
            else:
                try:
                    await ws.send_text(json.dumps({"type": "presence", "online": False}))
                except Exception:
                    pass
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        s = phones.get(device_id)
        if s and ws in s:
            s.discard(ws)
            if not s:
                phones.pop(device_id, None)
