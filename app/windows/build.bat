@echo off
setlocal

rem Build ScarecrowControl.exe with the .NET Framework compiler.
rem No Visual Studio / NuGet required.

set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo [ERROR] .NET Framework 4.x compiler not found
  exit /b 1
)

if not exist "%~dp0dist" mkdir "%~dp0dist"

"%CSC%" -nologo -target:winexe -platform:anycpu -codepage:65001 -optimize+ ^
  -win32icon:"%~dp0app.ico" ^
  -win32manifest:"%~dp0app.manifest" ^
  -r:System.dll -r:System.Windows.Forms.dll -r:System.Drawing.dll -r:System.Web.Extensions.dll ^
  -out:"%~dp0dist\ScarecrowControl.exe" ^
  "%~dp0ScarecrowControl.cs" "%~dp0Features.cs" || exit /b 1

echo.
echo Done: %~dp0dist\ScarecrowControl.exe
endlocal
