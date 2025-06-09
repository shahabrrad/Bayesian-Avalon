import { Room, Client } from "@colyseus/core";
import { AvalonLobbyState } from "./schema/AvalonLobbyState";
import { lobbyRegistry } from "../LobbyRegistry";
import { matchMaker } from "colyseus";
import { IncomingMessage } from "http";
import { JWT } from "@colyseus/auth";

// Define the type
type PlayerObject = {
  id: string;
  player: string;
  playerName: string;
  role: string;
  type: string;
};

async function createGameRoom(agents: Array<PlayerObject>) {
  const room = await matchMaker.createRoom("avalon_game", { agents: agents });
  return room.roomId;
}

export class AvalonLobby extends Room<AvalonLobbyState> {
  maxClients = 32;

  static async onAuth(token: string, req: IncomingMessage) {
    const result = await JWT.verify(token);
    return result;
  }

  onCreate(options: any) {
    this.setState(new AvalonLobbyState());
    lobbyRegistry.registerLobby(this.roomId);
  }

  onJoin(client: Client, options: any) {
    const playerName = options.name || `Guest-${client.sessionId}`;
    
    lobbyRegistry.addPlayerToLobby(this.roomId, {
      sessionId: client.sessionId,
      name: playerName
    });
  }

  onLeave(client: Client, consented: boolean) {
    lobbyRegistry.removePlayerFromLobby(this.roomId, client.sessionId);
  }

  onDispose() {
    lobbyRegistry.unregisterLobby(this.roomId)
    console.log("room", this.roomId, "disposing...");
  }
}
