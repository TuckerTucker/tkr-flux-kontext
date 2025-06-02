#!/bin/bash

### Copy Script
# From the project directory run this in the console
# cp tkr_env/start_env.copyToParent ./start_env

# Function to display help message
display_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -h, --help           Display this help message"
    echo "  --env NAME           Specify the name of the virtual environment (default: project_env). If you change it be sure to update the .gitignore"
    echo "  --python-path PATH   Specify the directory to add to the Python path"
    echo "  --base-dir PATH      Specify the base directory path (default: current directory)"
}

# Function to check and add Python path
add_python_path() {
    if [ -n "$python_path" ]; then
        if echo "$PYTHONPATH" | grep -q "\(^\|:\)$python_path\(:\|$\)"; then
            echo -e "\e[38;5;208m$python_path \nis already in PYTHONPATH.\e[0m"
        else
            echo -e "\e[38;5;208mAdding $python_path to PYTHONPATH\e[0m"
            export PYTHONPATH="$python_path:$PYTHONPATH"
        fi
    fi
}

# Function to add the virtual environment name to .gitignore
add_to_gitignore() {
    if ! grep -qx "$env_name" ".gitignore"; then
        echo -e "\e[38;5;208mAdding '$env_name' to .gitignore\e[0m"
        echo "$env_name" >> ".gitignore"
    else
        echo -e "\e[38;5;208m'$env_name' is already in .gitignore\e[0m"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            display_help
            exit 0
            ;;
        --env)
            env_name="$2"
            shift
            shift
            ;;
        --python-path)
            python_path="$2"
            shift
            shift
            ;;
        --base-dir)
            base_dir="$2"
            shift
            shift
            ;;
        *)
            echo "Unknown option: $1"
            display_help
            exit 1
            ;;
    esac
done

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
project_directory="$(dirname "$SCRIPT_DIR")"

# Set default values if not provided
env_name=${env_name:-project_env} # 'project_env' is the default name
base_dir=${base_dir:-$project_directory} # sets the project directory as base directory
python_path=${python_path:-$base_dir}

# Check if the virtual environment already exists
if [ -d "$env_name" ]; then
    source "$env_name/bin/activate"
    echo -e "\e[38;5;208mActivated '$env_name'.\e[0m"
    
    # Call the function to check and add Python path
    add_python_path
else
    # Create the virtual environment if it does not exist
    python3 -m venv $env_name
    echo -e "\e[38;5;208mCreated '$env_name'.\e[0m"

    # Add the virtual environment name to .gitignore
    add_to_gitignore

    # Define a timeout in seconds and polling interval (e.g., half a second)
    timeout=300
    elapsed=0
    poll_interval=0.5
    pip_interval=1

    # Check if the activation script exists, with polling
    while [ $elapsed -lt $timeout ]; do
        if [ -f "$env_name/bin/activate" ]; then
            source "$env_name/bin/activate"
            echo -e "\e[38;5;208mActivated '$env_name'.\e[0m"

            # Check if the virtual environment is correctly activated
            if [[ -z "$VIRTUAL_ENV" ]]; then
                echo -e "\e[38;5;201mThe virtual environment is not activated properly. Please check the environment.\e[0m"
                break
            else
                # Update pip
                echo -e "\e[38;5;208mUpdating pip\e[0m"
                pip install --upgrade pip > /dev/null 2>&1
                
                # Install requirements from env_requirements
                echo -e "\e[38;5;208mInstalling requirements from env_requirements\e[0m"
                
                # Show progress with package names
                total_packages=$(wc -l < "env_requirements" | tr -d ' ')
                current_package=0
                
                while IFS= read -r package || [[ -n "$package" ]]; do
                    # Skip empty lines and comments
                    [[ -z "$package" || "$package" =~ ^[[:space:]]*# ]] && continue
                    
                    ((current_package++))
                    printf "\r\e[38;5;208m  [%d/%d] Installing: %-20s\e[0m" "$current_package" "$total_packages" "$package"
                    pip install --no-cache-dir "$package" > /dev/null 2>&1
                done < "env_requirements"
                
                printf "\r\e[38;5;208m  ✓ All packages installed successfully!%-30s\e[0m\n" " "

                # Call the function to check and add Python path
                add_python_path
            fi
            break
        else
            echo -e "\e[38;5;208mWaiting for the virtual environment to be ready...\e[0m"
            sleep $poll_interval
            elapsed=$((elapsed + poll_interval))
        fi
    done

    if [ $elapsed -ge $timeout ]; then
        echo -e "\e[38;5;201mTimeout reached. The virtual environment was not activated.\e[0m"
    fi
fi
