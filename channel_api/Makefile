# Developing
logs:
	docker logs -f --tail 300 fami-channel-api-service

install_all:
	poetry install --with dev --no-root

update_dependencies:
	poetry update
	poetry export --without-hashes -f requirements.txt -E all --output requirements.txt
	poetry export --without-hashes -f requirements.txt --with dev -E all --output requirements-dev.txt

format:
	poetry run black .
