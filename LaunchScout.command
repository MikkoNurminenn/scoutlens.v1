#!/bin/bash

# Navigate to the project folder on Desktop
cd "$HOME/Desktop/project root" || {
  echo "❌ Could not find the project folder!"
  exit 1
}

# Make sure setup.sh is executable and run it
chmod +x setup.sh
./setup.sh
