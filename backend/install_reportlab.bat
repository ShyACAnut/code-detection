@echo off
chcp 65001 >nul
echo ===========================================
echo 自动安装 reportlab 库
echo ===========================================
echo.

set PYTHON_FOUND=0
set PYTHON_CMD=

echo [1/4] 尝试查找可用的Python...
echo.

:: 尝试常见的Python命令
for %%p in (python3 python py) do (
    where %%p >nul 2>&1
    if errorlevel 0 (
        echo 找到: %%p
        %%p -c "import sys; print('Python路径:', sys.executable); print('Python版本:', sys.version)" 2>nul
        if not errorlevel 1 (
            set PYTHON_CMD=%%p
            set PYTHON_FOUND=1
            goto :INSTALL
        )
    )
)

:: 如果上面都找不到，尝试常见的安装路径
if %PYTHON_FOUND%==0 (
    echo.
    echo 尝试从常见路径查找...
    for %%p in (
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
        "C:\Python39\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) do (
        if exist %%p (
            echo 找到: %%~p
            %%p -c "import sys; print('Python路径:', sys.executable); print('Python版本:', sys.version)" 2>nul
            if not errorlevel 1 (
                set PYTHON_CMD=%%p
                set PYTHON_FOUND=1
                goto :INSTALL
            )
        )
    )
)

:INSTALL
if %PYTHON_FOUND%==1 (
    echo.
    echo ===========================================
    echo [2/4] 使用Python: %PYTHON_CMD%
    echo ===========================================
    echo.

    echo [3/4] 检查 reportlab 是否已安装...
    %PYTHON_CMD% -c "import reportlab; print('✓ reportlab已安装，版本:', reportlab.Version)" 2>nul
    if not errorlevel 1 (
        echo.
        echo ✓ reportlab 已经安装！
        echo.
        goto :TEST
    )

    echo.
    echo reportlab 未安装，正在安装...
    echo.
    echo [4/4] 执行: %PYTHON_CMD% -m pip install reportlab
    echo.

    %PYTHON_CMD% -m pip install reportlab

    if errorlevel 1 (
        echo.
        echo ✗ 安装失败，尝试使用 --user 选项...
        %PYTHON_CMD% -m pip install reportlab --user
    )

    echo.
    echo ===========================================
    echo 验证安装...
    echo ===========================================
    echo.

    %PYTHON_CMD% -c "import reportlab; print('✓ reportlab安装成功！版本:', reportlab.Version)" 2>nul
    if not errorlevel 1 (
        echo.
        goto :TEST
    ) else (
        echo.
        echo ✗ 安装验证失败
        echo.
        goto :END
    )
) else (
    echo.
    echo ✗ 未找到Python！
    echo.
    echo 请手动安装Python，或者:
    echo 1. 找到你启动后端服务的Python路径
    echo 2. 在该Python环境下执行: pip install reportlab
    echo.
    goto :END
)

:TEST
echo.
echo ===========================================
echo 运行PDF功能测试...
echo ===========================================
echo.

%PYTHON_CMD% test_pdf_generation.py

:END
echo.
echo ===========================================
echo 完成！
echo ===========================================
echo.
echo 如果成功，请重启你的后端服务
echo.
pause
