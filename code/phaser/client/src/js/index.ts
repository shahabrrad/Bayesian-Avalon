import {LoginClient} from "../utils/LoginClient";

const loginClient: LoginClient = new LoginClient();

document.addEventListener("DOMContentLoaded", (event) => {
  document
    .getElementById("login_button")!
    .addEventListener("click", async (event) => {
      const username = `${
        (<HTMLInputElement>document.getElementById("username")).value
      }`;
      const password = (<HTMLInputElement>document.getElementById("password"))
        .value;

      try {
        await loginClient.signIn({ username, password });
      } catch (e: any) {
        const element = document.getElementById("login-msg");
        if (element) {
          element.innerHTML = `${"Login failed"}-${e.message}`;
          element.style.display = "block";
        }
      }
    });
});
