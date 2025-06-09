import { Client, Room } from "colyseus.js";
import { AvalonLobbyState, Player } from "../schema/AvalonLobbyState";
import { SERVER_URL } from "../utils/LoginClient";
// custom scene class
class AvalonLobby {
  client: Client;
  room: Room<AvalonLobbyState>;

  constructor(serverUrl: string) {
    this.client = new Client(serverUrl);
    console.log("Joining lobby...");
  }

  async joinRoom(roomName: string) {
    console.log("room name", roomName);
    try {
      const userData = await this.client.auth.getUserData();
      console.log(userData);
      this.room = await this.client.joinOrCreate<AvalonLobbyState>(roomName, {
        name: userData.user.id,
      });

      const playerNameElement = document.getElementById("player_name_box");
      if (playerNameElement) {
        playerNameElement.innerText = userData.user.id;
      }

      this.listAvailableRoomsWithRetry();
    } catch (e: any) {
      //TODO: better error handling -- some kind of error alert
      //401 you don't have the authorityyy
      console.log("YOU DO NOT BELONG HERE");
      console.error(e.message);
      logout();
    }

    this.room.onMessage("room_created", (message) => {
      const element = document.getElementById("login-msg");
      if (element) {
        element.innerHTML = `Game Created: ${message.roomId}`;
        element.style.display = "block";
      }
    });
  }

  createGameRoom(agents: string) {
    console.log("Creating game room with agents:", agents);
    this.room.send("create_game_room", JSON.stringify(agents));
  }

  async listAvailableRoomsWithRetry(retryInterval = 3000) {
    let foundRooms = false;

    while (!foundRooms) {
      try {
        const rooms = await this.client.getAvailableRooms("avalon_game"); // Replace with your room type
        console.log("Available rooms:", rooms);

        if (rooms.length === 0) {
          console.log(
            "❌ No available rooms found. Retrying in",
            retryInterval / 1000,
            "seconds..."
          );
          await new Promise((resolve) => setTimeout(resolve, retryInterval)); // Wait before retrying
        } else {
          foundRooms = true; // Stop retrying once rooms are available

          // ✅ Update UI
          const input = document.getElementById("game-id");
          if (input) {
            input.value = rooms[0].roomId;
          }

          const element = document.getElementById("join_game_button");
          if (element) {
            element.removeAttribute("disabled"); // Corrected: Enable button
          }

          const status = document.getElementById("game-state");
          if (status) {
            status.innerHTML = "Current Game:";
          }

          // ✅ Log available rooms
          rooms.forEach((room, index) => {
            console.log(
              `${index + 1}. Room ID: ${room.roomId}, Clients: ${
                room.clients
              }/${room.maxClients}`
            );
          });
        }
      } catch (err) {
        console.error("❌ Error fetching available rooms:", err);
        await new Promise((resolve) => setTimeout(resolve, retryInterval)); // Wait before retrying
      }
    }
  }
}

const roomName = "avalon_lobby";
const lobbyClient: AvalonLobby = new AvalonLobby(SERVER_URL);
lobbyClient.joinRoom(roomName);

document.addEventListener("DOMContentLoaded", (event) => {
  // Add a listener for the create game button
  document
    .getElementById("join_game_button")!
    .addEventListener("click", async (event) => {
      // get the value of the gam-id input element
      const game_id = (document.getElementById("game-id") as HTMLInputElement)
        .value;
      const playerNameElement = document.getElementById("player_name_box");
      const playerName = playerNameElement?.innerHTML;
      window.location.href = `game.html?cmode=j&roomID=${game_id}&playerName=${encodeURI(
        playerName || ""
      )}`;
    });

  document
    .getElementById("login-msg")!
    .addEventListener("click", async (event) => {
      const element = <HTMLInputElement>document.getElementById("game-id");
      if (element && event.target) {
        element.value = event.target.innerHTML.split(": ")[1];
      }
    });

  document
    .getElementById("logout_btn")
    ?.addEventListener("click", async (event) => {
      logout();
    });

  const helpButton = document.getElementById("help_button");
  if (helpButton) {
    console.log("Help button found");
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
});

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

const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const roomID = urlParams.get("roomID");
if (roomID) {
  document.getElementById("login-msg")!.innerHTML = `Game Created: ${roomID}`;
}

const logout = () => {
  lobbyClient.client.auth.signOut();
  window.location.href = "/";
};
