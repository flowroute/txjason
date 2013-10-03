all: buildout

# Creates the Python virtual environment.
ve:
	virtualenv --distribute ve

# Bootstraps buildout.
bin/buildout: ve
	ve/bin/python bootstrap.py --version 2.1.1

# Runs buildout to fetch and install dependencies into the environment.
buildout: bin/buildout
	bin/buildout -N

# Cleans the build environment.
clean:
	rm -rf *.egg-info bin develop-eggs eggs parts downloads .installed.cfg build ve

# Runs all tests.
tests: unittests

# Runs unit tests.
unittests:
	rm txjason/tests/*.pyc; :
	bin/trial txjason.tests

# Updates dependencies where applicable.
update-deps:
	bin/buildout
