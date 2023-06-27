freeze:
	pip freeze > requirements.txt

run:
	python main.py

.PHONY: freeze run
