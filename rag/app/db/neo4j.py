from neo4j import Driver, GraphDatabase

from app.core.config import get_settings

_driver: Driver | None = None


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        try:
            _driver.verify_connectivity()
        except Exception:
            _driver.close()
            _driver = None
            raise
    return _driver


def check_neo4j_connectivity() -> None:
    settings = get_settings()
    try:
        driver = get_neo4j_driver()
        driver.execute_query("RETURN 1", database_=settings.neo4j_database)
    except Exception as exc:
        raise ConnectionError(
            f"Cannot connect to Neo4j at {settings.neo4j_uri} "
            f"(database: {settings.neo4j_database}): {exc}"
        ) from exc


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
