#!/bin/bash


echo "Updating system package lists..."
sudo apt update -y

echo "Installing required system dependencies..."
sudo apt install -y wget unzip curl gnupg software-properties-common

echo "Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null
then
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo add-apt-repository -y "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main"
    sudo apt update
    sudo apt install -y google-chrome-stable
else
    echo "Google Chrome is already installed."
fi

echo "Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip

echo "Verifying ChromeDriver installation..."
chromedriver --version

echo "Installing Python and required dependencies..."
sudo apt install -y python3 python3-pip python3-venv

echo "Creating a Python virtual environment..."
python3 -m venv sitc_env
source sitc_env/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install selenium selenium-stealth webdriver-manager pandas beautifulsoup4

echo "Setup completed successfully."
echo "To activate the virtual environment, run: source sitc_env/bin/activate"
