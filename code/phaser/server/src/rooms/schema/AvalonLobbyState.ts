import { Schema, type, MapSchema } from "@colyseus/schema";

export class Player extends Schema {
  @type("string") id: string;
  @type("string") name: string;

  constructor(id: string, name: string) {
    super();
    this.id = id;
    this.name = name;
  }
}

export class AvalonLobbyState extends Schema {
  @type("string") mySynchronizedProperty: string = "Hello world";

  @type({ map: Player }) players = new MapSchema<Player>();
}
