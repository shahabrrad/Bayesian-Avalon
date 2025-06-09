import axios, { AxiosError } from "axios";

// Define API request and response types
interface ApiResponse {
  success: boolean;
  message?: string;
  error?: Error;
}

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
  [key: string]: any;
}

type ApiResponseCallback = (error: Error | null, data?: any) => void;

const SERVER_LOCATION =
  process.env.AGENT_SERVICE_URL || "http://agentmanager:23003";
console.log("Agent Service URL:", SERVER_LOCATION);

// Retry utility function
async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 2,
  delayMs: number = 1000
): Promise<T> {
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;
      
      // Check if it's a retryable error
      // Just retry them all...
      // const isRetryable = 
      //   error instanceof AxiosError && 
      //   ((error as AxiosError).code === 'ECONNRESET' || 
      //    (error as Error).message.includes('socket hang up'));
      
      // if (!isRetryable || attempt === maxRetries) {
      if (attempt === maxRetries) {
        console.log(`Agent API max retries reached, throwing error:`, error);
        throw error;
      }
      
      if (error instanceof AxiosError) {
        console.log(`Retry attempt ${attempt + 1} after prior axios error:`, (error as AxiosError).code);
      } else {
        console.log(`Retry attempt ${attempt + 1} after prior error: Unknown error`);
      }
      
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
  
  throw lastError;
}

export async function callStartupApi(
  params: AgentStartupAPI
): Promise<ApiResponse> {
  const url = `${SERVER_LOCATION}/api/startup/`;
  console.log("Calling URL:", url);
  
  return withRetry(async () => {
    const response = await axios.get<ApiResponse>(url, { params });
    console.log("Response data:", response.data);
    return response.data.success
      ? response.data
      : { success: false, message: "API call failed" };
  });
}

export async function callShutdownAPI(params: AgentShutdownAPI): Promise<void> {
  const url = `${SERVER_LOCATION}/api/agent/${params.agent_id}/shutdown/`;
  
  return withRetry(async () => {
    const response = await axios.get<ApiResponse>(url, { params });
    if (!response.data.success) {
      console.error("Error shutting down agent:", response.data.message);
    }
  });
}

export async function callPrivateDataApi(
  agent_id: string,
  data: any
): Promise<boolean> {
  const url = `${SERVER_LOCATION}/api/agent/${agent_id}/private_data/`;
  
  return withRetry(async () => {
    const response = await axios.post<ApiResponse>(url, data, {
      headers: { "Content-Type": "application/json" },
    });
    return response.data.success;
  });
}

export async function callMessageApi(
  agent_id: string,
  message: any
): Promise<void> {
  const url = `${SERVER_LOCATION}/api/agent/${agent_id}/message/`;
  
  return withRetry(async () => {
    const response = await axios.post<ApiResponse>(url, message, {
      headers: { "Content-Type": "application/json" },
    });
    if (!response.data.success) {
      console.error("Error sending message:", response.data.message);
    }
  });
}

export async function callActionApi(
  agent_id: string,
  params: AgentTaskAPI,
  gameState: any,
  callback?: ApiResponseCallback
): Promise<any> {
  console.log(`agent ${agent_id} called with params ${JSON.stringify(params)}`);
  const url = `${SERVER_LOCATION}/api/agent/${agent_id}/action/`;
  
  // Keep the random delay before the retry mechanism
  await new Promise((resolve) =>
    setTimeout(resolve, Math.floor(Math.random() * 2000) + 1000)
  );
  
  return withRetry(async () => {
    // Format state similar to callStateUpdateApi
    const stateUpdate = {
      timestamp: new Date().toISOString(),
      changes: {},
      full: gameState
    };
    
    const payload = {
      task: params,
      state: stateUpdate
    };
    
    const response = await axios.post<ApiResponse>(url, payload, {
      headers: { "Content-Type": "application/json" },
    });
    
    if (callback) {
      callback(null, response.data);
    }
    return response.data;
  });
}

export async function callStateUpdateApi(
  agent_id: string,
  state_change: any
): Promise<void> {
  const url = `${SERVER_LOCATION}/api/agent/${agent_id}/state/`;
  
  return withRetry(async () => {
    const response = await axios.post<ApiResponse>(url, state_change, {
      headers: { "Content-Type": "application/json" },
    });
    if (!response.data.success) {
      console.error("Error sending state update:", response.data.message);
    }
  });
}
