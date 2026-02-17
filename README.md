# basic-ere
A basic implementation of the Entity Resolution Engine (ERE).

## Requirements
TODO. For testing, you need: Python, Poetry, Docker (used by pytest + testcontainers).


## TODO
* Migrate entity-resolution-spec to Poetry (and ers?)
* Complete this hereby README
* CLI wrapper to start the Redis service
* Dockerisation
* github action for test, build, PyPI publish. * Also, add code cleaning:
	```shell
	poetry run isort --indent "\t" src test
	poetry run autoflake --remove-all-unused-imports --recursive --in-place src test
	```
  * **plus code style tools**

## TODO: Resolver implementation

See the dedicated shape and [here](docs/resolution-tools.md).
