import sqlalchemy.engine as engine


def get_db_url(username: str, password: str) -> engine.URL:
    return engine.URL.create(
        "mysql",
        username=username,
        password=password,
        host="95.217.222.91",
        database="elfys",
        port=3306,
    )
