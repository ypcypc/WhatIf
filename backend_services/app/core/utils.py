"""
Core utility functions for the WhatIf backend services.

This module provides common utility functions used across different services.
"""

from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    Get the project root directory by looking for pyproject.toml.
    
    This function traverses up the directory tree from the current file
    until it finds a directory containing pyproject.toml, which indicates
    the project root.
    
    Returns:
        Path: The project root directory
        
    Raises:
        FileNotFoundError: If project root cannot be found
    """
    current_file = Path(__file__).resolve()
    
    # 向上遍历目录，寻找项目根目录标识文件
    for parent in current_file.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    
    raise FileNotFoundError("Could not find project root directory (looking for pyproject.toml)")


def get_data_file_path(filename: str) -> Path:
    """
    Get the full path to a data file in the project's data directory.
    
    Args:
        filename: Name of the data file (e.g., "article_data.json")
        
    Returns:
        Path: Full path to the data file
        
    Raises:
        FileNotFoundError: If project root or data directory cannot be found
    """
    project_root = get_project_root()
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    data_file = data_dir / filename
    
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    return data_file


def ensure_data_file_exists(filename: str) -> Path:
    """
    Ensure a data file exists and return its path.
    
    This is similar to get_data_file_path but provides more detailed
    error messages for debugging.
    
    Args:
        filename: Name of the data file
        
    Returns:
        Path: Full path to the data file
        
    Raises:
        FileNotFoundError: With detailed error message
    """
    try:
        project_root = get_project_root()
    except FileNotFoundError:
        raise FileNotFoundError(
            "Could not find project root directory. "
            "Make sure you're running from within the project directory."
        )
    
    data_dir = project_root / "data"
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory not found at {data_dir}. "
            f"Expected structure: {project_root}/data/{filename}"
        )
    
    data_file = data_dir / filename
    if not data_file.exists():
        available_files = list(data_dir.glob("*.json"))
        available_names = [f.name for f in available_files]
        raise FileNotFoundError(
            f"Data file '{filename}' not found in {data_dir}. "
            f"Available files: {available_names}"
        )
    
    return data_file
