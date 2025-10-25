@ECHO OFF
SETLOCAL EnableDelayedExpansion

git ls-files > file.txt

:: Define the string to prepend
SET "PrependString=https://raw.githubusercontent.com/MctMarcus3/Quizzler/refs/heads/main/"

:: Define the input file
SET "InputFile=file.txt"

:: Define a temporary output file
SET "TempFile=%InputFile%.tmp"

:: Check if the input file exists
IF NOT EXIST "%InputFile%" (
    ECHO Error: Input file "%InputFile%" not found.
    GOTO :EOF
)

:: Create a new file with prepended lines
FOR /F "usebackq delims=" %%a IN ("%InputFile%") DO (
    ECHO %PrependString%%%a>>"%TempFile%"
)

:: Replace the original file with the modified one
MOVE /Y "%TempFile%" "%InputFile%" >NUL

ECHO Prepending complete for "%InputFile%".
ENDLOCAL