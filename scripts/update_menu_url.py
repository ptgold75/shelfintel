import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_session
from core.models import Dispensary

NEW_URL = "https://www.gleaf.com/stores/maryland/rockville/shop"

def main():
    db = get_session()
    disp = db.query(Dispensary).first()
    disp.name = "gLeaf Rockville"
    disp.menu_url = NEW_URL
    disp.menu_provider = "gleaf"
    db.commit()
    print("✅ Updated:", disp.name)
    print("✅ menu_url:", disp.menu_url)
    print("✅ provider:", disp.menu_provider)

if __name__ == "__main__":
    main()
