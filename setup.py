#!/usr/bin/env python3
"""Setup script for fzf-ai."""

from setuptools import setup
import os

# Read version from version.py
version = {}
with open("bin/version.py") as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

setup(
    name="fzf-ai",
    version=__version__,
    description="Fuzzy-find and resume any AI coding session across multiple AI assistants",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="fzf-ai contributors",
    author_email="",
    url="https://github.com/yourusername/fzf-ai",  # Update this if it's on GitHub
    license="MIT",  # Update if you want a different license
    packages=[],  # We're installing scripts directly, not Python packages
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],
    # Entry points not needed - scripts are installed directly as data files
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",  # Update if using different license
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Text Processing :: Filters",
    ],
    keywords="fzf ai coding assistant claude codex opencode droid pi",
    data_files=[
        # Include the bin scripts
        ('bin', [
            'bin/fzf-ai',
            'bin/fzf-ai-index', 
            'bin/fzf-ai-preview',
            'bin/fzf-ai-resume',
            'bin/fzf-ai-ui',
        ]),
    ],
    zip_safe=False,
)