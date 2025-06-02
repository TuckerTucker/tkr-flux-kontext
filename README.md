# Flux API CLI

A Python command-line interface for generating images using Black Forest Labs' Flux API.

## Features

- 🎨 Generate images from text prompts using Flux Kontext models
- 🔄 Image-to-image generation support
- 📦 Batch processing from JSON files
- 📊 Generation history tracking with metadata
- 💾 Automatic recovery queue for interrupted generations
- 🔁 Resume failed or interrupted generations
- ⚙️ Configurable defaults and settings
- 🚀 Never lose a generation due to crashes or network issues

## Installation

### Quick Setup (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd flux_ap
```

2. Activate the virtual environment:
```bash
source start_env
```

3. Run the setup script:
```bash
./flux_setup.sh
```

This will install the CLI with all features including image preview support.

### Manual Installation

If you prefer to install manually:

1. Clone and navigate to the repository:
```bash
git clone <repository-url>
cd tkr-flux-kontext
```

2. Activate the virtual environment:
```bash
source start_env
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. (Optional) Install additional features:
```bash
# For terminal image preview support
pip install -e ".[preview]"

# For development tools (testing, linting)
pip install -e ".[dev]"

# For webhook support
pip install -e ".[webhook]"
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Add your Flux API key:
```
FLUX_API_KEY=your-api-key-here
```

3. (Optional) Copy and customize the configuration file:
```bash
cp config.example.yaml config.yaml
```

## Usage

### Basic Generation

Generate an image with a simple command:
```bash
flux generate --prompt "A majestic mountain landscape at sunset"
```

### Interactive Mode

Use interactive prompts:
```bash
flux generate -I
```

### Advanced Options

```bash
flux generate \
  --prompt "A futuristic city" \
  --model flux-kontext-max \
  --seed 42 \
  --aspect-ratio 16:9 \
  --output-format png \
  --safety 2
```

### Seed Handling

The CLI always uses a seed for reproducible results:
- If no seed is specified, a random one is generated
- Use `--seed <number>` to set a specific seed
- Configure default behavior in `config.yaml`:
  ```yaml
  defaults:
    seed: 42        # Always use this seed
    seed: random    # Explicitly random (default)
  ```
- The seed used is always saved in metadata for future reference

### Image-to-Image Generation

```bash
flux generate \
  --prompt "Transform into a watercolor painting" \
  --input-image path/to/source.jpg
```

### View History

```bash
flux history --last 10
```

### Regenerate Previous Image

```bash
flux regenerate <generation-id>
```

### Recovery Queue

The CLI automatically saves generation information as soon as it's submitted to the API. If your script crashes or loses connection, you can recover your images. Successfully completed generations are automatically removed from the queue.

```bash
# List all pending generations
flux recover --list

# Resume a specific generation
flux recover --resume <generation-id>

# Resume all pending generations
flux recover --resume-all

# Clean up ALL completed entries
flux recover --clean

# Clean up completed entries older than N hours
flux recover --clean-old 24
```

**Example recovery scenario:**
```bash
# Start a generation
flux generate --prompt "A majestic mountain landscape"
# Script crashes during processing...

# Check what's pending
flux recover --list
# Shows: be11d443-b64b-4c67-b66b-3a50b5ecfc18 | processing | A majestic mountain landscape

# Resume the generation
flux recover --resume be11d443-b64b-4c67-b66b-3a50b5ecfc18
# Image downloads successfully!
```

## Directory Structure

```
data/
├── source_images/      # Input images for image-to-image
├── generated/          # Generated images (organized by date)
│   └── 2025/
│       └── 06/
│           └── 01/
├── history/           # Generation history log
└── queue/             # Recovery queue for pending generations
    └── active_generations.json
```

## Models

- `flux-kontext-pro`: Standard quality, faster generation
- `flux-kontext-max`: Higher quality, more detailed
- `flux-pro-1.0-expand`: Outpainting/expansion (coming soon)

## License

This project is licensed under the MIT License.