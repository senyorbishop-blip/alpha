# Setup and Install Guide (Founder Beta)

## Supported runtime

- Python 3.11 or 3.12 (3.12 recommended)
- Modern browser
- OS: Windows/macOS/Linux

## Clean install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`:

- Required for safe admin ops: `DND_ADMIN_KEY`, `DND_JWT_SECRET`
- Optional provider keys: `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc.

Do not put secrets in `config.txt`. `config.txt` is for optional non-secret local runtime settings only and should stay untracked.

## Start server

Option A (recommended dev launcher):

```bash
uvicorn main:app --reload
```

Option B (project startup path):

```bash
python main.py
```

Windows helper:

- `START SERVER.bat`

## Where data lives

Default data root (`DND_DATA_DIR`) is external to the repo:

- Windows: `%USERPROFILE%\Documents\CasualDnDData`
- Linux/macOS: `~/.casual-dnd`
- Linux with XDG: `$XDG_DATA_HOME/casual-dnd`

Inside that folder, key runtime data includes:

- `campaigns.db`
- `maps/`
- `assets/`
- `backups/`

## Local validation

1. Open `http://localhost:8000`
2. Start a DM session
3. Join from a second tab as player
4. Verify map/token/chat updates

## Test from another device (LAN)

1. Find host machine LAN IP (for example `192.168.1.25`)
2. Ensure firewall allows inbound TCP `8000`
3. Run server on host machine
4. On phone/tablet/laptop on same Wi-Fi, open `http://<LAN-IP>:8000`

## Audio/TTS assets/providers

- No API keys required for baseline play
- Without premium keys, narration/image features fall back or are reduced
- Ambient fallback assets are generated/served by runtime where applicable

## Common install pitfalls

- Python version mismatch (use 3.11/3.12)
- `.env` not configured for admin operations
- Accidentally putting secrets in `config.txt` instead of `.env`
- LAN device on a different network/VLAN
- Firewall blocking selected port
