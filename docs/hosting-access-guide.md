# Hosting and Access Guide (Founder Beta)

## Deployment modes

## 1) Local-only (single machine)

- URL: `http://localhost:8000`
- Best for solo testing and pre-flight validation

## 2) LAN/self-host (same network)

- Host runs server on local machine
- Players connect via `http://<LAN-IP>:8000`
- Good for home sessions or co-located testing

## 3) Public self-host (internet-facing)

Recommended minimum:

- reverse proxy (Nginx/Caddy/Traefik)
- HTTPS termination at proxy
- correct WebSocket upgrade forwarding
- hardened env settings (`APP_ENV=production`, secure cookie/rate-limit flags)

## Port forwarding basics (home/SMB setups)

- Forward external TCP port to host machine port (often 8000 or 443 at proxy)
- Restrict exposure with firewall allow rules where possible
- Prefer exposing proxy TLS port over raw app port

## Firewall/domain notes

- Ensure inbound rule for chosen public port
- DNS A/AAAA record should target public host IP
- If dynamic IP, use DDNS or tunnel service

## Reverse proxy must-haves

- Preserve `Host`
- Forward `X-Forwarded-For`
- Forward `X-Forwarded-Proto`
- Support WebSocket upgrade headers

## TRUST_PROXY_HEADERS — why it matters and how to enable it

When a reverse proxy (nginx, Caddy, Apache, Traefik, …) sits in front of the app, the
server's raw TCP connection comes from the proxy, not from the player's browser.
Without proxy-header trust, two things break:

- **Rate limiting** — all auth attempts appear to come from the proxy's IP, so limits
  are either never triggered (one shared bucket) or immediately triggered for everyone.
- **IP logging / audit trail** — logs record the proxy address, not the real client.
- **Secure-cookie detection** — if `AUTH_COOKIE_SECURE` is `false`, the app checks
  `X-Forwarded-Proto` to decide whether to mark cookies `Secure`; without trust the
  header is ignored and cookies may be set insecurely over HTTPS.

### Enabling trust

Set in your `.env` or environment:

```
TRUST_PROXY_HEADERS=true
```

**Only set this when your server is actually behind a trusted reverse proxy.**
If the app is exposed directly to the internet, leave it `false` — a malicious client
could forge `X-Forwarded-For` to spoof any IP.

### Minimal proxy configs that forward the required headers

**nginx** (inside a `server {}` block):

```nginx
location / {
    proxy_pass         http://127.0.0.1:8000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header   Upgrade    $http_upgrade;
    proxy_set_header   Connection "upgrade";
}
```

**Apache** (requires `mod_proxy`, `mod_proxy_http`, `mod_proxy_wstunnel`):

```apache
ProxyPass        / http://127.0.0.1:8000/
ProxyPassReverse / http://127.0.0.1:8000/
RequestHeader set X-Forwarded-Proto "https"
# X-Forwarded-For is added automatically by mod_proxy
```

**Caddy** (`Caddyfile`):

```caddyfile
example.com {
    reverse_proxy 127.0.0.1:8000
    # Caddy automatically sets X-Forwarded-For and X-Forwarded-Proto
}
```

### Startup warning

When `APP_ENV=production` and `TRUST_PROXY_HEADERS=false` the server logs a warning at
startup:

```
[BOOT] TRUST_PROXY_HEADERS=false in production. If this server runs behind a reverse
proxy … Set TRUST_PROXY_HEADERS=true when a trusted proxy forwards X-Forwarded-For.
```

If you see this warning and the server is behind a proxy, add `TRUST_PROXY_HEADERS=true`
to your environment and restart.

## When self-host is okay

- small trusted founder groups
- controlled user count
- operator can maintain backups and updates

## When managed hosting is better

- broader external testing cohorts
- stronger uptime/security expectations
- need for easier TLS + monitoring + scaling support

## Honesty note

This founder beta package is practical self-host guidance, not enterprise-grade SRE coverage.
