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
    ) -> dict[str, Any]:

        query = """
            INSERT INTO journals (
                journal_id,
                patient_id,
                encounter_id,
                author_id,
                author_role,
                timestamp,
                content
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
                journal_id,
                patient_id,
                encounter_id,
                author_id,
                author_role,
                timestamp,
                content,
                created_at,
                updated_at
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

                return dict(
                    zip(columns, row)
                )

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
                updated_at
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

                return dict(
                    zip(columns, row)
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