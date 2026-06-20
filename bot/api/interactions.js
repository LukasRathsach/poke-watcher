// Discord Interactions endpoint (slash commands), hosted on Vercel.
// Instant replies; writes subscriptions to Supabase. The GitHub Actions cron reads
// the same tables to know who to @mention on a restock. No restock polling here.
import { verifyKey, InteractionType, InteractionResponseType } from "discord-interactions";

const PUBLIC_KEY = process.env.DISCORD_PUBLIC_KEY;
const SB_URL = process.env.SUPABASE_URL;
const SB_KEY = process.env.SUPABASE_SERVICE_KEY;

// raw body needed for signature verification
export const config = { api: { bodyParser: false } };

async function rawBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(typeof c === "string" ? Buffer.from(c) : c);
  return Buffer.concat(chunks).toString("utf8");
}

function sb(path, opts = {}) {
  return fetch(`${SB_URL}/rest/v1/${path}`, {
    ...opts,
    headers: {
      apikey: SB_KEY,
      Authorization: `Bearer ${SB_KEY}`,
      "Content-Type": "application/json",
      ...(opts.headers || {}),
    },
  });
}

const ephemeral = (content) => ({
  type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
  data: { content, flags: 64, allowed_mentions: { parse: [] } }, // flags 64 = only the caller sees it
});

export default async function handler(req, res) {
  const sig = req.headers["x-signature-ed25519"];
  const ts = req.headers["x-signature-timestamp"];
  const body = await rawBody(req);
  if (!sig || !ts || !(await verifyKey(body, sig, ts, PUBLIC_KEY))) {
    return res.status(401).send("invalid request signature");
  }
  const i = JSON.parse(body);

  if (i.type === InteractionType.PING) {
    return res.json({ type: InteractionResponseType.PONG });
  }

  if (i.type === InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE) {
    const focused = (i.data.options?.find((o) => o.focused)?.value || "").toLowerCase();
    const r = await sb("pokewatcher_sets?select=token,label&order=label");
    const sets = r.ok ? await r.json() : [];
    const choices = sets
      .filter((s) => s.label.toLowerCase().includes(focused) || s.token.includes(focused))
      .slice(0, 25)
      .map((s) => ({ name: s.label, value: s.token }));
    return res.json({
      type: InteractionResponseType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT,
      data: { choices },
    });
  }

  if (i.type === InteractionType.APPLICATION_COMMAND) {
    const name = i.data.name;
    const uid = i.member?.user?.id || i.user?.id;
    const arg = (n) => i.data.options?.find((o) => o.name === n)?.value;

    if (name === "track") {
      const token = (arg("set") || "").toLowerCase().trim();
      if (!token) return res.json(ephemeral("Angiv et sæt."));
      await sb("pokewatcher_subscriptions", {
        method: "POST",
        headers: { Prefer: "resolution=ignore-duplicates" },
        body: JSON.stringify({ set_token: token, user_id: uid }),
      });
      return res.json(ephemeral(`✅ Du følger nu **${token}** — du bliver tagget når det kommer på lager.`));
    }

    if (name === "untrack") {
      const token = (arg("set") || "").toLowerCase().trim();
      await sb(`pokewatcher_subscriptions?set_token=eq.${encodeURIComponent(token)}&user_id=eq.${uid}`, {
        method: "DELETE",
      });
      return res.json(ephemeral(`Du følger ikke længere **${token}**.`));
    }

    if (name === "mysets") {
      const r = await sb(`pokewatcher_subscriptions?select=set_token&user_id=eq.${uid}`);
      const rows = r.ok ? await r.json() : [];
      return res.json(ephemeral(
        rows.length ? "Du følger: " + rows.map((x) => `**${x.set_token}**`).join(", ")
                    : "Du følger ingen sæt endnu. Brug `/track`."));
    }

    if (name === "sets") {
      const r = await sb("pokewatcher_sets?select=label&order=label");
      const rows = r.ok ? await r.json() : [];
      return res.json(ephemeral(
        rows.length ? "Tilgængelige sæt:\n" + rows.map((x) => `• ${x.label}`).join("\n")
                    : "Ingen sæt registreret endnu."));
    }

    return res.json(ephemeral("Ukendt kommando."));
  }

  return res.status(400).send("unhandled interaction type");
}
