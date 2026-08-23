from db import fetch_all, fetch_one


def main() -> None:
    database = fetch_one("SELECT DATABASE() AS database_name")

    print("Connected database:", database["database_name"])

    rules = fetch_all(
        """
        SELECT
            rule_code,
            title,
            priority
        FROM authority_advice_rules
        WHERE is_active = 1
        ORDER BY advice_rule_id
        """
    )

    print("\nAuthority advice rules:")

    for rule in rules:
        print(
            f"- {rule['rule_code']} | "
            f"{rule['title']} | "
            f"{rule['priority']}"
        )

    verified_count = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM v_verified_authority_rag_knowledge
        """
    )

    print(
        "\nVerified authority knowledge:",
        verified_count["total"],
    )


if __name__ == "__main__":
    main()