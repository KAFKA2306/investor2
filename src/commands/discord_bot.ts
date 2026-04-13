import { type DiscordConfig, initializeDiscordBot } from "../io/discord";
import { config } from "./_config";

async function main() {
	const discordConfig: DiscordConfig = {
		enabled: config.integrations?.discord?.enabled ?? false,
		token:
			process.env[config.integrations?.discord?.tokenEnv ?? "DISCORD_TOKEN"] ??
			"",
		webhookUrl:
			process.env[
				config.integrations?.discord?.webhookUrlEnv ?? "DISCORD_WEBHOOK_URL"
			] ?? "",
		commandPrefix: config.integrations?.discord?.commandPrefix ?? "!",
		maxMessageLength: config.integrations?.discord?.maxMessageLength ?? 2000,
	};

	if (!discordConfig.enabled) {
		throw new Error("Discord integration is not enabled in config");
	}

	const bot = await initializeDiscordBot(discordConfig);

	process.on("SIGINT", async () => {
		await bot.stop();
		process.exit(0);
	});

	process.on("SIGTERM", async () => {
		await bot.stop();
		process.exit(0);
	});
}

main().catch((error) => {
	throw error;
});
