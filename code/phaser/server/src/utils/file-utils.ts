const fs = require("fs").promises; // Use the promises API for async/await
// Add a static mutex for log writing
let logWriteMutex = false;
const logWriteQueue: Array<() => Promise<void>> = [];
// Define the initial content for the JSON file
const initialContent = {};

// Function to read or create the file and return its data
export async function readOrCreateFile(filePath: string) {
  try {
    // Attempt to read the file
    const data = await fs.readFile(filePath, "utf8");
    return JSON.parse(data); // Parse and return the JSON content
  } catch (err: any) {
    if (err.code === "ENOENT") {
      // File does not exist, create it
      console.log("File does not exist. Creating file...");
      await fs.writeFile(filePath, JSON.stringify(initialContent, null, 2));
      console.log("File created successfully with initial content!");
      return initialContent; // Return the initial content
    } else {
      // Some other error occurred
      console.error("Error reading file:", err);
      throw err; // Re-throw the error to handle it further up
    }
  }
}

// Function to append data to a JSON file
export async function writeLogData(data: any, roomId: string) {
  const filePath = `./logs/${roomId}.json`;
  try {
    // Read the existing file content
    const fileContent = await readOrCreateFile(filePath);

    // Append the new data
    fileContent.logs = fileContent.logs || [];
    fileContent.logs.push(data);

    // Write the updated content back to the file
    await fs.writeFile(filePath, JSON.stringify(fileContent, null, 2));
  } catch (err) {
    console.error("Failed to append data:", err);
  }
}

/**
 * Appends data to a JSON log file, ensuring writes are queued to avoid conflicts.
 * @param data - The data to append to the log.
 * @param roomId - The identifier for the log file.
 */
export async function appendLogData(data: any, roomId: string): Promise<void> {
  return new Promise<void>((resolve) => {
    logWriteQueue.push(async () => {
      try {
        const filePath = `./logs/${roomId}.json`;
        const fileContent = await readOrCreateFile(filePath);

        // Append the new data
        fileContent.logs = fileContent.logs || [];
        fileContent.logs.push(data);

        // Write the updated content back to the file
        await fs.writeFile(filePath, JSON.stringify(fileContent, null, 2));
      } catch (error) {
        console.error("Error appending log data:", error.message);
      } finally {
        resolve();
      }
    });

    // Ensure the queue is processed
    processLogWriteQueue();
  });
}

/**
 * Processes the log write queue to prevent concurrent writes.
 */
async function processLogWriteQueue() {
  if (logWriteMutex || logWriteQueue.length === 0) {
    return;
  }

  logWriteMutex = true;
  const nextOperation = logWriteQueue.shift();

  if (nextOperation) {
    await nextOperation();
  }

  logWriteMutex = false;
  if (logWriteQueue.length > 0) {
    processLogWriteQueue();
  }
}

// Run the function and handle the result
module.exports = {
  readOrCreateFile,
  appendLogData,
};
