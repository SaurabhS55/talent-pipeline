import json

from pipeline.run_pipeline import run_pipeline


def main() -> None:
    result = run_pipeline()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
