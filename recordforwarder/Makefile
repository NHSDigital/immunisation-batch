build:
	docker build -t forwarder-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build forwarder-lambda-build
test:
	python -m unittest

coverage run:
	coverage run -m unittest discover

coverage report:
	coverage report -m 

coverage html:
	coverage html  	

.PHONY: build package