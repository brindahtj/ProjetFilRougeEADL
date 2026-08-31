import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd):
    print(f"\n$ {' '.join(cmd)}  (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--service-dir",
        default="services/validation-service",
        help="Chemin vers le microservice a verifier",
    )
    parser.add_argument(
        "--min-coverage",
        type=int,
        default=60,
        help="Seuil minimal de couverture (%%), doit matcher la pipeline",
    )
    args = parser.parse_args()

    service_dir = Path(args.service_dir)
    if not service_dir.exists():
        print(f"[ERREUR] Dossier introuvable : {service_dir}")
        sys.exit(1)

    steps = [
        (["ruff", "check", "."], "Lint (Ruff)"),
        (
            [
                "pytest",
                "--cov=.",
                "--cov-report=term",
                "--cov-report=xml:coverage.xml",
                f"--cov-fail-under={args.min_coverage}",
            ],
            "Tests + couverture",
        ),
    ]

    failures = []
    for cmd, label in steps:
        code = run(cmd, cwd=service_dir)
        status = "OK" if code == 0 else "ECHEC"
        print(f"[{status}] {label}")
        if code != 0:
            failures.append(label)

    print("\n" + "=" * 50)
    if failures:
        print(f"RESULTAT : {len(failures)} etape(s) en echec -> {', '.join(failures)}")
        sys.exit(1)
    print("RESULTAT : toutes les etapes ont reussi (equivalent au job CI 'quality-and-tests')")


if __name__ == "__main__":
    main()
