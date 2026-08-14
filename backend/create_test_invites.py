import secrets

from repositories.auth_repository import (
    create_registration_invite,
)


def main():

    employee_number = (
        secrets.randbelow(
            900000
        )
        + 100000
    )

    employee_code = (
        f"ECO-EMP-{employee_number}"
    )


    # ========================================================
    # EMPLOYEE INVITE
    # ========================================================

    employee_invite = (
        create_registration_invite(
            invite_role="employee",

            # Existing approved demo authority.
            authority_id=1,

            employee_code=(
                employee_code
            ),

            job_title=(
                "Cleaning Employee"
            ),

            valid_days=30,
        )
    )


    # ========================================================
    # COMMUNITY AUTHORITY INVITE
    #
    # No ward is forced here.
    # Authority selects coverage during signup.
    # The account stays pending afterwards.
    # ========================================================

    authority_invite = (
        create_registration_invite(
            invite_role=(
                "community_authority"
            ),

            assigned_region_id=None,

            valid_days=30,
        )
    )


    print()
    print(
        "EMPLOYEE INVITATION"
    )

    print(
        "Employee code:",
        employee_code,
    )

    print(
        "Signup code:",
        employee_invite,
    )


    print()
    print(
        "AUTHORITY INVITATION"
    )

    print(
        "Signup code:",
        authority_invite,
    )


    print()
    print(
        "Save these codes only "
        "for local testing."
    )


if __name__ == "__main__":
    main()