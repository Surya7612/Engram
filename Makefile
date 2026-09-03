.PHONY: up down seed health serve preflight eval run outcomes install test

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

outcomes:
	python main.py outcomes --stats

test:
	pytest
