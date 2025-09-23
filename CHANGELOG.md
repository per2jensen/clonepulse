# Changelog

All notable changes to **ClonePulse** will be documented in this file.  
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.3]

### Added

- `--year` CLI option for `generate_clone_dashboard.py`
  - Allows selecting a full calendar year of data
  - Mutually exclusive with `--start` and `--weeks`
  - Validation: errors on future years, empty dashboard if no data
- Test cases added for the clone data fetcher
- Documentation split into **README.md** (user) and **DEVELOP.md** (developer)
- New **CHANGELOG.md**

### Changed

- CLI help text updated to clarify `--weeks` is ignored when `--year` is provided
- README reorganized and simplified for end-users

---

## [1.0.2] – 2025-09-22

### Changed

- Added --start and --weeks to create dashboard for a specified period
- Doc changes

---

## [1.0.1] – 2025-07-11

### Changed

- Doc fixes

---

## [1.0.0] – 2025-06-19

### Added

- Initial release of ClonePulse
- Fetch clone statistics via GitHub API
- Generate weekly dashboard PNGs (12-week default)
- Automatic milestone badge generation
- Example GitHub Actions workflows
- Badge JSON endpoints for total clones and milestones
- Example dashboard and documentation

---
