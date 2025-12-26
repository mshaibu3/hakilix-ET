from __future__ import annotations
import os
import uvicorn

mode = os.environ.get("HAKILIX_RUN_MODE", "api").lower()
if mode == "migrate":
    from hakilix.scripts.migrate_and_seed import main
    main()
else:
    from hakilix.app import app
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get('PORT','8080')))
