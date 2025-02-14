import sys
import os
from cx_Freeze import setup, Executable

sys.setrecursionlimit(5000)

# TARGET
target = Executable(
    script="main.py",
    base="Win32GUI",
    # base="Console",
    icon="icon.ico"
)

build_exe_options = {
    "packages": ["torch"],
    "excludes": [],
    "include_files": ['icon.ico', 'themes/', 'config/'],
}

# SETUP CX FREEZE
setup(
    name="AI视觉检测系统",
    version="1.0",
    description="AI视觉检测系统",
    author="",
    options={"build_exe": build_exe_options},
    executables=[target]
)
