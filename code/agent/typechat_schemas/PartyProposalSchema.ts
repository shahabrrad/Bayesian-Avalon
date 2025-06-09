// The following is a schema definition for proposing a party

export interface PartyProposalSchema {
    party: Array<"Luca" | "Mia" | "Sam" | "Paul" | "Kira" | "Jane"> ;  // A list of players that should be on the party. Refer to all players, including yourself, by their respective name.
}
