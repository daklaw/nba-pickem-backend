#!/usr/bin/env bash
set -eux  # Exit on error, print commands before execution

PYTHON_VERSION=3.13.1
VIRTUALENV_NAME=nba_pickem
declare -a BREW_PACKAGES=(
  "postgresql@14"
  "pyenv-virtualenv"
  "pyenv"
)

RED='\033[0;31m'
NC='\033[0m' # No Color

install_brew() {
    if ! command -v brew >/dev/null; then
        echo -e "Installing ${RED}brew${NC}"
        bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo -e "${RED}brew${NC} already installed"
    fi
}

install_brew_packages() {
    for package in "${BREW_PACKAGES[@]}"
    do
        brew ls --versions "$package" &> /dev/null || brew install "$package"
    done
}

start_brew_services() {
    brew services start postgresql@14
}

create_virtualenv() {
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"

    if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
        pyenv install "$PYTHON_VERSION"
    fi

    if ! pyenv versions | grep -q "$VIRTUALENV_NAME"; then
        pyenv virtualenv "$PYTHON_VERSION" "$VIRTUALENV_NAME"
    fi

    pyenv activate "$VIRTUALENV_NAME"
    pip install --upgrade pip pip-tools uv
    pip install -r requirements.txt
}

configure_db() {
    if [ "$(psql postgres -tXAc "SELECT 1 FROM pg_roles WHERE rolname='nba_pickem'")" = '1' ]; then
        echo "Requirement already satisfied: role nba_pickem exists"
    else
        psql -U "$(whoami)" postgres -c "CREATE ROLE nba_pickem WITH LOGIN SUPERUSER PASSWORD 'nba_pickem';"
        psql -U "$(whoami)" postgres -c "ALTER ROLE nba_pickem WITH CREATEDB REPLICATION;"
        psql -U "$(whoami)" postgres -c "ALTER ROLE nba_pickem WITH BYPASSRLS;"
    fi

    if [ "$(psql postgres -tXAc "SELECT 1 FROM pg_database WHERE datname='nba_pickem'")" = '1' ]; then
        echo "Requirement already satisfied: database nba_pickem exists"
    else
        createdb -O nba_pickem nba_pickem
    fi
}

setup_env() {
    if [ ! -f .env ]; then
        echo "Creating .env file from .env.example"
        cp .env.example .env
        echo "Please update .env with your configuration"
    else
        echo ".env file already exists"
    fi
}

install() {
    install_brew
    install_brew_packages
    start_brew_services
    create_virtualenv
    configure_db
    setup_env
}

install