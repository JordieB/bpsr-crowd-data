from __future__ import annotations

import argparse
from pathlib import Path


def validate_key_format(key: str) -> bool:
    """Validate API key format (non-empty, reasonable length)."""
    if not key or len(key) < 8:
        return False
    if len(key) > 256:
        return False
    return True


def update_env_file(key: str, env_path: Path = Path(".env")) -> None:
    """Update or create .env file with DEFAULT_API_KEY.
    
    Reads existing .env if present, updates/inserts DEFAULT_API_KEY entry,
    and preserves all other environment variables.
    """
    env_vars: dict[str, str] = {}
    
    # Read existing .env file if it exists
    if env_path.exists():
        with env_path.open("r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE format
                if "=" in line:
                    key_part, value_part = line.split("=", 1)
                    # Remove quotes if present
                    value_part = value_part.strip().strip('"').strip("'")
                    env_vars[key_part.strip()] = value_part
    
    # Update DEFAULT_API_KEY
    env_vars["DEFAULT_API_KEY"] = key
    
    # Write back to .env file
    with env_path.open("w") as f:
        for env_key, env_value in sorted(env_vars.items()):
            # Escape special characters and wrap in quotes if needed
            if any(char in env_value for char in [" ", "#", "=", "$"]):
                f.write(f'{env_key}="{env_value}"\n')
            else:
                f.write(f"{env_key}={env_value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Utility commands for BPSR crowd data")
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser("seed-key", help="Validate and print instructions for API key")
    seed.add_argument("key", help="API key value to validate")

    args = parser.parse_args()

    if args.command == "seed-key":
        if not validate_key_format(args.key):
            print("ERROR: API key must be at least 8 characters and no more than 256 characters")
            exit(1)
        
        # Update .env file
        env_path = Path(".env")
        update_env_file(args.key, env_path)
        
        key_preview = f"{args.key[:8]}...{args.key[-4:]}" if len(args.key) > 12 else args.key
        print(f"SUCCESS: API key updated in {env_path.absolute()}")
        print(f"  Key preview: {key_preview}")
        print("\nThe key is now available via DEFAULT_API_KEY environment variable.")
        print("Restart your FastAPI server or reload to pick up the change.")


if __name__ == "__main__":
    main()
