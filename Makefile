.PHONY: default
default: tests

getdeps:
	@echo "Installing required dependencies"
	@pip install --user --upgrade autopep8 pytest pylint urllib3 typing-extensions mypy

check: getdeps
	@echo "Running checks"
	@pylint --reports=no --score=no --disable=R0401,R0801 newtera/*py
	@pylint --reports=no --score=no newtera/credentials tests/functional
	@isort --diff .
	@mypy newtera

apply: getdeps
	@isort .
	@find . -name "*.py" -exec autopep8 --in-place {} +

tests: check
	@echo "Running unit tests"
	@pytest
	@echo "Running functional tests"
	@env bash run_functional_tests.sh
