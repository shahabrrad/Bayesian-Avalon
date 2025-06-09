import { auth } from "@colyseus/auth";
import fs from "fs";
import { readOrCreateFile } from "../utils/file-utils";

const userFile = "usersDB.json";
const FAKE_EMAIL_SUFFIX = "@NOTAREALEMAIL.com";

const filePath = `${process.cwd()}/${userFile}`;
let users: Record<string, string> = {};

fetchUsers(filePath).then((fetchedUsers) => {
  users = fetchedUsers;
});

auth.settings.onFindUserByEmail = async (email) => {
  return _findUser(email);
};

auth.settings.onRegisterWithEmailAndPassword = async function (
  email,
  password
) {
  return _registerUser(email, password);
};

function _findUser(email: string) {
  const username = email.split(FAKE_EMAIL_SUFFIX)[0];
  if (users[username]) {
    return { id: username, password: users[username] };
  }
}

function _registerUser(email: string, password: string) {
  const userName = email.split(FAKE_EMAIL_SUFFIX)[0];
  if (!users.userName) {
    try {
      users[userName] = password;
      fs.writeFileSync(filePath, JSON.stringify(users, null, 2));
    } catch (e) {
      //TODO: do something w this error probs
    }
  }
}

async function fetchUsers(filePath: string) {
  return await readOrCreateFile(filePath);
}
