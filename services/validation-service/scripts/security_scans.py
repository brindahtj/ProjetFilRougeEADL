import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd, label):
    print(f"\n--- {label} ---")
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode not in (0, 1):  # 1 = vulns trouvees, pas un crash outil
        print(f"[ATTENTION] '{label}' a retourne un code inattendu : {result.returncode}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-dir", default="services/validation-service")
    parser.add_argument("--out", default="reports")
    args = parser.parse_args()

    service_dir = Path(args.service_dir).resolve()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not service_dir.exists():
        print(f"[ERREUR] Dossier introuvable : {service_dir}")
        sys.exit(1)

    # 1. Bandit (SAST) - on exclut explicitement les dependances vendorisees
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{service_dir}:/apps",
            "ghcr.io/pycqa/bandit/bandit:latest",
            "-r",
            "/apps",
            "-x",
            "*/.venv/*,*/site-packages/*",
            "-f",
            "json",
            "-o",
            f"/apps/{out_dir.name}/bandit-report.json",
        ],
        "Bandit (SAST)",
    )

    # 2. Gitleaks (secrets) - mode 'dir', pas 'detect' (qui ne scanne que l'historique git)
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{service_dir}:/apps",
            "zricethezav/gitleaks",
            "dir",
            "/apps",
            "--report-path",
            f"/apps/{out_dir.name}/gitleaks-report.json",
        ],
        "Gitleaks (secrets)",
    )

    # 3. Trivy FS (dependances / SCA)
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{service_dir}:/src",
            "aquasec/trivy",
            "fs",
            "--scanners",
            "vuln",
            "--skip-dirs",
            "**/.venv",
            "--skip-dirs",
            "**/__pycache__",
            "--format",
            "cyclonedx",
            "--output",
            f"/src/{out_dir.name}/trivy-fs-report.json",
            "/src",
        ],
        "Trivy FS (SCA)",
    )

    print(f"\nRapports generes dans : {out_dir}/")
    print("Utilise ces fichiers pour completer 04_analyse_qualite_securite.md")


if __name__ == "__main__":
    main()
