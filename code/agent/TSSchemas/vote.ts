// The following is a schema definition for conducting a vote

export interface VoteInterface {
    vote: "Yes" | "No"; // The vote of the agent 
    reasoning: string;  // A brief summary of the reasoning behind the vote
}
