/**
 * User prompts and input handling.
 */

import inquirer from "inquirer";
import chalk from "chalk";

export interface ConfirmResult {
  action: "allow" | "deny" | "allow_all";
}

/**
 * Ask user for confirmation before executing a tool.
 */
export async function askConfirmation(
  toolName: string,
  args: Record<string, unknown>
): Promise<ConfirmResult> {
  console.log();
  console.log(chalk.yellow("─".repeat(60)));
  console.log(chalk.yellow.bold("  Confirmation Required"));
  console.log(chalk.yellow("─".repeat(60)));
  console.log();
  console.log(chalk.white(`  Tool: ${chalk.cyan(toolName)}`));
  console.log(chalk.white("  Arguments:"));

  // Pretty print arguments
  for (const [key, value] of Object.entries(args)) {
    const valueStr =
      typeof value === "string"
        ? value.length > 100
          ? value.substring(0, 100) + "..."
          : value
        : JSON.stringify(value);
    console.log(chalk.gray(`    ${key}: ${valueStr}`));
  }

  console.log();

  const { action } = await inquirer.prompt<{ action: string }>([
    {
      type: "list",
      name: "action",
      message: "Allow this action?",
      choices: [
        { name: "Allow (this time only)", value: "allow" },
        { name: "Allow all (for this tool)", value: "allow_all" },
        { name: "Deny", value: "deny" },
      ],
    },
  ]);

  console.log(chalk.yellow("─".repeat(60)));
  console.log();

  return { action: action as "allow" | "deny" | "allow_all" };
}

/**
 * Get user input.
 */
export async function getUserInput(prompt: string = "You"): Promise<string> {
  const { input } = await inquirer.prompt<{ input: string }>([
    {
      type: "input",
      name: "input",
      message: chalk.green(prompt + ":"),
    },
  ]);

  return input;
}

/**
 * Display formatted text from the agent.
 */
export function displayAgentText(text: string): void {
  console.log(chalk.blue("\nHonolulu: ") + text);
}

/**
 * Display thinking indicator.
 */
export function displayThinking(text: string): void {
  console.log(chalk.gray(`\n${text}`));
}

/**
 * Display tool execution.
 */
export function displayToolCall(
  toolName: string,
  args: Record<string, unknown>
): void {
  console.log(chalk.magenta(`\n→ Calling: ${toolName}`));

  // Show abbreviated args
  const argsStr = JSON.stringify(args);
  if (argsStr.length > 100) {
    console.log(chalk.gray(`  ${argsStr.substring(0, 100)}...`));
  } else {
    console.log(chalk.gray(`  ${argsStr}`));
  }
}

/**
 * Display tool result.
 */
export function displayToolResult(
  toolName: string,
  result: Record<string, unknown>
): void {
  if (result.success) {
    console.log(chalk.green(`✓ ${toolName} completed`));
  } else {
    console.log(chalk.red(`✗ ${toolName} failed: ${result.error}`));
  }
}

/**
 * Display error.
 */
export function displayError(message: string): void {
  console.log(chalk.red(`\nError: ${message}`));
}

/**
 * Display welcome message.
 */
export function displayWelcome(): void {
  console.log();
  console.log(chalk.cyan("═".repeat(60)));
  console.log(chalk.cyan.bold("  🌋 Honolulu - AI Agent Assistant"));
  console.log(chalk.cyan("     by 易成 Kim"));
  console.log(chalk.cyan("═".repeat(60)));
  console.log();
  console.log(chalk.white("  我的能力包括："));
  console.log(chalk.gray("  📁 文件操作  💻 代码执行  🔍 网络搜索  🌐 网页抓取"));
  console.log();
  console.log(chalk.gray("  输入你的请求，按回车发送"));
  console.log(chalk.gray('  输入 "exit" 或 "quit" 退出'));
  console.log();
}

/**
 * Display goodbye message.
 */
export function displayGoodbye(): void {
  console.log();
  console.log(chalk.cyan("再见！期待下次为你服务 🌺"));
  console.log();
}
