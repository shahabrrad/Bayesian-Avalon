// The following is a schema definition for actions taken by the agent.

export interface TakeTurn {
    chat: string;       // The communication to be sent to the other player
    reasoning: string;  // A brief summary of the reasoning behind the communication that is not sent to the other player
}
