import {Client, Room} from "@colyseus/core";
import {AvalonGameState, Message, Player,} from "./schema/AvalonGameState";
import {ArraySchema, type type} from "@colyseus/schema";
import {IncomingMessage} from "http";
import {JWT} from "@colyseus/auth";
import * as fs from "fs";
import * as path from "path";
import {AvalonRerunState} from "./schema/AvalonRerunState";
import {AvalonGame} from "./AvalonGame";

interface LogEntry {
    timestamp: Date,
    msgtype: "game" | "player" | "llm_message"
    full: any
}

const LOBBY_CHANNEL = "$mylobby";

export class AvalonRerun extends Room<AvalonRerunState> {
    constructor() {
        super();
    }

    spectators: Client[] = [];
    maxClients = 10;
    logStates: Array<AvalonGameState> = []

    static async onAuth(token: string, req: IncomingMessage) {
        return await JWT.verify(token);
    }

    async onCreate(options: any) {
        console.log(options)
        this.setState(new AvalonRerunState());
        const logPath = path.join(__dirname, "../../logs", `${options.log}.json`)
        const raw = fs.readFileSync(logPath, "utf-8");
        const logData: { logs: LogEntry[] } = JSON.parse(raw);

        logData.logs.map(entry => {
            if (entry.msgtype === "game" && entry.full.all_joined) {
                this.logStates.push(this.loadGameStateFromSnapshot(entry.full))
            }
        })
        this.state.game = this.logStates[this.state.currentState]

        this.onMessage("next_turn", (client, message) => {
            const current = this.state.currentState;
            const next = current + 1;

            if (next >= this.logStates.length) {
                return
            } else {
                this.state.currentState = next;

                // Get the message diff
                const prevMessages = this.logStates[current].messages;
                const newMessages = this.logStates[next].messages.slice(prevMessages.length);

                // Update game state
                this.state.game = this.loadGameStateFromSnapshot(this.logStates[next])

                // Send delta to the client
                this.broadcast("new_messages", newMessages);
            }
        });


        this.onMessage("prev_turn", (client, message) => {
            const current = this.state.currentState;
            let prev = current - 1;

            if (prev < 0) {
                return
            }

            // Compute diff: messages removed when going backward
            const currentMessages = this.logStates[current].messages;
            const prevMessages = this.logStates[prev].messages;

            const removedMessages = currentMessages.slice(prevMessages.length);

            // Update state
            this.state.currentState = prev;
            this.state.game = this.loadGameStateFromSnapshot(this.logStates[prev])

            // Inform clients about removed messages
            this.broadcast("removed_messages", removedMessages);
        });

    }

    async onJoin(client: Client, options: any) {
        client.send("spectator_data", {
            data: this.state.game.all_players,
        });
    }

    onDispose() {
        // Disconnect the agents
        this.presence.srem(LOBBY_CHANNEL, this.roomId);
    }

    extractGameState(currentState: number, prevState: number): AvalonGameState {
        const currentMessages = this.logStates[currentState].messages;
        const previousMessages = this.logStates[prevState].messages;
        const messageDiff = this.getMessageDiffOnly(currentMessages, previousMessages);
        const state = this.logStates[currentState]
        state.messages = new ArraySchema<Message>(...messageDiff);

        console.log(JSON.stringify(state.messages))
        return state;
    }

    getMessageDiffOnly(
        currentMessages: ArraySchema<Message>,
        previousMessages: ArraySchema<Message>
    ): Message[] {
        if (currentMessages.length > previousMessages.length) {
            // Moving forward — new messages were added
            return currentMessages.slice(previousMessages.length);
        } else if (currentMessages.length < previousMessages.length) {
            // Moving backward — messages were removed
            return previousMessages.slice(currentMessages.length);
        }

        // No difference
        return [];
    }


    loadGameStateFromSnapshot(snapshot: any): AvalonGameState {
        const state = new AvalonGameState();
        // Primitive values
        state.all_joined = snapshot.all_joined;
        state.winner = snapshot.winner;
        state.leader_pid = snapshot.leader_pid;
        state.turn_pid = snapshot.turn_pid;
        state.currentRound = snapshot.currentRound;
        state.quest = snapshot.quest;
        state.turn = snapshot.turn;
        state.target_party_size = snapshot.target_party_size;
        state.turn_timer = snapshot.turn_timer;
        state.vote_party = snapshot.vote_party;
        state.vote_quest = snapshot.vote_quest;
        state.failed_party_votes = snapshot.failed_party_votes;
        state.vote_assassin = snapshot.vote_assassin;

        // Arrays
        state.players = new ArraySchema<string>(...snapshot.players);
        state.quest_results = new ArraySchema<string>(...snapshot.quest_results);
        state.party = new ArraySchema<string>(...snapshot.party);
        state.proposed_party = new ArraySchema<number>(...snapshot.proposed_party);

        // Nested Player schemas
        state.all_players = new ArraySchema<Player>(
            ...snapshot.all_players.map((p: any) => {
                return new Player(p.id, p.name, p.role, p.sessionId, p.userId, p.active, p.knowledge);
            })
        );

        state.messages = new ArraySchema<Message>(
            ...snapshot.messages.map((m: any) => {
                const message = new Message();
                message.quest = m.quest;
                message.turn = m.turn;
                message.room = m.room;
                message.player = m.player;
                message.msg = m.msg;
                message.strategy = m.strategy;
                message.pid = m.pid;
                message.mid = m.mid;
                message.failed_party_votes = m.failed_party_votes;
                return message;
            })
        )
        return state;
    }


}
