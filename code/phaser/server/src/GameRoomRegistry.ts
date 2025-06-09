type RoomData = {
  id: string;
};

class GameRegistry {
  private games: Map<string, RoomData> = new Map();

  registerGame(id: string) {
    this.games.set(id, { id });
  }

  unregisterGame(id: string) {
    this.games.delete(id);
  }

  getAllGames(): RoomData[] {
    return Array.from(this.games.values());
  }
}

export const gameRegistry = new GameRegistry();
