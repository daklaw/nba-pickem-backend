"""
Fabric deployment script for NBA Pick'em Backend

Usage:
    fab -H user@host deploy              # Deploy latest code
    fab -H user@host setup               # Initial server setup
    fab -H user@host migrate             # Run database migrations
    fab -H user@host restart             # Restart the application
    fab -H user@host logs                # View application logs
    fab -H user@host status              # Check application status
    fab -H user@host backup-db           # Backup the database
"""

from fabric import task, Connection
from invoke import run as local
import os
from datetime import datetime


# Configuration - customize these for your deployment
PROJECT_NAME = "nba_pickem_backend"
REMOTE_USER = "root"
REMOTE_HOST = "165.232.129.168"
REMOTE_DIR = "/home/apps/nba_pickem_backend"
VENV_DIR = "/home/venvs/nba_pickem_backend"
PYTHON_BIN = f"{VENV_DIR}/bin/python"
PIP_BIN = f"{VENV_DIR}/bin/pip"
ALEMBIC_BIN = f"{VENV_DIR}/bin/alembic"
SERVICE_NAME = "nba-pickem"
SYSTEMD_SERVICE_FILE = f"/etc/systemd/system/{SERVICE_NAME}.service"

# Files/directories to exclude from sync
EXCLUDE_PATTERNS = [
    '.git',
    '.venv',
    '__pycache__',
    '*.pyc',
    '.DS_Store',
    '.idea',
    '*.db',
    '.env',
    'data/',
    'alembic/versions/__pycache__',
]


@task
def setup(c):
    """
    Initial server setup - run this once on a fresh server

    This will:
    - Install system dependencies
    - Create project directory
    - Set up Python virtual environment
    - Install application dependencies
    - Create systemd service
    - Set up environment file
    """
    print("🚀 Setting up NBA Pick'em Backend on remote server...")

    # Update system packages
    print("\n📦 Updating system packages...")
    c.sudo("apt-get update")
    c.sudo("apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx")

    # Create project and venv directories
    print(f"\n📁 Creating directories...")
    c.run(f"mkdir -p {REMOTE_DIR}")
    c.run(f"mkdir -p /home/venvs")

    # Create virtual environment
    print(f"\n🐍 Creating Python virtual environment at {VENV_DIR}...")
    c.run(f"python3 -m venv {VENV_DIR}")

    # Upload project files
    print("\n📤 Uploading project files...")
    sync_code(c)

    # Install Python dependencies
    print("\n📚 Installing Python dependencies...")
    c.run(f"{PIP_BIN} install --upgrade pip")
    c.run(f"{PIP_BIN} install -r {REMOTE_DIR}/requirements.txt")

    # Set up environment file
    print("\n⚙️  Setting up environment file...")
    setup_env(c)

    # Create systemd service
    print("\n🔧 Creating systemd service...")
    create_systemd_service(c)

    # Setup PostgreSQL database
    print("\n🗄️  Setting up PostgreSQL database...")
    setup_database(c)

    print("\n✅ Setup complete! Next steps:")
    print(f"   1. Run: fab -H {c.host} migrate")
    print(f"   2. Run: fab -H {c.host} start")
    print(f"   💡 To update production env: fab -H {c.host} update-env")


@task
def deploy(c):
    """
    Deploy the latest code to the server

    This will:
    - Sync code to server
    - Install/update dependencies
    - Run database migrations
    - Restart the application
    """
    print("🚀 Deploying NBA Pick'em Backend...")

    # Sync code
    print("\n📤 Syncing code to server...")
    sync_code(c)

    # Install dependencies
    print("\n📚 Installing/updating dependencies...")
    c.run(f"{PIP_BIN} install -r {REMOTE_DIR}/requirements.txt")

    # Run migrations
    print("\n🔄 Running database migrations...")
    migrate(c)

    # Restart service
    print("\n🔄 Restarting application...")
    restart(c)

    # Check status
    print("\n✅ Deployment complete!")
    status(c)


@task
def sync_code(c):
    """Sync local code to remote server using rsync"""
    exclude_args = ' '.join([f"--exclude '{pattern}'" for pattern in EXCLUDE_PATTERNS])

    # Use rsync to sync files
    local_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = f"rsync -avz {exclude_args} --delete {local_dir}/ {c.user}@{c.host}:{REMOTE_DIR}/"

    local(cmd)
    print(f"✅ Code synced to {c.host}:{REMOTE_DIR}")


@task
def update_env(c):
    """
    Update production environment file on remote server

    This will:
    - Sync the latest .env.production from local to remote
    - Copy it to .env on the remote server
    - Restart the application to apply changes
    """
    print("🔄 Updating production environment...")

    # Sync just the .env.production file
    local_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = f"rsync -avz {local_dir}/.env.production {c.user}@{c.host}:{REMOTE_DIR}/"
    local(cmd)

    # Apply the production env
    setup_env(c)

    # Restart to apply changes
    print("\n🔄 Restarting application to apply new environment...")
    restart(c)

    print("✅ Production environment updated!")


@task
def setup_env(c):
    """Create .env file on remote server from .env.production"""
    # Check if .env.production exists
    result = c.run(f"test -f {REMOTE_DIR}/.env.production", warn=True)

    if result.failed:
        print("❌ .env.production file not found on remote server!")
        print("⚠️  Make sure .env.production is synced to the server")
        return

    # Copy .env.production to .env
    print("📝 Creating .env file from .env.production...")
    c.run(f"cp {REMOTE_DIR}/.env.production {REMOTE_DIR}/.env")
    print("✅ Production .env file configured")


@task
def setup_database(c):
    """Set up PostgreSQL database"""
    db_name = "nba_pickem"
    db_user = "nba_pickem"
    db_password = "changeme"  # Change this!

    print(f"Creating PostgreSQL database: {db_name}")

    # Create database user
    c.sudo(f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\"", warn=True)

    # Create database
    c.sudo(f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER {db_user};\"", warn=True)

    print(f"✅ Database '{db_name}' created")
    print(f"⚠️  Remember to update DATABASE_URL in {REMOTE_DIR}/.env")


@task
def create_systemd_service(c):
    """Create systemd service file for the application"""
    service_content = f"""[Unit]
Description=NBA Pick'em Backend API
After=network.target postgresql.service

[Service]
Type=notify
User={REMOTE_USER}
WorkingDirectory={REMOTE_DIR}
Environment="PATH={VENV_DIR}/bin"
ExecStart={VENV_DIR}/bin/gunicorn main:app --workers 3 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    # Write service file using cat with heredoc to avoid quoting issues
    c.run(f"""cat > /tmp/{SERVICE_NAME}.service << 'ENDOFFILE'
{service_content}ENDOFFILE""")
    c.sudo(f"mv /tmp/{SERVICE_NAME}.service {SYSTEMD_SERVICE_FILE}")
    c.sudo(f"chmod 644 {SYSTEMD_SERVICE_FILE}")

    # Reload systemd
    c.sudo("systemctl daemon-reload")
    c.sudo(f"systemctl enable {SERVICE_NAME}")

    print(f"✅ Systemd service created: {SERVICE_NAME}")


@task
def migrate(c):
    """Run database migrations"""
    with c.cd(REMOTE_DIR):
        print("🔄 Running Alembic migrations...")
        c.run(f"{VENV_DIR}/bin/alembic upgrade head")
        print("✅ Migrations complete")


@task
def migrate_create(c, message="auto migration"):
    """Create a new database migration"""
    with c.cd(REMOTE_DIR):
        print(f"📝 Creating new migration: {message}")
        c.run(f"{VENV_DIR}/bin/alembic revision --autogenerate -m '{message}'")


@task
def start(c):
    """Start the application service"""
    print(f"▶️  Starting {SERVICE_NAME}...")
    c.sudo(f"systemctl start {SERVICE_NAME}")
    print("✅ Service started")
    status(c)


@task
def stop(c):
    """Stop the application service"""
    print(f"⏹️  Stopping {SERVICE_NAME}...")
    c.sudo(f"systemctl stop {SERVICE_NAME}")
    print("✅ Service stopped")


@task
def restart(c):
    """Restart the application service"""
    print(f"🔄 Restarting {SERVICE_NAME}...")
    c.sudo(f"systemctl restart {SERVICE_NAME}")
    print("✅ Service restarted")
    status(c)


@task
def status(c):
    """Check application service status"""
    print(f"📊 Checking status of {SERVICE_NAME}...")
    c.sudo(f"systemctl status {SERVICE_NAME} --no-pager", warn=True)


@task
def logs(c, lines=50, follow=False):
    """
    View application logs

    Args:
        lines: Number of lines to show (default: 50)
        follow: Follow logs in real-time (default: False)
    """
    follow_flag = "-f" if follow else ""
    print(f"📜 Viewing last {lines} lines of logs...")
    c.sudo(f"journalctl -u {SERVICE_NAME} -n {lines} {follow_flag} --no-pager")


@task
def backup_db(c):
    """Backup the PostgreSQL database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{REMOTE_DIR}/backups"
    backup_file = f"{backup_dir}/nba_pickem_{timestamp}.sql"

    print(f"💾 Creating database backup: {backup_file}")

    # Create backup directory
    c.run(f"mkdir -p {backup_dir}")

    # Create backup
    c.run(f"pg_dump nba_pickem > {backup_file}")
    c.run(f"gzip {backup_file}")

    print(f"✅ Backup created: {backup_file}.gz")


@task
def restore_db(c, backup_file):
    """
    Restore database from backup

    Args:
        backup_file: Path to backup file on remote server
    """
    print(f"♻️  Restoring database from {backup_file}...")

    # Check if backup file is gzipped
    if backup_file.endswith('.gz'):
        c.run(f"gunzip -c {backup_file} | psql nba_pickem")
    else:
        c.run(f"psql nba_pickem < {backup_file}")

    print("✅ Database restored")


@task
def shell(c):
    """Open a shell on the remote server in the project directory"""
    print(f"🐚 Opening shell on {c.host} in {REMOTE_DIR}...")
    c.run(f"cd {REMOTE_DIR} && exec $SHELL", pty=True)


@task
def python_shell(c):
    """Open a Python shell with the application context"""
    with c.cd(REMOTE_DIR):
        print("🐍 Opening Python shell...")
        c.run(f"{PYTHON_BIN}", pty=True)


@task
def run_command(c, command):
    """
    Run a manage.py command on the remote server

    Example: fab -H user@host run-command --command="seed-teams"
    """
    with c.cd(REMOTE_DIR):
        print(f"🎯 Running command: python manage.py {command}")
        c.run(f"{PYTHON_BIN} manage.py {command}")


@task
def seed_teams(c):
    """Seed NBA teams on remote server"""
    run_command(c, "seed-teams")


@task
def ingest_games(c):
    """Ingest NBA games schedule on remote server"""
    run_command(c, "ingest-games")


@task
def backfill_scores(c):
    """Backfill game scores from NBA API on remote server"""
    run_command(c, "backfill-scores")


@task
def recalculate_points(c):
    """Recalculate all user points on remote server"""
    run_command(c, "recalculate-points")


@task
def retabulate_season(c, season_id=None):
    """Retabulate season scores on remote server"""
    cmd = "retabulate-season"
    if season_id:
        cmd += f" --season-id {season_id}"
    run_command(c, cmd)


@task
def update_requirements(c):
    """Update Python dependencies on remote server"""
    print("📦 Updating Python dependencies...")
    c.run(f"{PIP_BIN} install --upgrade -r {REMOTE_DIR}/requirements.txt")
    restart(c)


@task
def setup_nginx(c, domain="your-domain.com"):
    """
    Set up Nginx as a reverse proxy

    Args:
        domain: Your domain name
    """
    nginx_config = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    config_file = f"/etc/nginx/sites-available/{SERVICE_NAME}"
    enabled_file = f"/etc/nginx/sites-enabled/{SERVICE_NAME}"

    # Write nginx config using heredoc
    c.run(f"""cat > /tmp/{SERVICE_NAME}.nginx << 'ENDOFFILE'
{nginx_config}ENDOFFILE""")
    c.sudo(f"mv /tmp/{SERVICE_NAME}.nginx {config_file}")

    # Enable site
    c.sudo(f"ln -sf {config_file} {enabled_file}")

    # Test nginx config
    c.sudo("nginx -t")

    # Reload nginx
    c.sudo("systemctl reload nginx")

    print(f"✅ Nginx configured for {domain}")
    print(f"💡 To enable HTTPS, run: sudo certbot --nginx -d {domain}")


@task
def setup_ssl(c, domain, email):
    """
    Set up SSL certificate with Let's Encrypt

    Args:
        domain: Your domain name
        email: Your email for Let's Encrypt
    """
    print("🔒 Setting up SSL certificate...")

    # Install certbot
    c.sudo("apt-get install -y certbot python3-certbot-nginx")

    # Get certificate
    c.sudo(f"certbot --nginx -d {domain} --non-interactive --agree-tos -m {email}")

    print("✅ SSL certificate installed")


@task
def clean_pyc(c):
    """Remove all .pyc files and __pycache__ directories"""
    with c.cd(REMOTE_DIR):
        print("🧹 Cleaning .pyc files and __pycache__ directories...")
        c.run("find . -type f -name '*.pyc' -delete")
        c.run("find . -type d -name '__pycache__' -delete")
        print("✅ Cleanup complete")


@task
def disk_usage(c):
    """Check disk usage on remote server"""
    print("💾 Checking disk usage...")
    c.run("df -h")
    print("\n📊 Project directory size:")
    c.run(f"du -sh {REMOTE_DIR}")


@task
def health_check(c):
    """Check if the API is responding"""
    print("🏥 Running health check...")
    result = c.run("curl -s http://localhost:8000/health", warn=True)

    if result.ok and "healthy" in result.stdout:
        print("✅ API is healthy!")
    else:
        print("❌ API health check failed!")
        status(c)


# Convenience task for full deployment pipeline
@task
def full_deploy(c):
    """
    Complete deployment pipeline:
    - Backup database
    - Deploy code
    - Run migrations
    - Restart service
    - Health check
    """
    print("🚀 Starting full deployment pipeline...")

    backup_db(c)
    deploy(c)
    health_check(c)

    print("\n✅ Full deployment complete!")