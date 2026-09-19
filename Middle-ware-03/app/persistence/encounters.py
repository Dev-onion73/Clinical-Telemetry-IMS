from datetime import datetime
from typing import Any, Optional

from app.persistence.connection import get_connection


class EncounterRepository:

    def create(
        self,
        encounter_id: str,
        patient_id: str,
        encounter_type: str,
        care_setting: str,
        start_time: datetime,
        start_reason: str,
        started_by: str,
        start_details: Optional[str] = None,
    ) -> dict[str, Any]:

        query = """
            INSERT INTO encounters (
                encounter_id,
                patient_id,
                encounter_type,
                care_setting,
                status,
                start_time,
                start_reason,
                started_by,
                start_details
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                'OPEN',
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                encounter_id,
                patient_id,
                encounter_type,
                care_setting,
                status,
                start_time,
                end_time,
                start_reason,
                started_by,
                start_details,
                end_reason,
                ended_by,
                end_details,
                trace_id,
                span_id,
                created_at,
                updated_at
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        encounter_id,
                        patient_id,
                        encounter_type,
                        care_setting,
                        start_time,
                        start_reason,
                        started_by,
                        start_details,
                    ),
                )

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        "Encounter creation returned no row"
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(zip(columns, row))

    def get(
        self,
        encounter_id: str,
    ) -> Optional[dict[str, Any]]:

        query = """
            SELECT
                encounter_id,
                patient_id,
                encounter_type,
                care_setting,
                status,
                start_time,
                end_time,
                start_reason,
                started_by,
                start_details,
                end_reason,
                ended_by,
                end_details,
                trace_id,
                span_id,
                created_at,
                updated_at
            FROM encounters
            WHERE encounter_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (encounter_id,),
                )

                row = cursor.fetchone()

                if row is None:
                    return None

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(zip(columns, row))

    def update_trace_identity(
        self,
        encounter_id: str,
        trace_id: str,
        span_id: str,
    ) -> None:

        query = """
            UPDATE encounters
            SET
                trace_id = %s,
                span_id = %s
            WHERE encounter_id = %s
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        trace_id,
                        span_id,
                        encounter_id,
                    ),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Encounter not found: {encounter_id}"
                    )

    def close(
        self,
        encounter_id: str,
        end_time: datetime,
        end_reason: str,
        ended_by: str,
        end_details: Optional[str] = None,
    ) -> None:

        query = """
            UPDATE encounters
            SET
                status = 'CLOSED',
                end_time = %s,
                end_reason = %s,
                ended_by = %s,
                end_details = %s
            WHERE encounter_id = %s
              AND status <> 'CLOSED'
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        end_time,
                        end_reason,
                        ended_by,
                        end_details,
                        encounter_id,
                    ),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Active encounter not found: {encounter_id}"
                    )
    

    def delete(
    self,
    encounter_id: str,
    ) -> None:
    
        query = """
            DELETE FROM encounters
            WHERE encounter_id = %s
        """
    
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (encounter_id,),
                )