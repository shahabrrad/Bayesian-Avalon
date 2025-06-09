// The following is a schema definition for reasoning about the current game state and sending a message to other players

export interface TalkSchema {
    think: string ; // The hidden reasoning of the agent. It will not be shared and can discuss private information
    speak: string ; // The public message that the agent will say to the other players, which shouldn't expose private information
}
