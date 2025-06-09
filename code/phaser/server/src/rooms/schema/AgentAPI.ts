interface AgentStartupAPI {
  game_id: string;
  agent_type: string;
  agent_role_preference: string;
  agent_name: string;
}

interface AgentShutdownAPI {
  agent_id: string;
}

interface AgentTaskAPI {
  task: string[];
  target_party_size: number;
  sequence: number;
}

type ApiResponseCallback = (error: Error | null, data?: any) => void;
interface ApiResponse {
  error?: Error | null;
  success?: boolean;
  agent_id?: string;
  agent_role_preference?: string;
  agent_name_preference?: string;
}

export {
  AgentTaskAPI,
  AgentStartupAPI,
  AgentShutdownAPI,
  ApiResponseCallback,
  ApiResponse,
};
