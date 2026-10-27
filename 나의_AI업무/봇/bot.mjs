// 디스코드 연결부. 방 이름으로 역할을 구분하고, 캡틴(허용된 사용자 1명)의 메시지만 처리한다.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { Client, GatewayIntentBits, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { cfg, enqueue, startTask, resumeTask, decide, diagnose, LimitError } from './orchestrator.mjs';

// 토큰은 OneDrive 밖의 파일에서만 읽는다(클라우드에 올라가지 않게).
const ENV_FILE = process.env.AI_WORK_ENV || path.join(os.homedir(), '.ai-work-bot', '.env');
const env = {};
try {
  for (const line of fs.readFileSync(ENV_FILE, 'utf8').split(/\r?\n/)) {
    const m = /^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} catch {
  console.error(`설정 파일을 찾지 못했어요: ${ENV_FILE}\n봇_만들기_안내.md의 5번을 따라 만들어 주세요.`);
  process.exit(1);
}
for (const k of ['DISCORD_TOKEN', 'ALLOWED_USER_ID']) {
  if (!env[k]) { console.error(`${k} 값이 비어 있어요: ${ENV_FILE}`); process.exit(1); }
}

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });
const channelOf = (guild, roleKey) => guild.channels.cache.find((c) => c.name === cfg.roles[roleKey].channel && c.isTextBased());

function makeSay(guild) {
  return async (roleKey, text, opts = {}) => {
    const ch = channelOf(guild, roleKey) || channelOf(guild, 'secretary');
    if (!ch) return console.error('보낼 방이 없어요:', roleKey);
    const chunks = String(text).match(/[\s\S]{1,1900}/g) || [''];
    for (let i = 0; i < chunks.length; i++) {
      const payload = { content: chunks[i] };
      if (opts.approvalFor && i === chunks.length - 1) {
        const id = opts.approvalFor;
        payload.components = [new ActionRowBuilder().addComponents(
          new ButtonBuilder().setCustomId(`decide:${id}:approve`).setLabel('승인').setStyle(ButtonStyle.Success),
          new ButtonBuilder().setCustomId(`decide:${id}:revise`).setLabel('수정 요청').setStyle(ButtonStyle.Secondary),
          new ButtonBuilder().setCustomId(`decide:${id}:reject`).setLabel('반려').setStyle(ButtonStyle.Danger))];
      }
      await ch.send(payload);
    }
  };
}

let announced = false;
const onReady = () => {
  if (announced) return;
  announced = true;
  const have = (r) => (client.guilds.cache.some((g) => channelOf(g, r)) ? '있음' : '없음');
  console.log(`로그인: ${client.user.tag} / 들어가 있는 서버: ${client.guilds.cache.map((g) => g.name).join(', ') || '없음'}`);
  for (const [k, r] of Object.entries(cfg.roles)) console.log(`  #${r.channel}: ${have(k)}`);
  for (const g of client.guilds.cache.values())
    console.log(`  [${g.name}] 봇이 보는 글 방: ${g.channels.cache.filter((c) => c.isTextBased()).map((c) => '#' + c.name).join(' ') || '없음'}`);
};
client.once('ready', onReady);
client.once('clientReady', onReady);

client.on('messageCreate', (msg) => {
  if (msg.author.bot || msg.author.id !== env.ALLOWED_USER_ID || !msg.guild) return;
  const secretaryRoom = cfg.roles.secretary.channel;
  const text = msg.content.trim();
  const say = makeSay(msg.guild);
  if (msg.channel.name !== secretaryRoom) {
    if (Object.values(cfg.roles).some((r) => r.channel === msg.channel.name))
      msg.reply(`이 방은 비서가 지시를 전달하는 방이에요. #${secretaryRoom}에 말씀해 주세요.`).catch(() => {});
    return;
  }
  const id = /T-\d{4}/.exec(text)?.[0];
  if (id && /(왜|진단|원인|이상)/.test(text) && !/진행|수정:/.test(text)) return void enqueue(() => diagnose(id, text, say));
  if (id && /진행/.test(text)) return void enqueue(() => resumeTask(id, '', say));
  if (id && /수정\s*:/.test(text)) return void enqueue(() => resumeTask(id, text.split(/수정\s*:/)[1].trim(), say));
  if (text) enqueue(() => startTask(text, say)).catch((e) => console.error(e));
});

client.on('interactionCreate', async (i) => {
  if (!i.isButton() || i.user.id !== env.ALLOWED_USER_ID) return;
  const [, id, decision] = i.customId.split(':');
  await i.update({ components: [] }).catch(() => {});
  enqueue(() => decide(id, decision, makeSay(i.guild)));
});

client.login(env.DISCORD_TOKEN);
