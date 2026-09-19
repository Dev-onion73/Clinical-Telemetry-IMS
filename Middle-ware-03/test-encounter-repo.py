from datetime import datetime, timezone

from app.persistence.encounters import EncounterRepository


def main():

    repository = EncounterRepository()

    encounter_id = "E-REPO-001"

    print("\n=== CREATE ENCOUNTER ===")

    encounter = repository.create(
        encounter_id=encounter_id,
        patient_id="PAT-0001",
        encounter_type="EMERGENCY",
        care_setting="EMERGENCY",
        start_time=datetime.now(timezone.utc),
        start_reason="Repository integration test",
        started_by="ADMIN-001",
        start_details="Testing PostgreSQL persistence",
    )

    print(encounter)

    print("\n=== GET ENCOUNTER ===")

    result = repository.get(
        encounter_id
    )

    if result is None:
        raise RuntimeError(
            "Encounter was not found"
        )

    print(result)

    print("\n=== VERIFY ===")

    assert result["encounter_id"] == encounter_id
    assert result["patient_id"] == "PAT-0001"
    assert result["status"] == "OPEN"
    assert result["start_reason"] == (
        "Repository integration test"
    )
    assert result["started_by"] == "ADMIN-001"

    print("Repository persistence: PASS")

    print("\n=== CLEANUP ===")

    # Remove test record directly.
    # This is test-only cleanup.
    import psycopg
    from app.persistence.connection import get_connection

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM encounters
                WHERE encounter_id = %s
                """,
                (encounter_id,),
            )

    print("Cleanup: PASS")


if __name__ == "__main__":
    main()