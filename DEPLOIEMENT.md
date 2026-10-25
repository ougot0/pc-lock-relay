# Déployer le serveur relais

Le relais doit être accessible en HTTPS/WSS depuis internet. Deux options simples.

## Option A — Render (le plus simple, sans ligne de commande)
1. Mets ce dossier `cloud/` dans un dépôt GitHub.
2. Va sur https://render.com → New → Web Service → connecte le dépôt.
3. Render détecte le `Dockerfile`. Laisse le port par défaut (il fournit `PORT`).
4. Déploie. Tu obtiens une URL du type `https://pc-lock-relay.onrender.com`.
5. L'URL WebSocket devient `wss://pc-lock-relay.onrender.com`.

> Free tier Render : le service s'endort après inactivité (le PC perd la
> connexion). Pour un usage réel, prends l'instance payante la moins chère
> (~7 $/mois) pour qu'il reste toujours réveillé.

## Option B — Fly.io (CLI)
```bash
# installe flyctl puis :
cd cloud
fly launch --no-deploy        # cree l'app (garde le fly.toml fourni)
fly deploy
```
URL : `https://<nom-app>.fly.dev` → WSS : `wss://<nom-app>.fly.dev`.

## Tester que le relais tourne
Ouvre l'URL dans un navigateur : tu dois voir `{"ok": true, ...}`.

## Ce que l'agent et le téléphone utiliseront
- Agent PC :   `wss://<ton-relais>/ws/agent/<device_id>?secret=<secret>`
- Téléphone :  `wss://<ton-relais>/ws/phone/<device_id>`

(L'agent et l'app web rempliront ça automatiquement — tu n'auras qu'à coller
l'URL du relais une fois dans la config.)
