type PlayerData = { sessionId: string; name: string };
type LobbyData = {
  roomId: string;
  players: Map<string, PlayerData>;
};

class LobbyRegistry {
  private lobbies: Map<string, LobbyData> = new Map();

  registerLobby(roomId: string) {
    this.lobbies.set(roomId, { roomId, players: new Map() });
  }

  unregisterLobby(roomId: string) {
    this.lobbies.delete(roomId);
  }

  addPlayerToLobby(roomId: string, player: PlayerData) {
    this.lobbies.get(roomId)?.players.set(player.sessionId, player);
    console.log(this.lobbies)
  }

  removePlayerFromLobby(roomId: string, sessionId: string) {
    this.lobbies.get(roomId)?.players.delete(sessionId);
  }

  getLobbyData(roomId: string): LobbyData | undefined {
    return this.lobbies.get(roomId);
  }

  getAllLobbies(): LobbyData[] {
    return Array.from(this.lobbies.values());
  }
}

export const lobbyRegistry = new LobbyRegistry();
