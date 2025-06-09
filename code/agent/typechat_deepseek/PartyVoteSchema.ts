// Schema for voting on a proposed party in Avalon

export interface PartyVoteSchema {
    vote: "approve" | "disapprove";  // whether to approve or disapprove the proposed team
} 