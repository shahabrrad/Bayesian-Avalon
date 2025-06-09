import { Schema, type } from "@colyseus/schema";

export class AvalonLoginState extends Schema {
  @type("string") mySynchronizedProperty: string = "Hello world";
}