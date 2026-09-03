Frontend skeleton
=================

This is a minimal static frontend for the Weaver project. It uses Tailwind CDN and a small vanilla JavaScript file to render a map grid and demonstrate a WebSocket placeholder.

Run locally
-----------

1. Serve the `frontend` directory with a simple HTTP server (Python example):

```bash
cd frontend
python -m http.server 8080
# then open http://localhost:8080 in your browser
```

2. The `Connect` button attempts a WebSocket connection to `ws://<host>:8000/ws`. The backend does not yet expose a WebSocket route; implement that in `src/weaver` to accept connections.

Next steps
----------

- Add a small React/Vite or Svelte app if you prefer a SPA developer experience.
- Implement WebSocket endpoints in FastAPI and integrate with the game's event bus.
- Replace Tailwind CDN with a build-time Tailwind pipeline for production.
