"""Temps estimé de la file des synthèses, lu par l'interface du module."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.services.summaries_queue import SummariesQueue


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def add_pending_jobs(session, survey_id, count):
    for _ in range(count):
        session.add(
            Summary(
                survey_id=survey_id,
                http_status=0,
                summary_text=None,
                metadata_text=None,
            )
        )
    session.commit()


def test_one_survey_of_45_pending_jobs_is_estimated_at_1h30(session):
    add_pending_jobs(session, survey_id=1, count=45)

    assert SummariesQueue(session).estimated_seconds() == 5400


def test_estimate_counts_the_pending_jobs_of_every_survey(session):
    # Un soir de campagne : 10 sondages de 45 synthèses, soit 450 en attente.
    for survey_id in range(1, 11):
        add_pending_jobs(session, survey_id=survey_id, count=45)

    assert SummariesQueue(session).estimated_seconds() == 54000
