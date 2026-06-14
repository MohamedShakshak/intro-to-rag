run:
	uv run --directory .. -m Module-5-Monotoring.assistant

chat:
	uv run streamlit run --directory .. -m Module-5-Monotoring.app

network:
	docker network create monitoring

postgres: network
	docker run -it \
		--name course-assistant-pg \
		--network monitoring \
		-e POSTGRES_USER=user \
		-e POSTGRES_PASSWORD=password \
		-e POSTGRES_DB=course_assistant \
		-p 5432:5432 \
		-v pgdata:/var/lib/postgresql/data \
		postgres:17