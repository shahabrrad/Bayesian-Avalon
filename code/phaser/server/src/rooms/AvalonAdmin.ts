import { Room, Client } from "@colyseus/core";
import { lobbyRegistry } from "../LobbyRegistry";
import { gameRegistry } from "../GameRoomRegistry";
import { AvalonAdminState } from "./schema/AvalonAdminState";
import { matchMaker } from "colyseus";
import { IncomingMessage } from "http";
import { JWT } from "@colyseus/auth";

type PlayerObject = {
  id: string;
  player: string;
  playerName: string;
  role: string;
  type: string;
};

async function createGameRoom(agents: Array<PlayerObject>) {
  const room = await matchMaker.createRoom("avalon_game", {agents: agents});
  return room.roomId;
}

export class AvalonAdmin extends Room<AvalonAdminState> {
  maxClients = 10;

  static async onAuth(token: string, req: IncomingMessage) {
    return await JWT.verify(token);
  }
  

  onCreate(options: any) {
    this.setPatchRate(null); // Don't need state patches
    this.setState(new AvalonAdminState());

    this.onMessage("create_game_room", (client, message) => {
      // undo JSON parsing
      const agents: Array<PlayerObject> = JSON.parse(message);
      const roomId = createGameRoom(agents);
      roomId.then((roomId) => {
        client.send("room_created", { success: true, roomId: roomId });
      });
    });

    this.onMessage("get_lobby_data", (client, message) => {
        client.send("lobby_overview", lobbyRegistry.getAllLobbies());
    })

    this.onMessage("get_game_data", (client, message) => {
        client.send("game_overview", gameRegistry.getAllGames());
    })

  }

  onJoin(client: Client, options: any) {
    const allLobbyData = lobbyRegistry.getAllLobbies();
    const allGameData = gameRegistry.getAllGames();
    client.send("lobby_overview", allLobbyData);
    client.send("game_overview", allGameData)
  }

  onLeave(client: Client, consented: boolean) {
  }

  onDispose() {
    console.log("admin room", this.roomId, "disposing...");
  }
}
