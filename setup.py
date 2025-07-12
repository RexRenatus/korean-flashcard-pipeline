"""
Setup script for Korean Flashcard Pipeline
Enables installation and CLI command creation
"""

from setuptools import setup, find_packages
import os

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="flashcard-pipeline",
    version="1.0.0",
    author="Korean Flashcard Pipeline Team",
    author_email="",
    description="AI-powered Korean language flashcard generation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/flashcard-pipeline",
    packages=find_packages(where="src/python"),
    package_dir={"": "src/python"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
        "monitoring": [
            "watchdog>=2.0",
        ],
        "scheduling": [
            "schedule>=1.0",
        ],
        "export": [
            "genanki>=0.13",
            "reportlab>=3.6",
            "markdown>=3.0",
            "pandas>=1.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "flashcard-pipeline=flashcard_pipeline.cli_v2:app",
            "flashcard-pipeline-simple=flashcard_pipeline.pipeline_cli:app",
            "flashcard-pipeline-enhanced=flashcard_pipeline.cli_enhanced:app",
        ],
    },
    include_package_data=True,
    package_data={
        "flashcard_pipeline": [
            "templates/*.html",
            "templates/*.css",
            "migrations/*.sql",
        ],
    },
    zip_safe=False,
)