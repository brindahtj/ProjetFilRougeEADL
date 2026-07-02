[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "validation-service"
version = "1.0.0"
description = "Smart City Validation Service for pollution and traffic measurements"
authors = [
    {name = "Smart City Team", email = "team@smartcity.local"}
]
requires-python = ">=3.11"

dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "pydantic==2.5.0",
    "pika==1.3.2",
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "pytest-asyncio==0.21.1",
    "pytest-cov==4.1.0",
    "httpx==0.25.2",
    "ruff==0.1.8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=app --cov-report=html --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"