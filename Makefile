SHELL := /bin/bash
PYTHONPATH := src

SYMLINKED_MODULES := cat app-modules.txt | grep -v '^ *\#'

.PHONY: bootstrap clean test test-fast deploy module-dependencies

bootstrap: clean
	virtualenv --no-site-packages --distribute -p python2.7 .
	bin/easy_install pip
	bin/pip install -r requirements.txt
	$(SYMLINKED_MODULES) | xargs -I % bash -c "cd src && ln -s ../lib/python2.7/site-packages/% ."

clean:
	rm -rf bin include lib man
	$(SYMLINKED_MODULES) | xargs -I % bash -c "cd src && rm -f %"

test:
	@cd src && find test -name "*.py" | xargs nosetests --with-gae --without-sandbox
test-fast:
	@cd src && find test -name "*.py" | xargs nosetests --with-gae --without-sandbox -a '!slow'

deploy:
	@cd src && appcfg.py update .
