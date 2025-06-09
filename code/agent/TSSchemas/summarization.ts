// The following is a schema definition for determining the main arguments of a paragraph of text.

export interface ArgumentSummary {
    summary: string;                          // A brief summary of the entire context paragraph
    main_arguments: Array<ArgumentDetails>;   // An array of the main arguments extracted from the text that are actionable
}

export interface ArgumentDetails {
    argument: string;       // The main argument or point, highlighting player's actions, justifications, and desires about other players or game states
    importance: number;     // A score or measure of the argument's importance or relevance on a scale of 0-1 where 0 is not important and 1 is very important
    text_reference: string; // A specific part of the text that this argument refers to
    persuasion_strategy: "assertion" | "questioning" | "suggestion" | "agreement" | "critique"; // The general sentiment of the argument
    context: "current party" | "game state" | PNAMES ; // The party, general game, or player that the argument is about. This is not the player that is speaking.
}