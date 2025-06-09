import { Room, Client } from "@colyseus/core";
import { AvalonLoginState } from "./schema/AvalonLoginState";
// import { JWT } from "@colyseus/auth"; // Remove the import for SignOptions
import JWT from 'jsonwebtoken';

interface LoginMessage {
  username: string;
  password: string;
}

const users: { [key: string]: string } = {
  'aa': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
  'bb': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d',
  // Add more users as needed
};

export class AvalonLogin extends Room<AvalonLoginState> {
  maxClients = 1;

  onCreate(options: any) {
    // this.setState(new AvalonLoginState()); // This causes issues...

    console.log('Login room created!');

    this.onMessage('login_request', (client: Client, message: LoginMessage) => {
      const { username, password } = message;
      // Check if the username exists and the password matches
      if (users[username] && users[username] === password) {
        const token = JWT.sign({ username }, 'merlinsbeard');
        console.log("Signed token:", token);
        client.send("login_result", { success: true, message: "Login successful!", token: token });
      } else {
        client.send("login_result", { success: false, message: "Invalid username or password!" });
      }
    });
  }

  onJoin(client: Client, options: any) {
    console.log(client.sessionId, 'joined the login room.');
  }

  onLeave(client: Client, consented: boolean) {
    console.log(client.sessionId, "left the login room!");
  }

  onDispose() {
    console.log("room", this.roomId, "disposing login room...");
  }

}

