# CHANGELOG

This document records all notable changes to ``omni.kit.environment.sunstudy`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.0.11] - 2023-02-21
### Fixed
- OM-101351: sunstudy window does not move correctly according to viewport size change. It always
    move to default position while viewport size changed.
    This fix: Re-implement the sunstudy window using Viewport Layer instead of an independent window,
    using a stub window (physically invisible at any time) to make it compitiable with USD-Presenter
    (which detect/operate the window using ui.Workspace staff). A viewport layer is nested in viewport window,
    so this bug should have been fixed thoroughly.

## [1.0.10] - 2023-02-21
### Added
- OM-83377: Fix error for python 3.10

## [1.0.9] - 2022-09-10
### Removed
- Remove env preference test since it is already in omni.kit.environment.core

## [1.0.8] - 2022-09-08
### Fixed
- Only show Environment in preferences window to fix ETM test failures

## [1.0.7] - 2022-09-02
### Fixed
- ETM test failures

## [1.0.6] - 2022-08-22
### Changed
- Removed redundant modules (use `omni.kit.widgets.custom` instead)

## [1.0.5] - 2022-06-26
### Changed
- Remove omni.kit.window.viewport

## [1.0.4] - 2022-03-30
### Changed
- Update repo_build and repo_licensing

## [1.0.3] - 2022-01-04
### Changed
- Fix location window input issue.

## [1.0.2] - 2021-12-09
### Changed
- Updated the use of omni.kit.viewport to omni.kit.viewport_legacy

## [1.0.1] - 2021-11-25
### Changed
- Time slider argument

## [1.0.0] - 2021-11-25
### Added
- Rename from omni.kit.window.sunstudy
