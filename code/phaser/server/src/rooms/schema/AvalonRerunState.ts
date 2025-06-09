import {AvalonGameState} from "./AvalonGameState";
import { Schema, type, ArraySchema, MapSchema } from "@colyseus/schema";

export class AvalonRerunState extends Schema {
    @type("string") logName: string = "";
    @type("number") currentState: int = 0;
    @type(AvalonGameState) game: AvalonGameState;
}