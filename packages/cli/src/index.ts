#!/usr/bin/env node

/**
 * Honolulu CLI - Interactive AI Agent Assistant
 */

import { Command } from "commander";
import { HonoluluClient, AgentMessage } from "./client.js";
import { Spinner } from "./ui/spinner.js";
import {
  askConfirmation,
  getUserInput,
  displayAgentText,
  displayThinking,
  displayToolCall,
  displayToolResult,
  displayError,
  displayWelcome,
  displayGoodbye,
} from "./ui/prompt.js";

const program = new Command();

program
  .name("honolulu")
  .description("Honolulu - AI Agent Assistant CLI")
  .version("0.1.0");

program
  .option("-s, --server <url>", "Server URL", "http://127.0.0.1:8420")
  .option("-e, --execute <command>", "Execute a single command and exit")
  .action(async (options: { server: string; execute?: string }) => {
    const client = new HonoluluClient(options.server);
    const spinner = new Spinner();

    // Pending confirmations
    const pendingConfirmations = new Map<
      string,
      { toolName: string; args: Record<string, unknown> }
    >();

    async function handleMessage(msg: AgentMessage): Promise<void> {
      switch (msg.type) {
        case "thinking":
          spinner.start(msg.content || "Thinking...");
          break;

        case "text":
          spinner.stop();
          displayAgentText(msg.content || "");
          break;

        case "tool_call":
          spinner.stop();
          displayToolCall(msg.tool || "unknown", msg.args || {});

          if (msg.requires_confirmation) {
            // Store for confirmation handling
            pendingConfirmations.set(msg.id || "", {
              toolName: msg.tool || "",
              args: msg.args || {},
            });
          }
          break;

        case "confirm_request":
          spinner.stop();

          const pending = pendingConfirmations.get(msg.id || "");
          if (pending) {
            const result = await askConfirmation(pending.toolName, pending.args);
            client.sendConfirmResponse(
              msg.id || "",
              result.action,
              pending.toolName
            );
            pendingConfirmations.delete(msg.id || "");

            if (result.action !== "deny") {
              spinner.start("Executing...");
            }
          }
          break;

        case "tool_result":
          spinner.stop();
          displayToolResult(
            msg.tool || "unknown",
            (typeof msg.content === "object" && msg.content !== null
              ? msg.content
              : {}) as Record<string, unknown>
          );
          break;

        case "permission_denied":
          spinner.stop();
          displayError(`Permission denied: ${msg.reason}`);
          break;

        case "done":
          spinner.stop();
          break;

        case "error":
          spinner.stop();
          displayError(msg.content || "Unknown error");
          break;

        case "cancelled":
          spinner.stop();
          console.log("\nOperation cancelled.");
          break;
      }
    }

    // Single command mode
    if (options.execute) {
      try {
        const chatResponse = await client.startChat(options.execute);

        await new Promise<void>((resolve, reject) => {
          client.connect(
            chatResponse.session_id,
            async (msg) => {
              await handleMessage(msg);
              if (msg.type === "done" || msg.type === "error") {
                resolve();
              }
            },
            (error) => {
              displayError(error.message);
              reject(error);
            },
            () => {
              resolve();
            }
          );

          // Send the message after connecting
          setTimeout(() => {
            client.sendMessage(options.execute!);
          }, 100);
        });

        client.close();
        process.exit(0);
      } catch (error) {
        displayError(String(error));
        process.exit(1);
      }
    }

    // Interactive mode
    displayWelcome();

    try {
      // Start a session
      const chatResponse = await client.startChat("");

      let isConnected = false;
      let waitingForResponse = false;

      const messageQueue: AgentMessage[] = [];

      client.connect(
        chatResponse.session_id,
        async (msg) => {
          if (waitingForResponse) {
            await handleMessage(msg);
            if (msg.type === "done" || msg.type === "error") {
              waitingForResponse = false;
              promptUser();
            }
          } else {
            messageQueue.push(msg);
          }
        },
        (error) => {
          displayError(`Connection error: ${error.message}`);
          process.exit(1);
        },
        () => {
          if (isConnected) {
            console.log("\nConnection closed.");
            process.exit(0);
          }
        }
      );

      isConnected = true;

      async function promptUser(): Promise<void> {
        const input = await getUserInput();

        if (input.toLowerCase() === "exit" || input.toLowerCase() === "quit") {
          displayGoodbye();
          client.close();
          process.exit(0);
        }

        if (!input.trim()) {
          promptUser();
          return;
        }

        waitingForResponse = true;
        client.sendMessage(input);
      }

      // Start the prompt loop
      await promptUser();
    } catch (error) {
      displayError(`Failed to connect to server: ${error}`);
      console.log("\nMake sure the Honolulu server is running:");
      console.log("  cd packages/core && pip install -e . && honolulu-server");
      process.exit(1);
    }
  });

program
  .command("tools")
  .description("List available tools")
  .option("-s, --server <url>", "Server URL", "http://127.0.0.1:8420")
  .action(async (options: { server: string }) => {
    try {
      const client = new HonoluluClient(options.server);
      const tools = await client.getTools();
      console.log("\nAvailable tools:\n");
      for (const tool of tools as Array<{
        name: string;
        description: string;
      }>) {
        console.log(`  ${tool.name}`);
        console.log(`    ${tool.description}\n`);
      }
    } catch (error) {
      displayError(`Failed to get tools: ${error}`);
      process.exit(1);
    }
  });

program
  .command("config")
  .description("Show current configuration")
  .option("-s, --server <url>", "Server URL", "http://127.0.0.1:8420")
  .action(async (options: { server: string }) => {
    try {
      const client = new HonoluluClient(options.server);
      const config = await client.getConfig();
      console.log("\nCurrent configuration:\n");
      console.log(JSON.stringify(config, null, 2));
    } catch (error) {
      displayError(`Failed to get config: ${error}`);
      process.exit(1);
    }
  });

program.parse();
