from datetime import date
from typing import Optional

from app.persistence.connection import get_connection


class PatientRepository:

    def create(
        self,
        patient_id: str,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        sex: str,
        blood_group: str,
    ) -> dict:

        query = """
            INSERT INTO patients (
                patient_id,
                first_name,
                last_name,
                date_of_birth,
                sex,
                blood_group
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                patient_id,
                first_name,
                last_name,
                date_of_birth,
                sex,
                blood_group,
                created_at,
                updated_at;
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        patient_id,
                        first_name,
                        last_name,
                        date_of_birth,
                        sex,
                        blood_group,
                    ),
                )

                row = cursor.fetchone()

        return {
            "patient_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "date_of_birth": row[3],
            "sex": row[4],
            "blood_group": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

    def get(
        self,
        patient_id: str,
    ) -> Optional[dict]:

        query = """
            SELECT
                patient_id,
                first_name,
                last_name,
                date_of_birth,
                sex,
                blood_group,
                created_at,
                updated_at
            FROM patients
            WHERE patient_id = %s;
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (patient_id,),
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return {
            "patient_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "date_of_birth": row[3],
            "sex": row[4],
            "blood_group": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

    def list_all(self) -> list[dict]:

        query = """
            SELECT
                patient_id,
                first_name,
                last_name,
                date_of_birth,
                sex,
                blood_group,
                created_at,
                updated_at
            FROM patients
            ORDER BY created_at DESC;
        """

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

        return [
            {
                "patient_id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "date_of_birth": row[3],
                "sex": row[4],
                "blood_group": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]