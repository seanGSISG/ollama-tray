#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="ollama-tray",
    version="0.3.0",  # Updated version
    description="A system tray application to monitor and control Ollama AI model server",
    author="Swan",
    packages=find_packages(),
    package_data={
        "app": ["*.png"],
    },
    install_requires=[
        "PyQt5>=5.15.0",
        "psutil>=5.8.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "ollama-tray=app.ollama-tray:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
)
