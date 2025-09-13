
from setuptools import setup, find_packages

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="leakage-buster",
    version="1.0.0",
    author="Leakage Buster Team",
    author_email="team@leakage-buster.dev",
    description="Data leakage detection and audit tool for machine learning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/li147852xu/leakage-buster",
    project_urls={
        "Bug Reports": "https://github.com/li147852xu/leakage-buster/issues",
        "Source": "https://github.com/li147852xu/leakage-buster",
        "Documentation": "https://leakage-buster.readthedocs.io",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0",
        "numpy>=1.23",
        "scikit-learn>=1.2",
        "jinja2>=3.1",
        "pyyaml>=6.0",
        "pydantic>=2.0",
        "psutil>=5.9",
    ],
    extras_require={
        "polars": ["polars>=0.20.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1",
            "mypy>=1.0",
        ],
        "docs": [
            "sphinx>=5.0",
            "sphinx-rtd-theme>=1.0",
            "myst-parser>=1.0",
        ],
        "perf": [
            "polars>=0.20.0",
            "joblib>=1.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "leakage-buster=leakage_buster.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "leakage_buster.templates": ["*.j2"],
    },
    zip_safe=False,
)
