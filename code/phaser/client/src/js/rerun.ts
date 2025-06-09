import {Client, Room} from "colyseus.js";
import {AvalonGameState, Message} from "../schema/AvalonGameState";
import Hashids from "hashids/cjs";
import * as images from "../img/*.png";
import {SERVER_URL} from "../utils/LoginClient";
import {AvalonRerunState} from "../schema/AvalonRerunState";
import {ArraySchema} from "@colyseus/schema";

class AvalonGameClient {
    client: Client;
    room: Room<AvalonRerunState>;
    userId: string | null;
    hashids: Hashids;
    previousGameState: AvalonGameState | null = null;


    constructor(serverUrl: string) {
        this.client = new Client(serverUrl);
        this.userId = this.generateUserId();
    }

    generateUserId(): string {
        // Generate or retrieve a unique user ID
        this.hashids = new Hashids("your-salt", 10);
        this.userId = localStorage.getItem("userId");
        if (!this.userId) {
            this.userId = this.generateUniqueId(); // Implement a function to generate a unique ID
            localStorage.setItem("userId", this.userId as string);
        }
        return this.userId;
    }

    generateUniqueId(): string {
        const now = Date.now(); // Get current time in milliseconds
        const seconds = Math.floor(now / 1000); // Extract seconds
        const milliseconds = now % 1000; // Extract milliseconds

        // Encode both seconds and milliseconds
        return this.hashids.encode(seconds, milliseconds);
    }

    handleSpectatorData() {
        this.room.onMessage("spectator_data", (response) => {
            const {data} = response;
            for (const player of data) {
                const player_position = player.id;

                const player_role_field = document.getElementById(
                    `player-predicted-role-${player_position}`
                );
                if (player_role_field) {
                    player_role_field.innerHTML = player.role.split("-")[0];
                }
                // Set player icon:
                const player_icon = document.getElementById(
                    `player-portrait-${player_position}`
                );
                if (player_icon) {
                    player_icon.src = images[`${player.role.toLowerCase()}`];
                    player_icon.style.display = "block";
                }
                // Remove belief selector
                const belief_selector = document.getElementById(
                    `player-belief-${player_position}`
                );
                if (belief_selector) {
                    // Disable the dropdown
                    belief_selector.disabled = true;
                }

                // Setup the private data if needed...
                for (const [key, value] of Object.entries(player.knowledge)) {
                    const element = document.getElementById(`${value}-ring-${key}`);
                    if (element) {
                        element.style.display = "block";
                    }
                }
            }
        });
    }

    async joinRoom(roomName: staring) {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const roomID = urlParams.get("roomID");
            this.room = await this.client.joinOrCreate<AvalonRerunState>(roomName, {
                userId: localStorage.getItem("userId"),
                accessToken: localStorage.getItem("accessToken"),
                log: roomID
            });

            // Store reconnection token and room ID before the window unloads
            window.onbeforeunload = () => {
                localStorage.setItem("reconnectionToken", this.room.reconnectionToken);
                localStorage.setItem("roomId", this.room.id);
            };
        } catch (e: any) {
            console.error("Error joining room", e);
            this.showErrorMessage(e.message);
        }

        this.handleSpectatorData();
        const handleTurnChange = (new_pid: number, prev_pid: number) => {
            const prev_arrow = document.getElementById(`jester-${prev_pid}`);
            if (prev_arrow) prev_arrow.style.display = "none";
            const new_arrow = document.getElementById(`jester-${new_pid}`);
            if (new_arrow) new_arrow.style.display = "block";
        };

        const handleLeaderChange = (new_pid: number, prev_pid: number) => {
            const prev_crown = document.getElementById(`crown-${prev_pid}`);
            if (prev_crown) prev_crown.style.display = "none";

            const new_crown = document.getElementById(`crown-${new_pid}`);
            if (new_crown) new_crown.style.display = "block";
        };


        const handleFailedPartyVotes = (failedPartVotes: number) => {
            {
                // loop through the failed votes and set them to display: block
                for (let i = 1; i <= 5; i++) {
                    const failed_vote = document.getElementById(`party-image-${i}`);
                    if (!failed_vote) {
                        continue;
                    }
                    if (i <= failedPartVotes) {
                        failed_vote.style.display = "block";
                    } else {
                        failed_vote.style.display = "none";
                    }
                }
            }
        };

        const handleProposedParty = (proposedParty: ArraySchema<number>) => {
            for (let i = 1; i <= 6; i++) {
                this.toggleShield(i, this.room.state.game.proposed_party.includes(i));
            }
        }

        const handleMessages = (messages: ArraySchema<Message>) => {
            messages.forEach(message => {
                this.addMessage(message)
            })
        }

        const handleQuestResults = (questResults: ArraySchema<string>) => {
            // Loop over the current quest results and show images
            for (let i = 0; i < questResults.length; i++) {
                const quest_result = document.getElementById(
                    `quest-image-${i + 1}`
                ) as HTMLImageElement;

                if (!quest_result) continue;

                quest_result.style.display = "block";
                quest_result.src =
                    questResults[i] === "success"
                        ? images["quest-success"]
                        : images["quest-fail"];
            }

            // Clear any remaining slots (up to 5 total)
            for (let i = questResults.length; i < 5; i++) {
                const quest_result = document.getElementById(
                    `quest-image-${i + 1}`
                ) as HTMLImageElement;
                if (!quest_result) continue;
                quest_result.style.display = "none"; // Correct way to hide it
                quest_result.src = ""; // Reset the image
            }
        };


        // ********************** START LISTENERS ********************** //

        const handleStatechange = (newState: AvalonGameState, prevState: AvalonGameState) => {
            handleTurnChange(newState.turn_pid, prevState.turn_pid);
            handleLeaderChange(newState.leader_pid, prevState.leader_pid);
            handleFailedPartyVotes(newState.failed_party_votes);
            handleProposedParty(newState.proposed_party)
            handleQuestResults(newState.quest_results)
        };


        this.room.onStateChange.once((state) => {
            this.room.onMessage("new_messages", (newMessages: ArraySchema<Message>) => {
                handleMessages(newMessages);
            });
            this.room.onMessage("removed_messages", (removedMessages: Message[]) => {
                removedMessages.forEach(() => {
                    this.removeLastMessage(); // implement this to pop messages from UI
                });
            });
            if (this.room.state?.game?.all_joined) {
                const waitingAElement = document.getElementById("waiting_a");
                const waitingBElement = document.getElementById("waiting_b");
                const hiderAElement = document.getElementById("hider_a");
                const hiderBElement = document.getElementById("hider_b");

                if (waitingAElement) {
                    waitingAElement.style.display = "none";
                }

                if (waitingBElement) {
                    waitingBElement.style.display = "none";
                }

                if (hiderAElement) {
                    hiderAElement.style.display = "block";
                }

                if (hiderBElement) {
                    hiderBElement.style.display = "block";
                }

                // Iterate through the players array
                this.room.state.game.players.forEach((player, index) => {
                    // set player by loop index
                    const playerElement = document.getElementById(
                        `player-name-${index + 1}`
                    );
                    if (playerElement) {
                        playerElement.innerHTML = player;
                    }
                });
            }
        });

        this.room.onStateChange((state) => {
            if (this.previousGameState) {
                handleStatechange(state.game, this.previousGameState);
            }
            this.previousGameState = state.game;
        })
        // ********************** END LISTENERS ********************** //
    }

    /**used to toggle shield based on other player's party proposals */
    toggleShield(player_position: number, force?: boolean) {
        const shield = document.getElementById(`shield-${player_position}`);
        if (shield) {
            if (force !== undefined) {
                shield.style.display = force ? "block" : "none";
            } else {
                const canProposeParty = this.room.state.game.leader_pid === this.room.state.game.turn_pid &&
                    !this.room.state.game.vote_party &&
                    !this.room.state.game.vote_quest
                if (canProposeParty) {
                    shield.style.display =
                        shield.style.display === "block" ? "none" : "block";
                }
            }
        }
    }

    addMessage(message: Message) {
        const iDiv = document.createElement("div");
        iDiv.className = "message-container";

        if (message.player === "system") {
            iDiv.style.backgroundColor = "rgba(255, 0, 191, 0.3)";
        } else {
            iDiv.style.backgroundColor = "rgba(255, 191, 0, 0.3)";
        }

        iDiv.innerHTML = `<div class='message-strategy'></div><div class='message-inner'>${message.player}: ${message.msg}</div>`;
        const chat = document.getElementById("chat");
        if (chat) {
            chat.appendChild(iDiv);
        }
        this.updateScroll();
    }

    removeLastMessage() {
        const chat = document.getElementById("chat");
        if (chat && chat.lastChild) {
            chat.removeChild(chat.lastChild);
        }
    }

    showErrorMessage(message: string) {
        const waitingElement = document.getElementById("waiting_a");
        if (waitingElement) {
            waitingElement.innerHTML = `<h3 style="text-align: center; color: red;">Error: ${message}</h3>`;
        }
    }

    updateScroll() {
        const chat = document.getElementById("chat");
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    }
}

// Define the function in the global scope
function toggleHelpBox() {
    const helpBox = document.getElementById("help_box");
    if (helpBox) {
        if (
            helpBox?.style.display === "none" ||
            helpBox.style?.display === "" ||
            !helpBox.style?.display
        ) {
            helpBox.style.display = "block";
        } else {
            helpBox.style.display = "none";
        }
    } else {
        console.log("Help box not found");
    }
}

const gameClient: AvalonGameClient = new AvalonGameClient(SERVER_URL);

document.addEventListener("DOMContentLoaded", () => {
    const helpButton = document.getElementById("help_button");
    if (helpButton) {
        helpButton.addEventListener("click", (event) => {
            toggleHelpBox();
        });
    } else {
        console.log("Help button not found");
    }

    document.addEventListener("click", (event) => {
        const helpBox = document.getElementById("help_box");
        const helpButton = document.getElementById("help_button");
        if (helpBox && helpButton) {
            if (
                !helpBox.contains(event.target as Node) &&
                !helpButton.contains(event.target as Node)
            ) {
                helpBox.style.display = "none";
            }
        }
    });

    document.getElementById("next_button")?.addEventListener("click", () => {
        gameClient.room.send("next_turn", {});
    });

    document.getElementById("prev_button")?.addEventListener("click", () => {
        gameClient.room.send("prev_turn", {});
    });

    document.addEventListener("keydown", (event) => {
        if (!gameClient?.room) return;

        if (event.key === "ArrowRight") {
            event.preventDefault();
            gameClient.room.send("next_turn", {});
        } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            gameClient.room.send("prev_turn", {});
        }
    });


    const questBar = document.getElementById("quest-bar");
    const qsize = [2, 3, 4, 3, 4];

    for (let i = 1; i <= 5; i++) {
        const questRing = document.createElement("div");
        questRing.className = "quest-ring";
        questRing.style.left = `${(i - 1) * 62}px`;

        const questText = document.createElement("div");
        questText.className = "quest-text";
        questText.innerText = qsize[i - 1] || "";

        const questImage = document.createElement("img");
        questImage.className = "quest-image";
        questImage.id = `quest-image-${i}`;
        questImage.style.display = "none";
        questImage.src = "quest-success.png"; // Adjust the path as needed

        questRing.appendChild(questText);
        questRing.appendChild(questImage);
        questBar?.appendChild(questRing);
    }

    // Add the party bar
    const partyBar = document.getElementById("party-bar");
    for (let i = 1; i <= 5; i++) {
        const partyRing = document.createElement("div");
        partyRing.className = "party-ring";
        partyRing.style.left = `${(i - 1) * 40}px`;
        if (i === 5) {
            partyRing.style.backgroundColor = "maroon";
        }

        const partyImage = document.createElement("img");
        partyImage.className = "party-image";
        partyImage.id = `party-image-${i}`;
        partyImage.style.display = "none";
        partyImage.src = images["chip"]; // Adjust the path as needed

        partyRing.appendChild(partyImage);
        partyBar?.appendChild(partyRing);
    }

    // Add the player box
    const playerBox = document.getElementById("player-box");

    for (let i = 1; i <= 6; i++) {
        const playerLoc = document.createElement("div");
        playerLoc.className = `player-box player-loc-${i}`;

        const playerFrame = document.createElement("img");
        playerFrame.className = "player-frame";
        playerFrame.id = `player-frame-${i}`;
        playerFrame.src = images["avatar-frame"];
        playerLoc.appendChild(playerFrame);

        const playerNameBox = document.createElement("img");
        playerNameBox.className = "player-name-box";
        playerNameBox.src = images["name-frame"];
        playerLoc.appendChild(playerNameBox);

        const playerPortrait = document.createElement("img");
        playerPortrait.className = "player-portrait";
        playerPortrait.id = `player-portrait-${i}`;
        playerPortrait.style.display = "none";
        playerPortrait.src = "empty.png";
        playerLoc.appendChild(playerPortrait);

        const playerRoleBox = document.createElement("img");
        playerRoleBox.className = "player-role-box";
        playerRoleBox.id = `player-role-box-${i}`;
        playerRoleBox.src = images["name-frame"];
        playerLoc.appendChild(playerRoleBox);

        const xMark = document.createElement("div");
        xMark.className = "x-mark";
        xMark.id = `x-mark-${i}`;
        xMark.style.display = "none";
        playerLoc.appendChild(xMark);

        const evilRing = document.createElement("div");
        evilRing.className = "evil-ring";
        evilRing.id = `evil-ring-${i}`;
        evilRing.style.display = "none";
        playerLoc.appendChild(evilRing);

        const goodRing = document.createElement("div");
        goodRing.className = "good-ring";
        goodRing.id = `good-ring-${i}`;
        goodRing.style.display = "none";
        playerLoc.appendChild(goodRing);

        const unknownRing = document.createElement("div");
        unknownRing.className = "unknown-ring";
        unknownRing.id = `unknown-ring-${i}`;
        unknownRing.style.display = "none";
        playerLoc.appendChild(unknownRing);

        const disconnected = document.createElement("div");
        disconnected.className = "disconnected";
        disconnected.id = `disconnected-${i}`;
        disconnected.style.display = "none";
        playerLoc.appendChild(disconnected);

        const crown = document.createElement("div");
        crown.className = "crown";
        crown.id = `crown-${i}`;
        crown.style.display = "none";
        playerLoc.appendChild(crown);

        const jester = document.createElement("div");
        jester.className = "jester";
        jester.id = `jester-${i}`;
        jester.style.display = "none";
        playerLoc.appendChild(jester);

        const shield = document.createElement("div");
        shield.className = "shield";
        shield.id = `shield-${i}`;
        shield.style.display = "none";
        playerLoc.appendChild(shield);

        const playerName = document.createElement("div");
        playerName.className = "player-name";
        playerName.id = `player-name-${i}`;
        playerName.innerText = "...";
        playerLoc.appendChild(playerName);

        const playerPredictedRole = document.createElement("div");
        playerPredictedRole.className = "player-predicted-role";
        playerPredictedRole.id = `player-predicted-role-${i}`;
        playerPredictedRole.innerText = "";
        playerLoc.appendChild(playerPredictedRole);

        const playerBelief = document.createElement("select");
        playerBelief.className = "player-belief";
        playerBelief.name = `player-${i}-belief`;
        playerBelief.id = `player-belief-${i}`;
        playerBelief.onchange = () => selectBelief(playerBelief.id);

        const optionUndecided = document.createElement("option");
        optionUndecided.value = "undecided";
        optionUndecided.innerText = "Undecided";
        playerBelief.appendChild(optionUndecided);

        const optGroupArthur = document.createElement("optgroup");
        optGroupArthur.label = "Arthur's Servants";
        optGroupArthur.className = "green";

        const optionMerlin = document.createElement("option");
        optionMerlin.value = "merlin";
        optionMerlin.innerText = "Merlin";
        optGroupArthur.appendChild(optionMerlin);

        const optionPercival = document.createElement("option");
        optionPercival.value = "percival";
        optionPercival.innerText = "Percival";
        optGroupArthur.appendChild(optionPercival);

        const optionServant = document.createElement("option");
        optionServant.value = "servant";
        optionServant.innerText = "Servant";
        optGroupArthur.appendChild(optionServant);

        playerBelief.appendChild(optGroupArthur);

        const optGroupMordred = document.createElement("optgroup");
        optGroupMordred.label = "Mordred's Servants";

        const optionAssassin = document.createElement("option");
        optionAssassin.value = "assassin";
        optionAssassin.innerText = "Assassin";
        optGroupMordred.appendChild(optionAssassin);

        const optionMorgana = document.createElement("option");
        optionMorgana.value = "morgana";
        optionMorgana.innerText = "Morgana";
        optGroupMordred.appendChild(optionMorgana);

        const optionMinion = document.createElement("option");
        optionMinion.value = "minion";
        optionMinion.innerText = "Minion";
        optGroupMordred.appendChild(optionMinion);

        playerBelief.appendChild(optGroupMordred);

        playerLoc.appendChild(playerBelief);
        playerBox?.appendChild(playerLoc);
    }
});

const ROOMNAME = "avalon_rerun";

async function main() {
    await gameClient.joinRoom(ROOMNAME);
}

main();
