"""
Cortex Core - Setup Script

This module sets up the Cortex Core package for installation and distribution.
"""

import os
from setuptools import setup, find_packages

# Read the contents of the README file
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Read requirements from requirements.txt
with open(
    os.path.join(os.path.dirname(__file__), "requirements.txt"), encoding="utf-8"
) as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="cortex-core",
    version="1.0.0",
    description="Cortex Core - AI-powered assistance framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cortex Team",
    author_email="admin@example.com",
    url="https://github.com/example/cortex-core",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    entry_points={
        "console_scripts": [
            "cortex-core=app.main:main",
        ],
    },
    extras_require={
        "dev": [
            "black>=23.3.0",
            "isort>=5.12.0",
            "mypy>=1.2.0",
            "ruff>=0.0.260",
            "pre-commit>=3.2.0",
        ],
        "test": [
            "pytest>=7.3.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "httpx>=0.24.0",
        ],
    },
)
