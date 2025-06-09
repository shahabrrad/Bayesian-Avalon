import { Client, Room } from "colyseus.js";
import { AvalonGameState, Message } from "../schema/AvalonGameState";
import Hashids from "hashids/cjs";
import * as images from "../img/*.png";
import { SERVER_URL } from "../utils/LoginClient";

class AvalonGameClient {
  client: Client;
  room: Room<AvalonGameState>;
  userId: string | null;
  hashids: Hashids;
  my_name: string;
  my_pid: number;
  proposed_party: Set<number> = new Set();
  my_role: any;
  my_knowledge: any;
  assassin_target_id: any;
  myTurn: boolean = false;

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
    const uniqueId = this.hashids.encode(seconds, milliseconds);
    return uniqueId;
  }

  handlePrivateData(callback: Function) {
    this.room.onMessage("private_data", (message) => {
      const { player } = message.data;
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

      // set up assassin stuff
      if (player.role.toLowerCase() === "assassin") {
        for (let i = 1; i <= this.room.state.players.length; i++) {
          // Check if the player with index i is in my_knowledge
          if (!player.knowledge[i] && player.id != i) {
            const element = document.getElementById(
              `player-predicted-role-${i}`
            );
            if (element) {
              element.innerHTML =
                '<span style="color: red;"><i>Assassinate</i></span>';
            }
            const element_2 = document.getElementById(`player-role-box-${i}`);
            if (element_2) {
              element_2.classList.add("brighten-on-hover");
              element_2.addEventListener("click", (event) => {
                // Cast the event target to an HTMLDivElement
                if (event && event.target) {
                  const divId = event.target as HTMLDivElement;
                  gameClient.processAssassination(divId.id);
                }
              });
            }
          }
        }
      }

      this.my_name = player.name;
      this.my_pid = player.id;
      this.my_role = player.role;
      this.my_knowledge = player.knowledge;
      callback();
    });
  }

  handleSpectatorData() {
    this.room.onMessage("spectator_data", (response) => {
      const { data } = response;
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

  async joinRoom(roomID: string, admin: boolean) {
    console.log("Joining room with ID:", roomID);
    try {
      this.room = await this.client.joinById<AvalonGameState>(roomID, {
        userId: localStorage.getItem("userId"),
        accessToken: localStorage.getItem("accessToken"),
        spectator: admin
      });
      // Store reconnection token and room ID before the window unloads
      window.onbeforeunload = () => {
        localStorage.setItem("reconnectionToken", this.room.reconnectionToken);
        localStorage.setItem("roomId", this.room.id);
      };
    } catch (e: any) {
      console.error("Error joining room", e);
      this.showErrorMessage(e.message);
      // logout();
    }

    this.handleSpectatorData();
    this.handlePrivateData(() => {
      handleStatechange(this.room.state);
    });

    // Initial update
    this.updatePlayerCount(this.room.state.players.length);

    // ********************** START BUTTONS ********************** //
    const end_turn_button = document.getElementById("end_turn_button");
    if (end_turn_button) {
      end_turn_button.addEventListener("click", () => {
        this.room.send("end_turn", { userId: this.userId });
      });
    }

    // Setup the internal listeners for the party proposal
    // if player-frame-N, player-portrait-N, evil-ring-N, or unknown-ring-N is clicked, toggle the shield-N element
    for (let i = 1; i <= 6; i++) {
      const player_frame = document.getElementById(`player-frame-${i}`);
      if (player_frame) {
        player_frame.addEventListener("click", () => {
          this.addToParty(i);
        });
      }
      const player_portret = document.getElementById(`player-portrait-${i}`);
      if (player_portret) {
        player_portret.addEventListener("click", () => {
          this.addToParty(i);
        });
      }
      const evil_ring = document.getElementById(`evil-ring-${i}`);
      if (evil_ring) {
        evil_ring.addEventListener("click", () => {
          this.addToParty(i);
        });
      }
      const unknown_ring = document.getElementById(`unknown-ring-${i}`);
      if (unknown_ring) {
        unknown_ring.addEventListener("click", () => {
          this.addToParty(i);
        });
      }
    }

    // Setup the listeners for the party proposal button
    const propose_party_button = document.getElementById("vote_confirm_button");
    if (propose_party_button) {
      propose_party_button.addEventListener("click", () => {
        this.room.send("propose_party", {
          party: Array.from(this.proposed_party),
          userId: this.userId,
        });
        // Also enable the vote_party button
        this.disableElement("vote_party_button", false);
        this.disableElement("end_turn_button", false)
      });
    }

    // Setup the listeners for initiating the party vote button
    const vote_party_button = document.getElementById("vote_party_button");
    if (vote_party_button) {
      vote_party_button.addEventListener("click", () => {
        this.room.send("vote_party", { userId: this.userId });
      });
    }

    const game_id_box = document.getElementById("game-id-box");
    if (game_id_box) {
      game_id_box.innerHTML = `Game ID: ${this.room.roomId}`;
    }

    // Enable the chat capability
    const message_box = document.getElementById(
      "text"
    ) as HTMLInputElement | null;
    if (message_box) {
      message_box.addEventListener("keypress", (e: KeyboardEvent) => {
        if (e.key === "Enter") {
          if (!this.myTurn) {
            return;
          }
          const message = message_box.value.trim();
          this.room.send("send_message", { msg: message, userId: this.userId });
          message_box.value = "";
        }
      });
    }

    // Vote yes and no buttons
    const vote_yes_button = document.getElementById("vote_yes_button");
    if (vote_yes_button) {
      vote_yes_button.addEventListener("click", () => {
        this.room.send("vote_result", { userId: this.userId, vote: true });
        this.disableElement("vote_yes_button", true);
        this.disableElement("vote_no_button", true);
      });
    }
    const vote_no_button = document.getElementById("vote_no_button");
    if (vote_no_button) {
      vote_no_button.addEventListener("click", () => {
        this.room.send("vote_result", { userId: this.userId, vote: false });
        this.disableElement("vote_yes_button", true);
        this.disableElement("vote_no_button", true);
      });
    }

    // Assassin choice event listeners
    const confirmYes = document.getElementById("confirmYes");
    const confirmNo = document.getElementById("confirmNo");
    const customDialog = document.getElementById("customDialog");

    if (confirmYes && confirmNo && customDialog) {
      confirmYes.addEventListener("click", () => {
        customDialog.classList.add("hidden");
        // Add the action you want to perform here
        this.room.send("assassination", {
          userId: this.userId,
          target: this.assassin_target_id,
        });
      });

      confirmNo.addEventListener("click", () => {
        customDialog.classList.add("hidden");
      });
    }

    // ********************** END BUTTONS ********************** //

    const handleTurnChange = (turn_pid: number) => {
      const prev = turn_pid > 1 ? turn_pid - 1 : 6;
      const prev_arrow = document.getElementById(`jester-${prev}`);
      if (prev_arrow) {
        prev_arrow.style.display = "none";
      }
      const new_arrow = document.getElementById(`jester-${turn_pid}`);
      if (new_arrow) {
        new_arrow.style.display = "block";
      }

      this.myTurn = this.my_pid === turn_pid;
      // Do the things we need to do when it turns out that it's our turn

      this.hideElement("end_turn_button", !this.myTurn || this.room.state.vote_party || this.room.state.vote_quest);
      this.hideElement("voting-task", true);
      this.hideElement("vote_yes_button", true);
      this.hideElement("vote_no_button", true);
      this.hideElement("vote_party_button", true);
      this.hideElement("vote_confirm_button", true);
      this.hideElement("vote_party_button", true);

      // enable message box
      // const message_box = document.getElementById(
      //   "text"
      // ) as HTMLInputElement | null;
      // if (message_box) {
      //   message_box.disabled = !myTurn;
      // }
      // update our proposed party so that we can alter an already proposed party (for example, if there was an auto party proposal)
      // otherwise our proposed party will start colliding wtih already proposed party
      if (this.room.state.turn_pid == this.room.state.leader_pid) {
        this.proposed_party = new Set(this.room.state.proposed_party);
      }
  
    };

    const handleLeaderChange = (leader_pid: number) => {
      const prev = leader_pid > 1 ? leader_pid - 1 : 6;

      const prev_crown = document.getElementById(`crown-${prev}`);
      if (prev_crown) {
        prev_crown.style.display = "none";
      }
      const new_crown = document.getElementById(`crown-${leader_pid}`);
      if (new_crown) {
        new_crown.style.display = "block";
      }
    };

    const proposeParty = () => {
      const canProposeParty = this.room.state.leader_pid === this.room.state.turn_pid &&
      !this.room.state.vote_party &&
      !this.room.state.vote_quest

      this.myTurn = this.my_pid === this.room.state.turn_pid
      {
        if (canProposeParty) {
          // For all shield-N elements, if they are in proposed_party, set them to display: block, else display: none
          for (let i = 1; i <= 6; i++) {
            this.toggleShield(i, this.room.state.proposed_party.includes(i));
          }

          if (!this.myTurn || !canProposeParty) {
            this.hideElement("voting-task", true);
            this.hideElement("vote_party_button", true);
            this.hideElement("vote_party_button", true);
            return;
          }

          this.hideElement("voting-task", false);
          const voting_task = document.getElementById("voting-task");
          if (voting_task) {
            voting_task.innerHTML = `Propose a party of ${this.room.state.target_party_size}!<br>Selected Size: ${this.proposed_party.size}/${this.room.state.target_party_size}`;
            // voting_task.style.display = "block";
          }
          this.hideElement("vote_confirm_button", false);
          this.hideElement("vote_party_button", false);
          if (
            this.room.state.proposed_party.length !=
            this.room.state.target_party_size
          ) {
            this.disableElement("vote_confirm_button", true);
            this.disableElement("vote_party_button", true);
            this.disableElement("end_turn_button", true);
          }
        } else if (!this.room.state.vote_party && !this.room.state.vote_quest) {
          this.hideElement("voting-task", true);
          this.hideElement("vote_yes_button", true);
          this.hideElement("vote_no_button", true);
          this.hideElement("vote_party_button", true);
          this.hideElement("vote_confirm_button", true);
          this.hideElement("vote_party_button", true);
        }
      }
    };

    const voteParty = (voteParty: boolean) => {
      if (!voteParty) {
        this.hideElement("vote_yes_button", true);
        this.hideElement("vote_no_button", true);
        this.hideElement("voting-task", true);
        return false;
      }
      this.hideElement('end_turn_button', true)
      this.hideElement("voting-task", false);
      this.hideElement("vote_yes_button", false);
      this.disableElement("vote_yes_button", false);
      this.hideElement("vote_no_button", false);
      this.disableElement("vote_no_button", false);
      this.hideElement("vote_party_button", true);
      this.hideElement("vote_confirm_button", true);
      this.hideElement("vote_party_button", true);
      const voting_task = document.getElementById("voting-task");
      if (voting_task) {
        voting_task.innerHTML = `Do you approve of the current party?`;
      }
      return true
    };

    const voteQuest = (voteQuest: boolean) => {
      {
        // if my_pid is not in this.room.state.proposed_party, hide the voting task
        // console.log("Quest Voting", this.room.state.proposed_party, this.my_pid);
        if (!this.room.state.proposed_party.includes(this.my_pid)) {
          return false;
        }

        if (!voteQuest) {
          this.hideElement("vote_yes_button", true);
          this.hideElement("vote_no_button", true);
          this.hideElement("voting-task", true);
          return false;
        }

        this.hideElement("end_turn_button", true)
        this.hideElement("voting-task", false);
        this.hideElement("vote_yes_button", false);
        this.disableElement("vote_yes_button", false);
        this.hideElement("vote_no_button", false);
        this.disableElement("vote_no_button", false);
        this.hideElement("vote_party_button", true);
        this.hideElement("vote_confirm_button", true);
        this.hideElement("vote_party_button", true);
        const voting_task = document.getElementById("voting-task");
        if (voting_task) {
          voting_task.innerHTML = `Do you wish to succeed the quest?`;
        }
        return true
      }
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

    // ********************** START LISTENERS ********************** //

    const handleStatechange = (state: AvalonGameState) => {
      handleTurnChange(state.turn_pid);
      handleLeaderChange(state.leader_pid);
      voteQuest(state.vote_quest) || voteParty(state.vote_party);
      proposeParty()
      handleFailedPartyVotes(state.failed_party_votes)
    };

    this.room.state.proposed_party.onAdd((player, key) => {
      // If it's not our turn, just show the current party
      if (this.room.state.turn_pid != this.my_pid) {
        for (let i = 1; i <= 6; i++) {
          this.toggleShield(i, this.room.state.proposed_party.includes(i));
        }
      }
    });

    this.room.state.players.onAdd((player, key) => {
      this.updatePlayerCount(this.room.state.players.length);
    });

    this.room.state.players.onRemove((player, key) => {
      this.updatePlayerCount(this.room.state.players.length);
    });

    // For all previous messages, add them to the chat
    this.room.state.messages.onAdd((message, key) => {
      this.addMessage(message);
    });

    // Listen for quest results
    this.room.state.quest_results.onAdd((result, key) => {
      // Loop over all of them and set the right images:
      for (let i = 1; i <= this.room.state.quest_results.length; i++) {
        const quest_result = document.getElementById(
          `quest-image-${i}`
        ) as HTMLImageElement;
        if (!quest_result) {
          continue;
        }
        quest_result.style.display = "block";
        quest_result.src =
          this.room.state.quest_results[i - 1] === "success"
            ? images["quest-success"]
            : images["quest-fail"];
      }
    });

    // Listen for changes in all_joined
    this.room.state.listen("all_joined", (currentValue, previousValue) => {
      // return if the value is false
      if (currentValue === false) {
        return;
      }

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
      this.room.state.players.forEach((player, index) => {
        // set player by loop index
        const playerElement = document.getElementById(
          `player-name-${index + 1}`
        );
        if (playerElement) {
          playerElement.innerHTML = player;
        }
      });
    });

    this.room.onStateChange((state) => {
      handleStatechange(state)
    })

    this.room.onMessage("game_over", (message) => {
      this.hideElement("end_turn_button", true)
      this.hideElement("voting-task", true);
      this.hideElement("vote_yes_button", true);
      this.disableElement("vote_yes_button", true);
      this.hideElement("vote_no_button", true);
      this.disableElement("vote_no_button", true);
      this.hideElement("vote_party_button", true);
      this.hideElement("vote_confirm_button", true);
      this.hideElement("vote_party_button", true);
    });

    // ********************** END LISTENERS ********************** //
  }

  async reconnect(reconnectionToken: string) {
    console.log("reconnecitng with token", reconnectionToken);
    try {
      this.room = await this.client.reconnect(reconnectionToken);
      console.log("Reconnected!");
    } catch (error) {
      console.error("Reconnection failed:", error);
      // Retry logic could be implemented here
    }
  }

  hideElement(buttonId: string, hide: boolean) {
    const button = document.getElementById(buttonId);
    if (button) {
      button.style.display = hide ? "none" : "block";
    }
  }

  disableElement(buttonId: string, state: boolean) {
    const button = document.getElementById(
      buttonId
    ) as HTMLButtonElement | null;
    if (button) {
      button.disabled = state;
    }
  }

  /** Used to add players to the proposed party */
  addToParty(player_position: number) {
    const canProposeParty = this.room.state.leader_pid === this.room.state.turn_pid &&
        !this.room.state.vote_party &&
        !this.room.state.vote_quest

    this.myTurn = this.my_pid === this.room.state.turn_pid

    if(!this.myTurn || !canProposeParty) {
      return
    }

    const shield = document.getElementById(`shield-${player_position}`);
    if (shield) {
      if (shield.style.display === "block") {
        this.proposed_party.delete(player_position);
        shield.style.display = "none";
      } else {
        if (this.proposed_party.size < this.room.state.target_party_size) {
          this.proposed_party.add(player_position);
          shield.style.display = "block";
        }
      }
    }

    // Update the voting task display
    const voting_task = document.getElementById("voting-task");
    if (voting_task) {
      voting_task.innerHTML = `Propose a party of ${this.room.state.target_party_size}!<br>Selected Size: ${this.proposed_party.size}/${this.room.state.target_party_size}`;
    }

    this.disableElement(
      "vote_confirm_button",
      this.proposed_party.size !== this.room.state.target_party_size
    );
    // Enable the vote party button if the player is the leader and this.proposed_party is the same as this.room.state.proposed_party
   
    const disable_end_turn_and_vote = !(
      this.my_pid === this.room.state.leader_pid &&
      this.arraysContainSameItems(
        Array.from(this.proposed_party),
        this.room.state.proposed_party
      ) &&
      this.proposed_party.size === this.room.state.target_party_size
    )
   
    this.disableElement(
      "vote_party_button",
      disable_end_turn_and_vote
    );

    this.disableElement("end_turn_button", disable_end_turn_and_vote)
  }

  /**used to toggle shield based on other player's party proposals */
  toggleShield(player_position: number, force?: boolean) {
    const shield = document.getElementById(`shield-${player_position}`);
    if (shield) {
      if (force !== undefined) {
        shield.style.display = force ? "block" : "none";
      } else {
        const canProposeParty = this.room.state.leader_pid === this.room.state.turn_pid &&
        this.my_pid === this.room.state.leader_pid &&
        !this.room.state.vote_party &&
        !this.room.state.vote_quest
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

    if (message.player === this.my_name) {
      iDiv.style.backgroundColor = "rgba(0, 255, 191, 0.3)";
    } else if (message.player === "system") {
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

  updatePlayerCount(playerCount: number) {
    const waitingElement = document.getElementById("waiting_a");
    if (waitingElement) {
      waitingElement.innerHTML = `<h3 style="text-align: center;">Waiting for players... (${playerCount}/6)</h3>`;
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

  arraysContainSameItems(arr1: number[], arr2: number[]): boolean {
    if (arr1.length !== arr2.length) {
      return false;
    }

    // Compare the sorted arrays
    for (let i = 0; i < arr1.length; i++) {
      // Check if arr2 contains the element
      if (arr2.indexOf(arr1[i]) === -1) {
        return false;
      }
    }
    return true;
  }

  processAssassination(id: string) {
    // convert id from string to integer by splitting it on "-" and taking the last element
    const target_id = parseInt(id.split("-").pop() || "", 10);
    const customDialog = document.getElementById("customDialog");
    const confirmText = document.getElementById("dialogMessage");

    if (customDialog && confirmText) {
      confirmText.innerHTML = `Are you sure that <i>${
        this.room.state.players[target_id - 1]
      }</i> is Merlin and that you want to assassinate them? <br><br>Note: Evil wins the game if you are correct, otherwise, Good wins.`;
      customDialog.classList.remove("hidden"); // Show the dialog
      this.assassin_target_id = target_id;
    }
    return target_id;
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
      console.log("Help button clicked");
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
    //playerFrame.onclick = (event) => selectedForParty(event);
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
    //playerPortrait.onclick = (event) => selectedForParty(event);
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

async function main() {
  const queryString = window.location.search;
  const urlParams = new URLSearchParams(queryString);
  const cmode = urlParams.get("cmode");
  if (cmode === "j") {
    const roomID = urlParams.get("roomID");
    if (roomID) {
      gameClient.joinRoom(roomID, false);
    }
  } else {
    console.log("No mode specified");
  }
}

const logout = () => {
  gameClient.client.auth.signOut();
  window.location.href = "/";
};

main();
