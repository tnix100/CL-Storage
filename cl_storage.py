from cloudlink import server, client
from cloudlink.server.protocols import clpv4, cl4_protocol, scratch_protocol

from typing import Any
import sqlite3
import ujson
import re


class CLStorage:
    def __init__(
        self,
        parent: server,
        clpv4: clpv4,
        db_file: str = "cl_storage.db",
        disable_gmsg: bool = False,
        disable_pmsg: bool = False,
        disable_gvar: bool = False,
        disable_pvar: bool = False,
        disable_scratch: bool = False,
        enabled_rooms: list[str] = [],
        disabled_rooms: list[str] = [],
    ):
        self.enabled_rooms = enabled_rooms
        self.disabled_rooms = disabled_rooms

        # Connect to database and get cursor
        self.db_con = sqlite3.connect(db_file)
        self.db_cur = self.db_con.cursor()

        # Create tables
        self.db_cur.execute(
            """CREATE TABLE IF NOT EXISTS cl_msgs (
                            room TEXT NOT NULL,
                            val TEXT NOT NULL,
                            origin TEXT NOT NULL,
                            id TEXT NOT NULL,
                            PRIMARY KEY (room, id)
                        )"""
        )
        self.db_cur.execute(
            """CREATE TABLE IF NOT EXISTS cl_vars (
                            room TEXT NOT NULL,
                            name TEXT NOT NULL,
                            val TEXT NOT NULL,
                            origin TEXT NOT NULL,
                            id TEXT NOT NULL,
                            PRIMARY KEY (room, name, id)
                        )"""
        )
        self.db_cur.execute(
            """CREATE TABLE IF NOT EXISTS scratch_vars (
                            project_id TEXT NOT NULL,
                            name TEXT NOT NULL,
                            val TEXT NOT NULL,
                            PRIMARY KEY (project_id, name)
                        )"""
        )
        self.db_con.commit()

        parent.logger.info("CL Storage database initialized!")

        @parent.on_protocol_identified(schema=cl4_protocol)
        async def protocol_identified(client):
            if not self._is_room_enabled("default"):
                return

            # Send saved msgs
            for val, origin, id in self.fetch_cl_msgs("default"):
                val = ujson.loads(val)
                origin = ujson.loads(origin)
                id = ujson.loads(id)
                if id:
                    if disable_pmsg:
                        continue
                    if id != client.username:
                        continue
                    parent.send_packet(
                        client,
                        {
                            "cmd": "pmsg",
                            "val": val,
                            "origin": origin,
                            "rooms": "default",
                        },
                    )
                else:
                    if disable_gmsg:
                        continue
                    parent.send_packet(
                        client, {"cmd": "gmsg", "val": val, "rooms": "default"}
                    )

            # Send saved vars
            for name, val, origin, id in self.fetch_cl_vars("default"):
                name = ujson.loads(name)
                val = ujson.loads(val)
                origin = ujson.loads(origin)
                id = ujson.loads(id)
                if id:
                    if disable_pvar:
                        continue
                    if id != client.username:
                        continue
                    parent.send_packet(
                        client,
                        {
                            "cmd": "pvar",
                            "name": name,
                            "val": val,
                            "origin": origin,
                            "rooms": "default",
                        },
                    )
                else:
                    if disable_gvar:
                        continue
                    parent.send_packet(
                        client,
                        {"cmd": "gvar", "name": name, "val": val, "rooms": "default"},
                    )

        @parent.on_command(cmd="link", schema=cl4_protocol)
        async def on_link(client: client, message):
            if isinstance(message["val"], str):
                message["val"] = [message["val"]]

            for room in message["val"]:
                if not self._is_room_enabled(room):
                    continue

                # Send saved msgs
                for val, origin, id in self.fetch_cl_msgs(room):
                    val = ujson.loads(val)
                    origin = ujson.loads(origin)
                    id = ujson.loads(id)
                    if id:
                        if disable_pmsg:
                            continue
                        if id != client.username:
                            continue
                        parent.send_packet(
                            client,
                            {
                                "cmd": "pmsg",
                                "val": val,
                                "origin": origin,
                                "rooms": room,
                            },
                        )
                    else:
                        if disable_gmsg:
                            continue
                        parent.send_packet(
                            client, {"cmd": "gmsg", "val": val, "rooms": room}
                        )

                # Send saved vars
                for name, val, origin, id in self.fetch_cl_vars(room):
                    name = ujson.loads(name)
                    val = ujson.loads(val)
                    origin = ujson.loads(origin)
                    id = ujson.loads(id)
                    if id:
                        if disable_pvar:
                            continue
                        if id != client.username:
                            continue
                        parent.send_packet(
                            client,
                            {
                                "cmd": "pvar",
                                "name": name,
                                "val": val,
                                "origin": origin,
                                "rooms": room,
                            },
                        )
                    else:
                        if disable_gvar:
                            continue
                        parent.send_packet(
                            client,
                            {"cmd": "gvar", "name": name, "val": val, "rooms": room},
                        )

        if not disable_gmsg:

            @parent.on_command(cmd="gmsg", schema=cl4_protocol)
            async def on_gmsg(client: client, message):
                for room in clpv4.gather_rooms(client, message):
                    if not self._is_room_enabled(room):
                        continue
                    self.save_cl_msg(room, message["val"])

        if not disable_pmsg:

            @parent.on_command(cmd="pmsg", schema=cl4_protocol)
            async def on_pmsg(client: client, message):
                origin = clpv4.generate_user_object(client)
                for room in clpv4.gather_rooms(client, message):
                    if not self._is_room_enabled(room):
                        continue
                    for client in await parent.rooms_manager.get_specific_in_room(
                        room, cl4_protocol, message["id"]
                    ):
                        self.save_cl_msg(
                            room, message["val"], origin=origin, id=client.username
                        )

        if not disable_gvar:

            @parent.on_command(cmd="gvar", schema=cl4_protocol)
            async def on_gvar(client: client, message):
                for room in clpv4.gather_rooms(client, message):
                    if not self._is_room_enabled(room):
                        continue
                    self.save_cl_var(room, message["name"], message["val"])

        if not disable_pvar:

            @parent.on_command(cmd="pvar", schema=cl4_protocol)
            async def on_pvar(client: client, message):
                origin = clpv4.generate_user_object(client)
                for room in clpv4.gather_rooms(client, message):
                    if not self._is_room_enabled(room):
                        continue
                    for client in await parent.rooms_manager.get_specific_in_room(
                        room, cl4_protocol, message["id"]
                    ):
                        self.save_cl_var(
                            room,
                            message["name"],
                            message["val"],
                            origin=origin,
                            id=client.username,
                        )

        if not disable_scratch:

            @parent.on_command(cmd="handshake", schema=scratch_protocol)
            async def handshake(client: client, message):
                if not self._is_room_enabled(message["project_id"]):
                    return

                # Get room and whether room exists in room manager
                room = parent.rooms_manager.get(message["project_id"])
                room_exists = parent.rooms_manager.exists(message["project_id"])

                # Send saved variables
                for name, val in self.fetch_scratch_vars(message["project_id"]):
                    if name not in room["global_vars"]:
                        if room_exists:
                            room["global_vars"][name] = val
                        parent.send_packet(
                            client, {"method": "set", "name": name, "value": val}
                        )

            @parent.on_command(cmd="create", schema=scratch_protocol)
            async def create_variable(_, message):
                if not self._is_room_enabled(message["project_id"]):
                    return
                self.save_scratch_var(
                    message["project_id"], message["name"], message["value"]
                )

            @parent.on_command(cmd="set", schema=scratch_protocol)
            async def set_variable(_, message):
                if not self._is_room_enabled(message["project_id"]):
                    return
                self.save_scratch_var(
                    message["project_id"], message["name"], message["value"]
                )

            @parent.on_command(cmd="rename", schema=scratch_protocol)
            async def rename_variable(_, message):
                if not self._is_room_enabled(message["project_id"]):
                    return
                self.rename_scratch_var(
                    message["project_id"], message["name"], message["new_name"]
                )

            @parent.on_command(cmd="delete", schema=scratch_protocol)
            async def delete_variable(_, message):
                if not self._is_room_enabled(message["project_id"]):
                    return
                self.delete_scratch_var(message["project_id"], message["name"])

    def _is_room_enabled(self, room: str) -> bool:
        # Check disabled rooms
        for pattern in self.disabled_rooms:
            if re.fullmatch(pattern, room):
                return False

        # Check enabled rooms
        if not len(self.enabled_rooms):
            return True
        for pattern in self.enabled_rooms:
            if re.fullmatch(pattern, room):
                return True

        # Default
        return False

    def fetch_cl_msgs(
        self, room: str
    ) -> list[tuple[str, None | dict[str, str], None | str]]:
        return self.db_cur.execute(
            "SELECT val, origin, id FROM cl_msgs WHERE room=?", (room,)
        ).fetchall()

    def save_cl_msg(
        self, room: str, val: Any, origin: dict[str, str] = None, id: str = None
    ):
        val = ujson.dumps(val)
        origin = ujson.dumps(origin)
        id = ujson.dumps(id)
        self.db_cur.execute(
            "INSERT OR REPLACE INTO cl_msgs (room, val, origin, id) VALUES (?, ?, ?, ?)",
            (
                room,
                val,
                origin,
                id,
            ),
        )
        self.db_con.commit()

    def fetch_cl_vars(
        self, room: str
    ) -> list[tuple[str, str, None | dict[str, str], None | str]]:
        return self.db_cur.execute(
            "SELECT name, val, origin, id FROM cl_vars WHERE room=?", (room,)
        ).fetchall()

    def save_cl_var(
        self,
        room: str,
        name: str,
        val: Any,
        origin: dict[str, str] = None,
        id: str = None,
    ):
        name = ujson.dumps(name)
        val = ujson.dumps(val)
        origin = ujson.dumps(origin)
        id = ujson.dumps(id)
        self.db_cur.execute(
            "INSERT OR REPLACE INTO cl_vars (room, name, val, origin, id) VALUES (?, ?, ?, ?, ?)",
            (
                room,
                name,
                val,
                origin,
                id,
            ),
        )
        self.db_con.commit()

    def fetch_scratch_vars(self, project_id: str) -> list[tuple[str, str]]:
        return self.db_cur.execute(
            "SELECT name, val FROM scratch_vars WHERE project_id=?", (project_id,)
        ).fetchall()

    def save_scratch_var(self, project_id: str, name: str, val: str):
        self.db_cur.execute(
            "INSERT OR REPLACE INTO scratch_vars (project_id, name, val) VALUES (?, ?, ?)",
            (
                project_id,
                name,
                val,
            ),
        )
        self.db_con.commit()

    def rename_scratch_var(self, project_id: str, name: str, new_name: str):
        val = self.db_cur.execute(
            "SELECT val FROM scratch_vars WHERE project_id=? name=?",
            (
                project_id,
                name,
            ),
        )
        if val:
            self.save_scratch_var(project_id, name, val[0])
            self.delete_scratch_var(project_id, name)

    def delete_scratch_var(self, project_id: str, name: str):
        self.db_cur.execute(
            "DELETE FROM scratch_vars WHERE project_id=? name=?",
            (
                project_id,
                name,
            ),
        )
        self.db_con.commit()
