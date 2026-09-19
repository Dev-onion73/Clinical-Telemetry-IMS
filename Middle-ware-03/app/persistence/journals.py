from datetime import datetime
from typing import Any, Optional

from app.persistence.connection import get_connection


class JournalRepository:

    def create(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        timestamp: datetime,
        content: str,
        entry_type: str = "EVENT",
        episode_id: Optional[str] = None,
    ) -> dict[str, Any]:

        query = """
            INSERT INTO journals (
                journal_id,
                patient_id,
                encounter_id,
                author_id,
                author_role,
                timestamp,
                content,
                entry_type,
                episode_id
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::journal_entry_type,
                %s
            )
            RETURNING
                journal_id,
                patient_id,
                encounter_id,
                author_id,
                author_role,
                timestamp,
                content,
                created_at,
                updated_at,
                entry_type,
                episode_id
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        journal_id,
                        patient_id,
                        encounter_id,
                        author_id,
                        author_role,
                        timestamp,
                        content,
                        entry_type,
                        episode_id,
                    ),
                )

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        "Journal creation returned no row"
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(zip(columns, row))

    def get(
        self,
        journal_id: str,
    ) -> Optional[dict[str, Any]]:

        query = """
            SELECT
                journal_id,
                patient_id,
                encounter_id,
                author_id,
                author_role,
                timestamp,
                content,
                created_at,
                updated_at,
                entry_type,
                episode_id
            FROM journals
            WHERE journal_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (journal_id,),
                )

                row = cursor.fetchone()

                if row is None:
                    return None

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(zip(columns, row))

    def update_episode_identity(
        self,
        journal_id: str,
        episode_id: str,
    ) -> None:

        query = """
            UPDATE journals
            SET
                entry_type = 'EPISODE_START',
                episode_id = %s
            WHERE journal_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        episode_id,
                        journal_id,
                    ),
                )

    def delete(
        self,
        journal_id: str,
    ) -> None:

        query = """
            DELETE FROM journals
            WHERE journal_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (journal_id,),
                )