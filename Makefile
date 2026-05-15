.PHONY: dev

dev:
	@trap 'kill 0' INT; \
	(cd api && uv run uvicorn app.main:app --port 8001 --reload) & \
	(cd web && python3 -m http.server 8080) & \
	wait
