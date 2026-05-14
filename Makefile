.PHONY: prod-smoke prod-smoke-auth prod-smoke-ops

prod-smoke:
	python3 scripts/production_smoke.py

prod-smoke-auth:
	@test -n "$$AURAFIT_SESSION_TOKEN" || (echo "Set AURAFIT_SESSION_TOKEN from a logged-in browser session first" && exit 1)
	python3 scripts/production_smoke.py

prod-smoke-ops:
	@test -n "$$AURAFIT_OPS_TOKEN" || (echo "Set AURAFIT_OPS_TOKEN to OPS_ADMIN_TOKEN first" && exit 1)
	python3 scripts/production_smoke.py
