import logging
from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError

from wxcloudrun import db

logger = logging.getLogger(__name__)


@contextmanager
def session_scope():
    try:
        yield db.session
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Database operation failed", exc_info=exc)
        raise


def save(entity):
    with session_scope() as session:
        session.add(entity)
        session.flush()
        return entity


def delete(entity):
    with session_scope() as session:
        session.delete(entity)


__all__ = ['session_scope', 'save', 'delete']
