import { Room, Client } from "@colyseus/core";
import {
  AvalonGameState,
  Message,
  Player,
  PlayerRoleType,
  RoleType,
} from "./schema/AvalonGameState";
import { gameRegistry } from "../GameRoomRegistry";
import { VoteManager } from "../utils/VoteManager";
import { ArraySchema } from "@colyseus/schema";
import { AgentTaskAPI } from "./schema/AgentAPI";
import { IncomingMessage } from "http";
import { JWT } from "@colyseus/auth";
import * as fs from "fs";
import * as path from "path";

import {
  getNextPlayer,
  findPlayerByRole,
  findPlayerBySessionId,
  findPlayerByUserId,
  createPartyString,
  addPlayer,
  getPlayerByPosition,
  generateRoomIdSingle,
} from "../utils/game-utils";

import {
  callMessageApi,
  callActionApi,
  callStateUpdateApi,
} from "../utils/agent-api-utils";
import {
  addAgent,
  sendPrivateDataToAgents,
  shutDownAgents,
  validateAgents,
} from "../utils/agent-utils";
import { appendLogData } from "../utils/file-utils";
import { findDifferences, shuffleArray } from "../utils/utils";
import { ACTIONS, PLAYER_TYPE, SYSTEM } from "../types/constants";
const LOBBY_CHANNEL = "$mylobby";

interface AgentEntry {
  id: string;
  player: string;
  role: string;
  type: string;
}

export class AvalonGame extends Room<AvalonGameState> {
  // spectators: { [key: string]: Client } = {};
  constructor() {
    super();
    this.unlock();
    this.autoDispose = false;
  }

  spectators: Client[] = [];
  partyVoteManager: VoteManager;
  questVoteManager: VoteManager;
  maxClients = 10;
  num_players = 6;
  num_agents = 5;
  num_humans = 1;
  connected_clients: { [key: string]: { sessionId: string; client: Client } } =
    {};
  configPath = path.resolve(__dirname, "./../../config.json");
  configData = JSON.parse(fs.readFileSync(this.configPath, "utf8"));
  delay_messages = this.configData.agent.delay_messages;
  roles: RoleType[] = (() => {
    try {
      const configRoles = this.configData.game.roles.map((role: string) => {
        // Convert role names from config to RoleType enum values
        // e.g., "servant-1" to RoleType.SERVANT_1
        const formattedRole = role.replace(/-/g, "_").toUpperCase();
        return RoleType[formattedRole as keyof typeof RoleType];
      });
      return shuffleArray(configRoles);
    } catch (error) {
      console.error("Error loading roles from config:", error);
      console.error("Failed to load roles from config. Exiting program.");
      process.exit(1);
    }
  })();
  names = shuffleArray(["Kira", "Jane", "Luca", "Mia", "Paul", "Sam"]);
  positions = Array.from({ length: 6 }, (_, i) => i + 1).sort(
    () => Math.random() - 0.5
  );
  playerRoleTypes: PlayerRoleType[] = this.roles.map((role, index) => ({
    role: role,
    playerName: undefined,
    name: this.names[index],
    type: undefined,
    position: this.positions[index],
  }));

  requestedAgents: Array<{
    id: string;
    player: string;
    role: string;
    type: string;
    playerName?: string;
  }> = [];

  party_size_per_quest: { [key: number]: number } = {
    1: 2,
    2: 3,
    3: 4,
    4: 3,
    5: 4,
  };
  internal_turn_tracker = -1;
  previousState = {};
  votes: { [key: string]: any } = {};
  agent_types: string[];
  assassin_vote_active: boolean = false;

  //generate a unique 4 character room id
  async generateRoomId(): Promise<string> {
    const currentIds = await this.presence.smembers(LOBBY_CHANNEL);
    let id;
    do {
      id = generateRoomIdSingle();
    } while (currentIds.includes(id));

    await this.presence.sadd(LOBBY_CHANNEL, id);
    return id;
  }

  static async onAuth(token: string, req: IncomingMessage) {
    return await JWT.verify(token);
  }

  async onCreate(options: any) {
    console.log("$$$ -> Running Server with Roles:", this.playerRoleTypes);
    this.setState(new AvalonGameState());
    this.roomId = await this.generateRoomId();
    gameRegistry.registerGame(this.roomId);

    this.requestedAgents = options.agents.sort((a: any, b: any) => {
      if (a.type === PLAYER_TYPE.AGENT && b.type !== PLAYER_TYPE.AGENT) {
        return -1;
      }
      if (a.type !== PLAYER_TYPE.AGENT && b.type === PLAYER_TYPE.AGENT) {
        return 1;
      }
      return 0;
    });

    let servant_count = 1;
    this.requestedAgents.forEach((agent) => {
      if (agent.role === "servant") {
        agent.role = `SERVANT-${servant_count}` as RoleType;
        servant_count++;
      }
    });

    const agents_valid = validateAgents(this.requestedAgents);
    console.log(
      "Game with",
      this.requestedAgents.length,
      "agents is valid:",
      agents_valid
    );
    if (!agents_valid) {
      console.log(
        "Game with",
        this.requestedAgents.length,
        "agents is invalid -> Disposing"
      );
      this.disconnect();
      return;
    }

    // update the number of players based on the number of agents
    this.num_agents = this.requestedAgents.filter(
      (agent) => agent.player === PLAYER_TYPE.AGENT
    ).length;

    this.num_humans = this.num_players - this.num_agents;

    this.onMessage("send_message", (client, message) => {
      
      this.addMessage(message.userId, message.msg);
    });

    this.onMessage("end_turn", (client, message) => {
      const player = findPlayerByUserId(message.userId, this.state.all_players);

      if (
        player &&
        player.id === this.state.turn_pid &&
        player.userId === message.userId
      ) {
        this.startNextTurn();
      }
    });

    // Listen to propose party
    this.onMessage("propose_party", (client, message) => {
      const player = findPlayerByUserId(message.userId, this.state.all_players);

      if (
        player &&
        player.id === this.state.turn_pid &&
        player.userId === message.userId
      ) {
        {
          this.state.proposed_party = new ArraySchema<number>(...message.party);
          // get the list of player names for the party from their pids
          const party_names_str = createPartyString(
            this.state.proposed_party,
            this.state.all_players
          );
          this.addMessage(
            "system",
            `${player.name} proposed a party: ${party_names_str}`
          );
        }
      }
    });

    // Listen to vote for the party
    this.onMessage("vote_party", (client, message) => {
      const player = findPlayerByUserId(message.userId, this.state.all_players);

      if (
        player &&
        player.id != this.state.leader_pid &&
        player.userId === message.userId
      ) {
        return;
      }

      this.addMessage("system", `${player.name} initiated a party vote.`);
      this.facilitatePartyVotes();
    });

    this.onMessage("assassination", (client, message) => {
      // Make sure the assassin is only allowed to assassinate
      const player = findPlayerByUserId(message.userId, this.state.all_players);
      if (!player) return;
      if (
        player.role !== RoleType.ASSASSIN ||
        message.userId !== player.userId
      ) {
        return;
      }
      const target = getPlayerByPosition(
        message.target,
        this.state.all_players
      );
      this.processAssassinVote(target.userId);
    });

    // Listen to the vote yes and vote no buttons
    this.onMessage("vote_result", (client, message) => {
      const player = findPlayerByUserId(message.userId, this.state.all_players);
      if (!player) return;

      if (player.userId === message.userId) {
        if (this.state.vote_party) {
          this.processVote(player.userId, message.vote);
        } else if (this.state.vote_quest) {
          this.processVoteQ(player.userId, message.vote);
        }
      }
    });

    console.log(
      "Game with ID",
      this.roomId,
      "created with",
      this.requestedAgents.length,
      "agents"
    );

    if (
      this.requestedAgents.filter((agent) => agent.player === PLAYER_TYPE.AGENT)
        .length === this.num_players
    ) {
      await this.handleAllJoined();
    }
  }

  async onJoin(client: Client, options: any) {
    if (options.spectator) {
      this.spectators.push(client);
      client.send("spectator_data", {
        data: this.state.all_players,
      });
      return;
    }

    const userId = options.userId;
    const sessionId = client.sessionId;
    this.connected_clients[userId] = {
      client: client,
      sessionId: sessionId,
    };
    if (this.state.all_joined) {
      await this.rejoin(userId, client);
    } else {
      if (Object.keys(this.connected_clients).length === this.num_humans) {
        await this.handleAllJoined();
      }
    }
  }

  async addHumans() {
    const randomHumans = this.requestedAgents.filter(
      (agent) =>
        agent.player === PLAYER_TYPE.HUMAN && agent.role === RoleType.RANDOM
    );

    const assignedHumans = this.requestedAgents.filter(
      (agent) =>
        agent.player === PLAYER_TYPE.HUMAN && agent.role !== RoleType.RANDOM
    );

    for (const userId in this.connected_clients) {
      const { sessionId, client } = this.connected_clients[userId];
      let agent = assignedHumans.shift() || randomHumans.shift(); // Get one agent, prioritizing assignedHumans
      if (agent) {
        await this.onJoinInternal(
          sessionId,
          userId,
          agent.role || RoleType.RANDOM,
          client,
          agent.playerName
        );
      }
    }
  }

  async addAllPlayers() {
    const assignedRoleAgents = this.requestedAgents.filter(
      (agent) =>
        agent.player === PLAYER_TYPE.AGENT && agent.role !== RoleType.RANDOM
    );
    const randomRoleAgents = this.requestedAgents.filter(
      (agent) =>
        agent.player === PLAYER_TYPE.AGENT && agent.role === RoleType.RANDOM
    );

    const addAgentsToGame = async (agents: any[]) => {
      for (const agent of agents) {
        if (agent.player === PLAYER_TYPE.AGENT) {
          const newAgent = await addAgent(
            agent,
            this.state.all_players,
            this.playerRoleTypes,
            this.roomId
          );
          await this.onJoinInternal(
            newAgent.sessionId,
            newAgent.userId,
            newAgent.rolePref
          );
        }
      }
    };

    await addAgentsToGame(assignedRoleAgents);
    await this.addHumans();
    await addAgentsToGame(randomRoleAgents);
  }

  async rejoin(userId: string, client: Client) {
    return new Promise<void>((resolve) => {
      const existingPlayer = findPlayerByUserId(userId, this.state.all_players);
      if (this.state.all_joined) {
        if (existingPlayer) {
          existingPlayer.active = true;
          this.addMessage("system", `${existingPlayer.name} re-joined.`);
          if (client) {
            client.send("private_data", {
              data: { player: Object.assign({}, existingPlayer) },
            });
          }
        } else {
          this.spectators.forEach((spectator) => {
            spectator.send("spectator_data", {
              data: this.state.all_players,
            });
          });
        }
        resolve();
      }
    });
  }

  async onJoinInternal(
    sessionId: string,
    userId: string,
    rolePref: string,
    client?: Client,
    playerName?: string
  ) {
    return new Promise<void>((resolve) => {
      const player = addPlayer(
        sessionId,
        userId,
        this.state.all_players,
        this.playerRoleTypes,
        rolePref,
        playerName
      );
      if (player) {
        player.active = true;
        this.state.all_players.push(player);
        this.state.players.push(player.name);
      }

      if (client) {
        client.send("private_data", { data: { player } });
      }
      resolve();
    });
  }

  //TODO: FIX ASSASSIN VOTE
  processAssassinVote(target_id: string | number) {
    const assassin = findPlayerByRole("Assassin", this.state.all_players);
    const target =
      typeof target_id === "string"
        ? findPlayerByUserId(target_id, this.state.all_players)
        : getPlayerByPosition(target_id, this.state.all_players);

    if (assassin) {
      this.addMessage(
        "system",
        `${assassin.name} (Assassin) assassinated ${target.name} (${target.role}).`
      );
      console.log("Assassinating: ", target.name, " (", target.name, ")");
    }

    // Check if the target is merlin
    if (target.role === "Merlin") {
      this.state.winner = "evil";
      this.finishGame("Evil wins by assassinating Merlin!");
    } else {
      this.state.winner = "good";
      this.finishGame("Good wins as Evil assassinated the wrong Merlin!");
    }
  }

  endVotingPhase() {
    this.state.vote_party = false;
    this.state.vote_quest = false;
    this.state.vote_assassin = false;
    this.clock.clear();
    this.state.turn_timer = 0;
  }

  facilitatePartyVotes() {
    console.log("Facilitating party votes...");
    // Clear the timer
    this.clock.clear();
    this.state.turn_timer = 0;

    this.state.vote_party = true;
    this.state.vote_quest = false;
    this.state.vote_assassin = false;

    const userIds = this.state.all_players.map((p) => p.userId);
    this.partyVoteManager = new VoteManager(userIds, (votes) => {
      this.state.vote_party = false;
      this.processPartyVotes(Object.fromEntries(votes));
    });
    // Ask all the AI agents...

    for (const player of this.state.all_players) {
      const { userId } = player;
      if (player.userId === player.sessionId) {
        const options = ["vote_party"];
        const task: AgentTaskAPI = {
          task: options,
          target_party_size: this.state.target_party_size,
          sequence: 0,
        };
        // console.log("Asking agent", userId, "to vote on party...");
        callActionApi(userId, task, this.state.toJSON(), async (error, data) => {
          if (data.success) {
            if (data?.data?.vote !== undefined) {
              console.log(
                "Received vote from",
                userId,
                "for party vote.",
                data
              );
              const llm_data = data?.data?.llm_data || []
              if(llm_data.length > 0) {
                await appendLogData(
                  {
                    timestamp: new Date().toISOString(),
                    msgtype: "llm_message",
                    action: ACTIONS.VOTE_PARTY,
                    agent: player.name,
                    data: llm_data,
                  },
                  this.roomId
                );
              }
              this.processVote(userId, data.data.vote);
            } else {
              console.log(
                "No vote received from",
                userId,
                "for party vote.",
                data
              );
            }
          }
        });
      }
    }
  }

  processVote(userId: string, vote: boolean) {
    this.partyVoteManager?.castVote(userId, vote);
  }

  processPartyVotes(votes: { [key: string]: any }) {
    // Send a summary message with which user has voted what:
    let vote_summary: string[] = [];

    for (const user_id in votes) {
      const player = findPlayerByUserId(user_id, this.state.all_players);
      if (!player) {
        console.error(`Player with user_id ${user_id} not found`);
        continue;
      }
      const { name } = player;
      vote_summary.push(`${name}: ${votes[user_id] ? "yes" : "no"}`);
    }

    const summary = vote_summary.join(", ");
    this.addMessage("system", `Party vote summary: ${summary}`);
    // Count if the majority of votes are true, then the party is approved
    let approved = 0;
    for (const user_id in votes) {
      if (votes[user_id]) {
        approved++;
      }
    }
    if (approved > this.num_players / 2) {
      this.addMessage("system", "The party has been approved!");
      // Move on to quest vote
      this.facilitateQuestVotes();
    } else {
      this.addMessage("system", "The party has been rejected!");
      // Move to the next leader
      this.state.failed_party_votes = this.state.failed_party_votes + 1;
      if (this.state.failed_party_votes === 5) {
        this.state.winner = "evil";
        this.finishGame("Evil wins by rejecting five parties!");
        return;
      }
      this.startNextRound(false);
    }
  }

  facilitateQuestVotes() {
    this.addMessage("system", "Voting for the quest has started...");

    const voterIds = this.state.proposed_party.map((pid) => {
      const p = getPlayerByPosition(pid, this.state.all_players);
      return p.userId;
    });
    this.questVoteManager = new VoteManager(voterIds, (votes) => {
      this.state.vote_quest = false;
      this.processQuestVotes(Object.fromEntries(votes));
    });

    this.state.vote_assassin = false;
    this.state.vote_party = false;
    this.state.vote_quest = true;

    // Ask all the AI agents...
    for (const player of this.state.all_players) {
      const { userId } = player;
      if (player.sessionId === player.userId && voterIds.includes(userId)) {
        const options = ["vote_quest"];
        const task: AgentTaskAPI = {
          task: options,
          target_party_size: this.state.target_party_size,
          sequence: 0,
        };
        callActionApi(userId, task, this.state.toJSON(), async (error, data) => {
          if (data.success) {
            console.log("vote_quest success from", player.name);
            console.log(data);
            const llm_data = data?.data?.llm_data || []
              if(llm_data.length > 0) {
              await appendLogData(
                {
                  timestamp: new Date().toISOString(),
                  msgtype: "llm_message",
                  action: ACTIONS.VOTE_QUEST,
                  agent: player.name,
                  data: data.llm_data,
                },
                this.roomId
              );
            }
            this.processVoteQ(userId, data.data.vote);
          }
        });
      }
    }
  }

  processVoteQ(userId: string, vote: boolean) {
    this.questVoteManager?.castVote(userId, vote);
  }

  processQuestVotes(votes: { [key: string]: any }) {
    // Figure out if all votes are true, then the quest is successful
    let success = true;
    for (const userId in votes) {
      if (!votes[userId]) {
        success = false;
        break;
      }
    }
    if (success) {
      this.state.quest_results.push("success");
      this.addMessage("system", "The quest has succeeded!");
    } else {
      this.state.quest_results.push("fail");
      this.addMessage("system", "The quest has failed!");
    }
    this.checkEndOfGame();
  }

  checkEndOfGame() {
    // Check if either side has won (three wins for good or three fails for evil)
    let good_wins = 0;
    let evil_wins = 0;
    for (const result of this.state.quest_results) {
      if (result === "success") {
        good_wins++;
      } else {
        evil_wins++;
      }
    }
    if (good_wins === 3) {
      this.state.winner = "good";

      // Check if there's an assassin in the game
      const assassin = findPlayerByRole("Assassin", this.state.all_players);

      if (assassin) {
        this.addMessage(
          "system",
          "Good wins, for now, by succeeding three quests..."
        );
        this.addMessage(
          "system",
          "The Assassin will now try to kill Merlin, potentially changing the outcome of the game..."
        );
        this.assassinVote();
      } else {
        // No assassin in the game, good wins immediately
        this.finishGame("Good wins by succeeding three quests!");
      }
    } else if (evil_wins === 3) {
      this.state.winner = "evil";
      this.finishGame("Evil wins by failing three quests!");
    } else {
      this.startNextRound();
    }
  }

  assassinVote() {
    this.assassin_vote_active = true;
    // console.log("Facilitating assassin vote...")
    this.addMessage("system", "The Assassin is now voting to kill Merlin...");
    this.state.vote_assassin = true;
    const options = ["vote_assassin"];
    // Start the voting timer

    const assassin = findPlayerByRole("Assassin", this.state.all_players);

    if (assassin.userId === assassin.sessionId) {
      const task: AgentTaskAPI = {
        task: options,
        target_party_size: this.state.target_party_size,
        sequence: 0,
      };
      callActionApi(
        assassin.userId,
        task,
        this.state.toJSON(),
        (error, data) => {
          if (data.success) {
            this.processAssassinVote(data.data.vote);
          }
        }
      );
    }
  }

  async onBeforePatch() {
    const current_state = this.state.toJSON();
    const changes = findDifferences(this.previousState, current_state);
    this.previousState = current_state;
    // remove keys that are not needed, if they exist
    delete changes["turn_timer"];

    if (Object.keys(changes).length < 1) {
      return;
    }

    const ts = new Date().toISOString();
    const logEntry = {
      timestamp: ts,
      changes: changes,
      full: this.state.toJSON(),
    };

    // Queue the log write operation

    
    await appendLogData(
      { timestamp: ts, msgtype: "game", full: this.state.toJSON() },
      this.roomId
    );

    // Send changes to agents
    for (const player of this.state.all_players) {
      if (player.userId === player.sessionId) {
        callStateUpdateApi(player.userId, logEntry);
      }
    }
  }

  startNextRound(reset_turn: boolean = true) {
    this.state.proposed_party = new ArraySchema<number>();
    const nextPlayer = getNextPlayer(this.state.turn_pid);
    this.state.turn_pid = nextPlayer;
    this.state.leader_pid = nextPlayer;
    this.state.currentRound += 1;

    if (!reset_turn) {
      this.state.turn += 1;
    }

    if (reset_turn) {
      this.state.quest += 1;
      this.state.turn = 0;
      this.state.failed_party_votes = 0;
      this.state.target_party_size =
        this.party_size_per_quest[this.state.quest];
    }

    this.executeTurn();
  }

  startNextTurn() {
    console.log("starting next turn")
    this.state.turn_pid = getNextPlayer(this.state.turn_pid);
    this.state.turn += 1;
    this.executeTurn();
  }

  executeTurn() {
    const { userId, sessionId } = getPlayerByPosition(
      this.state.turn_pid,
      this.state.all_players
    );
    // Disable all voting capabilities and cancel ongoing timers
    this.state.vote_assassin = false;
    this.state.vote_party = false;
    this.state.vote_quest = false;
    this.clock.clear();
    this.state.turn_timer = 0;

    if (sessionId === userId) {
      this.agentLoop(userId);
    }
  }

  canSkipTurn() {
    return this.state.vote_party === false && this.state.vote_quest === false;
  }

  async agentLoop(userId: string) {
    let step_counter = 0;
    let choosen_action = null;
    let skip_turn = false;
    let keep_running = true;
    const agent = findPlayerByUserId(userId, this.state.all_players);

    do {
      // Recompute options for the agent
      const options = this.computeOptions();
      const task: AgentTaskAPI = {
        task: options,
        target_party_size: this.party_size_per_quest[this.state.quest],
        sequence: step_counter,
      };

      // Pass the current game state to the action API
      const gameState = this.state.toJSON();
      let res;
      try {
        res = await callActionApi(userId, task, gameState);
        if (!res || !res.success) {
          throw new Error(
            `Agent ${agent.name} callActionApi did not respond`
          );
        }
        const llm_data = res?.data?.llm_data || []
          if(llm_data.length > 0) {
          await appendLogData(
            {
              timestamp: new Date().toISOString(),
              msgtype: "llm_message",
              action: res.action,
              agent: agent.name,
              data: llm_data,
            },
            this.roomId
          );
        }
      } catch (error: unknown) {
        console.error(`Error in agent loop for ${agent.name}:`, error);
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error occurred";
        await this.terminateGame(
          `Agent ${agent.name} failed to respond: ${errorMessage}`
        );
        return;
      }

      step_counter++;

      // Check if it's still the agent's turn
      if (this.state.turn_pid !== agent.id) {
        console.log("it is NOT this agent's turn")
        skip_turn = true;
        break;
      }

      choosen_action = res.action;

      const { valid, reason } = this.isValidAction(
        userId,
        choosen_action,
        res.data
      );

      if (!valid) {
        console.warn(
          `Invalid agent action: ${choosen_action}. Reason: ${reason}`
        );
        keep_running = true; // Agent can try again
        continue;
      }

      // Action is valid — process it
      keep_running = await this.processAction(userId, choosen_action, res.data);
    } while (keep_running && step_counter < 10);

    if (step_counter >= 10) {
      await this.terminateGame(
        `Agent ${agent.name} exceeded maximum action attempts`
      );
      return;
    }

    console.log("Agent loop ended for", userId);
    if(!skip_turn && choosen_action === ACTIONS.END_TURN) {
      this.startNextTurn();
    } 
  }

  async handleAllJoined() {
    let agentPlayers = this.state.all_players.filter(
      (player) => player.userId === player.sessionId
    ).length;

    if (this.state.all_joined) {
      return;
    }

    await this.addAllPlayers();

    const activePlayers = this.state.all_players.filter(
      (player) => player.active
    ).length;

    if (activePlayers === this.num_players) {
      // Validate game state before proceeding
      const validationErrors = this.validateGameState();
      if (validationErrors.length > 0) {
        await this.terminateGame(
          `Game state validation failed: ${validationErrors.join(", ")}`
        );
        return;
      }

      this.state.all_joined = true;
      //TODO: maybe Delete all non-active users
      this.state.players = new ArraySchema<string>(
        ...this.state.all_players
          .sort((a: Player, b: Player) => a.id - b.id)
          .map((player) => player.name)
      );

      // Write all the private data to logfile
      for (const player of this.state.all_players) {
        // Find the agent entry for this player to get the type
        const agentEntry = this.requestedAgents.find(
          (agent) =>
            agent.role.toUpperCase() === player.role.toUpperCase() ||
            (agent.role === "RANDOM" &&
              agent.player ===
                (player.userId === player.sessionId ? "agent" : "human"))
        );

        const playerType = agentEntry ? agentEntry.type : "unknown";

        const pData = {
          timestamp: new Date().toISOString(),
          msgtype: "player",
          name: player.name,
          role: player.role,
          pid: player.id,
          knowledge: player.knowledge,
          type: playerType,
          player: player.userId === player.sessionId ? "agent" : "human",
        };
        await appendLogData(pData, this.roomId);
      }

      const success = await sendPrivateDataToAgents(this.state.all_players);
      if (!success) {
        await this.terminateGame("Failed to send private data to agents");
        return;
      }

      agentPlayers = this.state.all_players.filter(
        (player) => player.userId === player.sessionId
      ).length;

      if (agentPlayers === this.num_players)
        this.clients.forEach((client) => {
          client.send("spectator_data", {
            data: this.state.all_players,
          });
        });

      // Start the game
      setTimeout(() => {
        this.addMessage(
          SYSTEM,
          "All players have joined. The game is starting!"
        );
        this.startNextRound();
      }, 2000);
    }
  }

  validateGameState(): string[] {
    const errors: string[] = [];

    // Check if all players have unique IDs
    const playerIds = new Set(this.state.all_players.map((p) => p.id));
    if (playerIds.size !== this.state.all_players.length) {
      errors.push("Duplicate player IDs found");
    }

    // Check if all players have valid roles
    const validRoles = new Set(Object.values(RoleType));
    for (const player of this.state.all_players) {
      if (!validRoles.has(player.role as RoleType)) {
        errors.push(`Invalid role for player ${player.name}: ${player.role}`);
      }
    }

    // Check if the number of players matches the expected count
    if (this.state.all_players.length !== this.num_players) {
      errors.push(
        `Expected ${this.num_players} players, found ${this.state.all_players.length}`
      );
    }

    // Check if all players have unique names
    const playerNames = new Set(this.state.all_players.map((p) => p.name));
    if (playerNames.size !== this.state.all_players.length) {
      errors.push("Duplicate player names found");
    }

    return errors;
  }

  isValidAction(
    userId: string,
    action: string,
    data?: any
  ): { valid: boolean; reason?: string } {
    try {
      const player = findPlayerByUserId(userId, this.state.all_players);
      if (!player) return { valid: false, reason: "Player not found" };

      switch (action) {
        case ACTIONS.MESSAGE:
          if (!data?.msg || data.msg.trim() === "") {
            return { valid: false, reason: "Empty message" };
          }
          break;

        case ACTIONS.PROPOSE_PARTY: {
          if (!Array.isArray(data?.party)) {
            return { valid: false, reason: "Invalid party data" };
          }
          const party = new ArraySchema<number>(...data.party);

          // Check party size
          if (party.length !== this.state.target_party_size) {
            return { valid: false, reason: "Party size mismatch" };
          }

          // Check if player is leader
          if (player.id !== this.state.leader_pid) {
            return { valid: false, reason: "Player is not the leader" };
          }

          // Check for duplicate players
          const uniquePlayers = new Set(party);
          if (uniquePlayers.size !== party.length) {
            return { valid: false, reason: "Party contains duplicate players" };
          }

          // Check if all players exist and are valid
          for (const playerId of party) {
            const partyPlayer = getPlayerByPosition(
              playerId,
              this.state.all_players
            );
            if (!partyPlayer) {
              return {
                valid: false,
                reason: `Invalid player ID in party: ${playerId}`,
              };
            }
          }
          break;
        }

        case ACTIONS.START_PARTY_VOTE:
          if (
            this.state.proposed_party.length !== this.state.target_party_size
          ) {
            return { valid: false, reason: "Proposed party size incorrect" };
          }
          break;

        case ACTIONS.VOTE_QUEST:
          if (!this.state.vote_quest) {
            return { valid: false, reason: "No active quest vote" };
          }
          break;

        case ACTIONS.VOTE_PARTY:
          if (!this.state.vote_party) {
            return { valid: false, reason: "No active party vote" };
          }
          break;

        case ACTIONS.END_TURN:
          if (!this.state.vote_party) {
            return { valid: true };
          }
          break;

        default:
          return { valid: false, reason: `Unknown action: ${action}` };
      }

      return { valid: true };
    } catch (error) {
      console.error("Failed to validate agent action:", error);
      return { valid: false, reason: "Exception during validation" };
    }
  }

  async processAction(userId: string, action: string, data?: any): Promise<boolean> {
    const player = findPlayerByUserId(userId, this.state.all_players);
    if (!player) {
      console.warn(`No player found for userId: ${userId}`);
      return false;
    }

    switch (action) {
      case ACTIONS.MESSAGE: {
        let message = data.msg?.replace(/^"(.*)"$/, "$1") || "";
        
        if (this.delay_messages) {
          // Split the message into sentences and add them individually with delays
          const sentences = message.split(/(?<=[.!?])\s+/);
          // console.log("^^^^^^^^^^^^^^^^^^^^");
          // console.log(message);
          // console.log("^^^^^^^^^^^^^^^^^^^^");
          // console.log(sentences);
          // console.log("^^^^^^^^^^^^^^^^^^^^");
          const messagePromises = [];
          
          let cumulativeDelay = 0;
          let messageCounter = 0;
          for (const sentence of sentences) {
            messageCounter++;
            if (sentence.trim()) {
              // Add a delay proportional to the message length (~1 second per 15 chars)
              const delayMs = Math.max(100, Math.floor(sentence.length * (1000 / 15)));
              cumulativeDelay += messageCounter === 1 ? 0 : delayMs;

              // if the last character is a period, remove it
              let sentence_trimmed = sentence.trim();
              if (sentence_trimmed.endsWith(".")) {
                sentence_trimmed = sentence_trimmed.slice(0, -1);
              }
              
              const messagePromise = new Promise<void>(resolve => {
                setTimeout(() => {
                  this.addMessage(userId, sentence_trimmed);
                  resolve();
                }, cumulativeDelay);
              });
              messagePromises.push(messagePromise);
            }
          }
          
          // If no messages to send, return immediately
          if (messagePromises.length === 0) {
            return true;
          }
          
          // Wait for all messages to be sent before returning
          try {
            await Promise.all(messagePromises);
            return true;
          } catch (err) {
            console.error("Error sending delayed messages:", err);
            return false;
          }
        } else {
          this.addMessage(userId, message);
          return true;
        }
      }

      case ACTIONS.PROPOSE_PARTY: {
        const party = new ArraySchema<number>(...data.party);
        this.state.proposed_party = party;

        this.addMessage(
          SYSTEM,
          `${player.name} proposed a party: ${createPartyString(
            party,
            this.state.all_players
          )}`
        );

        this.state.vote_assassin = false;
        this.state.vote_party = false;
        this.state.vote_quest = false;

        return true;
      }

      case ACTIONS.START_PARTY_VOTE: {
        this.addMessage(SYSTEM, `${player.name} initiated a party vote.`);
        this.state.vote_assassin = false;
        this.state.vote_party = false;
        this.state.vote_quest = false;

        this.facilitatePartyVotes();
        return false; // Agent will vote on their own party
      }

      case ACTIONS.END_TURN:
        return false;

      case ACTIONS.VOTE_ASSASSIN:
        this.processAssassinVote(data.guess);
        return false;

      case ACTIONS.VOTE_QUEST:
        this.processVoteQ(player.userId, data.vote);
        return false;

      case ACTIONS.VOTE_PARTY:
        this.processVote(player.userId, data.vote);
        return false;

      default:
        console.warn(`Unknown action by ${player.name}:`, action);
        return false;
    }
  }

  computeOptions(): string[] {
    // const options = ["vote_quest", "vote_party", "vote_assassin", "start_party_vote", "propose_party", "message"];
    let options = [ACTIONS.END_TURN, ACTIONS.MESSAGE];

    // Check if we can propose a party
    if (
      this.state.leader_pid === this.state.turn_pid &&
      !this.state.vote_party &&
      !this.state.vote_quest
    ) {
      options.push(ACTIONS.PROPOSE_PARTY);
      if (this.state.proposed_party.length === this.state.target_party_size) {
        options.push(ACTIONS.START_PARTY_VOTE);
      }
    } // Check if we need to vote on a party
    else if (this.state.vote_party) {
      options = [ACTIONS.VOTE_PARTY];
    } // Check if we need to vote on a quest
    else if (this.state.vote_quest) {
      options = [ACTIONS.VOTE_QUEST];
    }
    // If the current player is the assassin, then add the assassination option
    if (
      getPlayerByPosition(this.state.turn_pid, this.state.all_players).role ===
      "Assassin"
    ) {
      options.push(ACTIONS.VOTE_ASSASSIN);
    }

    return options;
  }

  addMessage(userId: string, message: string) {
    const new_message = new Message();
    new_message.quest = this.state.quest;
    new_message.turn = this.state.turn;
    new_message.room = this.roomId;
    new_message.player =
      findPlayerByUserId(userId, this.state.all_players)?.name || SYSTEM;
    new_message.msg = message;
    new_message.pid =
      findPlayerByUserId(userId, this.state.all_players)?.id || -1;
    new_message.mid = `msg_${this.state.messages.length}`;
    new_message.failed_party_votes = this.state.failed_party_votes;
    this.state.messages.push(new_message);

    // Send messages to API agents
    for (const player of this.state.all_players) {
      if (player.sessionId === player.userId) {
        const json_msg = {
          quest: new_message.quest,
          turn: new_message.turn,
          room: new_message.room,
          player: new_message.player,
          msg: new_message.msg,
          failed_party_votes: new_message.failed_party_votes,
          strategy: Array.from(new_message.strategy), // Convert ArraySchema to plain array
          pid: new_message.pid,
          mid: new_message.mid,
        };
        callMessageApi(player.userId, json_msg);
      }
    }
  }

  async onLeave(client: Client, consented: boolean) {
    const player = findPlayerBySessionId(
      client.sessionId,
      this.state.all_players
    );

    if (player) {
      // Delete user if not all_joined
      if (!this.state.all_joined) {
        // remove name from the state.players array:
        const index = this.state.players.indexOf(player.name);
        delete this.state.players[index];
        this.connected_clients[player.userId] = null;
      } else {
        this.connected_clients[player.userId] = null;
        player.active = false;
        this.addMessage(SYSTEM, `${player.name} left the game.`);
      }
    }
    // Check if all players have left
    const activePlayers = this.state.all_players.filter(
      (player) => player.active
    ).length;
    //set timeout to 1 minute to allow rejoining
    if (activePlayers === 0) {
      setTimeout(() => {
        this.onDispose();
      }, 60000);
    }
  }

  onDispose() {
    // Disconnect the agents
    this.presence.srem(LOBBY_CHANNEL, this.roomId);
    gameRegistry.unregisterGame(this.roomId);
    this.disconnect();
    shutDownAgents(this.state.all_players);
  }

  finishGame(msg: string) {
    // Disconnect all clients in 2 seconds
    this.addMessage(SYSTEM, msg);
    let players = "";

    for (const player of this.state.all_players) {
      players +=
        "<li><b>" + player.name + "</b>: <i>" + player.role + "</i></li>";
    }

    this.addMessage(
      SYSTEM,
      "These were the game's players: <ul class='player_reveal_list'>" +
        players +
        "</ul>"
    );
    setTimeout(() => {
      this.broadcast("game_over", { msg: msg });
      this.disconnect();
      shutDownAgents(this.state.all_players);
    }, 2000);
  }

  async terminateGame(error_msg: string) {
    await appendLogData(
      {
        timestamp: new Date().toISOString(),
        msgtype: "error",
        message: error_msg,
      },
      this.roomId
    );
    // If the game has humans in it, then don't terminate the game
    if (
      this.state.all_players.some(
        (player) => player.userId === player.sessionId
      )
    ) {
      return;
    }
    shutDownAgents(this.state.all_players);
    process.exit(1);
  }
}
