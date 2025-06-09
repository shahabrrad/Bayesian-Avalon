export type VoteCallback = (votes: Map<string, boolean>) => void;

export class VoteManager {
  private votes: Map<string, boolean> = new Map();
  private expectedVoters: Set<string> = new Set();
  private hasProcessedVotes = false;
  private onComplete: VoteCallback;

  private processing = false;
  private taskQueue: (() => void)[] = [];

  constructor(expectedVoterIds: string[], onComplete: VoteCallback) {
    this.expectedVoters = new Set(expectedVoterIds);
    this.onComplete = onComplete;
  }

  castVote(userId: string, vote: boolean): void {
    this.enqueue(() => {
      if (!this.expectedVoters.has(userId)) return; //prevent irrelevant votes
      if (this.votes.has(userId)) return; // Prevent duplicates

      this.votes.set(userId, vote);
      this.checkVotes();
    });
  }

  private enqueue(task: () => void) {
    this.taskQueue.push(task);
    this.processQueue();
  }

  private processQueue() {
    if (this.processing) return;

    this.processing = true;
    while (this.taskQueue.length > 0) {
      const task = this.taskQueue.shift();
      task?.();
    }
    this.processing = false;
  }

  private checkVotes(): void {
    if (this.hasProcessedVotes) return;
    if (this.votes.size === this.expectedVoters.size) {
      this.hasProcessedVotes = true;
      this.onComplete(this.votes);
    }
  }

  reset(expectedVoterIds: string[]) {
    this.votes.clear();
    this.expectedVoters = new Set(expectedVoterIds);
    this.hasProcessedVotes = false;
    this.taskQueue = [];
    this.processing = false;
  }

  getVoteCount(): number {
    return this.votes.size;
  }

  hasVoted(userId: string): boolean {
    return this.votes.has(userId);
  }
}
