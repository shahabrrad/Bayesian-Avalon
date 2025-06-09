import { Request } from "express";

declare module "express" {
  export interface Request {
    auth?: any; // Adjust the type as needed
  }
}
