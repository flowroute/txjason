all: bootstrap buildout

bootstrap:
	if [ ! -d ve ]; then virtualenv ve; fi
	if [ ! -f bin/python ]; then ve/bin/python bootstrap.py; fi

buildout:
	bin/buildout -N

clean:
	rm -rf *.egg-info bin develop-eggs eggs parts downloads .installed.cfg build

tests: unittests

unittests:
	rm txjason/tests/*.pyc; :
	bin/trial txjason.tests
