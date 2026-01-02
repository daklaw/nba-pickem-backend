SHELL := /bin/sh

# Database commands
reset-database:
	@echo "🗑️  Dropping database..."
	dropdb nba_pickem || true
	@echo "📦 Creating fresh database..."
	createdb -O nba_pickem nba_pickem
	@echo "🧹 Cleaning alembic migrations..."
	rm -f alembic/versions/*.py
	rm -rf alembic/versions/__pycache__
	@echo "✨ Creating new migration..."
	alembic revision --autogenerate -m "initial migration"
	@echo "⬆️  Running migration..."
	alembic upgrade head
	@echo "✅ Database reset complete!"

reload-data:
	@echo "🔄 Reloading all data..."
	@echo "1/4 Seeding NBA teams..."
	@python manage.py seed-teams
	@echo ""
	@echo "2/4 Importing CSV data..."
	@python manage.py import-csv data/nba-pickem.csv
	@echo ""
	@echo "3/4 Ingesting NBA schedule..."
	@python manage.py ingest-games
	@echo ""
	@echo "4/4 Backfilling scores and calculating points..."
	@python manage.py backfill-scores
	@echo ""
	@echo "✅ All data reloaded successfully!"

# Score management commands
backfill:
	@echo "📊 Backfilling game scores from NBA API..."
	@python manage.py backfill-scores

recalculate:
	@echo "🔢 Recalculating all user points..."
	@python manage.py recalculate-points

retabulate:
	@echo "📋 Retabulating season scores..."
	@python manage.py retabulate-season

ingest:
	@echo "📥 Ingesting NBA games schedule..."
	@python manage.py ingest-games

# Migration commands
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-rollback:
	alembic downgrade -1

migrate-history:
	alembic history --verbose

# Setup and run commands
install:
	./install.sh

run:
	uvicorn main:app --reload

run-prod:
	uvicorn main:app --host 0.0.0.0 --port 8000

# Deployment commands
# Default host: root@165.232.129.168
# Override with: DEPLOY_HOST=user@other-host make deploy
DEPLOY_HOST ?= root@165.232.129.168

deploy:
	@echo "🚀 Deploying to $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) deploy

deploy-full:
	@echo "🚀 Running full deployment to $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) full-deploy

setup-server:
	@echo "🛠️  Setting up server at $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) setup

deploy-logs:
	@echo "📜 Viewing logs on $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) logs

deploy-status:
	@echo "📊 Checking status on $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) status

deploy-restart:
	@echo "🔄 Restarting service on $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) restart

deploy-health:
	@echo "🏥 Running health check on $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) health-check

deploy-backup:
	@echo "💾 Backing up database on $(DEPLOY_HOST)..."
	fab -H $(DEPLOY_HOST) backup-db