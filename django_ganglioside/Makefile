# Makefile for Ganglioside Analysis Platform
# Simplifies common Docker and Django commands

.PHONY: help build up down restart logs shell migrate makemigrations createsuperuser test clean

# Default target
help:
	@echo "Ganglioside Analysis Platform - Available Commands:"
	@echo ""
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make shell          - Open Django shell"
	@echo "  make bash           - Open bash in Django container"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make test           - Run tests"
	@echo "  make coverage       - Run tests with coverage"
	@echo "  make lint           - Run code linting (black, flake8, isort)"
	@echo "  make format         - Auto-format code (black, isort)"
	@echo "  make clean          - Remove containers, volumes, and images"
	@echo "  make ps             - Show running containers"
	@echo "  make top            - Show container resource usage"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting... waiting 10 seconds..."
	@sleep 10
	@echo "Running migrations..."
	docker-compose exec django python manage.py migrate
	@echo ""
	@echo "✓ Application is running!"
	@echo "  - Web: http://localhost"
	@echo "  - Admin: http://localhost/admin"
	@echo "  - Health: http://localhost/health"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

ps:
	docker-compose ps

top:
	docker-compose top

# Django commands
shell:
	docker-compose exec django python manage.py shell

bash:
	docker-compose exec django /bin/bash

migrate:
	docker-compose exec django python manage.py migrate

makemigrations:
	docker-compose exec django python manage.py makemigrations

createsuperuser:
	docker-compose exec django python manage.py createsuperuser

collectstatic:
	docker-compose exec django python manage.py collectstatic --noinput

# Testing
test:
	docker-compose exec django python manage.py test

coverage:
	docker-compose exec django pytest --cov=apps --cov=config --cov-report=html --cov-report=term

# Code quality
lint:
	@echo "Running Black..."
	black --check .
	@echo "Running isort..."
	isort --check-only .
	@echo "Running flake8..."
	flake8 .

format:
	@echo "Formatting with Black..."
	black .
	@echo "Sorting imports with isort..."
	isort .

# Database commands
dbshell:
	docker-compose exec postgres psql -U ganglioside_user -d ganglioside_prod

backup-db:
	docker-compose exec postgres pg_dump -U ganglioside_user ganglioside_prod > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db:
	@echo "Usage: cat backup_file.sql | docker-compose exec -T postgres psql -U ganglioside_user -d ganglioside_prod"

# Cleanup
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Production deployment
deploy:
	@echo "Building production images..."
	docker-compose -f docker-compose.yml build
	@echo "Pulling latest code..."
	git pull origin main
	@echo "Running migrations..."
	docker-compose exec django python manage.py migrate
	@echo "Collecting static files..."
	docker-compose exec django python manage.py collectstatic --noinput
	@echo "Restarting services..."
	docker-compose restart django celery_worker celery_beat

# Health check
health:
	@echo "Checking service health..."
	@curl -f http://localhost/health && echo "✓ Application is healthy" || echo "✗ Application is unhealthy"
	@docker-compose ps

# Initial setup
setup:
	@echo "Setting up Ganglioside Analysis Platform..."
	make build
	make up
	@echo "Waiting for services to be ready..."
	@sleep 15
	@echo "Creating superuser..."
	docker-compose exec django python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
	@echo ""
	@echo "✓ Setup complete!"
	@echo "  Default credentials: admin / (set password above)"
	@echo "  Access at: http://localhost/admin"
