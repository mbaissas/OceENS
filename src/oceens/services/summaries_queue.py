"""Lecture de la file des synthèses : avancement par sondage et temps estimé.

La table `summaries` sert de file d'attente au daemon, et `http_status` y porte
l'état de chaque ligne. Ce module est le seul endroit qui sait le lire :

- `0` : en attente ;
- `200` : générée ;
- toute autre valeur, NULL compris : en échec.

Le temps estimé est un pire cas. Le daemon traite une ligne à la fois, tous
sondages confondus : il compte donc toutes les lignes en attente de la file, pas
seulement celles du sondage affiché, à raison du plafond de durée d'un appel. Il
ne lit pas l'horloge : les mêmes lignes donnent la même estimation.

La session vient de l'appelant, et la file est lue une fois, à la construction :
une erreur de base remonte à ce moment-là, sans être remplacée par des zéros.
"""

from dataclasses import dataclass

from sqlmodel import func, select

from oceens.models import Summary

# Plafond de durée d'une synthèse, retenu comme durée par ligne en attente
# (Design Document EPF-MDE/OceENS#120, Spec #171).
SECONDS_PER_PENDING_JOB = 120

STATUS_PENDING = 0
STATUS_DONE = 200


@dataclass(frozen=True)
class SurveySummaries:
    """Avancement des synthèses d'un sondage, et temps estimé de la file."""

    done: int = 0
    pending: int = 0
    failed: int = 0
    estimated_seconds: int = 0

    @property
    def total(self):
        return self.done + self.pending + self.failed

    @property
    def finished(self):
        """Vrai quand le sondage a des synthèses et qu'aucune n'est en attente."""
        return self.total > 0 and self.pending == 0


class SummariesQueue:
    def __init__(self, session):
        rows = session.exec(
            select(Summary.survey_id, Summary.http_status, func.count()).group_by(
                Summary.survey_id, Summary.http_status
            )
        ).all()

        self._counts = {}
        for survey_id, status, count in rows:
            counts = self._counts.setdefault(
                survey_id, {"done": 0, "pending": 0, "failed": 0}
            )
            if status == STATUS_PENDING:
                counts["pending"] += count
            elif status == STATUS_DONE:
                counts["done"] += count
            else:
                counts["failed"] += count

    def estimated_seconds(self):
        """Temps estimé avant que la file soit vide, en secondes."""
        pending = sum(counts["pending"] for counts in self._counts.values())
        return pending * SECONDS_PER_PENDING_JOB

    def of_survey(self, survey_id):
        """Avancement d'un sondage ; des zéros s'il n'a aucune synthèse."""
        counts = self._counts.get(survey_id, {})
        return SurveySummaries(estimated_seconds=self.estimated_seconds(), **counts)
