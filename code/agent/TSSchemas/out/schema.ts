// The following is a schema definition for proposing a party

export interface ProposeParty {
    party: Array<"Dan" | "Leo" | "Pia" | "Jax" | "Sam" | "Hugo">;       // The party suggested by the agent, which is a list of player names
}
