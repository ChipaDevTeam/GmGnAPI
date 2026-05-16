import inspect

import src.gmgnapi as gmgnapi


def print_classes_and_functions() -> None:
    classes = []
    functions = []

    for name in sorted(dir(gmgnapi)):
        if name.startswith("_"):
            continue

        obj = getattr(gmgnapi, name)
        if inspect.isclass(obj):
            classes.append(name)
        elif inspect.isfunction(obj):
            functions.append(name)

    print("Classes:")
    if classes:
        for name in classes:
            print(f"- {name}")
    else:
        print("- None")

    print("\nFunctions:")
    if functions:
        for name in functions:
            print(f"- {name}")
    else:
        print("- None")


if __name__ == "__main__":
    print_classes_and_functions()