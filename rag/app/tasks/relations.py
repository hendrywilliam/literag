from app.core.celery_app import celery_app
from app.services.neo4j_store import get_neo4j_vector_store
from app.services.relation_agent import get_relation_agent


@celery_app.task(bind=True, name="relations.build_document_relations")
def build_document_relations(self, document_id: str) -> dict:
    store = get_neo4j_vector_store()
    store.set_document_status(document_id, "building")

    try:
        summary = get_relation_agent().build_document_relations(document_id)
    except Exception as exc:
        store.set_document_status(document_id, "failed")
        raise exc

    store.set_document_status(document_id, "done")
    return summary
