install:
	pip install --upgrade pip
	pip install setuptools==65.5.0 pip==21
	pip install wheel==0.38.0
	pip install --user --upgrade setuptools
	pip install -r requirements.txt

run-local:
	python server.py

docker:
	docker build -t interactive-rl/server .

docker-run:
	docker run --rm -i -t \
	 -v $(PWD):/app \
	 -w /app \
	 -p 0.0.0.0:5000:5000 \
	 interactive-rl/server