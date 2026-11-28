from pathlib import Path
import subprocess
import sys

BASE_DIRECTORY = Path(__file__).parent

FETCHER = BASE_DIRECTORY / "cx_request_test.py"
DECODER = BASE_DIRECTORY / "cx_decoder.py"


def run_script(script):

    print(f"\nRunning {script.name}...")
    print("=" * 40)

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=BASE_DIRECTORY
    )

    if result.returncode != 0:
        raise RuntimeError(f"{script.name} failed.")

    print(f"\n{script.name} completed successfully!")


def main():

    print("Stray Legends - CX Automated Updater")
    print("====================================")

    # Step 1: Download latest CX data
    run_script(FETCHER)

    # Step 2: Decode and update JSON
    run_script(DECODER)

    print("\nCX UPDATE COMPLETE!")
    print("Latest leaderboard data has been saved.")


if __name__ == "__main__":
    main()