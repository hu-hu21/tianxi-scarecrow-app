@echo off
setlocal

rem ============================================================
rem  Offline APK build (no Gradle / Android Studio required)
rem  Needs: Android SDK build-tools 35 + Studio bundled JDK 21
rem
rem  aapt2 on Windows cannot open non-ASCII paths, so the project
rem  is staged into an ASCII work directory (C:\Users\Public\...),
rem  built there, and the signed APK is copied back to .\dist.
rem ============================================================

set "ROOT=%~dp0"
set "SDK=%LOCALAPPDATA%\Android\Sdk"
set "BT=%SDK%\build-tools\35.0.0"
set "AJ=%SDK%\platforms\android-34\android.jar"
set "JBR=C:\Program Files\Android\Android Studio\jbr"

if not exist "%BT%\aapt2.exe" (
  echo [ERROR] build-tools 35.0.0 not found
  exit /b 1
)
if not exist "%AJ%" (
  echo [ERROR] android-34 platform not found
  exit /b 1
)
if not exist "%JBR%\bin\javac.exe" (
  echo [ERROR] Android Studio JDK not found
  exit /b 1
)

rem ---------- stage into an ASCII path ----------
set "WORK=%PUBLIC%\scarecrow_apk_build"
if not exist "%PUBLIC%" set "WORK=%TEMP%\scarecrow_apk_build"
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%" || exit /b 1

xcopy "%ROOT%app" "%WORK%\app" /E /I /Q /Y >nul || exit /b 1
if exist "%ROOT%keystore" (
  xcopy "%ROOT%keystore" "%WORK%\keystore" /E /I /Q /Y >nul || exit /b 1
)

echo [0/6] staged to %WORK%

set "JAVA_HOME=%JBR%"
set "PATH=%JBR%\bin;%PATH%"

if not exist "%WORK%\build\classes" mkdir "%WORK%\build\classes"
if not exist "%WORK%\build\dex" mkdir "%WORK%\build\dex"
if not exist "%WORK%\dist" mkdir "%WORK%\dist"
if not exist "%WORK%\keystore" mkdir "%WORK%\keystore"

echo [1/6] compile resources
"%BT%\aapt2.exe" compile --dir "%WORK%\app\src\main\res" -o "%WORK%\build\res.zip" || goto :fail

echo [2/6] link resources and manifest
"%BT%\aapt2.exe" link -o "%WORK%\build\base.apk" -I "%AJ%" --manifest "%WORK%\app\src\main\AndroidManifest.xml" "%WORK%\build\res.zip" --min-sdk-version 24 --target-sdk-version 34 --version-code 1 --version-name 1.0 || goto :fail

echo [3/6] compile java sources
dir /s /b "%WORK%\app\src\main\java\*.java" > "%WORK%\build\sources.txt"
"%JBR%\bin\javac.exe" -encoding UTF-8 -source 8 -target 8 -nowarn -bootclasspath "%AJ%" -d "%WORK%\build\classes" @"%WORK%\build\sources.txt" || goto :fail

echo [4/6] build dex
"%JBR%\bin\jar.exe" cf "%WORK%\build\classes.jar" -C "%WORK%\build\classes" .
"%JBR%\bin\java.exe" -cp "%BT%\lib\d8.jar" com.android.tools.r8.D8 --lib "%AJ%" --min-api 24 --release --output "%WORK%\build\dex" "%WORK%\build\classes.jar" || goto :fail

pushd "%WORK%\build\dex"
"%JBR%\bin\jar.exe" uf "%WORK%\build\base.apk" classes.dex
popd

echo [5/6] align and sign
"%BT%\zipalign.exe" -f 4 "%WORK%\build\base.apk" "%WORK%\build\aligned.apk" || goto :fail

if not exist "%WORK%\keystore\debug.keystore" (
  "%JBR%\bin\keytool.exe" -genkeypair -v -keystore "%WORK%\keystore\debug.keystore" -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" || goto :fail
)

"%JBR%\bin\java.exe" -jar "%BT%\lib\apksigner.jar" sign --ks "%WORK%\keystore\debug.keystore" --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey --out "%WORK%\dist\ScarecrowControl.apk" "%WORK%\build\aligned.apk" || goto :fail

echo [6/6] copy back and verify
if not exist "%ROOT%dist" mkdir "%ROOT%dist"
copy /Y "%WORK%\dist\ScarecrowControl.apk" "%ROOT%dist\ScarecrowControl.apk" >nul || goto :fail

"%JBR%\bin\java.exe" -jar "%BT%\lib\apksigner.jar" verify --print-certs "%ROOT%\dist\ScarecrowControl.apk" || goto :fail

rem aapt.exe also fails on non-ASCII paths, so read badging from the ASCII copy.
"%BT%\aapt.exe" dump badging "%WORK%\dist\ScarecrowControl.apk" | findstr /b "package"

rmdir /s /q "%WORK%"

echo.
echo Done: %ROOT%dist\ScarecrowControl.apk
endlocal
exit /b 0

:fail
echo.
echo [ERROR] build failed. Work directory kept for inspection: %WORK%
endlocal
exit /b 1
