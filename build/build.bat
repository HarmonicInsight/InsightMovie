@echo off
REM ShortMaker Studio Build Script
REM Windows用ビルド自動化スクリプト

setlocal enabledelayedexpansion

echo ========================================
echo ShortMaker Studio Build Script
echo ========================================
echo.

REM カレントディレクトリをbuildフォルダに設定
cd /d %~dp0

REM Step 1: 環境確認
echo [Step 1/5] Checking environment...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    goto error
)
echo - Python: OK

pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller is not installed
    echo Please run: pip install pyinstaller
    goto error
)
echo - PyInstaller: OK

echo.

REM Step 2: クリーンアップ
echo [Step 2/5] Cleaning previous build...
echo.

if exist dist (
    echo Removing dist folder...
    rmdir /s /q dist
)

if exist build (
    echo Removing build folder...
    rmdir /s /q build
)

echo Clean completed.
echo.

REM Step 3: PyInstallerでビルド
echo [Step 3/5] Building with PyInstaller...
echo.

pyinstaller shortmaker_studio.spec
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    goto error
)

echo Build completed.
echo.

REM Step 4: ビルド結果の確認
echo [Step 4/5] Verifying build...
echo.

if not exist "dist\ShortMakerStudio\ShortMakerStudio.exe" (
    echo ERROR: ShortMakerStudio.exe not found in dist folder
    goto error
)

echo - ShortMakerStudio.exe: OK

REM ファイルサイズ表示
for %%F in ("dist\ShortMakerStudio\ShortMakerStudio.exe") do (
    set size=%%~zF
    set /a size_mb=!size! / 1048576
    echo - Size: !size_mb! MB
)

echo.

REM Step 5: インストーラー作成（オプション）
echo [Step 5/5] Creating installer (optional)...
echo.

set INNO_SETUP="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist %INNO_SETUP% (
    echo Inno Setup found. Creating installer...
    %INNO_SETUP% ..\installer\shortmaker_studio.iss

    if %errorlevel% neq 0 (
        echo WARNING: Installer creation failed
        echo Build completed, but installer was not created.
    ) else (
        echo Installer created successfully!

        REM インストーラーの場所を表示
        for %%F in ("..\build\installer_output\ShortMakerStudio-Setup-*.exe") do (
            echo - Installer: %%~nxF
            set /a inst_size=%%~zF / 1048576
            echo - Size: !inst_size! MB
        )
    )
) else (
    echo Inno Setup not found at %INNO_SETUP%
    echo Skipping installer creation.
    echo.
    echo To create installer manually:
    echo 1. Install Inno Setup from https://jrsoftware.org/isdl.php
    echo 2. Open installer\shortmaker_studio.iss
    echo 3. Click Build ^> Compile
)

echo.
echo ========================================
echo Build Summary
echo ========================================
echo.
echo Build directory: %cd%\dist\ShortMakerStudio\
echo Main executable: ShortMakerStudio.exe
echo.
echo Next steps:
echo 1. Test the application: dist\ShortMakerStudio\ShortMakerStudio.exe
echo 2. Create installer (if not already created)
echo 3. Run tests according to docs\TESTING_GUIDE.md
echo.
echo ========================================
echo Build completed successfully!
echo ========================================
goto end

:error
echo.
echo ========================================
echo Build failed!
echo ========================================
echo.
echo Please check the error messages above and fix the issues.
echo.
pause
exit /b 1

:end
echo.
pause
exit /b 0
