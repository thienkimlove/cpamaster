## Init setup

* Create `virtualenv` environment for this project and run `pip install -r requirements.txt`

* Create `PostgreSQL` database and run `cp .env.sample .env` and modify `.env` file with correct SQL information.

* Run `python manage.py migrate && python manage.py createsuperuser`

* Run `python manage.py runserver 0.0.0.0:9162` for testing.

* Browser `http://localhost:9162`.

