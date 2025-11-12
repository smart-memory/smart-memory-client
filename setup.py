"""Setup script for smartmemory-client package."""

from setuptools import setup, find_packages

setup(
    name="smartmemory-client",
    version="1.0.0",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    include_package_data=True,
    python_requires=">=3.11",
)
