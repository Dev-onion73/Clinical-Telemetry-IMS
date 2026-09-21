from datetime import datetime
from typing import Any, Optional

from app.persistence.connection import get_connection


class EpisodeRepository:

    def create(
        self,
        episode_id: str,
        patient_id: str,
        encounter_id: str,
        initiated_by: str,
        initiation_reason: str,
        start_time: datetime,
        source_journal_id: str,
    ) -> dict[str, Any]:

        query = """
            INSERT INTO episodes (
                episode_id,
                patient_id,
                encounter_id,
                initiated_by,
                initiation_reason,
                start_time,
                source_journal_id
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                episode_id,
                patient_id,
                encounter_id,
                trace_id,
                initiated_by,
                status,
                start_time,
                end_time,
                closure_by,
                closure_time,
                source_journal_id,
                initiation_reason,
                created_at,
                updated_at
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        episode_id,
                        patient_id,
                        encounter_id,
                        initiated_by,
                        initiation_reason,
                        start_time,
                        source_journal_id,
                    ),
                )

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        "Episode creation returned no row"
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(
                    zip(columns, row)
                )

    def get(
        self,
        episode_id: str,
    ) -> Optional[dict[str, Any]]:

        query = """
            SELECT
                episode_id,
                patient_id,
                encounter_id,
                trace_id,
                initiated_by,
                status,
                start_time,
                end_time,
                closure_by,
                closure_time,
                source_journal_id,
                initiation_reason,
                created_at,
                updated_at
            FROM episodes
            WHERE episode_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (episode_id,),
                )

                row = cursor.fetchone()

                if row is None:
                    return None

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(
                    zip(columns, row)
                )

    def update_trace_identity(
        self,
        episode_id: str,
        trace_id: str,
    ) -> None:

        query = """
            UPDATE episodes
            SET trace_id = %s
            WHERE episode_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        trace_id,
                        episode_id,
                    ),
                )

    def close(
        self,
        episode_id: str,
        end_time: datetime,
        closure_by: str,
    ) -> None:

        query = """
            UPDATE episodes
            SET
                status = 'CLOSED',
                end_time = %s,
                closure_by = %s,
                closure_time = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE episode_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        end_time,
                        closure_by,
                        end_time,
                        episode_id,
                    ),
                )

    def delete(
        self,
        episode_id: str,
    ) -> None:

        query = """
            DELETE FROM episodes
            WHERE episode_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (episode_id,),
                )