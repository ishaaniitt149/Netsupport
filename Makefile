.PHONY: setup test generate-data run demo clean

setup:
	@echo "Setting up Python environment..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example. Please review it."; fi
	@echo "Setup complete! Run 'source .venv/bin/activate' to activate."

test:
	@echo "Running test suite..."
	.venv/bin/pytest tests/ -v

lint:
	@echo "Running linters..."
	.venv/bin/ruff check .

generate-data:
	@echo "Generating synthetic network data..."
	.venv/bin/python scripts/generate_rich_data.py

run:
	@echo "Starting FastAPI server..."
	.venv/bin/python -m app.main

demo:
	@echo "Starting Streamlit engineer UI in Demo Mode..."
	.venv/bin/streamlit run ui/app.py

clean:
	@echo "Cleaning up..."
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -f .env
	@echo "Clean complete."
