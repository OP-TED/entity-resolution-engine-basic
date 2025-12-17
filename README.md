# basic-ere
A basic implementation of the Entity Resolution Engine (ERE).

## TODO
* Migrate `pytest-redis` to Test Containers.
* Move utilities in modules like redis.py to a utils module.
* github action for test, build, PyPI publish. Also, add code cleaning:
	```
	poetry run isort --indent "\t" src test
	poetry run autoflake --remove-all-unused-imports --recursive --in-place src test
	```
