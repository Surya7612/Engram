.PHONY: up down seed health serve preflight eval run outcomes situation install test demo-auth

up:
	docker compose up -d

down:
	docker compose down

install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

seed:
	python main.py seed

health:
	python main.py health

serve:
	python main.py serve --reload

preflight:
	python main.py preflight --service "Auth Service" --task "Increase auth session TTL from 24 hours to 7 days"

eval:
	python main.py eval

run:
	python main.py run --service "Auth Service" --task "Increase auth session TTL from 24 hours to 7 days"

# Thin V2 learning loop: run → reject → run again (priors). Requires seeded local store.
demo-auth:
	python main.py seed
	python main.py run --service "Auth Service" --task "Increase auth session TTL from 24 hours to 7 days"
	@echo "Resolve with: python main.py resolve --last --decision rejected --note 'ADR-12 stands'"
	@echo "Then: make run   # expect prior in constraints"

situation:
	python main.py situation --fixture payment-worker

outcomes:
	python main.py outcomes --stats

test:
	pytest
