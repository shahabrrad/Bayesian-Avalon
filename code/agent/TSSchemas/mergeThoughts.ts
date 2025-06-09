// The following is a schema definition for merging player opinions and thoughts into a single summary.

export interface ArgumentSummary {
    summary: string;      // The new summarized argument.
    importance: number;   // An estimated importance for the new argument, considering the importance of the original arguments
}
