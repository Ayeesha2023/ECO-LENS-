from repositories.employee_dashboard_repository import (
    get_model_classes,
)


print("=" * 60)
print("ECO-LENS EMPLOYEE DASHBOARD TEST")
print("=" * 60)


try:

    model_classes = get_model_classes()

    print(
        "\nDatabase connection: SUCCESS"
    )

    print(
        "\nNumber of active waste classes:",
        len(model_classes),
    )

    print(
        "\nWaste classes:"
    )

    for model_class in model_classes:

        print(
            "-",
            model_class[
                "model_class_id"
            ],
            model_class[
                "display_name"
            ],
            "→",
            model_class[
                "category_name"
            ],
        )

    print(
        "\n"
        + "=" * 60
    )

    if len(model_classes) == 10:

        print(
            "PASS: All 10 EcoLens classes are available."
        )

    else:

        print(
            "WARNING: Expected 10 active model classes."
        )

    print("=" * 60)


except Exception as error:

    print(
        "\nTEST FAILED"
    )

    print(
        error
    )