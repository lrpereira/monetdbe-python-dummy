
.PHONY: wheels tests docker

GITHUB_WORKSPACE=/build
DOCKER_IMAGE=gijzelaerr/monetdb


all: docker

venv/:
	python3 -m venv venv

setup: venv/
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -e ".[test]"


test: setup
	venv/bin/pytest 


docker-build:
	#docker build -t $(DOCKER_IMAGE):wheel -f docker/wheel.docker .
	docker build -t $(DOCKER_IMAGE):test38 -f docker/test38.docker .

docker-force-build:
	docker build --no-cache -t $(DOCKER_IMAGE):wheel -f docker/wheel.docker .
	docker build --no-cache -t $(DOCKER_IMAGE):test38 -f docker/test38.docker .


wheels: docker
	docker run -v `pwd`:$(GITHUB_WORKSPACE) $(DOCKER_IMAGE):wheel sh -c "cd $(GITHUB_WORKSPACE); .inside/make_wheel.sh 3.6"
	docker run -v `pwd`:$(GITHUB_WORKSPACE) $(DOCKER_IMAGE):wheel sh -c "cd $(GITHUB_WORKSPACE); .inside/make_wheel.sh 3.7"
	docker run -v `pwd`:$(GITHUB_WORKSPACE) $(DOCKER_IMAGE):wheel sh -c "cd $(GITHUB_WORKSPACE); .inside/make_wheel.sh 3.8"
	
shell:
	docker run -ti -v `pwd`:$(GITHUB_WORKSPACE) $(DOCKER_IMAGE) sh -c "cd $(GITHUB_WORKSPACE); bash"

docker-tests: docker-build
	docker run -v `pwd`:$(GITHUB_WORKSPACE) $(DOCKER_IMAGE):test38 sh -c "cd $(GITHUB_WORKSPACE); .inside/test.sh"

push: docker
	docker push $(DOCKER_IMAGE):wheel
	docker push $(DOCKER_IMAGE):test

clean:
	python3 setup.py clean
	rm -rf build dist *.egg-info .eggs monetdbe/*.so monetdbe/*.dylib

venv/bin/mypy: venv/
	venv/bin/pip install mypy

venv/bin/pycodestyle: venv/
	venv/bin/pip install pycodestyle

mypy: venv/bin/mypy
	venv/bin/mypy monetdbe tests

pycodestyle: venv/bin/pycodestyle
	venv/bin/pycodestyle monetdbe tests