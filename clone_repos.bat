@echo off
REM clone_repos.bat — Clone all 5 ZoomRx repositories for DTSA code investigation
REM
REM Usage:
REM   clone_repos.bat [TARGET_DIR]
REM
REM TARGET_DIR defaults to %USERPROFILE%\zoomrx-repos if not specified.
REM After cloning, set DTSA_LOCAL_REPOS_BASE in your .env to the target directory.
REM
REM Requirements:
REM   - git must be installed and on your PATH
REM   - Access to phab.zoomrx.com (Phabricator) for 4 of the 5 repos
REM   - Access to github.com/ZoomRx for perxcept-ap-server
REM
REM Phabricator access: you need an account on phab.zoomrx.com and HTTP
REM credentials configured. If cloning fails with a 403/auth error, ask your
REM team lead to grant you repository access in Phabricator.

setlocal enabledelayedexpansion

if "%~1"=="" (
    set TARGET_DIR=%USERPROFILE%\zoomrx-repos
) else (
    set TARGET_DIR=%~1
)

echo Cloning ZoomRx repositories into: %TARGET_DIR%
echo.

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

set PHAB_BASE=http://phab.zoomrx.com/source

call :clone_or_pull "digitrace-chrome-extension"       "%PHAB_BASE%/digitrace-chrome-extension.git"
call :clone_or_pull "perxcept-ios"                     "%PHAB_BASE%/perxcept-ios.git"
call :clone_or_pull "perxcept-macos"                   "%PHAB_BASE%/perxcept-macos.git"
call :clone_or_pull "perxcept-data-processing-service" "%PHAB_BASE%/perxcept-data-processing-service.git"
call :clone_or_pull "perxcept-ap-server"               "https://github.com/ZoomRx/perxcept-ap-server.git"

echo.
echo Done. Add this line to your .env:
echo.
echo   DTSA_LOCAL_REPOS_BASE=%TARGET_DIR%
echo.
goto :eof

:clone_or_pull
set REPO_NAME=%~1
set REPO_URL=%~2
set DEST=%TARGET_DIR%\%REPO_NAME%

if exist "%DEST%\.git" (
    echo   Pulling latest: %REPO_NAME%
    git -C "%DEST%" pull --ff-only
) else (
    echo   Cloning: %REPO_NAME%
    git clone "%REPO_URL%" "%DEST%"
)
goto :eof
