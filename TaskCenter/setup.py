"""
TaskCenter package setup configuration.
"""
from setuptools import setup, find_namespace_packages

setup(
    name="agent-os-task-center",
    version="1.0.0",
    description="Task state machine core for Agent OS",
    author="Agent OS Team",
    packages=find_namespace_packages(include=['agent_os.*']),
    install_requires=[
        "asyncpg>=0.29.0",
        "agent-os-common>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
        ]
    },
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)