# Basic Python Virtual Envirionment Set Up
 Automatically sets up a Python virtual environment. 

## Setup

From your project directory: 

Copy the start script

    ```bash
    cp tkr_env/start_env.copyToParent ./start_env
    ```

Start the env
    ```bash
    source start_env
    ```    
    
1. First it checks if the environment exists.
env true: Creates and activates the environtment then installs all packages in 'env_requirements' (listed below). 
env false: Activates the environment.

### Change Environment Nmme

Use --env to control the name

```bash
source start_env --env "my_env_name"
```

or 

Set the `env_name` variable in `tkr_env.sh` to set the default. 


*To change the environment name after it's created you'll need to do it manually.*
*It's easiest to just delete the project_env folder and restart with a new name.*