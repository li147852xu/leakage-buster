
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-09-13

### Added
- **Performance & Scalability**
  - Added `--engine` parameter to support both pandas and polars engines
  - Added `--n-jobs` parameter for parallel processing control
  - Added `--memory-cap` parameter for memory usage control
  - Added `--sample-ratio` parameter for large dataset sampling
  - Implemented `DataLoader` class with memory optimization
  - Implemented `ParallelProcessor` class with joblib integration
  - Added performance tests for medium-scale datasets (150K rows, 250 columns)

- **Enhanced Reporting**
  - Added interactive risk radar chart with JavaScript rendering
  - Enhanced risk matrix with visual severity indicators
  - Added comprehensive table of contents
  - Added collapsible evidence blocks for detailed inspection
  - Added footer with git hash, random seed, and system metadata
  - Improved responsive design for mobile and print media

- **Docker Support**
  - Added `Dockerfile` with Python 3.11-slim base image
  - Added health checks and proper entrypoint configuration
  - Added Docker labels for metadata and source tracking

- **PyPI Ready**
  - Updated `pyproject.toml` with complete project metadata
  - Added optional dependencies for polars, dev tools, docs, and performance
  - Added proper classifiers and keywords for discoverability
  - Added comprehensive test configuration with markers

- **CI/CD Improvements**
  - Fixed GitHub Actions workflow with proper job dependencies
  - Added conditional job execution based on branch and event type
  - Improved error handling and artifact management
  - Added security scanning and documentation jobs

### Changed
- **API Stability**
  - Stabilized all public APIs for v1.0 release
  - Updated Pydantic models to use `model_dump()` instead of deprecated `dict()`
  - Improved error handling and user feedback throughout CLI

- **Performance Optimizations**
  - Optimized memory usage with automatic data type downcasting
  - Added chunked processing for large datasets
  - Implemented intelligent sampling when memory limits are exceeded
  - Added system resource monitoring and adaptive parallelization

- **Documentation**
  - Created version-specific README files for each release
  - Added comprehensive "Three-minute Quick Start" guide
  - Added complete CLI parameter reference
  - Added tabular-agent integration documentation
  - Added performance benchmarks and scaling guidelines

### Fixed
- **Memory Management**
  - Fixed memory leaks in large dataset processing
  - Fixed OOM issues with datasets exceeding 4GB
  - Fixed data type optimization for better memory efficiency

- **CI/CD Issues**
  - Fixed GitHub Actions workflow failures
  - Fixed job cancellation issues
  - Fixed artifact upload and retention policies

- **File Management**
  - Improved `.gitignore` to properly exclude debug and test files
  - Cleaned up temporary files and debug outputs
  - Added proper project structure following Python packaging standards

### Security
- Added security scanning with Bandit and Safety
- Added dependency vulnerability checking
- Added proper input validation and sanitization

## [0.5.0-rc1] - 2024-09-13

### Added
- **Semi-Automatic Fix System**
  - Added `--auto-fix plan` mode to generate structured fix plans
  - Added `--auto-fix apply` mode to automatically apply fixes
  - Implemented Pydantic-based fix plan models with evidence tracking
  - Added intelligent fix recommendations based on risk analysis

- **Stable Python SDK**
  - Added `leakage_buster.api` module with stable public APIs
  - Implemented `audit()`, `plan_fixes()`, `apply_fixes_to_dataframe()` functions
  - Added comprehensive type annotations and documentation
  - Added `AuditResult` class with rich metadata and properties

- **Standardized Exit Codes**
  - Implemented `0=ok`, `2=warnings`, `3=high-leakage`, `4=invalid-config`
  - Added proper exit code handling throughout CLI
  - Added CI/CD integration examples with exit code checking

- **CI/CD Integration**
  - Added GitHub Actions workflow with comprehensive testing
  - Added security scanning and documentation jobs
  - Added artifact management and retention policies
  - Added multi-Python version testing (3.9-3.12)

### Changed
- **Project Structure**
  - Added version-specific documentation in `docs/versions/`
  - Improved `.gitignore` to hide debug and test files
  - Added proper project metadata and classifiers

## [0.4.0] - 2024-09-13

### Added
- **Calibration Consistency Audit**
  - Added `--cv-policy-file` parameter for CV policy configuration
  - Implemented `CVPolicyAuditor` class for policy validation
  - Added offline/online calibration difference detection
  - Added risk level assessment (High/Med/Low) for policy violations

- **Enhanced Reporting**
  - Added table of contents for better navigation
  - Added risk matrix with High/Med/Low counts
  - Added collapsible evidence blocks for detailed inspection
  - Enhanced report template with better visual hierarchy

- **Export Capabilities**
  - Added `--export pdf` parameter with WeasyPrint support
  - Added `--export-sarif` parameter for GitHub Code Scanning
  - Implemented `ReportExporter` class for multiple export formats
  - Added fallback mechanisms for missing dependencies

- **Testing & Examples**
  - Added `conf/cv_policy.yaml` example configuration
  - Added `tests/test_cv_policy.py` comprehensive test suite
  - Added `examples/group_cv.csv` synthetic dataset for group CV testing

## [0.3.0] - 2024-09-13

### Added
- **Statistical Leakage Detection**
  - Implemented Target Encoding (TE) leakage detection
  - Implemented Weight of Evidence (WOE) leakage detection
  - Implemented rolling statistics leakage detection
  - Implemented aggregation traces detection
  - Added leak score quantification (0-1 scale)

- **Time Series Simulator**
  - Added `--simulate-cv time` parameter for time series simulation
  - Added `--leak-threshold` parameter for configurable leak detection
  - Implemented TimeSeriesSplit vs KFold comparison
  - Added OOF metrics comparison with statistical significance testing

- **Enhanced Reporting**
  - Added "Statistical Leakage" section in reports
  - Added risk score visualization and evidence details
  - Added time series simulation results with comparison tables
  - Enhanced fix script generation with statistical leakage suggestions

- **Testing & Examples**
  - Added `examples/homecredit_te.csv` for target encoding testing
  - Added `examples/fraud_rolling.csv` for rolling statistics testing
  - Added `tests/test_te_woe_rolling.py` comprehensive test suite

## [0.2.0] - 2024-09-13

### Added
- **Extended Detection Framework**
  - Implemented abstract detector interface with `DetectorProtocol`
  - Added `BaseDetector` class for consistent detector implementation
  - Added `DetectorRegistry` for modular detector management
  - Added placeholder for statistical leakage detection

- **JSON Schema & Exit Codes**
  - Implemented standardized JSON output format
  - Added exit code definitions (0/2/3/4) for different scenarios
  - Added structured error handling with detailed error messages
  - Added API integration support for tabular-agent

- **Enhanced Reporting**
  - Added "修复建议摘要" (Fix Suggestions Summary) card
  - Added "统计类泄漏（预览）" (Statistical Leakage Preview) section
  - Enhanced report template with better organization

- **Testing**
  - Added `tests/test_schema.py` for JSON schema validation
  - Added comprehensive test coverage for new features

## [0.1.0] - 2024-09-13

### Added
- **Core Detection Capabilities**
  - Target leakage detection (high correlation, categorical purity)
  - Time leakage detection (time column parsing, time-awareness suggestions)
  - Group leakage detection (high duplicate columns → GroupKFold recommendation)
  - CV strategy consistency recommendations

- **Professional Reporting**
  - HTML report generation with Jinja2 templates
  - Automatic fix script generation (`fix_transforms.py`)
  - JSON metadata output (`meta.json`)
  - Chinese language support throughout

- **Project Structure**
  - `src` layout with proper package organization
  - `console_scripts` entry point for CLI access
  - Comprehensive test suite with smoke tests
  - Example datasets and usage documentation

- **CLI Interface**
  - `leakage-buster run` command with full parameter support
  - `--train`, `--target`, `--time-col`, `--out` parameters
  - `--cv-type` parameter for CV strategy specification
  - Comprehensive help and usage examples

---

## Migration Guide

### From v0.5-rc to v1.0.0

**Breaking Changes:**
- None (v1.0.0 is fully backward compatible)

**New Features:**
- Use `--engine polars` for better performance with large datasets
- Use `--n-jobs 8` for parallel processing
- Use `--memory-cap 4096` to limit memory usage
- Use `--sample-ratio 0.5` for large dataset sampling

**Performance Improvements:**
- Automatic memory optimization
- Chunked processing for large files
- Parallel processing for multiple detectors

### From v0.4.0 to v0.5-rc

**New Features:**
- Use `--auto-fix plan` to generate fix plans
- Use `--auto-fix apply` to automatically fix data
- Use Python SDK for programmatic access

**API Changes:**
- All APIs are now stable and documented
- Exit codes are standardized across all interfaces

### From v0.3.0 to v0.4.0

**New Features:**
- Use `--cv-policy-file` for policy-based auditing
- Use `--export pdf` for PDF reports
- Use `--export-sarif` for GitHub Code Scanning

### From v0.2.0 to v0.3.0

**New Features:**
- Use `--simulate-cv time` for time series simulation
- Use `--leak-threshold` to adjust sensitivity

### From v0.1.0 to v0.2.0

**New Features:**
- Use `--cv-type` to specify CV strategy
- JSON output format is now standardized

---

## Support

- **Documentation**: https://leakage-buster.readthedocs.io
- **Issues**: https://github.com/li147852xu/leakage-buster/issues
- **Source**: https://github.com/li147852xu/leakage-buster
- **PyPI**: https://pypi.org/project/leakage-buster/

