#!/bin/bash
set -e  # Stop on error

echo "Updating package list..."
sudo apt-get update

echo "Installing dependencies..."
sudo apt-get install -y wget curl unzip libgbm-dev libnss3 xvfb

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

echo "Setting up Python environment..."
pip install --upgrade pip
pip install selenium webdriver-manager beautifulsoup4 pandas selenium-stealth

echo "Setup completed!"

