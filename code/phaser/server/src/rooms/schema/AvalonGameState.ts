import { Schema, type, ArraySchema, MapSchema } from "@colyseus/schema";

export class Message extends Schema {
  @type("int32") quest: number = 0;
  @type("int32") turn: number = 0;
  @type("string") room: string = "";
  @type("string") player: string = "";
  @type("string") msg: string = "";
  @type(["string"]) strategy: ArraySchema<string> = new ArraySchema<string>();
  @type("int32") pid: number = -1;
  @type("string") mid: string = "";
  @type("int32") failed_party_votes: number = 0;
}

export class Player extends Schema {
  @type("string") name: string = "";
  @type("int32") id: number = -1;
  @type("string") role: string = "";
  @type("string") userId: string = "";
  @type("boolean") active: boolean = false;
  @type("string") sessionId: string = "";
  @type({ map: "string" }) knowledge: MapSchema<string> =
    new MapSchema<string>();

  constructor(
    id: number,
    name: string,
    role: string,
    sessionId: string,
    userId: string,
    active: boolean,
    knowledge: MapSchema<string>
  ) {
    super();
    this.id = id;
    this.name = name;
    this.role = role;
    this.sessionId = sessionId;
    this.userId = userId;
    this.active = active;
    this.knowledge = knowledge;
  }
}

export enum RoleType {
  RANDOM = "random",
  MERLIN = "Merlin",
  PERCIVAL = "Percival",
  ASSASSIN = "Assassin",
  MORGANA = "Morgana",
  SERVANT_1 = "Servant-1",
  SERVANT_2 = "Servant-2",
  SERVANT_3 = "Servant-3",
  SERVANT_4 = "Servant-4",
  MINION_1 = "Minion-1",
  MINION_2 = "Minion-2",
}

export interface PlayerRoleType {
  role: RoleType;
  name: string;
  playerName: string | undefined;
  type: string | undefined;
  position: number;
}

export interface RequestedAgents {
  id: string;
  player: string;
  playerName: string | undefined;
  role: string;
  type: string | undefined;
}

export class AvalonGameState extends Schema {
  // A list of player names
  @type(["string"]) players: ArraySchema<string> = new ArraySchema<string>();

  // A boolean indicating if all players joined
  @type("boolean") all_joined: boolean = false;

  @type([Player]) all_players: ArraySchema<Player> = new ArraySchema<Player>();

  // An array of message types
  @type([Message]) messages: ArraySchema<Message> = new ArraySchema<Message>();

  // The ID of the winning player
  @type("string") winner: string = "";

  // The player ID of the leader
  @type("int32") leader_pid: number = 0;

  // The player ID of the player whose turn it is
  @type("int32") turn_pid: number = 0;

  @type("int32") currentRound: number = 0;
  // The current quest number
  @type("int32") quest: number = 0;

  // The current turn number
  @type("int32") turn: number = 0;

  // An integer representing the number of players in the party
  @type("int32") target_party_size: number = 0;

  // Timer for the current turn, float between 0 and 1
  @type("float32") turn_timer: number = 0;

  // Array holding the currently proposed party as player IDs
  @type(["int32"]) proposed_party: ArraySchema<number> =
    new ArraySchema<number>();

  // A boolean indicating if party voting is active
  @type("boolean") vote_party: boolean = false;

  // A boolean indicating if quest voting is active
  @type("boolean") vote_quest: boolean = false;

  // The number of failed party votes
  @type("int32") failed_party_votes: number = 0;

  // A list of quest results
  @type(["string"]) quest_results: ArraySchema<string> =
    new ArraySchema<string>();

  // **********************************************
  // These are carried over states from the previous game
  // **********************************************

  // A list representing the current party
  @type(["string"]) party: ArraySchema<string> = new ArraySchema<string>();

  // A boolean indicating if assassin voting is active
  @type("boolean") vote_assassin: boolean = false;

}
