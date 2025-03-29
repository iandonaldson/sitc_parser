#!/bin/bash

set -e  # Stop on error.

# Define the workspace directory
WORKSPACE_DIR="/workspaces/sitc_parser"

# Ensure we're in the correct directory
cd $WORKSPACE_DIR || exit

# Update and install system dependencies
echo "Updating package lists and installing required system dependencies..."
sudo apt update && sudo apt install -y \
    wget \
    unzip \
    curl \
    libgbm-dev \
    libnss3 \
    xvfb \
    jq \
    python3-venv \
    python3-pip

echo "Installing Google Chrome..."
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome.deb || sudo apt-get -fy install
rm google-chrome.deb

# Install matching ChromeDriver version
echo "Installing ChromeDriver via Chrome for Testing..."

CHROMEDRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
  | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform == "linux64") | .url')

if [ -z "$CHROMEDRIVER_URL" ]; then
  echo "Failed to get ChromeDriver download URL."
  exit 1
fi

wget -q "$CHROMEDRIVER_URL" -O chromedriver.zip
unzip chromedriver.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm -rf chromedriver.zip chromedriver-linux64

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv $WORKSPACE_DIR/.venv
source $WORKSPACE_DIR/.venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies from requirements.txt
if [ -f "$WORKSPACE_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r $WORKSPACE_DIR/requirements.txt
else
    echo "No requirements.txt found, skipping dependency installation."
fi

# Verify installation
echo "Verifying installation..."
python3 --version
pip --version
google-chrome --version
chromedriver --version

# Ensure the environment is activated in every new shell session
echo "source $WORKSPACE_DIR/.venv/bin/activate" >> ~/.bashrc

echo "Setup complete. You may need to restart the terminal or run:"
echo "source ~/.bashrc"
