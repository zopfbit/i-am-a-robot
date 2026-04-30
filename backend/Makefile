.PHONY: all env

# Default target
all: env

# Generate .env template if not present
env:
	@if [ ! -f .env ]; then \
		echo "OPENROUTER_API_KEY=your_key_here" > .env; \
		echo ">>> .env created. Please add your OpenRouter API key."; \
	else \
		echo ">>> .env already exists."; \
	fi
