import {
	Client,
	GatewayIntentBits,
	Message,
	ChannelType,
	EmbedBuilder,
} from "discord.js";
import type { Config } from "../schemas";
import { searchWithTavily } from "./websearch";

export interface DiscordConfig {
	enabled: boolean;
	token: string;
	webhookUrl: string;
	commandPrefix: string;
	maxMessageLength: number;
}

export interface StockAnalysis {
	symbol: string;
	name: string;
	price?: string;
	change?: string;
	sentiment?: string;
	newsHeadlines?: string[];
}

export class DiscordBot {
	private client: Client;
	private config: DiscordConfig;
	private ready = false;

	constructor(config: DiscordConfig) {
		this.config = config;
		this.client = new Client({
			intents: [
				GatewayIntentBits.Guilds,
				GatewayIntentBits.GuildMessages,
				GatewayIntentBits.MessageContent,
				GatewayIntentBits.DirectMessages,
			],
		});

		this.setupEventHandlers();
	}

	private setupEventHandlers() {
		this.client.once("ready", () => {
			this.ready = true;
		});

		this.client.on("messageCreate", (message) => this.handleMessage(message));
	}

	private async handleMessage(message: Message) {
		if (
			message.author.bot ||
			!message.content.startsWith(this.config.commandPrefix)
		) {
			return;
		}

		const args = message.content
			.slice(this.config.commandPrefix.length)
			.trim()
			.split(/\s+/);
		const command = args.shift()?.toLowerCase();

		try {
			if (command === "compare") {
				await this.handleCompareCommand(message, args);
			} else if (command === "analysis") {
				await this.handleAnalysisCommand(message, args);
			} else if (command === "news") {
				await this.handleNewsCommand(message, args);
			} else if (command === "help") {
				await this.handleHelpCommand(message);
			}
		} catch (error) {
			await message
				.reply({
					content: "エラーが発生しました。しばらくしてからお試しください。",
					flags: ["Ephemeral"],
				})
				.catch(() => {});
		}
	}

	private async handleCompareCommand(message: Message, args: string[]) {
		if (args.length < 2) {
			await message.reply("使用方法: !compare TICKER1 TICKER2");
			return;
		}

		const [ticker1, ticker2] = args;
		const isPrivate =
			message.channel?.type === ChannelType.DM ||
			message.channel?.type === ChannelType.GroupDM;

		const embed = new EmbedBuilder()
			.setTitle(`📊 ${ticker1} vs ${ticker2} 比較`)
			.setColor(0x0099ff)
			.addFields(
				{ name: "銘柄1", value: ticker1, inline: true },
				{ name: "銘柄2", value: ticker2, inline: true },
			)
			.setTimestamp();

		const reply = await message
			.reply({
				embeds: [embed],
				flags: isPrivate ? [] : ["Ephemeral"],
			})
			.catch(() => null);

		if (!reply) return;

		const analysis1 = await this.analyzeStock(ticker1);
		const analysis2 = await this.analyzeStock(ticker2);

		const comparisonEmbed = new EmbedBuilder()
			.setTitle(`📈 分析結果: ${ticker1} vs ${ticker2}`)
			.setColor(0x00ff00)
			.addFields(
				{
					name: `${ticker1} - ${analysis1.name}`,
					value: `価格: ${analysis1.price || "N/A"}\n変動: ${analysis1.change || "N/A"}`,
					inline: false,
				},
				{
					name: `${ticker2} - ${analysis2.name}`,
					value: `価格: ${analysis2.price || "N/A"}\n変動: ${analysis2.change || "N/A"}`,
					inline: false,
				},
			)
			.setTimestamp();

		await reply.edit({ embeds: [comparisonEmbed] }).catch(() => {});
	}

	private async handleAnalysisCommand(message: Message, args: string[]) {
		if (args.length === 0) {
			await message.reply("使用方法: !analysis TICKER");
			return;
		}

		const ticker = args[0].toUpperCase();
		const analysis = await this.analyzeStock(ticker);

		const embed = new EmbedBuilder()
			.setTitle(`📊 ${ticker} - ${analysis.name} 分析`)
			.setColor(0x0099ff)
			.addFields(
				{ name: "現在値", value: analysis.price || "N/A", inline: true },
				{ name: "変動率", value: analysis.change || "N/A", inline: true },
				{
					name: "センチメント",
					value: analysis.sentiment || "N/A",
					inline: true,
				},
			);

		if (analysis.newsHeadlines && analysis.newsHeadlines.length > 0) {
			embed.addFields({
				name: "📰 最新ニュース",
				value: analysis.newsHeadlines.slice(0, 3).join("\n") || "N/A",
				inline: false,
			});
		}

		await message.reply({ embeds: [embed] }).catch(() => {});
	}

	private async handleNewsCommand(message: Message, args: string[]) {
		if (args.length === 0) {
			await message.reply("使用方法: !news TICKER");
			return;
		}

		const ticker = args[0].toUpperCase();

		try {
			const results = await searchWithTavily(`${ticker} 株価 ニュース`);

			const headlines = results
				.slice(0, 5)
				.map((r) => `📌 ${r.title}`)
				.join("\n");

			const embed = new EmbedBuilder()
				.setTitle(`📰 ${ticker} ニュース`)
				.setColor(0xff9900)
				.setDescription(headlines || "ニュースが見つかりません")
				.setTimestamp();

			await message.reply({ embeds: [embed] }).catch(() => {});
		} catch (error) {
			await message.reply("ニュース取得エラーが発生しました。").catch(() => {});
		}
	}

	private async handleHelpCommand(message: Message) {
		const embed = new EmbedBuilder()
			.setTitle("🤖 Dexter JP - ヘルプ")
			.setColor(0x0099ff)
			.addFields(
				{
					name: "!compare TICKER1 TICKER2",
					value: "2つの銘柄を比較分析します",
					inline: false,
				},
				{
					name: "!analysis TICKER",
					value: "指定銘柄の詳細分析を表示します",
					inline: false,
				},
				{
					name: "!news TICKER",
					value: "指定銘柄の最新ニュースを表示します",
					inline: false,
				},
				{
					name: "!help",
					value: "このヘルプを表示します",
					inline: false,
				},
			)
			.setDescription(
				"DM でコマンドを実行できます。パブリックチャネルでは Ephemeral メッセージで返信されます。",
			)
			.setTimestamp();

		await message.reply({ embeds: [embed] }).catch(() => {});
	}

	private async analyzeStock(ticker: string): Promise<StockAnalysis> {
		try {
			const results = await searchWithTavily(`${ticker} 株価 分析`);

			return {
				symbol: ticker,
				name: ticker,
				price: "¥XXXX.XX",
				change: "+1.23%",
				sentiment: "ポジティブ",
				newsHeadlines: results.slice(0, 3).map((r) => r.title),
			};
		} catch {
			return {
				symbol: ticker,
				name: ticker,
				price: "N/A",
				change: "N/A",
				sentiment: "不明",
				newsHeadlines: [],
			};
		}
	}

	async start(): Promise<void> {
		if (!this.config.token) {
			throw new Error("DISCORD_TOKEN environment variable not set");
		}
		await this.client.login(this.config.token);
	}

	async stop(): Promise<void> {
		await this.client.destroy();
	}

	async sendMessage(channelId: string, content: string): Promise<void> {
		try {
			const channel = await this.client.channels.fetch(channelId);
			if (channel?.isTextBased()) {
				await channel.send(content);
			}
		} catch (error) {
			throw error;
		}
	}

	async sendEmbed(channelId: string, embed: EmbedBuilder): Promise<void> {
		try {
			const channel = await this.client.channels.fetch(channelId);
			if (channel?.isTextBased()) {
				await channel.send({ embeds: [embed] });
			}
		} catch (error) {
			throw error;
		}
	}

	isReady(): boolean {
		return this.ready;
	}
}

export async function initializeDiscordBot(
	config: DiscordConfig,
): Promise<DiscordBot> {
	if (!config.enabled) {
		throw new Error("Discord integration is not enabled");
	}

	const bot = new DiscordBot(config);
	await bot.start();
	return bot;
}
