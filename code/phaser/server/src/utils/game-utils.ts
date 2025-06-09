import { ArraySchema, MapSchema } from "@colyseus/schema";
import {
  Player,
  PlayerRoleType,
  RoleType,
} from "../rooms/schema/AvalonGameState";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

export function createPlayer(
  sessionId: string,
  userId: string,
  allPlayers: ArraySchema<Player>,
  playerRoleTypes: Array<PlayerRoleType>,
  rolePref?: string,
  playerName?: string
) {
  let roleToAssign: PlayerRoleType | undefined = playerName
    ? playerRoleTypes.find((playerRole) => playerRole.playerName === playerName)
    : undefined;

  if (!roleToAssign) {
    const isRoleAvailable = (role: string) =>
      !allPlayers.some(
        (player) => player.role.toLowerCase() === role.toLowerCase()
      );

    if (rolePref !== undefined && rolePref !== RoleType.RANDOM) {
      roleToAssign = playerRoleTypes.find(
          (playerRole) =>
            playerRole.role.toLowerCase() === rolePref.toLowerCase() &&
          isRoleAvailable(rolePref)
      );
    }

    if (!roleToAssign) {
      roleToAssign = playerRoleTypes.find((playerRole) =>
        isRoleAvailable(playerRole.role)
        );
    }
  }

  const knowledge = _getPlayerKnowledge(roleToAssign.role, playerRoleTypes);

  return new Player(
    roleToAssign.position,
    roleToAssign.name,
    roleToAssign.role,
    sessionId,
    userId,
    true,
    knowledge
  );
}

function _getPlayerRoleTypeByRole(
  role: string,
  playerRoleTypes: Array<PlayerRoleType>
): number | null {
  const playerRoleType = playerRoleTypes.find(
    (playerRole) => playerRole.role === role
  );
  if (!playerRoleType) {
    return null;
  }
  return playerRoleType.position;
}

function _getPlayerKnowledge(
  role: string,
  players: Array<PlayerRoleType>
): MapSchema<string> {
  let knowledge: MapSchema<string> = new MapSchema<string>();

  if (role === "Merlin") {
    const assassin = _getPlayerRoleTypeByRole(RoleType.ASSASSIN, players);
    const morgana = _getPlayerRoleTypeByRole(RoleType.MORGANA, players);
    const minion_1 = _getPlayerRoleTypeByRole(RoleType.MINION_1, players);
    const minion_2 = _getPlayerRoleTypeByRole(RoleType.MINION_2, players);
    
    if (assassin !== null) knowledge.set(assassin.toString(), "evil");
    if (morgana !== null) knowledge.set(morgana.toString(), "evil");
    if (minion_1 !== null) knowledge.set(minion_1.toString(), "evil");
    if (minion_2 !== null) knowledge.set(minion_2.toString(), "evil");
  } else if (role === "Percival") {
    const merlin = _getPlayerRoleTypeByRole(RoleType.MERLIN, players);
    const morgana = _getPlayerRoleTypeByRole(RoleType.MORGANA, players);

    if (merlin !== null) knowledge.set(merlin.toString(), "unknown");
    if (morgana !== null) knowledge.set(morgana.toString(), "unknown");
  } else if (
    role === RoleType.MORGANA ||
    role === RoleType.ASSASSIN ||
    role === RoleType.MINION_1 ||
    role === RoleType.MINION_2
  ) {
    // All evil roles know each other
    const morgana = _getPlayerRoleTypeByRole(RoleType.MORGANA, players);
    const assassin = _getPlayerRoleTypeByRole(RoleType.ASSASSIN, players);
    const minion_1 = _getPlayerRoleTypeByRole(RoleType.MINION_1, players);
    const minion_2 = _getPlayerRoleTypeByRole(RoleType.MINION_2, players);

    if (morgana !== null) knowledge.set(morgana.toString(), "evil");
    if (assassin !== null) knowledge.set(assassin.toString(), "evil");
    if (minion_1 !== null) knowledge.set(minion_1.toString(), "evil");
    if (minion_2 !== null) knowledge.set(minion_2.toString(), "evil");
  }
  return knowledge;
}

export function getNextPlayer(currentIndex: number): number {
  return (currentIndex % 6) + 1;
}

export function proposeRandomParty(partySize: number) {
  const selectedIndices = new Set<number>();
  while (selectedIndices.size < partySize) {
    const randomIndex = Math.floor(Math.random() * 6) + 1;
    selectedIndices.add(randomIndex);
  }
  return Array.from(selectedIndices);
}

export function findPlayerByRole(
  role: string,
  players: ArraySchema<Player>
): Player {
  for (const player of players) {
    if (player.role === role) {
      return player;
    }
  }
}

export function findPlayerByUserId(
  userId: string,
  players: ArraySchema<Player>
): Player | undefined {
  for (const player of players) {
    if (player.userId === userId) {
      return player;
    }
  }
  return undefined;
}

export function findPlayerBySessionId(
  sessionId: string,
  players: ArraySchema<Player>
): Player | undefined {
  for (const player of players) {
    if (player.sessionId === sessionId) {
      return player;
    }
  }
  return undefined;
}

export function getPlayerByPosition(
  position: number,
  players: ArraySchema<Player>
): Player | undefined {
  return players.find((player) => player.id === position);
}

export function createPartyString(
  proposedParty: ArraySchema<number>,
  players: ArraySchema<Player>
) {
  const party_names = proposedParty.map(
    (playerId) => getPlayerByPosition(playerId, players).name
  );
  // concatenate the names with ", " in between
  return party_names.join(", ");
}

export function addPlayer(
  sessionId: string,
  userId: string,
  allPlayers: ArraySchema<Player>,
  playerRoleTypes: Array<PlayerRoleType>,
  rolePref?: string,
  playerName?: string
) {
  const newPlayer = createPlayer(
    sessionId,
    userId,
    allPlayers,
    playerRoleTypes,
    rolePref,
    playerName
  );
  return newPlayer;
}

export function generateRoomIdSingle(): string {
  // Generate a single 4 capital letter room ID.
  let result = "";
  for (var i = 0; i < 4; i++) {
    result += LETTERS.charAt(Math.floor(Math.random() * LETTERS.length));
  }
  return result;
}

module.exports = {
  addPlayer,
  createPartyString,
  createPlayer,
  findPlayerByRole,
  findPlayerBySessionId,
  findPlayerByUserId,
  generateRoomIdSingle,
  getNextPlayer,
  getPlayerByPosition,
  proposeRandomParty,
};
