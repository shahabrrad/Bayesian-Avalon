import {Client, Room} from "colyseus.js";
import {AvalonAdminState, Player, Game} from "../schema/AvalonAdminState";
import {SERVER_URL} from "../utils/LoginClient";

const roles = [
    "Minion-1",
    "Minion-2",
    "Servant-1",
    "Servant-2",
    "Servant-3",
    "Servant-4",
];

class AvalonAdmin {
    client: Client;
    room: Room<AvalonAdminState>;
    assignedRoles: string[];

    constructor(serverUrl: string) {
        this.client = new Client(serverUrl);
    }

    async joinRoom(roomName: string) {
        try {
            const userData = await this.client.auth.getUserData();
            this.room = await this.client.joinOrCreate<AvalonAdminState>(roomName, {
                userId: localStorage.getItem("userId"),
                accessToken: localStorage.getItem("accessToken"),
                spectator: true
            });
        } catch (e: any) {
            //TODO: better error handling -- some kind of error alert
            //401 you don't have the authorityyy
            alert("YOU DO NOT BELONG HERE");
            console.error(e.message);
            this.logout();
        }

        this.room.onMessage("lobby_overview", (lobbies) => {
            this.updateLobbies(lobbies)
        });

        this.room.onMessage("game_overview", (rooms) => {
            this.updateGameRooms(rooms);
        });

        this.room.send("get_lobby_data", {})
        this.room.send("get_game_data", {})
    }

    updateGameRooms(rooms: any) {
        const roomList = document.getElementById("room_list");
        if (!roomList) return;

        roomList.innerHTML = ""; // Clear previous list

        rooms.forEach((room: { id: string }) => {
            const listItem = document.createElement("li");


            // Add the text as a span or text node
            const label = document.createElement("span");
            label.textContent = `${room.id}`;
            listItem.appendChild(label);

            // Create and style the button
            const joinBtn = document.createElement("input");
            joinBtn.type = "submit";
            joinBtn.className = "spectate-btn";
            joinBtn.name = "game-type";
            joinBtn.value = "Spectate";
            joinBtn.style.marginLeft = "10px"; // optional spacing
            joinBtn.addEventListener("click", () => {
                this.joinGameRoom(room.id);

                setTimeout(() => {
                    this.room.send("get_game_data", {})
                }, 500);
            });

            listItem.appendChild(joinBtn);
            roomList.appendChild(listItem);
        });
    }

    updateLobbies(lobbies: any) {
        const allPlayers: Player[] = [];
        lobbies.forEach((lobby: { roomId: string; players: Record<string, Player> }) => {
            for (const sessionId in lobby.players) {
                allPlayers.push(lobby.players[sessionId]);
            }
        });
        this.updatePlayerList(allPlayers);
    }

    updatePlayerList(players: any) {
        const lobbyPlayersElement = document.getElementById("lobby_players");
        if (!lobbyPlayersElement) return;

        lobbyPlayersElement.innerHTML = "";

        const roleDropdowns: HTMLSelectElement[] = [];

        players.forEach((player: Player) => {
            const listItem = document.createElement("li");
            listItem.innerText = `${player.name}: `;

            const roleSelect = document.createElement("select");
            roleSelect.style.marginLeft = "12px";
            roleSelect.style.height = "2rem";
            // Add the blank default option
            const blank = document.createElement("option");

            blank.value = "";
            blank.textContent = "-- Select Role --";
            blank.disabled = false;
            blank.selected = true;
            roleSelect.appendChild(blank);

            // Add role options
            roles.forEach((role) => {
                const option = document.createElement("option");
                option.value = role;
                option.textContent = role;
                roleSelect.appendChild(option);
            });

            roleDropdowns.push(roleSelect);
            listItem.appendChild(roleSelect);
            lobbyPlayersElement.appendChild(listItem);
        });

        // Update disabled states
        function updateDisabledRoles() {
            roleDropdowns.forEach((dropdown, index) => {
                // Collect selected roles from all other dropdowns
                const selectedByOthers = new Set<string>();
                roleDropdowns.forEach((d, i) => {
                    if (i !== index && d.value) {
                        selectedByOthers.add(d.value);
                    }
                });

                // Enable everything first
                Array.from(dropdown.options).forEach((option) => {
                    option.disabled = false;
                });

                // Now disable options that are selected elsewhere (but not the current selection)
                Array.from(dropdown.options).forEach((option) => {
                    if (option.value !== dropdown.value && selectedByOthers.has(option.value)) {
                        option.disabled = true;
                    }
                });
            });
        }

        // Attach change listeners
        roleDropdowns.forEach((dropdown) => {
            dropdown.addEventListener("change", updateDisabledRoles);
        });

        // Initial update
        updateDisabledRoles();
    }

    createGameRoom(agents: string) {
        this.room.send("create_game_room", agents);
    }

    joinGameRoom(roomId: string) {
        const input = document.getElementById("game-id");
        const playerName = 'admin'

        if (!roomId) {
            return;
        }
        window.location.href = `spectate.html?cmode=j&roomID=${roomId}&admin=true`
    }

    logout = () => {
        adminClient.client.auth.signOut();
        window.location.href = "/";
    };
}


document
    .getElementById("create_game_button")!
    .addEventListener("click", async (event) => {
        const agents: Array<{
            playerName?: string;
            role: string;
            player: string;
        }> = [];

        const selectedRoles = new Set<string>();
        let hasDuplicate = false;

        document.querySelectorAll("#lobby_players li").forEach((li) => {
            const playerName =
                li.firstChild?.textContent?.split(":")[0]?.trim() || "Unknown";
            const roleSelect = li.querySelector("select") as HTMLSelectElement;
            const selectedRole = roleSelect?.value || "random";

            if (selectedRoles.has(selectedRole)) {
                hasDuplicate = true;
            } else {
                selectedRoles.add(selectedRole);
            }

            agents.push({
                playerName,
                role: selectedRole,
                player: "human",
            });
        });

        if (hasDuplicate) {
            alert("Each player must have a unique role! Please fix duplicates.");
            return;
        }

        const assignedRoles = agents.map(agents => agents.role);
        const unassignedRoles = roles.filter(role => !assignedRoles.includes(role));

        unassignedRoles.map(role => {
            agents.push({
                    role: role,
                    player: "agent"
                }
            )
        })

        const playersJson = JSON.stringify(agents);

        const roomId = adminClient.createGameRoom(playersJson);

        const input = document.getElementById("game-id");
        if (input) {
            input.value = roomId;
        }
    });

document
    .getElementById("rerun_game_button")!
    .addEventListener("click", async (event) => {
        const game_id = (document.getElementById("game-id") as HTMLInputElement)
        .value;
        window.location.href = `rerun.html?roomID=${encodeURI(game_id)}`
    });

const roomName = "avalon_admin";
const adminClient: AvalonAdmin = new AvalonAdmin(SERVER_URL);
adminClient.joinRoom(roomName);