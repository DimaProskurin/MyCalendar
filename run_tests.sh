#! /bin/sh

docker compose run api poetry run python manage.py test
# clear after yourself
docker compose down
