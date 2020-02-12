@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  Competitions startup script for Windows
@rem
@rem ##########################################################################
goto :init

:header
    echo Beam Competition script to run simulation
    echo providing command-line arguments
    echo.
    goto :eof

:usage
    echo USAGE:
    echo   %__BAT_NAME% [[-m args]] [[-c args]] [ [[--config args ]] or [[-s args]] [[-n args]] [[-sz args]] [[-i args]] ]
    echo.
    echo.  -h, --help           shows this help
    echo.  --config             provide config file
    echo.  -s, --scenario       scenario name
    echo.  -sz, --size          sample size
    echo.  -m, --memory         memory limit
    echo.  -c, --cpus           number of CPUs
    echo.  -i, --input          input folder path
    echo.  -n, --iters          iteration amount
    goto :eof

:missing_argument
    call :header
    call :usage
    echo.
    echo ****    MISSING "%~1"    ****
    echo.
    goto :eof
	
rem This extracts the first numerical serie in the input string    
:extractLeadingNumbers inputString returnNum returnExt
    setlocal enableextensions disabledelayedexpansion
    rem Retrieve the string from arguments
    set "string=%~1"

    rem Use numbers as delimiters (so they are removed) to retrieve the rest of the string
    for /f "tokens=1-2 delims=0123456789 " %%a in ("%string:^"=%") do set "delimiters=%%a%%b"

    rem Use the retrieved characters as delimiters to retrieve the first numerical serie
    for /f "delims=%delimiters% " %%a in ("%string:^"=%") do set "numbers=%%a"

    rem Return the found data to caller and leave
    endlocal & set "%~2=%numbers%" & set "%~3=%delimiters%"
    goto :eof

:init
    set "__NAME=%~n0"

    set "__BAT_FILE=%~0"
    set "__BAT_PATH=%~dp0"
    set "__BAT_NAME=%~nx0"

    set "MemoryOpt=4g"
    set "CpuOpt=2"

    set "InputOpt="

    set "ConfigPath="

    set "ScenarioArg="
    set "SizeArg="
    set "ItersArg="

:parse
    if "%~1"=="" goto :validate

    if /i "%~1"=="-h"         call :header & call :usage "%~2" & goto :end
    if /i "%~1"=="--help"     call :header & call :usage "%~2" & goto :end

    if /i "%~1"=="--memory"   set "MemoryOpt=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-m"  		  set "MemoryOpt=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--cpus"     set "CpuOpt=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-c"	      set "CpuOpt=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--config"   set "ConfigPath=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--scenario" set "ScenarioArg=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-s"         set "ScenarioArg=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--input"    set "InputOpt=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-i"         set "InputOpt=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--size" 	  set "SizeArg=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-sz"        set "SizeArg=%~2" & shift & shift & goto :parse

    if /i "%~1"=="--iters" 	  set "ItersArg=%~2" & shift & shift & goto :parse
    if /i "%~1"=="-n"         set "ItersArg=%~2" & shift & shift & goto :parse

    shift
    goto :parse

:prepare
	for /f "tokens=2" %%i in ('docker volume ls ^|findstr "competition-output"') do set output=%%i
	
	if defined output echo Volume already exists
	if not defined output (
		docker volume create competition-output > NUL
	)
	
	for /f "tokens=1" %%i in ('docker ps -a ^|findstr "beam-competition"') do set createdFlag=yes
	
	if defined createdFlag docker rm beam-competition > NUL

	goto :eof

:config
    if not defined ConfigPath call :missing_argument config & goto :end
    if not defined InputOpt   call :missing_argument input & goto :end
	
	call :prepare
	
	call :extractLeadingNumbers "%MemoryOpt%" xmx extension
	set /a xms=%xmx%/2
	set JJ=-Xmx%xmx%%extension% -Xms%xms%%extension%
	
	docker run -it --memory="%MemoryOpt%" --cpus="%CpuOpt%" --name=beam-competition -v "%InputOpt%":/submission-inputs:ro -v %cd%/output:/output:rw -e "JAVA_OPTS=%JJ%" beammodel/beam-competition:0.0.1-SNAPSHOT --config "%ConfigPath%"
	
	goto :end

:validate
    if not defined InputOpt call :missing_argument input & goto :end
    if defined ConfigPath goto :config

:scenario
    if not defined ScenarioArg  call :missing_argument scenario & goto :end
    if not defined SizeArg  call :missing_argument size & goto :end

	call :prepare

	call :extractLeadingNumbers "%MemoryOpt%" xmx extension
	set /a xms=%xmx%/2
	set JJ=-Xmx%xmx%%extension% -Xms%xms%%extension%

    if defined ItersArg (
    		docker run -it --memory="%MemoryOpt%" --cpus="%CpuOpt%" --name=beam-competition -v "%InputOpt%":/submission-inputs:ro -v %cd%/output:/output:rw -e " JAVA_OPTS=%JJ%" beammodel/beam-competition:0.0.1-SNAPSHOT --scenario "%ScenarioArg%" --sample-size "%SizeArg%" --iters "%ItersArg%"
    		goto :end
    	)

    docker run -it --memory="%MemoryOpt%" --cpus="%CpuOpt%" --name=beam-competition -v "%InputOpt%":/submission-inputs:ro -v %cd%/output:/output:rw -e  "JAVA_OPTS=%JJ%" beammodel/beam-competition:0.0.1-SNAPSHOT --scenario "%ScenarioArg%" --sample-size "%SizeArg%"

:end
    call :cleanup
    exit /B

:cleanup
    REM The cleanup function is only really necessary if you
    REM are _not_ using SETLOCAL.
    set "__NAME="
    
    set "__BAT_FILE="
    set "__BAT_PATH="
    set "__BAT_NAME="

    set "MemoryOpt="
    set "CpuOpt="
    set "InputOpt="
    set "ConfigPath="
    set "ScenarioArg="
    set "SizeArg="
    set "ItersArg="

    goto :eof