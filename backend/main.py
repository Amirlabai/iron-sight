import sys
import os
import asyncio

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.main import main as run_engine

if __name__ == "__main__":
    try:
        asyncio.run(run_engine())
    except KeyboardInterrupt:
        pass
