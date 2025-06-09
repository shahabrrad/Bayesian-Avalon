import { Client, Room } from "colyseus.js";
import { AvalonLoginState } from "../schema/AvalonLoginState";

export const SERVER_URL = process.env.SERVER_URL || "http://localhost:2567";
const ROOM_NAME = "avalon_login";
export const FAKE_EMAIL_SUFFIX = "@NOTAREALEMAIL.com";
const EMAIL_ALREADY_IN_USER_ERR = "email_already_in_use";
const USER_ALREADY_IN_USE_ERR = "Username is taken. Please try a new username";
const EMAIL_MALFORMED = "email_malformed";
const USERNAME_MALFORMED = "Please enter an alphanumeric username";

export interface User {
  username: string;
  password: string;
}

export class LoginClient {
  client: Client;
  room: Room<AvalonLoginState>;

  constructor() {
    this.client = new Client(SERVER_URL);
    console.log("Joining login...");
  }

  async joinRoom() {
    try {
      this.room = await this.client.joinOrCreate<AvalonLoginState>(ROOM_NAME, {
        userId: localStorage.getItem("userId"),
      });
    } catch (e) {
      console.error("Error joining lobby", e);
    }
  }

  async signIn({ username, password }: User) {
    try {
      const signIn = await this.client.auth.signInWithEmailAndPassword(
        `${username}${FAKE_EMAIL_SUFFIX}`,
        password
      );
      if (!signIn) {
        return;
      }
      window.location.href = "lobby.html";
    } catch (e: any) {
      if (e.message == EMAIL_MALFORMED) {
        throw new Error(USERNAME_MALFORMED);
      }
      throw e;
    }
  }

  async register({ username, password }: User) {
    try {
      return await this.client.auth.registerWithEmailAndPassword(
        `${username}${FAKE_EMAIL_SUFFIX}`,
        password
      );
    } catch (e: any) {
      if (e.message == EMAIL_ALREADY_IN_USER_ERR) {
        throw new Error(USER_ALREADY_IN_USE_ERR);
      }
      if (e.message == EMAIL_MALFORMED) {
        throw new Error(USERNAME_MALFORMED);
      }
      throw e;
    }
  }
}

module.exports = {
  LoginClient: LoginClient,
  SERVER_URL: SERVER_URL,
};
