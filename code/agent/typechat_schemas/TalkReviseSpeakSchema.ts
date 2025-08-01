// The following is a schema definition for reasoning about the current game state and sending a message to other players

export interface TalkReviseSpeakSchema {
    revised_speak: string ; // The public message that the agent will say to the other players, which shouldn't expose private information
}
