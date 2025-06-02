#!/bin/bash

# Flux CLI Setup Script
# This script installs the Flux CLI and its dependencies

# Color codes for consistent output
ORANGE='\033[38;5;208m'
RED='\033[38;5;201m'
RESET='\033[0m'

printf "${ORANGE}===================================${RESET}\n"
printf "${ORANGE}     Flux CLI Setup Script${RESET}\n"
printf "${ORANGE}===================================${RESET}\n"
printf "\n"

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    printf "${RED}ERROR: Virtual environment is not active!\n"
    printf "\n"
    printf "Please activate the tkr_env first by running:\n"
    printf "  source start_env\n"
    printf "\n"
    printf "Then run this script again.${RESET}\n"
    exit 1
fi

# Check if we're in the correct virtual environment
if [[ "$VIRTUAL_ENV" != *"tkr_env/project_env"* ]]; then
    printf "${ORANGE}WARNING: You appear to be in a different virtual environment:\n"
    printf "  Current: $VIRTUAL_ENV\n"
    printf "\n"
    printf "Expected tkr_env/project_env. Continue anyway? (y/N)${RESET} "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        printf "${RED}Setup cancelled.${RESET}\n"
        exit 1
    fi
fi

printf "${ORANGE}Virtual environment detected: $VIRTUAL_ENV${RESET}\n"
printf "\n"

# Check if we're in the correct directory
if [ ! -f "setup.py" ]; then
    printf "${RED}ERROR: setup.py not found!\n"
    printf "Please run this script from the project root directory.${RESET}\n"
    exit 1
fi

printf "${ORANGE}Installing Flux CLI...${RESET}\n"
printf "\n"

# Upgrade pip first
printf "${ORANGE}Updating pip${RESET}\n"
pip install --upgrade pip > /dev/null 2>&1

# Define installation steps
declare -a install_steps=(
    "Core package|pip install -e ."
    "Preview support|pip install -e .[preview]"
    "Development tools|pip install -e .[dev]"
)

# Track progress
total_steps=${#install_steps[@]}
current_step=0

# Install each component with progress indicator
for step in "${install_steps[@]}"; do
    IFS='|' read -r description command <<< "$step"
    ((current_step++))
    
    printf "\r${ORANGE}  [%d/%d] Installing: %-25s${RESET}" "$current_step" "$total_steps" "$description"
    
    # Execute the installation command
    eval "$command" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        printf "\r${ORANGE}  [%d/%d] ✓ Installed: %-25s${RESET}\n" "$current_step" "$total_steps" "$description"
    else
        printf "\r${RED}  [%d/%d] ✗ Failed: %-25s${RESET}\n" "$current_step" "$total_steps" "$description"
        echo -e "${RED}Installation failed. Check the error above.${RESET}"
        exit 1
    fi
done

printf "\r${ORANGE}  ✓ All components installed successfully!%-30s${RESET}\n" " "

printf "\n"
printf "${ORANGE}===================================${RESET}\n"
printf "${ORANGE}✓ Setup Complete!${RESET}\n"
printf "${ORANGE}===================================${RESET}\n"
printf "\n"
printf "${ORANGE}You can now use the Flux CLI:${RESET}\n"
printf "${ORANGE}  flux --help${RESET}\n"
printf "${ORANGE}  flux generate --prompt \"Your image prompt\"${RESET}\n"
printf "\n"
printf "${ORANGE}Don't forget to:${RESET}\n"
printf "${ORANGE}  1. Copy .env.example to .env${RESET}\n"
printf "${ORANGE}  2. Add your FLUX_API_KEY to .env${RESET}\n"
printf "${ORANGE}  3. (Optional) Copy config.example.yaml to config.yaml${RESET}\n"
printf "\n"