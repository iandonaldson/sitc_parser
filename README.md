# sitc_parser

## use
chmod +x install_dependencies.sh  
./install_dependencies.sh  
source sitc_env/bin/activate  
  
python sitc_parser.py  



**Sharing the Environment in GitHub Codespace**, you can save and share the environment by following these steps:

### **1. Use a `devcontainer.json` Configuration (Best Approach)**
GitHub Codespaces uses **Dev Containers** to define the development environment. You can specify dependencies, extensions, and configurations in a `devcontainer.json` file.

#### **Step 1: Create the `.devcontainer` Directory**
In the root of your repository, create a folder named `.devcontainer/`, and inside it, create a file named `devcontainer.json`:

```
mkdir -p .devcontainer && touch .devcontainer/devcontainer.json
```

#### **Step 2: Define the Development Environment**
Edit `.devcontainer/devcontainer.json` and add:

```json
{
  "name": "SITC Parser Dev Environment",
  "image": "mcr.microsoft.com/devcontainers/python:3.12", 
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:1": {}
  },
  "postCreateCommand": "bash .devcontainer/setup.sh",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-toolsai.jupyter",
        "ms-vscode-remote.remote-containers"
      ]
    }
  },
  "forwardPorts": [9222]
}
```
- This sets up a **Python 3.12 environment** inside Codespaces.
- It **installs extensions** for Python and Jupyter.
- The script `.devcontainer/setup.sh` will be executed after the container is created.

---

### **2. Automate Dependency Installation**
Create a **setup script** `.devcontainer/setup.sh` to install Selenium, Chrome, and WebDriver:

```bash
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
```
- This installs **Google Chrome, ChromeDriver, and necessary Python packages**.
- The **correct ChromeDriver version** is downloaded dynamically.

**Make the script executable:**
```bash
chmod +x .devcontainer/setup.sh
```

---

### **3. Commit and Share**
Now commit your changes:
```bash
git add .devcontainer
git commit -m "Add devcontainer setup for SITC Parser"
git push origin main
```

Now, anyone who **opens this repository in GitHub Codespaces** will have the same environment **pre-installed and ready to use!** 🚀

notes
https://chatgpt.com/c/67a74da3-0570-800a-ae92-d4e7d7c2496e 
