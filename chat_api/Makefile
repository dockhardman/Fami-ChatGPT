update_dependencies:
	poetry update
	poetry export --without-hashes -f requirements.txt --output requirements.txt
	poetry export --without-hashes -f requirements.txt --with dev --output requirements-dev.txt

format:
	poetry run black .