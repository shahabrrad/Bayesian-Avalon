import { ArraySchema } from "@colyseus/schema";
import {
  Player,
  PlayerRoleType,
  RequestedAgents,
  RoleType,
} from "../rooms/schema/AvalonGameState";
import {
  AgentStartupAPI,
  AgentShutdownAPI,
  ApiResponse,
} from "../rooms/schema/AgentAPI";
import {
  callPrivateDataApi,
  callStartupApi,
  callShutdownAPI,
} from "./agent-api-utils";

export async function addAgent(
  agent: RequestedAgents,
  allPlayers: ArraySchema<Player>,
  playerRoleTypes: Array<PlayerRoleType>,
  gameId: string
) {
  const roleToAssign =
    playerRoleTypes.find(
      (playerRole) =>
        playerRole.role.toLowerCase() === agent.role.toLowerCase() &&
        !allPlayers.some(
          (player) => player.role.toLowerCase() === agent.role.toLowerCase()
        )
    ) ||
    playerRoleTypes.find(
      (playerRole) =>
        !allPlayers.some(
          (player) =>
            player.role.toLowerCase() === playerRole.role.toLowerCase()
        )
    );
  if (!roleToAssign) {
    console.error("Failed to assign role to agent: No available roles");
    return;
  }

  const params: AgentStartupAPI = {
    game_id: gameId,
    agent_type: agent.type,
    agent_role_preference: roleToAssign.role,
    agent_name: roleToAssign.name,
  };

  const response: ApiResponse = await callStartupApi(params);
  if (!response || !response.success) {
    console.error("Error starting up agent:", response?.error || "Unknown error");
    return null;
  }
  return {
    userId: response.agent_id,
    sessionId: response.agent_id,
    rolePref: response.agent_role_preference,
    namePref: response.agent_name_preference,
  };
}

export async function sendPrivateDataToAgents(players: ArraySchema<Player>) {
  const promises = [];

  // Give the agents their private data
  for (const player of players) {
    if (player.userId === player.sessionId) {
      const named_knowledge: { [key: string]: string } = {};

      for (const [key, value] of player.knowledge.entries()) {
        named_knowledge[key] = players[parseInt(key) - 1].name;
      }

      const pdata = {
        name: player.name,
        role: player.role,
        pid: player.id,
        knowledge: player.knowledge,
        named_knowledge: named_knowledge,
        all_players: players.reduce<{ [key: string]: string }>((acc, p) => {
          acc[p.name] = p.role;
          return acc;
        }, {}), // Only send this to the API (such that humans don't cheat)
        // Having access to all_players is needed to generate some of the prompts properly...
        order_to_name: players.reduce<{ [key: string]: string }>((acc, p) => {
          acc[p.id] = p.name;
          return acc;
        }, {}),
      };

      promises.push(callPrivateDataApi(player.userId, pdata));
    }
  }
  // We need to wait her for a bit to make sure the agents have received their private data
  const results = await Promise.all(promises);
  const allConfirmed = results.every((result) => result);
  return allConfirmed;
}

export function validateAgents(
  agents: Array<{ id: string; player: string; role: string; type: string }>
): boolean {
  const roleCounts: { [key: string]: number } = {
    merlin: 0,
    morgana: 0,
    assassin: 0,
    percival: 0,
    [RoleType.SERVANT_1]: 0,
    [RoleType.SERVANT_2]: 0,
  };

  // Count the number of each role (excluding 'random')
  for (const agent of agents) {
    const role = agent.role.toLowerCase();
    if (role !== "random" && roleCounts.hasOwnProperty(role)) {
      roleCounts[role]++;
    }
  }

  // Validate the counts
  if (roleCounts["merlin"] > 1) {
    console.error("There must be at most one Merlin.");
    return false;
  }
  if (roleCounts["morgana"] > 1) {
    console.error("There must be at most one Morgana.");
    return false;
  }
  if (roleCounts["assassin"] > 1) {
    console.error("There must be at most one Assassin.");
    return false;
  }
  if (roleCounts["percival"] > 1) {
    console.error("There must be at most one Percival.");
    return false;
  }
  if (roleCounts[RoleType.SERVANT_1]) {
    console.error("There must be at most 1 servant_2.");
    return false;
  }
  if (roleCounts[RoleType.SERVANT_2] > 1) {
    console.error("There must be at most 1 servant_2.");
    return false;
  }

  return true;
}

export function shutDownAgents(players: ArraySchema<Player>) {
  for (const player of players) {
    if (player.userId === player.sessionId) {
      const params: AgentShutdownAPI = {
        agent_id: player.userId,
      };
      console.log(`shutting down ${params.agent_id}: ${player.name}`);
      callShutdownAPI(params);
    }
  }
}

module.exports = {
  addAgent,
  sendPrivateDataToAgents,
  validateAgents,
  shutDownAgents,
};
