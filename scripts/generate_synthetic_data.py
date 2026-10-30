import argparse
from pathlib import Path

from trading.data.synthetic import generate_synthetic_ohlcv


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate explicitly synthetic OHLCV data.")
    parser.add_argument("--symbol", default="RELIANCE.NS")
    parser.add_argument("--periods", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--frequency", default="1h")
    parser.add_argument("--output", type=Path, default=Path("data/raw/synthetic_ohlcv.csv"))
    arguments = parser.parse_args()

    data = generate_synthetic_ohlcv(
        symbol=arguments.symbol,
        periods=arguments.periods,
        seed=arguments.seed,
        frequency=arguments.frequency,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(arguments.output, index=False)
    print(f"Wrote {len(data)} explicitly synthetic rows to {arguments.output}")


if __name__ == "__main__":
    main()
