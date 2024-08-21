build:
	docker build -t processor-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build processor-lambda-build

.PHONY: build package