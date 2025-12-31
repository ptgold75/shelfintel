import os
import sys

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_session
from core.models import Dispensary

def main():
    db = get_session()

    disp = Dispensary(
        name="Test Dispensary",
        state="MD",
        menu_url="https://example.com",  # CHANGE THIS LATER
        menu_provider="unknown",
    )

    db.add(disp)
    db.commit()

    print("✅ Added dispensary_id:", disp.dispensary_id)

if __name__ == "__main__":
    main()
