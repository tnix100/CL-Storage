# CL Storage
CL Storage is an extension for CL4 Python servers to persist room data across server restarts.

> **Warning**
CL Storage only works on CL4 Python servers >=0.2.0.

## Installation
To install CL Storage on your CL4 Python server, all you need to do is follow these steps:

1. Download the `cl_storage.py` file from this repo.
2. Place the `cl_storage.py` file inside of the root folder for your CL server.
3. Import and load the CLStorage module from within your server's start script.

### Example:
```py
# main.py

from cloudlink import server
from cloudlink.server.protocols import clpv4, scratch

from cl_storage import CLStorage


if __name__ == "__main__":
    # Initialize the server
    server = server()

    # Load protocols
    clpv4 = clpv4(server)
    scratch = scratch(server)

    # Load CL Storage
    cl_storage = CLStorage(server, clpv4)
    
    # Start the server
    server.run(ip="127.0.0.1", port=3000)
```

## Configuration
There is multiple kwargs that can be changed during initialization of CL Storage to change its behavior. Here's details for each one:
```py
CLStorage(
    server,
    clpv4,
    db_file = "cl_storage.db",  # changes what file the database is stored in (default: "cl_storage.db")
    disable_gmsg = True,  # disables storage of CL4 global messages (default: False)
    disable_pmsg = True,  # disables storage of CL4 private messages (default: False)
    disable_gvar = True,  # disables storage of CL4 global variables (default: False)
    disable_pvar = True,  # disables storage of Cl4 private variables (default: False)
    disable_scratch = True,  # disables storage of Scratch cloud variables (default: False)
    enabled_rooms = ["regex pattern"],  # only enable storage for rooms that match one of these regex patterns (default: [])
    disabled_rooms = ["regex pattern"]  # disables storage for rooms that match one of these regex patterns (default: [])
)
```

> **Note**
CL Storage is enabled for all rooms by default.

## CL4 private messages/variables
Private messages/variables are only stored if the recipient is online at the time of the private message/variable being sent. The recipient will receive the private message/variable again upon linking to the room with the same username.

## Database
The database is a SQLite database with the following tables:
```sql
CREATE TABLE "cl_msgs" (
	"room"	TEXT NOT NULL,
	"val"	TEXT NOT NULL,
	"origin"	TEXT NOT NULL,
	"id"	TEXT NOT NULL,
	PRIMARY KEY("room","id")
);
```
```sql
CREATE TABLE "cl_vars" (
	"room"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"val"	TEXT NOT NULL,
	"origin"	TEXT NOT NULL,
	"id"	TEXT NOT NULL,
	PRIMARY KEY("room","name","id")
);
```
```sql
CREATE TABLE "scratch_vars" (
	"project_id"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"val"	TEXT NOT NULL,
	PRIMARY KEY("project_id","name")
);
```

## Support
If you require any assistance with getting CL Storage working on your server or just want to ask a question, please ping me (.tnix) in the CloudLink Discord server.

## Future plans
In the future I plan to add quotas to how many messages/variables a room can store at once and auto-deleting policies to help prevent spam and reduce storage usage.