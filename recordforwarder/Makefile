build:
	docker build -t forwarder-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build forwarder-lambda-build
test:
	python -m unittest

.PHONY: build package