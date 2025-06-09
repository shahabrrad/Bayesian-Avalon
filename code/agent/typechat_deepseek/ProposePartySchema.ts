// Schema for proposing a party team in Avalon and justifying it

export interface ProposePartySchema {
    party: Array<"###">;  // Array of player names that will form the party
    message: string; // Message to the other players that will be displayed to them, justifying the proposed team
}