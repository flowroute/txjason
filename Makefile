all: bootstrap buildout

bootstrap:
	virtualenv ve
	ve/bin/python bootstrap.py

buildout:
	bin/buildout -N

clean:
	rm -rf *.egg-info bin develop-eggs eggs parts downloads .installed.cfg build

tests: unittests

unittests:
	rm txjason/tests/*.pyc; :
	bin/trial txjason.tests
