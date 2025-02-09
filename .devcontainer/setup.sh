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
    python3-venv \
    python3-pip 

echo "Installing Google Chrome..."
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome.deb || sudo apt-get -fy install
rm google-chrome.deb

echo "Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
rm chromedriver_linux64.zip    

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv $WORKSPACE_DIR/sitc_env
source $WORKSPACE_DIR/sitc_env/bin/activate

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

# Ensure Chromedriver is properly linked
echo "Linking Chromedriver..."
CHROME_DRIVER_PATH=$(which chromedriver)
if [ -z "$CHROME_DRIVER_PATH" ]; then
    echo "Chromedriver not found, installing manually..."
    wget -N https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip -P /tmp
    unzip /tmp/chromedriver_linux64.zip -d /tmp
    sudo mv /tmp/chromedriver /usr/bin/chromedriver
    sudo chmod +x /usr/bin/chromedriver
fi

# Verify installation
echo "Verifying installation..."
python3 --version
pip --version
chromedriver --version

# Ensure the environment is activated in every new shell session
echo "source $WORKSPACE_DIR/sitc_env/bin/activate" >> ~/.bashrc

echo "Setup complete. You may need to restart the terminal or run:"
echo "source ~/.bashrc"


