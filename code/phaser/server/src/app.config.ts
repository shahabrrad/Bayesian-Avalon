import config from "@colyseus/tools";
import { monitor } from "@colyseus/monitor";
import { playground } from "@colyseus/playground";
import express, { Request, Response } from "express";
import session from "express-session";
import { auth } from "@colyseus/auth";
import "./config/auth";
/**
 * Import your Room files
 */
import { AvalonGame } from "./rooms/AvalonGame";
import { AvalonLobby } from "./rooms/AvalonLobby";
import { AvalonLogin } from "./rooms/AvalonLogin";
import { AvalonAdmin } from './rooms/AvalonAdmin';
import { AvalonRerun } from './rooms/AvalonRerun';
import { matchMaker } from "colyseus";

export default config({
  initializeGameServer: (gameServer) => {
    /**
     * Define your room handlers:
     */
    gameServer.define("avalon_login", AvalonLogin);
    gameServer.define("avalon_game", AvalonGame, { autoDispose: false });
    gameServer.define("avalon_lobby", AvalonLobby);
    gameServer.define("avalon_admin", AvalonAdmin, { autoDispose: false });
    gameServer.define("avalon_rerun", AvalonRerun);
  },

  initializeExpress: (app) => {
    /**
     * Bind your custom express routes here:
     * Read more: https://expressjs.com/en/starter/basic-routing.html
     */
    // app.get("/hello_world", (req, res) => {
    //     res.send("It's time to kick ass and chew bubblegum!");
    // });

    app.post("/api/create-room", async (req, res) => {
      console.log("I GOT A CREATE ROOM REQUEST!!!");
      const { agent_options } = req.body;
      const agents: Array<{ id: number; role: string; type: string }> = [];

      for (const key in agent_options) {
        if (agent_options.hasOwnProperty(key)) {
          agents.push({
            ...agent_options[key], // Spread the existing properties
          });
        }
      }

      try {
        const room = await matchMaker.createRoom("avalon_game", {
          agents: agents,
        });

        console.log("Room created:", room.roomId); // Log the room ID
        res.send(room);
      } catch (error) {
        console.error("Error creating room:", error);
        res.status(500).send({ error: "Failed to create room" });
      }
    });

    app.post("/room/:roomId/start-game", async (req, res) => {
      const roomId = req.params.roomId;
      const agents = req.body; // JSON payload

      try {
        // Find the room by roomId
        const room: AvalonGame = matchMaker.getRoomById(roomId);
        if (room) {
          // Call the addAgents function
          await room.handleAllJoined();
          res.json({ success: true, message: "Agents added successfully" });
        } else {
          res.status(404).json({ error: "Room not found" });
        }
      } catch (error) {
        console.error("Error adding agents:", error);
        res.status(500).json({ error: "Failed to add agents" });
      }
    });

    /**
     * Use @colyseus/playground
     * (It is not recommended to expose this route in a production environment)
     */
    if (process.env.NODE_ENV !== "production") {
      app.use("/", playground);
    }

    app.get("/", auth.middleware(), (req: Request, res) => {
      res.json(req.auth);
    });

    app.use(auth.prefix, auth.routes());

    /**
     * Use @colyseus/monitor
     * It is recommended to protect this route with a password
     * Read more: https://docs.colyseus.io/tools/monitor/#restrict-access-to-the-panel-using-a-password
     */
    app.use("/colyseus", monitor());

    /**
     * Session Management stuff
     */
    app.use(
      session({
        secret: "merlins-beard",
        resave: false,
        saveUninitialized: true,
      })
    );
  },

  beforeListen: () => {
    /**
     * Before before gameServer.listen() is called.
     */
  },
});
