"""Setup configuration for Flux CLI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="flux-cli",
    version="0.1.0",
    author="TKR",
    description="A Python CLI for Black Forest Labs' Flux image generation API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "rich>=13.7.0",
        "pillow>=10.2.0",
    ],
    extras_require={
        "preview": ["ascii-magic>=2.3.0"],
        "webhook": ["fastapi>=0.109.0", "uvicorn>=0.27.0", "aiofiles>=23.2.0"],
        "dev": ["pytest>=7.4.0", "pytest-cov>=4.1.0", "black>=23.12.0", "flake8>=6.1.0", "mypy>=1.7.0"],
    },
    entry_points={
        "console_scripts": [
            "flux=flux_cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)