#!/bin/bash

# Update and install necessary packages
sudo dnf update -y
sudo dnf install -y git-all python gcc

# Configure Git
git config --global user.name "JordanLevy99"

# Clone the repository
mkdir -p ~/GitHub
cd ~/GitHub
git clone https://github.com/JordanLevy99/Larrys_Gym_Tracker.git
cd Larrys_Gym_Tracker

# Set up Python virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Move necessary files into the project directory (adjust paths if necessary)
mv ~/Larrys_Gym_Tracker/data .

# Compile and install Opus codec
wget https://downloads.xiph.org/releases/opus/opus-1.5.1.tar.gz
tar xvf opus-1.5.1.tar.gz
cd opus-1.5.1/
sudo ./configure
sudo make
sudo make install

# Return to project directory and run the application
cd ~/GitHub/Larrys_Gym_Tracker
python larrys_gym_tracker.py --local