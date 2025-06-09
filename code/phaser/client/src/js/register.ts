import {LoginClient} from "../utils/LoginClient";

const loginClient: LoginClient = new LoginClient();
const PASSWORD_LENGTH = 6;

document.addEventListener("DOMContentLoaded", (event) => {
  // Add a listener for the create game button
  document
    .getElementById("registration_btn")!
    .addEventListener("click", async (event) => {
      const username = `${
        (<HTMLInputElement>document.getElementById("username")).value
      }`;
      const password = (<HTMLInputElement>document.getElementById("password"))
        .value;
      const checkbox = <HTMLInputElement>document.getElementById("agree");

      if (!isValidForm(username, password, checkbox)) {
        return;
      }

      try {
        await loginClient.register({ username, password });
      } catch (e) {
        const element = document.getElementById("login-msg");
        if (element) {
          element.innerHTML = `${"Registration failed"}: ${e.message}`;
          element.style.display = "block";
        }
        return;
      }

      try {
        window.location.href = "lobby.html";
      } catch (e) {
        console.log(e);
      }
    });
});

function isValidForm(
  username: string,
  password: string,
  checkbox: HTMLInputElement
) {
  const isValidUser = verifyUsername(username);
  const isValidPass = verifyPassword(password);
  const isValidCheckbox = verifyCheckbox(checkbox);

  return isValidUser && isValidPass && isValidCheckbox;
}

function verifyCheckbox(checkbox: HTMLInputElement) {
  const error = <HTMLInputElement>document.getElementById("checkbox-error");
  toggleError(
    error,
    !checkbox.checked,
    "You must agree to the terms before continuing."
  );
  return checkbox.checked;
}

function verifyPassword(password: string) {
  const error = <HTMLInputElement>document.getElementById("password-error");
  try {
    checkLength("password", password, PASSWORD_LENGTH);
    toggleError(error, false);
    return true;
  } catch (e: any) {
    toggleError(error, true, e.message);
    return false;
  }
}

function verifyUsername(username: string) {
  const error = <HTMLInputElement>document.getElementById("username-error");
  try {
    checkLength("username", username);
    toggleError(error, false);
    return true;
  } catch (e) {
    toggleError(error, true, "Username is required. Must be alphanumeric");
  }
  return false;
}

function checkLength(type: string, str: string, length?: number) {
  if (!str) {
    throw new Error(`${type} cannot be empty`);
  }
  if (length && str.length < length) {
    throw new Error(`${type} must be at least ${length} characters`);
  }
}

function toggleError(
  element: HTMLInputElement,
  isVisible: boolean,
  text?: string
) {
  if (isVisible) {
    element.classList.remove("hidden");
    if (text) {
      element.innerText = text;
    }
  } else {
    element.classList.add("hidden");
  }
}
