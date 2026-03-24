"""Setup configuration for coding_task_document_parser package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="coding_task_document_parser",
    version="1.0.0",
    author="Agent OS Team",
    author_email="team@agent-os.dev",
    description="Pure Python parsing library for Coding Task Documents (zero external dependencies)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agent-os/coding-task-document-parser",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        # Zero external dependencies - stdlib only
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="parsing document markdown json architect engineer coding-task",
    project_urls={
        "Documentation": "https://github.com/agent-os/coding-task-document-parser/blob/main/README.md",
        "Source": "https://github.com/agent-os/coding-task-document-parser",
        "Bug Reports": "https://github.com/agent-os/coding-task-document-parser/issues",
    },
)