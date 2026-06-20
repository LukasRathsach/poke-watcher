// Discord Interactions endpoint (slash commands + click-to-toggle set picker),
// hosted on Vercel. Instant replies; writes subscriptions to Supabase. The GitHub
// Actions cron reads the same tables to know who to @mention on a restock.
import { verifyKey, InteractionType, InteractionResponseType } from "discord-interactions";

const PUBLIC_KEY = process.env.DISCORD_PUBLIC_KEY;
const SB_URL = process.env.SUPABASE_URL;
const SB_KEY = process.env.SUPABASE_SERVICE_KEY;

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

const userId = (i) => i.member?.user?.id || i.user?.id;
const ephemeral = (content) => ({
  type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
  data: { content, flags: 64, allowed_mentions: { parse: [] } }, // 64 = only the caller sees it
});

async function allSets() {
  const r = await sb("pokewatcher_sets?select=token,label&order=label");
  return r.ok ? await r.json() : [];
}
async function userSets(uid) {
  const r = await sb(`pokewatcher_subscriptions?select=set_token&user_id=eq.${uid}`);
  return (r.ok ? await r.json() : []).map((x) => x.set_token);
}

// multi-select dropdown of all sets, with the user's current picks pre-checked.
// ponytail: Discord caps a select at 25 options; we have ~19. Paginate if it grows past 25.
function pickerRow(sets, selected) {
  return {
    type: 1, // action row
    components: [{
      type: 3, // string select
      custom_id: "setpicker",
      placeholder: "Vælg de sæt du vil følge",
      min_values: 0,
      max_values: Math.min(sets.length, 25),
      options: sets.slice(0, 25).map((s) => ({
        label: s.label,
        value: s.token,
        default: selected.includes(s.token),
      })),
    }],
  };
}

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

  // "Vælg dine sæt" button on the pinned intro -> open the picker (ephemeral, per-user)
  if (i.type === InteractionType.MESSAGE_COMPONENT && i.data.custom_id === "openpicker") {
    const uid = userId(i);
    const sets = await allSets();
    if (!sets.length) return res.json(ephemeral("Ingen sæt registreret endnu."));
    const selected = await userSets(uid);
    return res.json({
      type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
      data: {
        content: "Vælg de sæt du vil følge — du bliver tagget når de kommer på lager:",
        flags: 64,
        components: [pickerRow(sets, selected)],
      },
    });
  }

  // click-to-toggle: the dropdown submits the user's full selection -> set subs to match
  if (i.type === InteractionType.MESSAGE_COMPONENT && i.data.custom_id === "setpicker") {
    const uid = userId(i);
    const values = i.data.values || [];
    await sb(`pokewatcher_subscriptions?user_id=eq.${uid}`, { method: "DELETE" });
    if (values.length) {
      await sb("pokewatcher_subscriptions", {
        method: "POST",
        headers: { Prefer: "resolution=ignore-duplicates" },
        body: JSON.stringify(values.map((v) => ({ set_token: v, user_id: uid }))),
      });
    }
    const sets = await allSets();
    return res.json({
      type: 7, // UPDATE_MESSAGE — refresh the same ephemeral message
      data: {
        content: values.length
          ? "✅ Du følger nu disse sæt — klik for at ændre:"
          : "Du følger ingen sæt nu — klik for at vælge:",
        flags: 64,
        components: [pickerRow(sets, values)],
      },
    });
  }

  if (i.type === InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE) {
    const focused = (i.data.options?.find((o) => o.focused)?.value || "").toLowerCase();
    const sets = await allSets();
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
    const uid = userId(i);
    const arg = (n) => i.data.options?.find((o) => o.name === n)?.value;

    // /sets -> interactive click-to-toggle picker, pre-checked with the user's picks
    if (name === "sets") {
      const sets = await allSets();
      if (!sets.length) return res.json(ephemeral("Ingen sæt registreret endnu."));
      const selected = await userSets(uid);
      return res.json({
        type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: {
          content: "Vælg de sæt du vil følge — du bliver tagget når de kommer på lager:",
          flags: 64,
          components: [pickerRow(sets, selected)],
        },
      });
    }

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
      const mine = await userSets(uid);
      return res.json(ephemeral(
        mine.length ? "Du følger: " + mine.map((x) => `**${x}**`).join(", ")
                    : "Du følger ingen sæt endnu. Brug `/sets`."));
    }

    return res.json(ephemeral("Ukendt kommando."));
  }

  return res.status(400).send("unhandled interaction type");
}
